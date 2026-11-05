"""Tests for mode controller and mode transitions."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from reachy_mini_grokbot.config import Settings
from reachy_mini_grokbot.control_client import ControlState
from reachy_mini_grokbot.mode_controller import ModeController
from reachy_mini_grokbot.modes import IdleMode, ScribeMode, DocsChatMode


def make_settings() -> Settings:
    """Create a Settings object for testing."""
    return Settings(
        gemini_api_key="",
        google_credentials_path="",
        control_url="https://example.test",
        control_token="",
        control_poll_interval=0.1,
        control_offline_timeout=1.0,
        tts_provider="gemini",
        stt_provider="gemini",
        tts_voice="Kore",
        tts_language="en",
        gemini_tts_model="gemini-3.8-flash-tts",
        gemini_stt_model="gemini-3.5-transcribe",
        gemini_stt_live_model="gemini-3.5-transcribe-live",
        gemini_live_model="gemini-3.8-live",
        gemini_chat_model="gemini-3.8-flash",
        stt_custom_vocabulary=["Reachy", "Reachy Mini"],
        xai_api_key="",
        deepgram_api_key="",
        webhook_url="",
        webhook_key="",
        public_base_url="",
        mcp_host="127.0.0.1",
        mcp_port=8765,
        mcp_token="",
    )


def make_mock_body() -> MagicMock:
    """Create a mock RobotBody."""
    body = MagicMock()
    body.show = MagicMock(return_value="shown")
    return body


class TestIdleMode:
    def test_idle_mode_shows_listening_on_start(self) -> None:
        body = make_mock_body()
        settings = make_settings()
        mode = IdleMode(body, settings)
        
        state = ControlState(mode="idle")
        mode.start(state)
        
        body.show.assert_called_with("listening")
        assert mode.is_running

    def test_idle_mode_shows_neutral_on_stop(self) -> None:
        body = make_mock_body()
        settings = make_settings()
        mode = IdleMode(body, settings)
        
        state = ControlState(mode="idle")
        mode.start(state)
        body.reset_mock()
        
        mode.stop()
        
        body.show.assert_called_with("neutral")
        assert not mode.is_running

    def test_idle_mode_stop_is_idempotent(self) -> None:
        body = make_mock_body()
        settings = make_settings()
        mode = IdleMode(body, settings)
        
        mode.stop()
        mode.stop()
        
        assert not mode.is_running


class TestScribeMode:
    def test_scribe_mode_shows_focused_on_start(self) -> None:
        body = make_mock_body()
        settings = make_settings()
        mode = ScribeMode(body, settings)
        
        state = ControlState(mode="scribe", target_doc_id="doc-123")
        mode.start(state)
        
        body.show.assert_called_with("focused")
        assert mode.is_running
        assert mode._target_doc_id == "doc-123"

    def test_scribe_mode_updates_target_doc(self) -> None:
        body = make_mock_body()
        settings = make_settings()
        mode = ScribeMode(body, settings)
        
        state1 = ControlState(mode="scribe", target_doc_id="doc-123")
        mode.start(state1)
        
        state2 = ControlState(mode="scribe", target_doc_id="doc-456")
        mode.update(state2)
        
        assert mode._target_doc_id == "doc-456"


class TestDocsChatMode:
    def test_docs_chat_mode_shows_listening_on_start(self) -> None:
        body = make_mock_body()
        settings = make_settings()
        mode = DocsChatMode(body, settings)
        
        state = ControlState(mode="docs_chat", doc_ids=["doc-1", "doc-2"])
        mode.start(state)
        
        body.show.assert_called_with("listening")
        assert mode.is_running
        assert mode._doc_ids == ["doc-1", "doc-2"]

    def test_docs_chat_mode_updates_doc_ids(self) -> None:
        body = make_mock_body()
        settings = make_settings()
        mode = DocsChatMode(body, settings)
        
        state1 = ControlState(mode="docs_chat", doc_ids=["doc-1"])
        mode.start(state1)
        
        state2 = ControlState(mode="docs_chat", doc_ids=["doc-1", "doc-2", "doc-3"])
        mode.update(state2)
        
        assert mode._doc_ids == ["doc-1", "doc-2", "doc-3"]


class TestModeController:
    def test_controller_starts_in_idle_mode(self) -> None:
        body = make_mock_body()
        settings = make_settings()
        
        controller = ModeController(body, settings)
        assert controller.current_mode == "idle"
        
        state = ControlState(mode="idle")
        controller._transition_to("idle", state)
        
        assert controller.current_mode == "idle"
        assert controller._current_handler is not None
        assert controller._current_handler.name == "idle"
        assert controller._current_handler.is_running

    def test_controller_transitions_between_modes(self) -> None:
        body = make_mock_body()
        settings = make_settings()
        
        controller = ModeController(body, settings)
        
        state_idle = ControlState(mode="idle")
        controller._transition_to("idle", state_idle)
        assert controller.current_mode == "idle"
        idle_handler = controller._modes["idle"]
        
        state_scribe = ControlState(mode="scribe", target_doc_id="doc-123")
        controller._transition_to("scribe", state_scribe)
        assert controller.current_mode == "scribe"
        assert not idle_handler.is_running
        assert controller._current_handler.is_running
        
        state_docs = ControlState(mode="docs_chat", doc_ids=["doc-1"])
        controller._transition_to("docs_chat", state_docs)
        assert controller.current_mode == "docs_chat"

    def test_controller_handles_same_mode_as_update(self) -> None:
        body = make_mock_body()
        settings = make_settings()
        
        controller = ModeController(body, settings)
        
        state1 = ControlState(mode="scribe", target_doc_id="doc-1")
        controller._transition_to("scribe", state1)
        handler = controller._current_handler
        
        state2 = ControlState(mode="scribe", target_doc_id="doc-2")
        controller._transition_to("scribe", state2)
        
        assert controller._current_handler is handler
        assert controller._modes["scribe"]._target_doc_id == "doc-2"

    def test_controller_force_mode_works(self) -> None:
        body = make_mock_body()
        settings = make_settings()
        
        controller = ModeController(body, settings)
        
        controller._transition_to("idle", ControlState())
        controller.force_mode("scribe")
        
        assert controller.current_mode == "scribe"

    def test_controller_falls_back_to_idle_on_unknown_mode(self) -> None:
        body = make_mock_body()
        settings = make_settings()
        
        controller = ModeController(body, settings)
        controller._transition_to("idle", ControlState())
        
        controller._transition_to("unknown_mode", ControlState(mode="unknown_mode"))
        
        assert controller.current_mode == "idle"
