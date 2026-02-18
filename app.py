"""Application entry point — wires modules together and starts the server."""

from __future__ import annotations

import logging
import sys

from analyzer import VisionAnalyzer
from button import ButtonListener
from camera import PiCameraSession
from config import AppConfig
from prompts import DEFAULT_PROMPT
from server import create_app
from state import AppState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger(__name__)


def main() -> int:
    # ── 1. Load config ───────────────────────────────────────────────────
    try:
        cfg = AppConfig.from_env()
    except RuntimeError as exc:
        log.error("Config error: %s", exc)
        return 1

    log.info("Model: %s", cfg.openai_model)
    log.info("Image dir: %s", cfg.image_dir)
    log.info("Rotate 180: %s", cfg.rotate_180)
    log.info("Server: %s:%d", cfg.server_host, cfg.server_port)

    # ── 2. Initialise components ─────────────────────────────────────────
    app_state = AppState()

    # Camera
    log.info("Initializing camera…")
    try:
        camera = PiCameraSession(rotate_180=cfg.rotate_180)
        app_state.set_camera_ok(True)
    except RuntimeError as exc:
        log.error("Camera init failed: %s", exc)
        app_state.set_camera_ok(False)
        return 1

    # Analyzer
    analyzer = VisionAnalyzer(api_key=cfg.openai_api_key, model=cfg.openai_model)

    # Button listener (optional — only if device configured)
    listener: ButtonListener | None = None
    if cfg.input_device:
        listener = ButtonListener(
            input_device_path=cfg.input_device,
            camera=camera,
            analyzer=analyzer,
            prompt=DEFAULT_PROMPT,
            image_dir=cfg.image_dir,
            app_state=app_state,
        )
        listener.start()
        log.info("Button listener: %s", cfg.input_device)
    else:
        log.info("No ARPI_INPUT_DEVICE set — button listener disabled")
        app_state.set_button_ok(False)

    # ── 3. Start HTTP server ─────────────────────────────────────────────
    flask_app = create_app(app_state)

    try:
        log.info("Starting HTTP server on %s:%d", cfg.server_host, cfg.server_port)
        flask_app.run(
            host=cfg.server_host,
            port=cfg.server_port,
            debug=False,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        log.info("Shutting down…")
    finally:
        if listener:
            listener.stop()
        camera.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
