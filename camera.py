"""Camera abstraction — captures images via picamera2 or legacy picamera."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Protocol

log = logging.getLogger(__name__)


class Camera(Protocol):
    """Minimal camera interface."""

    def capture(self, output_path: Path) -> None: ...
    def close(self) -> None: ...
    @property
    def is_ready(self) -> bool: ...


class PiCameraSession:
    """Concrete camera using picamera2 (preferred) or legacy picamera."""

    def __init__(self, rotate_180: bool = False) -> None:
        self._backend: str | None = None
        self._cam: object | None = None
        self._rotate_180 = rotate_180
        self._init_camera()

    # ── Protocol properties ──────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._cam is not None

    @property
    def backend_name(self) -> str:
        return self._backend or "none"

    # ── Public API ───────────────────────────────────────────────────────

    def capture(self, output_path: Path) -> None:
        if self._backend == "picamera2":
            self._cam.capture_file(str(output_path))  # type: ignore[union-attr]
            return
        if self._backend == "picamera":
            self._cam.capture(str(output_path))  # type: ignore[union-attr]
            return
        raise RuntimeError("Camera backend is not initialized.")

    def close(self) -> None:
        if self._cam is None:
            return
        try:
            self._cam.close()  # type: ignore[union-attr]
        finally:
            self._cam = None
            self._backend = None

    # ── Initialization ───────────────────────────────────────────────────

    def _init_camera(self) -> None:
        errors: list[str] = []

        if self._try_picamera2(errors):
            return
        if self._try_picamera_legacy(errors):
            return

        raise RuntimeError(" | ".join(errors))

    def _try_picamera2(self, errors: list[str]) -> bool:
        try:
            from picamera2 import Picamera2  # type: ignore[import-untyped]

            cam = Picamera2()
            if self._rotate_180:
                from libcamera import Transform  # type: ignore[import-untyped]
                transform = Transform(hflip=1, vflip=1)
                config = cam.create_still_configuration(
                    main={"size": (1920, 1080)}, transform=transform,
                )
            else:
                config = cam.create_still_configuration(main={"size": (1920, 1080)})
            cam.configure(config)
            cam.start()
            time.sleep(0.7)  # warm-up
            self._cam = cam
            self._backend = "picamera2"
            log.info("Camera ready (picamera2)")
            return True
        except Exception as exc:  # noqa: BLE001
            errors.append(f"picamera2: {exc}")
            return False

    def _try_picamera_legacy(self, errors: list[str]) -> bool:
        try:
            from picamera import PiCamera  # type: ignore[import-untyped]

            cam = PiCamera()
            if self._rotate_180:
                cam.rotation = 180
            time.sleep(1.5)
            self._cam = cam
            self._backend = "picamera"
            log.info("Camera ready (legacy picamera)")
            return True
        except Exception as exc:  # noqa: BLE001
            errors.append(f"picamera: {exc}")
            return False
