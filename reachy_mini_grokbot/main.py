"""Reachy Mini app: body for a Grok Bot chief of staff with remote mode control."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from pydantic import BaseModel, Field
from reachy_mini import ReachyMini, ReachyMiniApp

from reachy_mini_grokbot.body import RobotBody
from reachy_mini_grokbot.config import load_settings, save_config_file
from reachy_mini_grokbot.expressions import BUILTIN_EMOTIONS
from reachy_mini_grokbot.mcp_server import start_mcp_thread
from reachy_mini_grokbot.mode_controller import ModeController
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
    """Config update payload (only non-secret fields via REST)."""

    REACHY_CONTROL_URL: str | None = None
    TTS_PROVIDER: str | None = None
    STT_PROVIDER: str | None = None
    TTS_VOICE: str | None = None
    TTS_LANGUAGE: str | None = None


class ReachyMiniGrokbot(ReachyMiniApp):
    custom_app_url: str | None = "http://0.0.0.0:8042"
    request_media_backend: str | None = "recording"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._settings = load_settings()
        self._mode_controller: ModeController | None = None
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
            return {
                "webhook_configured": settings.webhook_configured,
                "control_configured": settings.control_configured,
                "mcp_port": settings.mcp_port,
                "public_base_url": settings.public_base_url,
                "control_url": settings.control_url,
                "emotions": list(BUILTIN_EMOTIONS),
                **mode_info,
            }

        @app.get("/config")
        def get_config() -> dict[str, Any]:
            return {
                "REACHY_CONTROL_URL": settings.control_url,
                "TTS_PROVIDER": settings.tts_provider,
                "STT_PROVIDER": settings.stt_provider,
                "TTS_VOICE": settings.tts_voice,
                "TTS_LANGUAGE": settings.tts_language,
                "webhook_configured": settings.webhook_configured,
                "control_configured": settings.control_configured,
                "gemini_configured": settings.gemini_configured,
                "xai_configured": bool(settings.xai_api_key),
                "deepgram_configured": bool(settings.deepgram_api_key),
                "google_credentials_configured": bool(settings.google_credentials_path),
            }

        @app.post("/config")
        def update_config(payload: ConfigUpdate) -> dict[str, Any]:
            updates = {k: v for k, v in payload.model_dump().items() if v is not None}
            if updates:
                path = save_config_file(updates)
                return {"saved": True, "path": str(path), "updates": list(updates.keys())}
            return {"saved": False, "reason": "no updates provided"}

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
