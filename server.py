"""Flask HTTP server — serves /health and /result to Unity."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flask import Flask, jsonify

if TYPE_CHECKING:
    from state import AppState
    from prompts import VisionPrompt

log = logging.getLogger(__name__)


def create_app(app_state: AppState) -> Flask:
    """Create and configure the Flask application.

    Routes:
        GET /health  — Pi reachability, camera, button status
        GET /result  — Current pipeline status + last result text
        GET /prompts — List available prompts
    """
    app = Flask(__name__)
    app.config["state"] = app_state

    @app.route("/health", methods=["GET"])
    def health():  # type: ignore[no-untyped-def]
        snap = app_state.get_health()
        return jsonify({
            "status": snap.status,
            "camera": snap.camera,
            "button": snap.button,
            "uptime_s": snap.uptime_s,
        })

    @app.route("/result", methods=["GET"])
    def result():  # type: ignore[no-untyped-def]
        return jsonify(app_state.get_result())

    @app.route("/prompts", methods=["GET"])
    def list_prompts():  # type: ignore[no-untyped-def]
        from prompts import ALL_PROMPTS, DEFAULT_PROMPT
        return jsonify({
            "default": DEFAULT_PROMPT.name,
            "available": [
                {"name": p.name, "instruction": p.user_instruction}
                for p in ALL_PROMPTS.values()
            ],
        })

    return app
