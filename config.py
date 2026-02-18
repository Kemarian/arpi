"""Application configuration — secrets and hardware settings from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_ENV_DIR = Path(__file__).parent


def _load_env() -> None:
    load_dotenv(_ENV_DIR / ".env")


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration loaded from environment.

    Only secrets and hardware-specific settings belong here.
    Prompts do NOT belong here — see ``prompts.py``.
    """

    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    image_dir: Path = field(default_factory=lambda: _ENV_DIR / "captures")
    input_device: str | None = None
    rotate_180: bool = True
    server_host: str = "0.0.0.0"
    server_port: int = 5000

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load configuration from ``.env`` + shell environment."""
        _load_env()

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Put it in arpi/.env or shell env."
            )

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

        image_dir = Path(os.getenv("ARPI_IMAGE_DIR", "captures")).expanduser()
        if not image_dir.is_absolute():
            image_dir = _ENV_DIR / image_dir
        image_dir.mkdir(parents=True, exist_ok=True)

        input_device = os.getenv("ARPI_INPUT_DEVICE", "").strip() or None

        rotate_180 = os.getenv("ARPI_ROTATE_180", "1").strip().lower() in {
            "1", "true", "yes", "on",
        }

        server_host = os.getenv("ARPI_SERVER_HOST", "0.0.0.0").strip()
        server_port = int(os.getenv("ARPI_SERVER_PORT", "5000"))

        return cls(
            openai_api_key=api_key,
            openai_model=model,
            image_dir=image_dir,
            input_device=input_device,
            rotate_180=rotate_180,
            server_host=server_host,
            server_port=server_port,
        )
