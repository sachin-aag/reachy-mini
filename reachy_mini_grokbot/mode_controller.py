"""Mode controller: manages clean start/stop of mode handlers on state changes."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

from reachy_mini_grokbot.control_client import ControlClient, ControlState, Mode
from reachy_mini_grokbot.modes import DocsChatMode, IdleMode, ModeHandler, ScribeMode

if TYPE_CHECKING:
    from reachy_mini_grokbot.body import RobotBody
    from reachy_mini_grokbot.config import Settings


logger = logging.getLogger(__name__)


class ModeController:
    """Manages mode transitions based on control client state.
    
    The controller:
    - Creates and manages mode handler instances
    - Cleanly stops the current mode before starting a new one
    - Handles the control client polling lifecycle
    - Falls back to idle on offline timeout
    """

    def __init__(
        self,
        body: "RobotBody",
        settings: "Settings",
        reachy_mini: Any = None,
    ) -> None:
        self.body = body
        self.settings = settings
        self.reachy_mini = reachy_mini
        self._lock = threading.Lock()
        
        self._modes: dict[Mode, ModeHandler] = {
            "idle": IdleMode(body, settings, reachy_mini),
            "scribe": ScribeMode(body, settings, reachy_mini),
            "docs_chat": DocsChatMode(body, settings, reachy_mini),
        }
        
        self._current_mode: Mode = "idle"
        self._current_handler: ModeHandler | None = None
        
        self._control_client = ControlClient(
            settings,
            on_state_change=self._on_state_change,
        )
        
        self._offline_check_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def current_mode(self) -> Mode:
        """Return the current mode name."""
        with self._lock:
            return self._current_mode

    @property
    def current_state(self) -> ControlState:
        """Return the current control state."""
        return self._control_client.current_state

    @property
    def is_offline(self) -> bool:
        """True if control endpoint is unreachable past the timeout."""
        return self._control_client.is_offline

    def _on_state_change(self, state: ControlState) -> None:
        """Callback from control client when state changes."""
        self._transition_to(state.mode, state)

    def _transition_to(self, new_mode: Mode, state: ControlState) -> None:
        """Transition from current mode to a new mode."""
        with self._lock:
            if new_mode == self._current_mode and self._current_handler is not None:
                self._current_handler.update(state)
                return
            
            old_mode = self._current_mode
            logger.info("Mode transition: %s -> %s", old_mode, new_mode)
            
            if self._current_handler:
                self._current_handler.stop()
            
            self._current_mode = new_mode
            self._current_handler = self._modes.get(new_mode)
            
            if self._current_handler:
                self._current_handler.start(state)
            else:
                logger.error("Unknown mode: %s, falling back to idle", new_mode)
                self._current_mode = "idle"
                self._current_handler = self._modes["idle"]
                self._current_handler.start(state)

    def _offline_check_loop(self) -> None:
        """Periodically check if we've gone offline and should return to idle."""
        while not self._stop_event.is_set():
            self._stop_event.wait(5.0)
            if self._stop_event.is_set():
                break
            
            if self._control_client.is_offline:
                with self._lock:
                    if self._current_mode != "idle":
                        logger.warning("Control endpoint offline, returning to idle")
                        self._transition_to("idle", ControlState())

    def start(self) -> None:
        """Start the mode controller and control client polling."""
        logger.info("Mode controller starting")
        
        initial_state = ControlState(mode="idle")
        self._transition_to("idle", initial_state)
        
        self._control_client.start()
        
        self._stop_event.clear()
        self._offline_check_thread = threading.Thread(
            target=self._offline_check_loop,
            name="offline-check",
            daemon=True,
        )
        self._offline_check_thread.start()
        
        logger.info("Mode controller started, current mode: %s", self._current_mode)

    def stop(self) -> None:
        """Stop the mode controller and all handlers."""
        logger.info("Mode controller stopping")
        
        self._stop_event.set()
        
        self._control_client.stop()
        
        if self._offline_check_thread is not None:
            self._offline_check_thread.join(timeout=5.0)
            self._offline_check_thread = None
        
        with self._lock:
            if self._current_handler:
                self._current_handler.stop()
                self._current_handler = None
            self._current_mode = "idle"
        
        logger.info("Mode controller stopped")

    def force_mode(self, mode: Mode) -> None:
        """Force a mode change (for testing or manual override)."""
        state = ControlState(mode=mode)
        self._transition_to(mode, state)
