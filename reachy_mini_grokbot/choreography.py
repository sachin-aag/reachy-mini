"""Parse ClawBody-style [move:name] markers inside spoken text."""

from __future__ import annotations

import re
from typing import Literal, TypedDict


_MOVE_RE = re.compile(r"\[move:([^\]]+)\]")


class TextSegment(TypedDict):
    """Spoken text chunk."""

    type: Literal["text"]
    content: str


class MoveSegment(TypedDict):
    """Recorded-move marker."""

    type: Literal["move"]
    name: str


Segment = TextSegment | MoveSegment


def parse_choreographed_text(text: str) -> list[Segment]:
    """Split text into speech chunks and move markers."""
    segments: list[Segment] = []
    last_end = 0
    for match in _MOVE_RE.finditer(text):
        if match.start() > last_end:
            chunk = text[last_end : match.start()]
            if chunk:
                segments.append({"type": "text", "content": chunk})
        segments.append({"type": "move", "name": match.group(1).strip()})
        last_end = match.end()
    if last_end < len(text):
        tail = text[last_end:]
        if tail:
            segments.append({"type": "text", "content": tail})
    return segments


def estimate_speech_seconds(text: str) -> float:
    """Conservative spoken duration used when TTS has no length metadata."""
    return max(1.0, len(text.strip()) / 15.0)
