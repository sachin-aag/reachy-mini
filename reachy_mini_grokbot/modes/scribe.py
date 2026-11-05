"""Scribe mode: mic audio -> STT stream -> append text to a Google Doc.

This is a STUB implementation. The full implementation will:
1. Start mic capture via the SDK's media.start_recording()
2. Stream audio to Gemini Live API (gemini-3.5-transcribe-live) for real-time STT
3. Append transcribed text to the target Google Doc via the Drive API
4. Provide visual feedback (e.g., focused expression while listening)

Gemini STT uses the Live API over WebSockets:
- Model: gemini-3.5-transcribe-live
- Input: raw 16-bit PCM at 16kHz (mono, little-endian)
- Output: input_transcription (final) and interim_input_transcription (partial)
- SDK: google-genai >= 2.25.0, async WebSocket via client.aio.live.connect()

Fallback: Deepgram streaming STT if GEMINI_API_KEY is not available.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from reachy_mini_grokbot.modes.base import ModeHandler

if TYPE_CHECKING:
    from reachy_mini_grokbot.control_client import ControlState


logger = logging.getLogger(__name__)


class ScribeMode(ModeHandler):
    """Scribe mode: continuous speech-to-text transcription to a Google Doc.
    
    Interface contract (for future implementation):
    
    Inputs:
    - state.target_doc_id: The Google Doc ID to append transcribed text to
    - settings.google_credentials_path: Path to service account JSON (GOOGLE_APPLICATION_CREDENTIALS)
    - settings.gemini_api_key: For Gemini STT (primary)
    - settings.deepgram_api_key: For Deepgram STT (fallback)
    
    Audio pipeline (Gemini):
    - self.reachy_mini.media.start_recording() to start mic capture
    - self.reachy_mini.media.get_audio_sample() to read 16-bit PCM chunks
    - Stream to gemini-3.5-transcribe-live via client.aio.live.connect()
    - Read input_transcription for final text, interim_input_transcription for live preview
    
    Output:
    - Append transcribed text to the target Google Doc in real-time
    - Show 'focused' expression while actively listening
    - Show 'thinking' expression while processing
    """

    name = "scribe"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._target_doc_id: str | None = None
        self._transcription_thread: threading.Thread | None = None
        self._stop_transcription = threading.Event()

    def _on_start(self, state: "ControlState") -> None:
        """Start scribe mode: begin mic capture and transcription."""
        self._target_doc_id = state.target_doc_id
        if not self._target_doc_id:
            logger.warning("Scribe mode started without target_doc_id")
        
        try:
            self.body.show("focused")
            logger.info("Scribe mode: focused pose, target_doc=%s", self._target_doc_id)
        except Exception as exc:
            logger.warning("Could not show focused pose: %s", exc)
        
        # TODO: Start actual mic capture and STT streaming
        # self._start_transcription()
        logger.info("Scribe mode: STUB - transcription not yet implemented")

    def _on_stop(self) -> None:
        """Stop scribe mode: halt mic capture and transcription."""
        self._stop_transcription.set()
        
        if self._transcription_thread is not None:
            self._transcription_thread.join(timeout=5.0)
            self._transcription_thread = None
        
        try:
            self.body.show("neutral")
        except Exception as exc:
            logger.debug("Could not show neutral pose on scribe exit: %s", exc)
        
        logger.info("Scribe mode stopped")

    def _on_update(self, state: "ControlState") -> None:
        """Update target doc if it changed."""
        if state.target_doc_id != self._target_doc_id:
            logger.info("Scribe mode: target_doc changed %s -> %s", 
                       self._target_doc_id, state.target_doc_id)
            self._target_doc_id = state.target_doc_id

    def _start_transcription(self) -> None:
        """Start the transcription pipeline. STUB for future implementation."""
        self._stop_transcription.clear()
        self._transcription_thread = threading.Thread(
            target=self._transcription_loop,
            name="scribe-transcription",
            daemon=True,
        )
        self._transcription_thread.start()

    def _transcription_loop(self) -> None:
        """Main transcription loop. STUB for future implementation.
        
        Full implementation will use Gemini Live API with custom vocabulary
        for better recognition of names like "Reachy" (otherwise misheard as "Richie").
        
        Model: settings.gemini_stt_live_model (default: gemini-3.5-transcribe-live)
        Custom vocab: settings.stt_custom_vocabulary (e.g., ["Reachy", "Reachy Mini", "Grok"])
        
        from google import genai
        from google.genai import types
        
        # Build system instruction with custom vocabulary hints
        vocab_hint = f"Names to recognize: {', '.join(self.settings.stt_custom_vocabulary)}"
        
        client = genai.Client(api_key=self.settings.gemini_api_key)
        config = types.LiveConnectConfig(
            response_modalities=["TEXT"],
            system_instruction=vocab_hint,  # Helps with custom names
            input_audio_transcription=types.AudioTranscriptionConfig(
                language_codes=[],  # Auto-detect
                mode="SMART",       # Disfluency removal
            ),
        )
        
        async with client.aio.live.connect(
            model=self.settings.gemini_stt_live_model, config=config
        ) as session:
            while not stop:
                # Read audio from robot mic (16-bit PCM, 16kHz)
                chunk = self.reachy_mini.media.get_audio_sample()
                await session.send_realtime_input(
                    audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                )
                async for response in session.receive():
                    # Note: response structure is audioTranscription.text, not text
                    if response.server_content.input_transcription:
                        text = response.server_content.input_transcription.text
                        # Append to Google Doc via Drive API
        """
        logger.info("Transcription loop started (STUB)")
        
        while not self._stop_transcription.is_set():
            self._stop_transcription.wait(0.1)
        
        logger.info("Transcription loop ended")
