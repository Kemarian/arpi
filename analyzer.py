"""OpenAI Vision API client — single-responsibility image analysis."""

from __future__ import annotations

import base64
import logging
from pathlib import Path

from openai import OpenAI

from prompts import VisionPrompt

log = logging.getLogger(__name__)


def _to_data_url(image_path: Path) -> str:
    """Encode image file as a base64 data URL."""
    image_bytes = image_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{encoded}"


class VisionAnalyzer:
    """Stateless OpenAI Vision API wrapper.

    Knows how to send an image + prompt and return the text response.
    Does not know about cameras, buttons, servers, or state.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def analyze(self, image_path: Path, prompt: VisionPrompt) -> str:
        """Send *image_path* with *prompt* to OpenAI and return the text answer."""
        data_url = _to_data_url(image_path)

        messages: list[dict] = []

        if prompt.system_instruction:
            messages.append({"role": "system", "content": prompt.system_instruction})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt.user_instruction},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        })

        log.info("Sending image to OpenAI (%s) …", self._model)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.2,
        )
        content = response.choices[0].message.content
        result = content or "(no response content)"
        log.info("OpenAI responded (%d chars)", len(result))
        return result
