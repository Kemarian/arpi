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


def load_config() -> tuple[str, str, str, Path, Optional[str]]:
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

    return api_key, model, prompt, image_dir, input_device


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


def capture_image(output_path: Path) -> None:
    capture_errors = []

    try:
        from picamera2 import Picamera2

        cam = Picamera2()
        config = cam.create_still_configuration(main={"size": (1920, 1080)})
        cam.configure(config)
        cam.start()
        time.sleep(1.0)
        cam.capture_file(str(output_path))
        cam.close()
        return
    except Exception as exc:  # noqa: BLE001
        capture_errors.append(f"picamera2 failed: {exc}")

    try:
        from picamera import PiCamera

        cam = PiCamera()
        time.sleep(2.0)
        cam.capture(str(output_path))
        cam.close()
        return
    except Exception as exc:  # noqa: BLE001
        capture_errors.append(f"picamera failed: {exc}")

    raise RuntimeError(" | ".join(capture_errors))


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
        api_key, model, prompt, image_dir, input_device = load_config()
    except Exception as exc:  # noqa: BLE001
        print(f"Config error: {exc}")
        return 1

    client = OpenAI(api_key=api_key)
    print(f"Model: {model}")
    print(f"Image dir: {image_dir}")
    print(f"Trigger mode: {'hid' if input_device else 'terminal'}")
    if input_device:
        print(f"Input device: {input_device}")

    while True:
        key = wait_for_trigger(input_device)
        if key.lower() == "q":
            print("Exiting.")
            return 0

        filename = datetime.now().strftime("capture_%Y%m%d_%H%M%S.jpg")
        image_path = image_dir / filename
        print(f"Capturing: {image_path}")

        try:
            capture_image(image_path)
            print("Captured. Sending to OpenAI...")
            result = analyze_image(client, model, prompt, image_path)
            print("\n--- GPT RESULT ---")
            print(result)
            print("--- END ---")
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
