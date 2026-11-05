"""Tests for the control client (mocked HTTP)."""

from __future__ import annotations

import json
import threading
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from reachy_mini_grokbot.config import Settings
from reachy_mini_grokbot.control_client import ControlClient, ControlState


def make_settings(
    control_url: str = "https://example.test",
    control_token: str = "test-token",
    poll_interval: float = 0.1,
    offline_timeout: float = 1.0,
) -> Settings:
    """Create a Settings object for testing."""
    return Settings(
        gemini_api_key="",
        google_credentials_path="",
        control_url=control_url,
        control_token=control_token,
        control_poll_interval=poll_interval,
        control_offline_timeout=offline_timeout,
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


class MockResponse:
    """Mock httpx response."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return self._json_data


class MockClient:
    """Mock httpx.Client context manager."""

    def __init__(self, response: MockResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, url: str, headers: dict[str, str] | None = None) -> MockResponse:
        self.calls.append((url, headers or {}))
        return self.response


def test_control_state_from_response_parses_all_fields() -> None:
    data = {
        "mode": "scribe",
        "targetDocId": "doc-123",
        "docIds": ["doc-1", "doc-2"],
        "sourceFolderId": "folder-456",
        "version": 5,
        "updatedAt": "2024-01-01T00:00:00Z",
    }
    state = ControlState.from_response(data, etag="abc123")
    
    assert state.mode == "scribe"
    assert state.target_doc_id == "doc-123"
    assert state.doc_ids == ["doc-1", "doc-2"]
    assert state.source_folder_id == "folder-456"
    assert state.version == 5
    assert state.updated_at == "2024-01-01T00:00:00Z"
    assert state.etag == "abc123"


def test_control_state_from_response_defaults_unknown_mode_to_idle() -> None:
    state = ControlState.from_response({"mode": "unknown_mode"})
    assert state.mode == "idle"


def test_control_state_from_response_defaults_missing_mode_to_idle() -> None:
    state = ControlState.from_response({})
    assert state.mode == "idle"


def test_poll_once_returns_state_on_200(monkeypatch) -> None:
    settings = make_settings()
    response = MockResponse(
        status_code=200,
        json_data={"mode": "docs_chat", "version": 1},
        headers={"ETag": "etag-1"},
    )
    mock_client = MockClient(response)
    
    def mock_client_factory(*args, **kwargs):
        return mock_client
    
    monkeypatch.setattr("reachy_mini_grokbot.control_client.httpx.Client", mock_client_factory)
    
    client = ControlClient(settings)
    state = client.poll_once()
    
    assert state.mode == "docs_chat"
    assert state.version == 1
    assert len(mock_client.calls) == 1
    url, headers = mock_client.calls[0]
    assert "/api/reachy/state" in url
    assert "Bearer test-token" in headers.get("Authorization", "")


def test_poll_once_returns_cached_state_on_304(monkeypatch) -> None:
    settings = make_settings()
    
    call_count = [0]
    
    def mock_client_factory(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return MockClient(MockResponse(
                status_code=200,
                json_data={"mode": "scribe", "version": 1},
                headers={"ETag": "etag-1"},
            ))
        else:
            return MockClient(MockResponse(status_code=304))
    
    monkeypatch.setattr("reachy_mini_grokbot.control_client.httpx.Client", mock_client_factory)
    
    client = ControlClient(settings)
    
    state1 = client.poll_once()
    assert state1.mode == "scribe"
    
    state2 = client.poll_once()
    assert state2.mode == "scribe"


def test_poll_once_handles_401_unauthorized(monkeypatch) -> None:
    settings = make_settings()
    response = MockResponse(status_code=401)
    mock_client = MockClient(response)
    
    monkeypatch.setattr("reachy_mini_grokbot.control_client.httpx.Client", lambda *a, **k: mock_client)
    
    client = ControlClient(settings)
    state = client.poll_once()
    
    assert state.mode == "idle"
    assert client._consecutive_errors == 1


def test_poll_once_handles_network_error(monkeypatch) -> None:
    import httpx
    
    settings = make_settings()
    
    class ErrorClient:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, *args, **kwargs):
            raise httpx.ConnectError("Connection refused")
    
    monkeypatch.setattr("reachy_mini_grokbot.control_client.httpx.Client", lambda *a, **k: ErrorClient())
    
    client = ControlClient(settings)
    state = client.poll_once()
    
    assert state.mode == "idle"
    assert client._consecutive_errors == 1


def test_poll_once_handles_timeout(monkeypatch) -> None:
    import httpx
    
    settings = make_settings()
    
    class TimeoutClient:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, *args, **kwargs):
            raise httpx.TimeoutException("Timeout")
    
    monkeypatch.setattr("reachy_mini_grokbot.control_client.httpx.Client", lambda *a, **k: TimeoutClient())
    
    client = ControlClient(settings)
    state = client.poll_once()
    
    assert state.mode == "idle"
    assert client._consecutive_errors == 1


def test_callback_called_on_mode_change(monkeypatch) -> None:
    settings = make_settings()
    
    callback_states = []
    def on_change(state):
        callback_states.append(state.mode)
    
    call_count = [0]
    def mock_client_factory(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return MockClient(MockResponse(
                status_code=200,
                json_data={"mode": "idle"},
            ))
        else:
            return MockClient(MockResponse(
                status_code=200,
                json_data={"mode": "scribe"},
            ))
    
    monkeypatch.setattr("reachy_mini_grokbot.control_client.httpx.Client", mock_client_factory)
    
    client = ControlClient(settings, on_state_change=on_change)
    
    client.poll_once()
    client.poll_once()
    
    assert "scribe" in callback_states


def test_backoff_increases_on_errors() -> None:
    settings = make_settings(poll_interval=1.0)
    client = ControlClient(settings)
    
    assert client._backoff_seconds() == 1.0
    
    client._consecutive_errors = 1
    assert client._backoff_seconds() == 2.0
    
    client._consecutive_errors = 3
    assert client._backoff_seconds() == 8.0
    
    client._consecutive_errors = 10
    assert client._backoff_seconds() == 30.0


def test_is_offline_after_timeout() -> None:
    settings = make_settings(offline_timeout=0.1)
    client = ControlClient(settings)
    
    client._last_success_mono = time.monotonic() - 0.2
    assert client.is_offline is True
    
    client._last_success_mono = time.monotonic()
    assert client.is_offline is False


def test_client_does_not_start_without_token() -> None:
    settings = make_settings(control_token="")
    client = ControlClient(settings)
    
    client.start()
    
    assert client._thread is None
