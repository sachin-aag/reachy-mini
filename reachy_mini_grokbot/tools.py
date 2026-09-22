"""Shared tool implementations used by REST and MCP."""

from __future__ import annotations

import logging
from typing import Any

from reachy_mini_grokbot.body import RobotBody
from reachy_mini_grokbot.choreography import parse_choreographed_text
from reachy_mini_grokbot.config import Settings
from reachy_mini_grokbot.tts import synthesize_speech


logger = logging.getLogger(__name__)

_BODY: RobotBody | None = None
_SETTINGS: Settings | None = None


def bind_runtime(body: RobotBody, settings: Settings) -> None:
    """Attach the live robot to tool handlers."""
    global _BODY, _SETTINGS
    _BODY = body
    _SETTINGS = settings


def require_body() -> RobotBody:
    """Return the bound robot or raise."""
    if _BODY is None:
        raise RuntimeError("Robot is not ready yet")
    return _BODY


def speak(text: str, voice: str = "eve") -> str:
    """Speak on the robot. Plays TTS when a key is present; always runs move markers."""
    body = require_body()
    settings = _SETTINGS
    spoken = " ".join(
        segment["content"] for segment in parse_choreographed_text(text) if segment["type"] == "text"
    ).strip() or text
    notes = body.speak_markers(text)
    audio_note = "no TTS key configured; text only"
    if settings is not None:
        path = synthesize_speech(spoken, settings.xai_api_key, voice or settings.grok_voice, settings.deepgram_api_key)
        if path is not None:
            try:
                media = getattr(body.mini, "media", None)
                if media is not None and hasattr(media, "play_sound"):
                    media.play_sound(str(path))
                    audio_note = f"played {path.name}"
                else:
                    audio_note = f"synthesized {path.name} but media.play_sound is unavailable"
            finally:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
    extra = f" moves={notes}" if notes else ""
    return f"Spoke: {spoken} ({audio_note}){extra}"


def look(
    direction: str = "",
    roll: float = 0.0,
    pitch: float = 0.0,
    yaw: float = 0.0,
    duration: float = 1.0,
) -> str:
    """Look in a named direction or an explicit pose."""
    body = require_body()
    return body.look(
        direction=direction or None,
        roll=roll,
        pitch=pitch,
        yaw=yaw,
        duration=duration,
    )


def show(emotion: str = "neutral", move: str = "") -> str:
    """Express an emotion or play a recorded move."""
    return require_body().show(emotion=emotion, move=move)


def dance(name: str = "happy") -> str:
    """Play a dance clip."""
    return require_body().dance(name)


def rest(mode: str = "neutral") -> str:
    """Sleep, wake, or return to neutral."""
    return require_body().rest(mode)


def snap() -> str:
    """Capture a camera frame."""
    return require_body().snap()


def discover(library: str = "emotions") -> str:
    """List recorded moves."""
    return require_body().discover(library)


def tool_dispatch(name: str, arguments: dict[str, Any]) -> str:
    """Dispatch a REST tool call by name."""
    handlers = {
        "speak": lambda: speak(str(arguments.get("text", "")), str(arguments.get("voice", "eve"))),
        "look": lambda: look(
            direction=str(arguments.get("direction", "")),
            roll=float(arguments.get("roll", 0) or 0),
            pitch=float(arguments.get("pitch", 0) or 0),
            yaw=float(arguments.get("yaw", 0) or 0),
            duration=float(arguments.get("duration", 1) or 1),
        ),
        "show": lambda: show(str(arguments.get("emotion", "neutral") or "neutral"), str(arguments.get("move", "") or "")),
        "dance": lambda: dance(str(arguments.get("name", "happy") or "happy")),
        "rest": lambda: rest(str(arguments.get("mode", "neutral") or "neutral")),
        "snap": snap,
        "discover": lambda: discover(str(arguments.get("library", "emotions") or "emotions")),
    }
    handler = handlers.get(name)
    if handler is None:
        return f"Unknown tool {name!r}"
    try:
        return handler()
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        return f"error: {exc}"
