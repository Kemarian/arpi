#!/usr/bin/env python3
import base64
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI


def load_config() -> tuple[str, str, str, Path, Optional[str], bool]:
    load_dotenv(Path(__file__).parent / ".env")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Put it in arpi/.env or shell env.")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    prompt = os.getenv(
        "ARPI_PROMPT",
        "Describe what you see in this image in 3 concise bullet points.",
    ).strip()
    image_dir = Path(os.getenv("ARPI_IMAGE_DIR", "captures")).expanduser()
    if not image_dir.is_absolute():
        image_dir = Path(__file__).parent / image_dir
    image_dir.mkdir(parents=True, exist_ok=True)

    input_device = os.getenv("ARPI_INPUT_DEVICE", "").strip() or None
    rotate_180 = os.getenv("ARPI_ROTATE_180", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    return api_key, model, prompt, image_dir, input_device, rotate_180


def wait_for_keypress() -> str:
    print("\nPress any key to capture and analyze image. Press 'q' to quit.")
    if not sys.stdin.isatty():
        input("Press Enter to continue...")
        return "\n"

    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def wait_for_hid_button(input_device_path: str) -> str:
    try:
        from evdev import InputDevice, ecodes
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"evdev is required for ARPI_INPUT_DEVICE mode: {exc}. "
            "Install python3-evdev."
        )

    try:
        dev = InputDevice(input_device_path)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Cannot open input device '{input_device_path}': {exc}. "
            "Check ARPI_INPUT_DEVICE and permissions."
        )

    print(
        f"\nListening on {input_device_path}. "
        "Press remote button to capture (Ctrl+C to quit)."
    )
    try:
        for event in dev.read_loop():
            if event.type != ecodes.EV_KEY:
                continue
            if event.value != 1:
                continue
            key_name = ecodes.KEY.get(event.code, f"KEY_{event.code}")
            if isinstance(key_name, list):
                key_name = key_name[0]
            print(f"Detected key: {key_name}")
            return str(key_name)
    finally:
        dev.close()


def wait_for_trigger(input_device_path: Optional[str]) -> str:
    if input_device_path:
        return wait_for_hid_button(input_device_path)
    return wait_for_keypress()


class CameraSession:
    def __init__(self, rotate_180: bool = False) -> None:
        self.backend: Optional[str] = None
        self.cam = None
        self.rotate_180 = rotate_180
        self._init_camera()

    def _init_camera(self) -> None:
        init_errors = []

        try:
            from picamera2 import Picamera2

            cam = Picamera2()
            if self.rotate_180:
                from libcamera import Transform

                transform = Transform(hflip=1, vflip=1)
                config = cam.create_still_configuration(
                    main={"size": (1920, 1080)},
                    transform=transform,
                )
            else:
                config = cam.create_still_configuration(main={"size": (1920, 1080)})
            cam.configure(config)
            cam.start()
            # Warm up once at startup so button-trigger capture is fast.
            time.sleep(0.7)
            self.cam = cam
            self.backend = "picamera2"
            return
        except Exception as exc:  # noqa: BLE001
            init_errors.append(f"picamera2 init failed: {exc}")

        try:
            from picamera import PiCamera

            cam = PiCamera()
            if self.rotate_180:
                cam.rotation = 180
            time.sleep(1.5)
            self.cam = cam
            self.backend = "picamera"
            return
        except Exception as exc:  # noqa: BLE001
            init_errors.append(f"picamera init failed: {exc}")

        raise RuntimeError(" | ".join(init_errors))

    def capture(self, output_path: Path) -> None:
        if self.backend == "picamera2":
            self.cam.capture_file(str(output_path))
            return
        if self.backend == "picamera":
            self.cam.capture(str(output_path))
            return
        raise RuntimeError("Camera backend is not initialized.")

    def close(self) -> None:
        if self.cam is None:
            return
        try:
            self.cam.close()
        finally:
            self.cam = None


def to_data_url(image_path: Path) -> str:
    image_bytes = image_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    suffix = image_path.suffix.lower()
    if suffix == ".png":
        mime_type = "image/png"
    else:
        mime_type = "image/jpeg"
    return f"data:{mime_type};base64,{encoded}"


def analyze_image(client: OpenAI, model: str, prompt: str, image_path: Path) -> str:
    data_url = to_data_url(image_path)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        temperature=0.2,
    )
    message = response.choices[0].message
    content: Optional[str] = message.content
    return content or "(no response content)"


def main() -> int:
    try:
        api_key, model, prompt, image_dir, input_device, rotate_180 = load_config()
    except Exception as exc:  # noqa: BLE001
        print(f"Config error: {exc}")
        return 1

    client = OpenAI(api_key=api_key)
    print(f"Model: {model}")
    print(f"Image dir: {image_dir}")
    print(f"Trigger mode: {'hid' if input_device else 'terminal'}")
    if input_device:
        print(f"Input device: {input_device}")
    print(f"Rotate 180: {rotate_180}")

    print("Initializing camera...")
    try:
        camera = CameraSession(rotate_180=rotate_180)
    except Exception as exc:  # noqa: BLE001
        print(f"Camera init error: {exc}")
        return 1
    print(f"Camera ready (backend: {camera.backend}).")

    try:
        while True:
            key = wait_for_trigger(input_device)
            if key.lower() == "q":
                print("Exiting.")
                return 0

            filename = datetime.now().strftime("capture_%Y%m%d_%H%M%S.jpg")
            image_path = image_dir / filename
            print(f"Capturing: {image_path}")

            try:
                camera.capture(image_path)
                print("Captured. Sending to OpenAI...")
                result = analyze_image(client, model, prompt, image_path)
                print("\n--- GPT RESULT ---")
                print(result)
                print("--- END ---")
            except Exception as exc:  # noqa: BLE001
                print(f"Error: {exc}")
    finally:
        camera.close()


if __name__ == "__main__":
    raise SystemExit(main())
