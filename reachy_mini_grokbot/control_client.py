"""Client for polling the remote control state endpoint.

Polls GET {REACHY_CONTROL_URL}/api/reachy/state with ETag/If-None-Match support.
Never logs the token. On network errors, stays in current mode (or idle after timeout).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Literal

import httpx

from reachy_mini_grokbot.config import Settings


logger = logging.getLogger(__name__)

Mode = Literal["idle", "scribe", "docs_chat"]


@dataclass
class ControlState:
    """State returned from the remote control endpoint."""

    mode: Mode = "idle"
    target_doc_id: str | None = None
    doc_ids: list[str] = field(default_factory=list)
    source_folder_id: str | None = None
    version: int = 0
    updated_at: str | None = None
    etag: str | None = None

    @classmethod
    def from_response(cls, data: dict, etag: str | None = None) -> "ControlState":
        """Parse state from API response JSON."""
        raw_mode = data.get("mode", "idle")
        mode: Mode = raw_mode if raw_mode in ("idle", "scribe", "docs_chat") else "idle"
        return cls(
            mode=mode,
            target_doc_id=data.get("targetDocId"),
            doc_ids=data.get("docIds") or [],
            source_folder_id=data.get("sourceFolderId"),
            version=data.get("version", 0),
            updated_at=data.get("updatedAt"),
            etag=etag,
        )


class ControlClient:
    """Polls the remote control endpoint with ETag caching and error backoff."""

    def __init__(
        self,
        settings: Settings,
        on_state_change: Callable[[ControlState], None] | None = None,
    ) -> None:
        self._settings = settings
        self._on_state_change = on_state_change
        self._current_state = ControlState()
        self._etag: str | None = None
        self._consecutive_errors = 0
        self._last_success_time = time.monotonic()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def current_state(self) -> ControlState:
        """Return the last known control state."""
        with self._lock:
            return self._current_state

    @property
    def is_offline(self) -> bool:
        """True if we haven't reached the server in longer than the offline timeout."""
        timeout = self._settings.control_offline_timeout
        return (time.monotonic() - self._last_success_time) > timeout

    def _build_url(self) -> str:
        """Build the full endpoint URL."""
        base = self._settings.control_url.rstrip("/")
        return f"{base}/api/reachy/state"

    def _make_request(self) -> ControlState | None:
        """Make a single poll request. Returns new state or None on 304/error."""
        url = self._build_url()
        headers = {"Authorization": f"Bearer {self._settings.control_token}"}
        if self._etag:
            headers["If-None-Match"] = self._etag

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)

            if response.status_code == 304:
                self._consecutive_errors = 0
                self._last_success_time = time.monotonic()
                return None

            if response.status_code == 401:
                logger.error("Control endpoint returned 401 Unauthorized - check REACHY_CONTROL_TOKEN")
                self._consecutive_errors += 1
                return None

            if response.status_code != 200:
                logger.warning("Control endpoint returned %d", response.status_code)
                self._consecutive_errors += 1
                return None

            self._consecutive_errors = 0
            self._last_success_time = time.monotonic()
            new_etag = response.headers.get("ETag")
            self._etag = new_etag
            return ControlState.from_response(response.json(), etag=new_etag)

        except httpx.TimeoutException:
            logger.warning("Control endpoint request timed out")
            self._consecutive_errors += 1
            return None
        except httpx.RequestError as exc:
            logger.warning("Control endpoint network error: %s", type(exc).__name__)
            self._consecutive_errors += 1
            return None

    def _backoff_seconds(self) -> float:
        """Calculate backoff time based on consecutive errors."""
        if self._consecutive_errors == 0:
            return self._settings.control_poll_interval
        backoff = min(30.0, self._settings.control_poll_interval * (2 ** self._consecutive_errors))
        return backoff

    def poll_once(self) -> ControlState:
        """Poll the endpoint once and return the current state."""
        new_state = self._make_request()
        if new_state is not None:
            with self._lock:
                old_mode = self._current_state.mode
                self._current_state = new_state
            if new_state.mode != old_mode and self._on_state_change:
                try:
                    self._on_state_change(new_state)
                except Exception:
                    logger.exception("on_state_change callback failed")
        return self.current_state

    def _poll_loop(self) -> None:
        """Background polling loop."""
        logger.info("Control client polling started")
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception:
                logger.exception("Unexpected error in poll loop")
                self._consecutive_errors += 1

            wait_time = self._backoff_seconds()
            self._stop_event.wait(wait_time)
        logger.info("Control client polling stopped")

    def start(self) -> None:
        """Start the background polling thread."""
        if not self._settings.control_configured:
            logger.warning("Control client not started: REACHY_CONTROL_TOKEN not set")
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, name="control-poller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the background polling thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
