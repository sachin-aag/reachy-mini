"""Streamable HTTP MCP server for Grok Bot custom connectors."""

from __future__ import annotations

import logging
import threading

from reachy_mini_grokbot.config import Settings
from reachy_mini_grokbot import tools


logger = logging.getLogger(__name__)


def build_mcp():
    """Create the FastMCP app. Imported lazily so unit tests skip the MCP SDK."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "reachy-mini",
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


def start_mcp_thread(settings: Settings) -> threading.Thread | None:
    """Serve MCP over streamable HTTP. Returns None if the SDK cannot start."""
    try:
        mcp = build_mcp()
    except Exception as exc:
        logger.warning("MCP server not started: %s", exc)
        return None

    def _run() -> None:
        try:
            mcp.run(transport="streamable-http", host=settings.mcp_host, port=settings.mcp_port)
        except TypeError:
            mcp.run(transport="sse", host=settings.mcp_host, port=settings.mcp_port)
        except Exception:
            logger.exception("MCP server exited")

    thread = threading.Thread(target=_run, name="reachy-mcp", daemon=True)
    thread.start()
    logger.info("MCP listening on %s:%s", settings.mcp_host, settings.mcp_port)
    return thread
