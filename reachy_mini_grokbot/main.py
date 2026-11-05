"""Reachy Mini app: body for a Grok Bot chief of staff with remote mode control."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from reachy_mini import ReachyMini, ReachyMiniApp

from reachy_mini_grokbot.body import RobotBody
from reachy_mini_grokbot.config import load_settings, save_config_file
from reachy_mini_grokbot.expressions import BUILTIN_EMOTIONS
from reachy_mini_grokbot.mcp_server import start_mcp_thread
from reachy_mini_grokbot.mode_controller import ModeController
from reachy_mini_grokbot.settings_helpers import (
    check_gemini_key,
    create_pin,
    get_setup_status,
    mask_secret,
    parse_service_account_json,
    reset_config_and_pin,
    save_service_account,
    verify_auth_token,
)
from reachy_mini_grokbot.tools import bind_runtime, tool_dispatch
from reachy_mini_grokbot.webhook import notify_chief_of_staff


logger = logging.getLogger("reachy_mini.app")


class Utterance(BaseModel):
    """Text to send to the chief of staff."""

    text: str = Field(min_length=1)
    session_id: str = "main"


class ToolCall(BaseModel):
    """REST fallback for Grok Bot computer-use if MCP is not connected."""

    name: str = ""
    arguments: dict[str, Any] = Field(default_factory=dict)


class ConfigUpdate(BaseModel):
    """Config update payload (non-secret fields via REST)."""

    REACHY_CONTROL_URL: str | None = None
    TTS_PROVIDER: str | None = None
    STT_PROVIDER: str | None = None
    TTS_VOICE: str | None = None
    TTS_LANGUAGE: str | None = None
    STT_CUSTOM_VOCABULARY: str | None = None


class SecretsUpdate(BaseModel):
    """Secret config update with auth token."""

    auth_token: str = Field(description="Setup PIN or control token for auth")
    GEMINI_API_KEY: str | None = None
    REACHY_CONTROL_TOKEN: str | None = None
    REACHY_CONTROL_URL: str | None = None
    XAI_API_KEY: str | None = None
    DEEPGRAM_API_KEY: str | None = None
    STT_CUSTOM_VOCABULARY: str | None = None


class ServiceAccountUpload(BaseModel):
    """Service account JSON upload with auth."""

    auth_token: str = Field(description="Setup PIN or control token for auth")
    service_account_json: str = Field(description="Base64-encoded JSON or raw JSON")


class GeminiTestRequest(BaseModel):
    """Test a Gemini API key."""

    api_key: str | None = Field(None, description="Key to test, or use configured key")
    auth_token: str = Field(description="Setup PIN or control token for auth")


class CreatePinRequest(BaseModel):
    """Create a new PIN during first-run setup."""

    pin: str = Field(min_length=6, description="PIN (min 6 digits)")


class ResetRequest(BaseModel):
    """Reset PIN and secrets (only works shortly after app restart)."""

    confirm: bool = Field(description="Must be true to confirm reset")


class ReachyMiniGrokbot(ReachyMiniApp):
    custom_app_url: str | None = "http://0.0.0.0:8042"
    request_media_backend: str | None = "recording"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._settings = load_settings()
        self._mode_controller: ModeController | None = None
        self._last_poll_time: datetime | None = None
        self._last_poll_success: bool = False
        self._register_routes()

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event) -> None:
        settings = self._settings
        body = RobotBody(reachy_mini)
        bind_runtime(body, settings)
        start_mcp_thread(settings)
        
        self._mode_controller = ModeController(body, settings, reachy_mini)
        self._mode_controller.start()

        logger.info(
            "Chief-of-staff: webhook=%s MCP=%s:%s control=%s",
            settings.webhook_configured,
            settings.mcp_host,
            settings.mcp_port,
            settings.control_configured,
        )
        
        while not stop_event.is_set():
            time.sleep(0.2)

        if self._mode_controller:
            self._mode_controller.stop()

        try:
            body.rest("neutral")
        except Exception as exc:
            logger.debug("Shutdown pose skipped: %s", exc)

    def _register_routes(self) -> None:
        app = self.settings_app
        if app is None:
            return
        settings = self._settings

        @app.get("/status")
        def status() -> dict[str, Any]:
            mode_info: dict[str, Any] = {"current_mode": "idle", "is_offline": True}
            last_poll_info: dict[str, Any] = {}
            
            if self._mode_controller:
                mode_info = {
                    "current_mode": self._mode_controller.current_mode,
                    "is_offline": self._mode_controller.is_offline,
                    "control_state": {
                        "mode": self._mode_controller.current_state.mode,
                        "version": self._mode_controller.current_state.version,
                        "updated_at": self._mode_controller.current_state.updated_at,
                    },
                }
                ctrl = self._mode_controller._control_client
                if ctrl:
                    last_poll_info = {
                        "last_poll_time": ctrl._last_success_time.isoformat() if ctrl._last_success_time else None,
                        "last_poll_success": ctrl._last_success_time is not None and not ctrl.is_offline,
                        "control_reachable": not ctrl.is_offline,
                    }
            
            return {
                "webhook_configured": settings.webhook_configured,
                "control_configured": settings.control_configured,
                "gemini_configured": settings.gemini_configured,
                "mcp_port": settings.mcp_port,
                "public_base_url": settings.public_base_url,
                "control_url": settings.control_url,
                "emotions": list(BUILTIN_EMOTIONS),
                **mode_info,
                **last_poll_info,
            }

        @app.get("/config")
        def get_config() -> dict[str, Any]:
            return {
                "REACHY_CONTROL_URL": settings.control_url,
                "TTS_PROVIDER": settings.tts_provider,
                "STT_PROVIDER": settings.stt_provider,
                "TTS_VOICE": settings.tts_voice,
                "TTS_LANGUAGE": settings.tts_language,
                "STT_CUSTOM_VOCABULARY": ",".join(settings.stt_custom_vocabulary),
                "webhook_configured": settings.webhook_configured,
                "control_configured": settings.control_configured,
                "gemini_configured": settings.gemini_configured,
                "gemini_key_masked": mask_secret(settings.gemini_api_key),
                "control_token_masked": mask_secret(settings.control_token),
                "xai_configured": bool(settings.xai_api_key),
                "xai_key_masked": mask_secret(settings.xai_api_key),
                "deepgram_configured": bool(settings.deepgram_api_key),
                "deepgram_key_masked": mask_secret(settings.deepgram_api_key),
                "google_credentials_configured": bool(settings.google_credentials_path),
                "google_credentials_path": settings.google_credentials_path or "",
            }

        @app.get("/setup-status")
        def setup_status() -> dict[str, Any]:
            """Get current setup status for first-run flow."""
            return get_setup_status()

        @app.post("/setup/create-pin")
        def create_setup_pin(payload: CreatePinRequest) -> dict[str, Any]:
            """Create a new PIN during first-run setup.
            
            Only works if:
            - No PIN exists yet
            - App is within the setup window (30 min after start)
            """
            success, message = create_pin(payload.pin)
            return {"success": success, "message": message}

        @app.post("/setup/reset")
        def reset_setup(payload: ResetRequest) -> dict[str, Any]:
            """Reset PIN and wipe all secrets.
            
            Only works within first 5 minutes after app restart.
            Use this if you forgot your PIN.
            """
            if not payload.confirm:
                return {"success": False, "message": "Must confirm reset."}
            
            success, message = reset_config_and_pin()
            if success:
                self._settings = load_settings()
            return {"success": success, "message": message}

        @app.post("/config")
        def update_config(payload: ConfigUpdate) -> dict[str, Any]:
            updates = {k: v for k, v in payload.model_dump().items() if v is not None}
            if updates:
                path = save_config_file(updates)
                return {"saved": True, "path": str(path), "updates": list(updates.keys())}
            return {"saved": False, "reason": "no updates provided"}

        @app.post("/config/secrets")
        def update_secrets(payload: SecretsUpdate) -> dict[str, Any]:
            """Update secret configuration with PIN/token auth."""
            valid, error = verify_auth_token(payload.auth_token, settings)
            if not valid:
                return {"saved": False, "error": error, "status_code": 401}
            
            updates = {}
            for key in ["GEMINI_API_KEY", "REACHY_CONTROL_TOKEN", "REACHY_CONTROL_URL", 
                       "XAI_API_KEY", "DEEPGRAM_API_KEY", "STT_CUSTOM_VOCABULARY"]:
                value = getattr(payload, key, None)
                if value is not None:
                    updates[key] = value
            
            if not updates:
                return {"saved": False, "reason": "no updates provided"}
            
            path = save_config_file(updates)
            
            self._settings = load_settings()
            
            return {
                "saved": True, 
                "path": str(path), 
                "updates": list(updates.keys()),
                "note": "Settings saved. Changes take effect immediately for new requests.",
            }

        @app.post("/config/service-account")
        def upload_service_account(payload: ServiceAccountUpload) -> dict[str, Any]:
            """Upload Google service account JSON."""
            valid, error = verify_auth_token(payload.auth_token, settings)
            if not valid:
                return {"saved": False, "error": error, "status_code": 401}
            
            sa_data, error = parse_service_account_json(payload.service_account_json)
            if error:
                return {"saved": False, "error": error}
            
            sa_path = save_service_account(payload.service_account_json, sa_data)
            save_config_file({"GOOGLE_APPLICATION_CREDENTIALS": str(sa_path)})
            self._settings = load_settings()
            
            return {
                "saved": True,
                "path": str(sa_path),
                "client_email": sa_data.get("client_email", "unknown"),
            }

        @app.post("/config/test-gemini")
        def test_gemini(payload: GeminiTestRequest) -> dict[str, Any]:
            """Test Gemini API key connectivity."""
            valid, error = verify_auth_token(payload.auth_token, settings)
            if not valid:
                return {"error": error, "status_code": 401}
            
            key_to_test = payload.api_key or settings.gemini_api_key
            if not key_to_test:
                return {"valid": False, "status": "No API key", "detail": "No key provided or configured"}
            
            result = check_gemini_key(key_to_test)
            return result

        @app.post("/utterance")
        def utterance(payload: Utterance) -> dict[str, Any]:
            try:
                return notify_chief_of_staff(
                    settings.webhook_url,
                    settings.webhook_key,
                    payload.text,
                    session_id=payload.session_id,
                )
            except (RuntimeError, ValueError) as exc:
                return {"accepted": False, "status_code": 400, "detail": str(exc)}

        @app.post("/tools/{name}")
        def call_tool(name: str, payload: ToolCall | None = None) -> dict[str, Any]:
            arguments = payload.arguments if payload is not None else {}
            if payload is not None and payload.name:
                name = payload.name
            result = tool_dispatch(name, arguments)
            return {"name": name, "result": result}


def launch() -> None:
    """Console entrypoint."""
    app = ReachyMiniGrokbot()
    try:
        app.wrapped_run()
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    launch()
