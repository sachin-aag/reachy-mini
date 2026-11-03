"""Streamable HTTP MCP server for Grok Bot custom connectors."""

from __future__ import annotations

import hmac
import logging
import threading
from typing import Any
from urllib.parse import parse_qs, urlparse

from reachy_mini_grokbot.config import Settings
from reachy_mini_grokbot import tools


logger = logging.getLogger(__name__)


def allowed_hosts(settings: Settings) -> list[str]:
    """Host headers MCP accepts: loopback, plus the tunnel's public hostname."""
    hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    public = urlparse(settings.public_base_url).hostname if settings.public_base_url else None
    if public:
        hosts.append(public)
        hosts.append(f"{public}:*")
    return hosts


def build_mcp(settings: Settings):
    """Create the FastMCP app. Imported lazily so unit tests skip the MCP SDK."""
    from mcp.server.fastmcp import FastMCP
    from mcp.server.transport_security import TransportSecuritySettings

    mcp = FastMCP(
        "reachy-mini",
        host=settings.mcp_host,
        port=settings.mcp_port,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts(settings),
        ),
        instructions=(
            "You are driving a Pollen Robotics Reachy Mini. "
            "After answering the human, call speak() with a short spoken reply. "
            "Use show() or dance() for expression. Use look() to attend. "
            "Prefer show() for the 12 built-in emotions; use show(move=...) or "
            "discover() for Pollen recorded clips. "
            "If this task belongs to another Grok Bot, hand it off, then speak the result."
        ),
    )

    @mcp.tool()
    def speak(text: str, voice: str = "eve") -> str:
        """Speak through the robot. Supports [move:name] markers in the text."""
        return tools.speak(text, voice=voice)

    @mcp.tool()
    def look(direction: str = "", roll: float = 0, pitch: float = 0, yaw: float = 0, duration: float = 1.0) -> str:
        """Look left/right/up/down/front, or set roll/pitch/yaw in degrees."""
        return tools.look(direction=direction, roll=roll, pitch=pitch, yaw=yaw, duration=duration)

    @mcp.tool()
    def show(emotion: str = "neutral", move: str = "") -> str:
        """Express a built-in emotion, or play a recorded Pollen move by name."""
        return tools.show(emotion=emotion, move=move)

    @mcp.tool()
    def dance(name: str = "happy") -> str:
        """Play a recorded dance. Falls back to a built-in expression."""
        return tools.dance(name)

    @mcp.tool()
    def rest(mode: str = "neutral") -> str:
        """neutral, sleep, or wake."""
        return tools.rest(mode)

    @mcp.tool()
    def snap() -> str:
        """Capture the robot camera as a JPEG data URL."""
        return tools.snap()

    @mcp.tool()
    def discover(library: str = "emotions") -> str:
        """List recorded moves. library is emotions or dances."""
        return tools.discover(library)

    return mcp


class RequireToken:
    """ASGI guard: accept `Authorization: Bearer <token>` or `?token=<token>`."""

    def __init__(self, app: Any, token: str) -> None:
        self.app = app
        self.token = token.encode()

    def _presented(self, scope: dict[str, Any]) -> bytes:
        for key, value in scope.get("headers", []):
            if key == b"authorization" and value.lower().startswith(b"bearer "):
                return value[7:].strip()
        query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        return query.get("token", [""])[0].encode()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http" and not hmac.compare_digest(self._presented(scope), self.token):
            await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": b"Unauthorized"})
            return
        await self.app(scope, receive, send)


def start_mcp_thread(settings: Settings) -> threading.Thread | None:
    """Serve MCP over streamable HTTP. Returns None if it cannot start."""
    if not settings.mcp_token:
        logger.error("MCP not started: set MCP_TOKEN in .env so the public endpoint is not open")
        return None
    try:
        import uvicorn

        mcp = build_mcp(settings)
        app = RequireToken(mcp.streamable_http_app(), settings.mcp_token)
    except Exception as exc:
        logger.warning("MCP server not started: %s", exc)
        return None

    def _run() -> None:
        try:
            uvicorn.run(app, host=settings.mcp_host, port=settings.mcp_port, log_level="warning")
        except Exception:
            logger.exception("MCP server exited")

    thread = threading.Thread(target=_run, name="reachy-mcp", daemon=True)
    thread.start()
    logger.info("MCP listening on %s:%s/mcp", settings.mcp_host, settings.mcp_port)
    return thread
