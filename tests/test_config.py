"""Tests for configuration loading."""

from reachy_mini_grokbot.config import load_settings


def test_gemini_configured_when_key_set(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    settings = load_settings()
    assert settings.gemini_configured is True


def test_gemini_not_configured_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings = load_settings()
    assert settings.gemini_configured is False


def test_tts_provider_defaults_to_gemini(monkeypatch) -> None:
    monkeypatch.delenv("TTS_PROVIDER", raising=False)
    settings = load_settings()
    assert settings.tts_provider == "gemini"


def test_tts_provider_can_be_xai(monkeypatch) -> None:
    monkeypatch.setenv("TTS_PROVIDER", "xai")
    settings = load_settings()
    assert settings.tts_provider == "xai"


def test_stt_provider_defaults_to_gemini(monkeypatch) -> None:
    monkeypatch.delenv("STT_PROVIDER", raising=False)
    settings = load_settings()
    assert settings.stt_provider == "gemini"


def test_tts_configured_with_gemini(monkeypatch) -> None:
    monkeypatch.setenv("TTS_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    settings = load_settings()
    assert settings.tts_configured is True


def test_tts_configured_with_xai(monkeypatch) -> None:
    monkeypatch.setenv("TTS_PROVIDER", "xai")
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    settings = load_settings()
    assert settings.tts_configured is True


def test_tts_not_configured_when_key_missing(monkeypatch) -> None:
    monkeypatch.setenv("TTS_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings = load_settings()
    assert settings.tts_configured is False


def test_control_configured_needs_both(monkeypatch) -> None:
    monkeypatch.setenv("REACHY_CONTROL_URL", "https://example.test")
    monkeypatch.setenv("REACHY_CONTROL_TOKEN", "test-token")
    settings = load_settings()
    assert settings.control_configured is True


def test_control_not_configured_without_token(monkeypatch) -> None:
    monkeypatch.setenv("REACHY_CONTROL_URL", "https://example.test")
    monkeypatch.delenv("REACHY_CONTROL_TOKEN", raising=False)
    settings = load_settings()
    assert settings.control_configured is False


def test_webhook_configured_needs_both(monkeypatch) -> None:
    monkeypatch.setenv("GROK_BOT_WEBHOOK_URL", "https://example.test/hook")
    monkeypatch.setenv("GROK_BOT_WEBHOOK_KEY", "abc")
    settings = load_settings()
    assert settings.webhook_configured is True


def test_webhook_not_configured_by_default(monkeypatch) -> None:
    monkeypatch.delenv("GROK_BOT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("GROK_BOT_WEBHOOK_KEY", raising=False)
    settings = load_settings()
    assert settings.webhook_configured is False


def test_default_voice_is_kore(monkeypatch) -> None:
    monkeypatch.delenv("TTS_VOICE", raising=False)
    settings = load_settings()
    assert settings.tts_voice == "Kore"


def test_mcp_port_defaults_to_8765(monkeypatch) -> None:
    monkeypatch.delenv("MCP_PORT", raising=False)
    settings = load_settings()
    assert settings.mcp_port == 8765
