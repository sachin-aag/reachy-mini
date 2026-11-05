"""Docs Chat mode: mic -> STT -> LLM grounded in Drive docs -> TTS.

This is a STUB implementation. The full implementation will use Gemini Live API
for end-to-end conversational audio (mic in, spoken answer out) with grounding.

Option A: Gemini Live API (gemini-3.8-live) for full duplex conversation
- Supports bidirectional audio: mic input -> spoken response
- Can include system instructions with doc context for grounding
- Model handles turn detection, interrupts, and natural conversation flow

Option B: Separate STT -> LLM -> TTS pipeline
- STT: gemini-3.5-transcribe-live for real-time transcription
- LLM: gemini-2.5-flash or gemini-2.5-pro with doc context in prompt
- TTS: gemini-3.8-flash-tts for high-quality speech synthesis

The Live API approach is preferred for more natural conversation, but requires
loading grounding docs into the system instruction or as context files.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from reachy_mini_grokbot.modes.base import ModeHandler

if TYPE_CHECKING:
    from reachy_mini_grokbot.control_client import ControlState


logger = logging.getLogger(__name__)


class DocsChatMode(ModeHandler):
    """Docs Chat mode: voice Q&A grounded in Google Drive documents.
    
    Interface contract (for future implementation):
    
    Inputs:
    - state.doc_ids: List of Google Doc IDs to use as context
    - state.source_folder_id: Optional Drive folder to index
    - settings.google_credentials_path: Path to service account JSON (GOOGLE_APPLICATION_CREDENTIALS)
    - settings.gemini_api_key: For Gemini (STT, LLM, TTS)
    
    Option A - Gemini Live API (gemini-3.8-live):
    Full duplex conversation with grounding docs as system instruction.
    
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction="You are a helpful assistant. Answer based on these docs: <doc_content>",
            input_audio_transcription={},
            output_audio_transcription={},
        )
        async with client.aio.live.connect(model="gemini-3.8-live", config=config) as session:
            # Stream mic audio, receive spoken responses
    
    Option B - Separate pipeline:
    - STT: gemini-3.5-transcribe-live (via Live API WebSocket)
    - LLM: gemini-2.5-flash with doc context in prompt (via generateContent)
    - TTS: gemini-3.8-flash-tts (via generateContent with response_modalities=["AUDIO"])
    
    Visual feedback:
    - 'listening' expression when waiting for user
    - 'thinking' expression when processing
    - 'curious' expression when responding
    """

    name = "docs_chat"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._doc_ids: list[str] = []
        self._source_folder_id: str | None = None
        self._chat_thread: threading.Thread | None = None
        self._stop_chat = threading.Event()

    def _on_start(self, state: "ControlState") -> None:
        """Start docs_chat mode: begin listening for questions."""
        self._doc_ids = state.doc_ids or []
        self._source_folder_id = state.source_folder_id
        
        try:
            self.body.show("listening")
            logger.info("Docs Chat mode: listening, docs=%s, folder=%s",
                       self._doc_ids, self._source_folder_id)
        except Exception as exc:
            logger.warning("Could not show listening pose: %s", exc)
        
        # TODO: Start actual conversation loop
        # self._start_chat_loop()
        logger.info("Docs Chat mode: STUB - conversation not yet implemented")

    def _on_stop(self) -> None:
        """Stop docs_chat mode: halt conversation."""
        self._stop_chat.set()
        
        if self._chat_thread is not None:
            self._chat_thread.join(timeout=5.0)
            self._chat_thread = None
        
        try:
            self.body.show("neutral")
        except Exception as exc:
            logger.debug("Could not show neutral pose on docs_chat exit: %s", exc)
        
        logger.info("Docs Chat mode stopped")

    def _on_update(self, state: "ControlState") -> None:
        """Update doc context if it changed."""
        new_doc_ids = state.doc_ids or []
        if new_doc_ids != self._doc_ids:
            logger.info("Docs Chat mode: doc_ids changed %s -> %s",
                       self._doc_ids, new_doc_ids)
            self._doc_ids = new_doc_ids
        
        if state.source_folder_id != self._source_folder_id:
            logger.info("Docs Chat mode: source_folder_id changed %s -> %s",
                       self._source_folder_id, state.source_folder_id)
            self._source_folder_id = state.source_folder_id

    def _start_chat_loop(self) -> None:
        """Start the conversation loop. STUB for future implementation."""
        self._stop_chat.clear()
        self._chat_thread = threading.Thread(
            target=self._chat_loop,
            name="docs-chat",
            daemon=True,
        )
        self._chat_thread.start()

    def _chat_loop(self) -> None:
        """Main conversation loop. STUB for future implementation.
        
        Full implementation with Gemini Live API (Option A):
        
        Model: settings.gemini_live_model (default: gemini-3.8-live)
        Custom vocab: settings.stt_custom_vocabulary for name recognition
        
        from google import genai
        from google.genai import types
        
        # Load doc content from Drive
        doc_content = fetch_docs_from_drive(self._doc_ids, self.settings)
        
        # Build system instruction with doc context and custom vocabulary
        vocab_hint = f"Names: {', '.join(self.settings.stt_custom_vocabulary)}"
        system_instruction = f"{vocab_hint}\\n\\nAnswer based on these docs:\\n{doc_content}"
        
        client = genai.Client(api_key=self.settings.gemini_api_key)
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=system_instruction,
            input_audio_transcription={},
            output_audio_transcription={},
        )
        
        async with client.aio.live.connect(
            model=self.settings.gemini_live_model, config=config
        ) as session:
            while not stop:
                # Stream mic audio (16-bit PCM, 16kHz)
                chunk = self.reachy_mini.media.get_audio_sample()
                await session.send_realtime_input(
                    audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                )
                
                async for response in session.receive():
                    # Play audio response on robot speaker (24kHz PCM output)
                    if response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.inline_data:
                                self.reachy_mini.media.push_audio_sample(part.inline_data.data)
        """
        logger.info("Chat loop started (STUB)")
        
        while not self._stop_chat.is_set():
            self._stop_chat.wait(0.1)
        
        logger.info("Chat loop ended")
