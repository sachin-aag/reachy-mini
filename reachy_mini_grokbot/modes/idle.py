"""Idle mode: robot at rest, waiting for commands."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from reachy_mini_grokbot.modes.base import ModeHandler

if TYPE_CHECKING:
    from reachy_mini_grokbot.control_client import ControlState


logger = logging.getLogger(__name__)


class IdleMode(ModeHandler):
    """Idle mode: robot shows listening pose and waits.
    
    In idle mode, the robot:
    - Shows a neutral/listening expression
    - Responds to MCP/REST tool calls (speak, show, etc.)
    - Waits for mode change from the control endpoint
    """

    name = "idle"

    def _on_start(self, state: "ControlState") -> None:
        """Enter idle: show listening pose."""
        try:
            self.body.show("listening")
            logger.info("Idle mode: listening pose")
        except Exception as exc:
            logger.warning("Could not show listening pose: %s", exc)

    def _on_stop(self) -> None:
        """Exit idle: return to neutral."""
        try:
            self.body.show("neutral")
        except Exception as exc:
            logger.debug("Could not show neutral pose on idle exit: %s", exc)
