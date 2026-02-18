"""Prompt definitions — editable dataclasses, not environment variables.

Add new prompts by creating instances of ``VisionPrompt``.
Switch the active prompt by changing ``DEFAULT_PROMPT``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisionPrompt:
    """A named prompt template for the Vision API."""

    name: str
    system_instruction: str
    user_instruction: str


# ── Prompt Registry ──────────────────────────────────────────────────────────

DESCRIBE_SCENE = VisionPrompt(
    name="describe_scene",
    system_instruction="You are a concise visual assistant for an AR headset user.",
    user_instruction="Describe what you see in this image in 3 concise bullet points.",
)

IDENTIFY_OBJECTS = VisionPrompt(
    name="identify_objects",
    system_instruction="You are a concise visual assistant for an AR headset user.",
    user_instruction=(
        "List the main objects visible in this image. "
        "For each, give: name, approximate position (left/center/right), "
        "and one notable detail. Be concise."
    ),
)

TRANSLATE_TEXT = VisionPrompt(
    name="translate_text",
    system_instruction=(
        "You are a translation assistant for an AR headset user. "
        "If text is visible, translate it to English. "
        "If no text is found, say so briefly."
    ),
    user_instruction="Find and translate any visible text in this image to English.",
)

READ_DOCUMENT = VisionPrompt(
    name="read_document",
    system_instruction="You are a document reading assistant for an AR headset user.",
    user_instruction=(
        "Read the document or text visible in this image. "
        "Provide a brief summary (max 3 sentences) followed by key points."
    ),
)

# ── Default ──────────────────────────────────────────────────────────────────

DEFAULT_PROMPT = DESCRIBE_SCENE

# All registered prompts for lookup by name.
ALL_PROMPTS: dict[str, VisionPrompt] = {
    p.name: p
    for p in [DESCRIBE_SCENE, IDENTIFY_OBJECTS, TRANSLATE_TEXT, READ_DOCUMENT]
}


def get_prompt(name: str) -> VisionPrompt:
    """Look up a prompt by name. Raises ``KeyError`` if not found."""
    return ALL_PROMPTS[name]
