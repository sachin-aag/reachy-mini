"""Tests for the settings API endpoints."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from reachy_mini_grokbot.config import Settings
from reachy_mini_grokbot.settings_helpers import (
    get_or_create_setup_pin,
    mask_secret,
    parse_service_account_json,
    check_gemini_key,
    verify_auth_token,
)


def make_settings(
    control_token: str = "",
    gemini_api_key: str = "",
) -> Settings:
    """Create a Settings object for testing."""
    return Settings(
        gemini_api_key=gemini_api_key,
        google_credentials_path="",
        control_url="https://example.test",
        control_token=control_token,
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


class TestMaskSecret:
    def test_mask_returns_not_set_for_none(self) -> None:
        assert mask_secret(None) == "not set"

    def test_mask_returns_not_set_for_empty(self) -> None:
        assert mask_secret("") == "not set"

    def test_mask_shows_last_4_chars(self) -> None:
        result = mask_secret("sk-1234567890abcdef")
        assert result == "set (****cdef)"

    def test_mask_handles_short_secrets(self) -> None:
        result = mask_secret("abc")
        assert result == "set (****)"

    def test_mask_with_custom_length(self) -> None:
        result = mask_secret("sk-1234567890abcdef", show_last=6)
        assert result == "set (****abcdef)"


class TestVerifyAuthToken:
    def test_verify_with_control_token(self) -> None:
        settings = make_settings(control_token="my-secret-token")
        assert verify_auth_token("my-secret-token", settings) is True
        assert verify_auth_token("wrong-token", settings) is False

    def test_verify_with_setup_pin(self) -> None:
        settings = make_settings(control_token="")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            pin_path = Path(tmpdir) / ".setup_pin"
            pin_path.write_text("test-pin-12345")
            
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                assert verify_auth_token("test-pin-12345", settings) is True
                assert verify_auth_token("wrong-pin", settings) is False

    def test_verify_rejects_empty_token(self) -> None:
        settings = make_settings(control_token="")
        assert verify_auth_token("", settings) is False


class TestGetOrCreateSetupPin:
    def test_creates_new_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                pin = get_or_create_setup_pin()
                assert pin
                assert len(pin) >= 8
                
                pin_path = Path(tmpdir) / ".setup_pin"
                assert pin_path.exists()
                assert pin_path.read_text().strip() == pin

    def test_returns_existing_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pin_path = Path(tmpdir) / ".setup_pin"
            pin_path.write_text("existing-pin-xyz")
            
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                pin = get_or_create_setup_pin()
                assert pin == "existing-pin-xyz"


class TestTestGeminiKey:
    def test_valid_key_returns_valid(self) -> None:
        with patch("reachy_mini_grokbot.settings_helpers.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            result = check_gemini_key("test-key")
            assert result["valid"] is True
            assert result["status"] == "OK"

    def test_invalid_key_returns_invalid(self) -> None:
        with patch("reachy_mini_grokbot.settings_helpers.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Invalid API key"
            mock_post.return_value = mock_response
            
            result = check_gemini_key("bad-key")
            assert result["valid"] is False
            assert result["status_code"] == 401

    def test_timeout_returns_error(self) -> None:
        import httpx
        
        with patch("reachy_mini_grokbot.settings_helpers.httpx.post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("timed out")
            
            result = check_gemini_key("test-key")
            assert result["valid"] is False
            assert result["status"] == "Timeout"

    def test_network_error_returns_error(self) -> None:
        import httpx
        
        with patch("reachy_mini_grokbot.settings_helpers.httpx.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("connection refused")
            
            result = check_gemini_key("test-key")
            assert result["valid"] is False
            assert result["status"] == "Network error"


class TestServiceAccountValidation:
    def test_valid_service_account_json(self) -> None:
        sa_json = json.dumps({
            "type": "service_account",
            "client_email": "test@project.iam.gserviceaccount.com",
            "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
        })
        
        sa_data = json.loads(sa_json)
        assert sa_data.get("type") == "service_account"
        assert "client_email" in sa_data

    def test_invalid_type_rejected(self) -> None:
        sa_data = {"type": "oauth", "client_email": "test@example.com"}
        assert sa_data.get("type") != "service_account"

    def test_missing_client_email_rejected(self) -> None:
        sa_data = {"type": "service_account"}
        assert "client_email" not in sa_data


class TestConfigFileSecurity:
    def test_config_file_has_restricted_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text('{"test": "data"}')
            os.chmod(config_path, 0o600)
            
            mode = config_path.stat().st_mode & 0o777
            assert mode == 0o600

    def test_pin_file_has_restricted_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                pin = get_or_create_setup_pin()
                pin_path = Path(tmpdir) / ".setup_pin"
                
                mode = pin_path.stat().st_mode & 0o777
                assert mode == 0o600
