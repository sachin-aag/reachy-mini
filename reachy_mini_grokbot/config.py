"""Environment configuration. Secrets stay in the environment, never in git.

On the robot, config can also be loaded from a file (default ~/.reachy_grokbot/config.json)
with chmod 600 for secrets. Environment variables override the file.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".reachy_grokbot" / "config.json"
DEFAULT_CONTROL_URL = "https://creators-ecosystem.de"

TTSProvider = Literal["gemini", "xai", "deepgram"]
STTProvider = Literal["gemini", "deepgram"]


def _load_config_file(path: Path | None = None) -> dict[str, Any]:
    """Load config from JSON file if it exists. Returns empty dict on error."""
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load config from %s: %s", config_path, exc)
        return {}


def _env(name: str, default: str = "", file_config: dict[str, Any] | None = None) -> str:
    """Get config value: env var wins, then file, then default."""
    env_val = os.environ.get(name)
    if env_val is not None:
        return env_val.strip() if env_val else default
    if file_config:
        file_val = file_config.get(name)
        if file_val is not None:
            return str(file_val).strip()
    return default


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from the environment and/or config file.
    
    Primary provider: Google Gemini (GEMINI_API_KEY required)
    Fallback providers: xAI (XAI_API_KEY), Deepgram (DEEPGRAM_API_KEY)
    """

    gemini_api_key: str
    google_credentials_path: str
    control_url: str
    control_token: str
    control_poll_interval: float
    control_offline_timeout: float
    
    tts_provider: TTSProvider
    stt_provider: STTProvider
    tts_voice: str
    tts_language: str
    
    gemini_tts_model: str
    gemini_stt_model: str
    gemini_stt_live_model: str
    gemini_live_model: str
    gemini_chat_model: str
    
    stt_custom_vocabulary: list[str]
    
    xai_api_key: str
    deepgram_api_key: str
    
    webhook_url: str
    webhook_key: str
    public_base_url: str
    mcp_host: str
    mcp_port: int
    mcp_token: str

    @property
    def webhook_configured(self) -> bool:
        """True when a routine webhook URL and key are both set."""
        return bool(self.webhook_url and self.webhook_key)

    @property
    def control_configured(self) -> bool:
        """True when the remote control endpoint can be polled."""
        return bool(self.control_url and self.control_token)

    @property
    def gemini_configured(self) -> bool:
        """True when Gemini API key is set."""
        return bool(self.gemini_api_key)

    @property
    def tts_configured(self) -> bool:
        """True when at least one TTS provider is configured."""
        if self.tts_provider == "gemini":
            return bool(self.gemini_api_key)
        elif self.tts_provider == "xai":
            return bool(self.xai_api_key)
        elif self.tts_provider == "deepgram":
            return bool(self.deepgram_api_key)
        return False

    @property
    def stt_configured(self) -> bool:
        """True when at least one STT provider is configured."""
        if self.stt_provider == "gemini":
            return bool(self.gemini_api_key)
        elif self.stt_provider == "deepgram":
            return bool(self.deepgram_api_key)
        return False


def load_settings(config_path: Path | None = None) -> Settings:
    """Load settings from process environment, with file fallback."""
    file_config = _load_config_file(config_path)
    
    tts_provider_raw = _env("TTS_PROVIDER", "gemini", file_config=file_config).lower()
    tts_provider: TTSProvider = tts_provider_raw if tts_provider_raw in ("gemini", "xai", "deepgram") else "gemini"
    
    stt_provider_raw = _env("STT_PROVIDER", "gemini", file_config=file_config).lower()
    stt_provider: STTProvider = stt_provider_raw if stt_provider_raw in ("gemini", "deepgram") else "gemini"
    
    custom_vocab_raw = _env("STT_CUSTOM_VOCABULARY", "Reachy,Reachy Mini,Grok,Grok Bot", file_config=file_config)
    custom_vocabulary = [v.strip() for v in custom_vocab_raw.split(",") if v.strip()]
    
    return Settings(
        gemini_api_key=_env("GEMINI_API_KEY", file_config=file_config),
        google_credentials_path=_env("GOOGLE_APPLICATION_CREDENTIALS", file_config=file_config),
        control_url=_env("REACHY_CONTROL_URL", DEFAULT_CONTROL_URL, file_config=file_config),
        control_token=_env("REACHY_CONTROL_TOKEN", file_config=file_config),
        control_poll_interval=float(_env("REACHY_CONTROL_POLL_INTERVAL", "3.0", file_config=file_config) or "3.0"),
        control_offline_timeout=float(_env("REACHY_CONTROL_OFFLINE_TIMEOUT", "30.0", file_config=file_config) or "30.0"),
        tts_provider=tts_provider,
        stt_provider=stt_provider,
        tts_voice=_env("TTS_VOICE", "Kore", file_config=file_config) or "Kore",
        tts_language=_env("TTS_LANGUAGE", "en", file_config=file_config) or "en",
        gemini_tts_model=_env("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts", file_config=file_config),
        gemini_stt_model=_env("GEMINI_STT_MODEL", "gemini-3.5-transcribe", file_config=file_config),
        gemini_stt_live_model=_env("GEMINI_STT_LIVE_MODEL", "gemini-3.5-transcribe-live", file_config=file_config),
        gemini_live_model=_env("GEMINI_LIVE_MODEL", "gemini-3.8-live", file_config=file_config),
        gemini_chat_model=_env("GEMINI_CHAT_MODEL", "gemini-3.8-flash", file_config=file_config),
        stt_custom_vocabulary=custom_vocabulary,
        xai_api_key=_env("XAI_API_KEY", file_config=file_config),
        deepgram_api_key=_env("DEEPGRAM_API_KEY", file_config=file_config),
        webhook_url=_env("GROK_BOT_WEBHOOK_URL", file_config=file_config),
        webhook_key=_env("GROK_BOT_WEBHOOK_KEY", file_config=file_config),
        public_base_url=_env("PUBLIC_BASE_URL", file_config=file_config),
        mcp_host=_env("MCP_HOST", "127.0.0.1", file_config=file_config),
        mcp_port=int(_env("MCP_PORT", "8765", file_config=file_config) or "8765"),
        mcp_token=_env("MCP_TOKEN", file_config=file_config),
    )


def save_config_file(
    config: dict[str, Any],
    path: Path | None = None,
    merge: bool = True,
) -> Path:
    """Save config to JSON file with secure permissions. Returns the path used."""
    config_path = path or DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    if merge and config_path.exists():
        existing = _load_config_file(config_path)
        existing.update(config)
        config = existing
    
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    os.chmod(config_path, 0o600)
    return config_path
