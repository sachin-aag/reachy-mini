"""Reachy Mini app: body for a Grok Bot chief of staff."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from pydantic import BaseModel, Field
from reachy_mini import ReachyMini, ReachyMiniApp

from reachy_mini_grokbot.body import RobotBody
from reachy_mini_grokbot.config import load_settings
from reachy_mini_grokbot.expressions import BUILTIN_EMOTIONS
from reachy_mini_grokbot.mcp_server import start_mcp_thread
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


class ReachyMiniGrokbot(ReachyMiniApp):
    custom_app_url: str | None = "http://0.0.0.0:8042"
    request_media_backend: str | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._settings = load_settings()
        self._register_routes()

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event) -> None:
        settings = self._settings
        body = RobotBody(reachy_mini)
        bind_runtime(body, settings)
        start_mcp_thread(settings)
        try:
            body.show("listening")
        except Exception as exc:
            logger.warning("Could not take listening pose: %s", exc)

        logger.info(
            "Chief-of-staff webhook configured=%s MCP=%s:%s",
            settings.webhook_configured,
            settings.mcp_host,
            settings.mcp_port,
        )
        while not stop_event.is_set():
            time.sleep(0.2)

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
            return {
                "webhook_configured": settings.webhook_configured,
                "mcp_port": settings.mcp_port,
                "public_base_url": settings.public_base_url,
                "emotions": list(BUILTIN_EMOTIONS),
            }

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
