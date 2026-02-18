"""HID button listener — runs in a background thread, triggers the vision pipeline."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analyzer import VisionAnalyzer
    from camera import Camera
    from prompts import VisionPrompt
    from state import AppState

log = logging.getLogger(__name__)


class ButtonListener:
    """Listens for HID key events and triggers capture → analyze → store.

    Runs the evdev read loop in a daemon thread.
    On each button press: camera.capture → analyzer.analyze → state.mark_ready.
    """

    def __init__(
        self,
        input_device_path: str,
        camera: Camera,
        analyzer: VisionAnalyzer,
        prompt: VisionPrompt,
        image_dir: Path,
        app_state: AppState,
    ) -> None:
        self._device_path = input_device_path
        self._camera = camera
        self._analyzer = analyzer
        self._prompt = prompt
        self._image_dir = image_dir
        self._state = app_state
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def prompt(self) -> VisionPrompt:
        return self._prompt

    @prompt.setter
    def prompt(self, value: VisionPrompt) -> None:
        self._prompt = value

    def start(self) -> None:
        """Start listening in a daemon thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="button")
        self._thread.start()
        log.info("Button listener started on %s", self._device_path)

    def stop(self) -> None:
        self._stop_event.set()

    # ── Internal ─────────────────────────────────────────────────────────

    def _run(self) -> None:
        try:
            from evdev import InputDevice, ecodes  # type: ignore[import-untyped]
        except ImportError:
            log.error("evdev not installed — button listener disabled")
            self._state.set_button_ok(False)
            return

        try:
            dev = InputDevice(self._device_path)
        except Exception as exc:  # noqa: BLE001
            log.error("Cannot open %s: %s", self._device_path, exc)
            self._state.set_button_ok(False)
            return

        self._state.set_button_ok(True)
        log.info("Listening on %s (%s)", dev.path, dev.name)

        try:
            for event in dev.read_loop():
                if self._stop_event.is_set():
                    break
                if event.type == ecodes.EV_KEY and event.value == 1:
                    key_name = ecodes.KEY.get(event.code, f"KEY_{event.code}")
                    if isinstance(key_name, list):
                        key_name = key_name[0]
                    log.info("Button press: %s", key_name)
                    self._on_trigger()
        except Exception:  # noqa: BLE001
            log.exception("Button listener crashed")
            self._state.set_button_ok(False)
        finally:
            dev.close()

    def _on_trigger(self) -> None:
        """Handle a single button press: capture → analyze → store."""
        if self._state.pipeline_status.value == "processing":
            log.warning("Already processing — ignoring button press")
            return

        self._state.mark_processing()
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        filename = datetime.now().strftime("capture_%Y%m%d_%H%M%S.jpg")
        image_path = self._image_dir / filename

        try:
            log.info("Capturing: %s", image_path)
            self._camera.capture(image_path)

            result_text = self._analyzer.analyze(image_path, self._prompt)
            self._state.mark_ready(text=result_text, timestamp=timestamp)
            log.info("Result stored (%d chars)", len(result_text))
        except Exception as exc:  # noqa: BLE001
            log.exception("Pipeline error")
            self._state.mark_error(str(exc))
