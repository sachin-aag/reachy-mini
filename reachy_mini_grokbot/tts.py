"""Text-to-speech synthesis with provider fallback.

Primary provider: Google Gemini (gemini-3.8-flash-tts)
Fallback providers: xAI (/v1/tts), Deepgram (aura-2-saturn-en)

Gemini TTS uses the v1beta generateContent API with:
- Header: x-goog-api-key
- Config: responseModalities=["AUDIO"], speechConfig with prebuilt voice
- Returns: audio/wav 24kHz mono PCM

IMPORTANT: Style instructions go in speech_metadata, NOT in the text.
If you put "Say cheerfully: Hello" in the text, it will speak that literally.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reachy_mini_grokbot.config import Settings

logger = logging.getLogger(__name__)

GROK_VOICES = ("ara", "eve", "leo", "rex", "sal")
GEMINI_VOICES = (
    "Kore", "Charon", "Fenrir", "Aoede", "Puck", "Leda", "Orus", "Zephyr",
)


def synthesize_speech(
    text: str,
    settings: "Settings",
    voice_override: str | None = None,
) -> Path | None:
    """Synthesize speech using the configured provider with fallback.
    
    Returns a temp audio file path, or None if synthesis failed.
    """
    clean = text.strip()
    if not clean:
        return None

    provider = settings.tts_provider
    voice = voice_override or settings.tts_voice
    language = settings.tts_language

    if provider == "gemini" and settings.gemini_api_key:
        try:
            return _gemini_speech(
                clean,
                settings.gemini_api_key,
                voice,
                model=settings.gemini_tts_model,
            )
        except Exception as exc:
            logger.warning("Gemini TTS failed: %s", exc)
            if settings.xai_api_key:
                provider = "xai"
            elif settings.deepgram_api_key:
                provider = "deepgram"
            else:
                return None

    if provider == "xai" and settings.xai_api_key:
        try:
            return _xai_speech(clean, settings.xai_api_key, voice, language)
        except Exception as exc:
            logger.warning("xAI TTS failed: %s", exc)
            if settings.deepgram_api_key:
                provider = "deepgram"
            else:
                return None

    if provider == "deepgram" and settings.deepgram_api_key:
        try:
            return _deepgram_speech(clean, settings.deepgram_api_key)
        except Exception as exc:
            logger.warning("Deepgram TTS failed: %s", exc)
            return None

    return None


def _gemini_speech(
    text: str,
    api_key: str,
    voice: str,
    model: str = "gemini-3.8-flash-tts",
) -> Path:
    """Generate speech using Gemini TTS via v1beta generateContent API.
    
    Uses direct HTTP call with x-goog-api-key header.
    Returns WAV audio (24kHz, 16-bit mono).
    
    IMPORTANT: Style goes in speech_metadata, not in text. The model speaks
    the text literally, so "Say cheerfully: Hello" would be spoken aloud.
    """
    import base64
    import httpx

    chosen_voice = voice if voice in GEMINI_VOICES else "Kore"
    
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "contents": [{
                "role": "user",
                "parts": [{
                    "text": text,
                }],
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": chosen_voice,
                        },
                    },
                },
            },
        },
        timeout=60.0,
    )
    response.raise_for_status()
    
    result = response.json()
    audio_b64 = result["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    audio_data = base64.b64decode(audio_b64)
    
    handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    handle.write(audio_data)
    handle.close()
    return Path(handle.name)


def _xai_speech(text: str, api_key: str, voice: str, language: str = "en") -> Path:
    """Generate speech using xAI TTS (/v1/tts).
    
    Note: xAI TTS requires a funded API key (not OAuth subscription tokens).
    A 403 error means the key lacks TTS permission.
    """
    import httpx

    chosen = voice.lower() if voice.lower() in GROK_VOICES else "eve"
    response = httpx.post(
        "https://api.x.ai/v1/tts",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"text": text, "voice_id": chosen, "language": language},
        timeout=60.0,
    )
    response.raise_for_status()
    suffix = ".mp3" if "mpeg" in response.headers.get("content-type", "") else ".wav"
    handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    handle.write(response.content)
    handle.close()
    return Path(handle.name)


def _deepgram_speech(text: str, api_key: str) -> Path:
    """Generate speech using Deepgram TTS (aura-2-saturn-en)."""
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
