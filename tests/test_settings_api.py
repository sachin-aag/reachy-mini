"""Tests for the settings API endpoints."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from reachy_mini_grokbot.config import Settings
from reachy_mini_grokbot.settings_helpers import (
    check_gemini_key,
    create_pin,
    get_setup_status,
    mask_secret,
    parse_service_account_json,
    pin_exists,
    reset_config_and_pin,
    reset_setup_state,
    verify_auth_token,
    verify_pin,
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


class TestCreatePin:
    def test_create_pin_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                reset_setup_state()
                
                success, message = create_pin("123456")
                
                assert success is True
                assert "successfully" in message.lower()
                
                pin_path = Path(tmpdir) / ".setup_pin"
                assert pin_path.exists()

    def test_create_pin_too_short(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                reset_setup_state()
                
                success, message = create_pin("12345")
                
                assert success is False
                assert "6" in message

    def test_create_pin_not_digits(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                reset_setup_state()
                
                success, message = create_pin("abc123")
                
                assert success is False
                assert "digit" in message.lower()

    def test_create_pin_already_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pin_path = Path(tmpdir) / ".setup_pin"
            pin_path.write_text("existing-hash")
            
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                reset_setup_state()
                
                success, message = create_pin("123456")
                
                assert success is False
                assert "already exists" in message.lower()


class TestVerifyPin:
    def test_verify_pin_correct(self) -> None:
        import hashlib
        
        with tempfile.TemporaryDirectory() as tmpdir:
            pin_path = Path(tmpdir) / ".setup_pin"
            pin_hash = hashlib.sha256("123456".encode()).hexdigest()
            pin_path.write_text(pin_hash)
            
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                assert verify_pin("123456") is True
                assert verify_pin("654321") is False

    def test_verify_pin_no_pin_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                assert verify_pin("123456") is False


class TestVerifyAuthToken:
    def test_verify_with_control_token(self) -> None:
        settings = make_settings(control_token="my-secret-token")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                reset_setup_state()
                
                valid, _ = verify_auth_token("my-secret-token", settings)
                assert valid is True
                
                valid, _ = verify_auth_token("wrong-token", settings)
                assert valid is False

    def test_verify_with_pin(self) -> None:
        import hashlib
        
        settings = make_settings(control_token="")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            pin_path = Path(tmpdir) / ".setup_pin"
            pin_hash = hashlib.sha256("123456".encode()).hexdigest()
            pin_path.write_text(pin_hash)
            
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                reset_setup_state()
                
                valid, _ = verify_auth_token("123456", settings)
                assert valid is True
                
                valid, _ = verify_auth_token("654321", settings)
                assert valid is False

    def test_verify_rejects_empty_token(self) -> None:
        settings = make_settings(control_token="")
        valid, error = verify_auth_token("", settings)
        assert valid is False
        assert "required" in error.lower()

    def test_rate_limiting(self) -> None:
        settings = make_settings(control_token="secret")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                reset_setup_state()
                
                for _ in range(5):
                    verify_auth_token("wrong", settings, client_ip="1.2.3.4")
                
                valid, error = verify_auth_token("wrong", settings, client_ip="1.2.3.4")
                assert valid is False
                assert "too many" in error.lower()


class TestResetConfigAndPin:
    def test_reset_in_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text('{"test": "data"}')
            pin_path = Path(tmpdir) / ".setup_pin"
            pin_path.write_text("test-hash")
            
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", config_path):
                reset_setup_state()
                
                success, message = reset_config_and_pin()
                
                assert success is True
                assert "reset complete" in message.lower()
                assert not pin_path.exists()
                assert not config_path.exists()

    def test_reset_outside_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                reset_setup_state()
                
                from reachy_mini_grokbot.settings_helpers import get_setup_state
                state = get_setup_state()
                state.app_start_time = time.time() - 600
                
                success, message = reset_config_and_pin()
                
                assert success is False
                assert "restart" in message.lower()


class TestGetSetupStatus:
    def test_setup_status_needs_setup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                reset_setup_state()
                
                status = get_setup_status()
                
                assert status["has_pin"] is False
                assert status["needs_first_run_setup"] is True
                assert status["setup_window_open"] is True

    def test_setup_status_has_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pin_path = Path(tmpdir) / ".setup_pin"
            pin_path.write_text("test-hash")
            
            with patch("reachy_mini_grokbot.settings_helpers.CONFIG_PATH", Path(tmpdir) / "config.json"):
                reset_setup_state()
                
                status = get_setup_status()
                
                assert status["has_pin"] is True
                assert status["needs_first_run_setup"] is False


class TestCheckGeminiKey:
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
        
        sa_data, error = parse_service_account_json(sa_json)
        assert error is None
        assert sa_data["type"] == "service_account"

    def test_invalid_type_rejected(self) -> None:
        sa_json = json.dumps({"type": "oauth", "client_email": "test@example.com"})
        
        sa_data, error = parse_service_account_json(sa_json)
        assert sa_data is None
        assert "type" in error.lower()

    def test_missing_client_email_rejected(self) -> None:
        sa_json = json.dumps({"type": "service_account"})
        
        sa_data, error = parse_service_account_json(sa_json)
        assert sa_data is None
        assert "client_email" in error.lower()


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
                reset_setup_state()
                
                success, _ = create_pin("123456")
                assert success
                
                pin_path = Path(tmpdir) / ".setup_pin"
                mode = pin_path.stat().st_mode & 0o777
                assert mode == 0o600
