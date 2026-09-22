from reachy_mini_grokbot.config import load_settings


def test_webhook_configured_false_by_default(monkeypatch) -> None:
    monkeypatch.delenv("GROK_BOT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("GROK_BOT_WEBHOOK_KEY", raising=False)
    settings = load_settings()
    assert settings.webhook_configured is False


def test_webhook_configured_needs_both(monkeypatch) -> None:
    monkeypatch.setenv("GROK_BOT_WEBHOOK_URL", "https://example.test/hook")
    monkeypatch.setenv("GROK_BOT_WEBHOOK_KEY", "abc")
    settings = load_settings()
    assert settings.webhook_configured is True
    assert settings.mcp_port == 8765
