"""Optional TTS used by the speak tool. Failures are non-fatal."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path


logger = logging.getLogger(__name__)

GROK_VOICES = ("ara", "eve", "leo", "rex", "sal")


def synthesize_speech(text: str, xai_key: str, voice: str, deepgram_key: str) -> Path | None:
    """Return a temp audio file, or None if no TTS provider is configured."""
    clean = text.strip()
    if not clean:
        return None
    if xai_key:
        try:
            return _xai_speech(clean, xai_key, voice)
        except Exception as exc:
            logger.warning("xAI TTS failed: %s", exc)
    if deepgram_key:
        try:
            return _deepgram_speech(clean, deepgram_key)
        except Exception as exc:
            logger.warning("Deepgram TTS failed: %s", exc)
    return None


def _xai_speech(text: str, api_key: str, voice: str) -> Path:
    import httpx

    chosen = voice.lower() if voice.lower() in GROK_VOICES else "eve"
    response = httpx.post(
        "https://api.x.ai/v1/audio/speech",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "grok-tts", "input": text, "voice": chosen},
        timeout=60.0,
    )
    response.raise_for_status()
    suffix = ".mp3" if "mpeg" in response.headers.get("content-type", "") else ".wav"
    handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    handle.write(response.content)
    handle.close()
    return Path(handle.name)


def _deepgram_speech(text: str, api_key: str) -> Path:
    import httpx

    response = httpx.post(
        "https://api.deepgram.com/v1/speak?model=aura-2-saturn-en",
        headers={"Authorization": f"Token {api_key}", "Content-Type": "application/json"},
        json={"text": text},
        timeout=60.0,
    )
    response.raise_for_status()
    handle = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    handle.write(response.content)
    handle.close()
    return Path(handle.name)
