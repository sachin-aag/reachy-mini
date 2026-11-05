"""Base class for mode handlers."""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from reachy_mini_grokbot.body import RobotBody
    from reachy_mini_grokbot.config import Settings
    from reachy_mini_grokbot.control_client import ControlState


logger = logging.getLogger(__name__)


class ModeHandler(ABC):
    """Base class for mode handlers.
    
    Each mode (idle, scribe, docs_chat) subclasses this and implements:
    - start(): called when entering this mode
    - stop(): called when leaving this mode (must be idempotent)
    - update(state): called when state changes while in this mode
    
    The handler has access to the robot body and settings for robot control.
    """

    name: str = "base"

    def __init__(
        self,
        body: "RobotBody",
        settings: "Settings",
        reachy_mini: Any = None,
    ) -> None:
        self.body = body
        self.settings = settings
        self.reachy_mini = reachy_mini
        self._running = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        """True if the mode is currently active."""
        with self._lock:
            return self._running

    def start(self, state: "ControlState") -> None:
        """Start this mode. Called when transitioning into this mode."""
        with self._lock:
            if self._running:
                return
            self._running = True
        logger.info("Mode %s starting", self.name)
        try:
            self._on_start(state)
        except Exception:
            logger.exception("Mode %s start failed", self.name)

    def stop(self) -> None:
        """Stop this mode. Must be idempotent."""
        with self._lock:
            if not self._running:
                return
            self._running = False
        logger.info("Mode %s stopping", self.name)
        try:
            self._on_stop()
        except Exception:
            logger.exception("Mode %s stop failed", self.name)

    def update(self, state: "ControlState") -> None:
        """Update while in this mode (e.g., different target doc)."""
        if not self.is_running:
            return
        try:
            self._on_update(state)
        except Exception:
            logger.exception("Mode %s update failed", self.name)

    @abstractmethod
    def _on_start(self, state: "ControlState") -> None:
        """Subclass implementation of start behavior."""
        ...

    @abstractmethod
    def _on_stop(self) -> None:
        """Subclass implementation of stop behavior."""
        ...

    def _on_update(self, state: "ControlState") -> None:
        """Subclass implementation of update behavior. Default is no-op."""
        pass
