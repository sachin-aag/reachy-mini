"""Environment configuration. Secrets stay in the environment, never in git."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name, default)
    return value.strip() if value else default


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from the environment."""

    daemon_url: str
    webhook_url: str
    webhook_key: str
    public_base_url: str
    mcp_host: str
    mcp_port: int
    xai_api_key: str
    grok_voice: str
    deepgram_api_key: str

    @property
    def webhook_configured(self) -> bool:
        """True when a routine webhook URL and key are both set."""
        return bool(self.webhook_url and self.webhook_key)


def load_settings() -> Settings:
    """Load settings from process environment."""
    return Settings(
        daemon_url=_env("REACHY_DAEMON_URL", "http://127.0.0.1:8000/api"),
        webhook_url=_env("GROK_BOT_WEBHOOK_URL"),
        webhook_key=_env("GROK_BOT_WEBHOOK_KEY"),
        public_base_url=_env("PUBLIC_BASE_URL"),
        mcp_host=_env("MCP_HOST", "0.0.0.0"),
        mcp_port=int(_env("MCP_PORT", "8765") or "8765"),
        xai_api_key=_env("XAI_API_KEY"),
        grok_voice=_env("GROK_VOICE", "eve") or "eve",
        deepgram_api_key=_env("DEEPGRAM_API_KEY"),
    )
