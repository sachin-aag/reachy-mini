"""Helper functions for the settings API.

These are separate from main.py to allow testing without the reachy_mini SDK.

First-Run Setup Flow:
1. If no PIN exists and app started within SETUP_WINDOW_MINUTES, allow PIN creation
2. PIN must be at least 6 digits
3. After PIN is set OR setup window closes, require PIN or control token for changes
4. Forgot PIN: reset only works within first minutes after app restart, wipes secrets
5. Rate-limit PIN attempts to prevent brute force
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

import httpx

from reachy_mini_grokbot.config import CONFIG_PATH

if TYPE_CHECKING:
    from reachy_mini_grokbot.config import Settings


SETUP_WINDOW_MINUTES = 30
RESET_WINDOW_MINUTES = 5
PIN_MIN_LENGTH = 6
MAX_PIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300


@dataclass
class SetupState:
    """Track first-run setup and rate limiting state."""
    
    app_start_time: float = field(default_factory=time.time)
    pin_attempts: dict[str, list[float]] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)
    
    def is_in_setup_window(self) -> bool:
        """True if still within the initial setup window."""
        elapsed = time.time() - self.app_start_time
        return elapsed < (SETUP_WINDOW_MINUTES * 60)
    
    def is_in_reset_window(self) -> bool:
        """True if within the reset window after app restart."""
        elapsed = time.time() - self.app_start_time
        return elapsed < (RESET_WINDOW_MINUTES * 60)
    
    def get_setup_window_remaining(self) -> int:
        """Seconds remaining in setup window, or 0 if closed."""
        elapsed = time.time() - self.app_start_time
        remaining = (SETUP_WINDOW_MINUTES * 60) - elapsed
        return max(0, int(remaining))
    
    def get_reset_window_remaining(self) -> int:
        """Seconds remaining in reset window, or 0 if closed."""
        elapsed = time.time() - self.app_start_time
        remaining = (RESET_WINDOW_MINUTES * 60) - elapsed
        return max(0, int(remaining))
    
    def check_rate_limit(self, client_ip: str) -> tuple[bool, str]:
        """Check if client is rate-limited. Returns (allowed, message)."""
        with self._lock:
            now = time.time()
            cutoff = now - LOCKOUT_SECONDS
            
            if client_ip not in self.pin_attempts:
                self.pin_attempts[client_ip] = []
            
            self.pin_attempts[client_ip] = [
                t for t in self.pin_attempts[client_ip] if t > cutoff
            ]
            
            if len(self.pin_attempts[client_ip]) >= MAX_PIN_ATTEMPTS:
                oldest = min(self.pin_attempts[client_ip])
                wait_time = int(oldest + LOCKOUT_SECONDS - now)
                return False, f"Too many attempts. Try again in {wait_time} seconds."
            
            return True, ""
    
    def record_failed_attempt(self, client_ip: str) -> None:
        """Record a failed PIN attempt."""
        with self._lock:
            if client_ip not in self.pin_attempts:
                self.pin_attempts[client_ip] = []
            self.pin_attempts[client_ip].append(time.time())
    
    def clear_attempts(self, client_ip: str) -> None:
        """Clear failed attempts on successful auth."""
        with self._lock:
            self.pin_attempts.pop(client_ip, None)


_setup_state: SetupState | None = None


def get_setup_state() -> SetupState:
    """Get or create the global setup state."""
    global _setup_state
    if _setup_state is None:
        _setup_state = SetupState()
    return _setup_state


def reset_setup_state() -> None:
    """Reset setup state (for testing)."""
    global _setup_state
    _setup_state = None


def pin_exists() -> bool:
    """Check if a PIN has been set."""
    pin_path = CONFIG_PATH.parent / ".setup_pin"
    return pin_path.exists() and bool(pin_path.read_text().strip())


def get_setup_status() -> dict[str, Any]:
    """Get current setup status for the UI."""
    state = get_setup_state()
    has_pin = pin_exists()
    
    return {
        "has_pin": has_pin,
        "needs_first_run_setup": not has_pin and state.is_in_setup_window(),
        "setup_window_open": state.is_in_setup_window(),
        "setup_window_remaining_seconds": state.get_setup_window_remaining(),
        "reset_window_open": state.is_in_reset_window(),
        "reset_window_remaining_seconds": state.get_reset_window_remaining(),
    }


def create_pin(pin: str) -> tuple[bool, str]:
    """Create a new PIN during first-run setup.
    
    Returns (success, message).
    """
    state = get_setup_state()
    
    if pin_exists():
        return False, "PIN already exists. Use forgot PIN to reset."
    
    if not state.is_in_setup_window():
        return False, "Setup window has closed. Restart the app to set up again."
    
    if len(pin) < PIN_MIN_LENGTH:
        return False, f"PIN must be at least {PIN_MIN_LENGTH} characters."
    
    if not pin.isdigit():
        return False, "PIN must contain only digits."
    
    pin_path = CONFIG_PATH.parent / ".setup_pin"
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    
    pin_hash = hashlib.sha256(pin.encode()).hexdigest()
    pin_path.write_text(pin_hash)
    os.chmod(pin_path, 0o600)
    
    return True, "PIN created successfully."


def verify_pin(pin: str) -> bool:
    """Verify a PIN against the stored hash."""
    pin_path = CONFIG_PATH.parent / ".setup_pin"
    if not pin_path.exists():
        return False
    
    stored_hash = pin_path.read_text().strip()
    if not stored_hash:
        return False
    
    if len(stored_hash) == 64:
        provided_hash = hashlib.sha256(pin.encode()).hexdigest()
        return secrets.compare_digest(stored_hash, provided_hash)
    
    return secrets.compare_digest(stored_hash, pin)


def verify_auth_token(provided: str, settings: "Settings", client_ip: str = "unknown") -> tuple[bool, str]:
    """Verify the provided auth token against control token or setup PIN.
    
    Returns (success, error_message).
    """
    if not provided:
        return False, "Auth token required."
    
    state = get_setup_state()
    
    allowed, rate_msg = state.check_rate_limit(client_ip)
    if not allowed:
        return False, rate_msg
    
    if settings.control_token and secrets.compare_digest(provided, settings.control_token):
        state.clear_attempts(client_ip)
        return True, ""
    
    if verify_pin(provided):
        state.clear_attempts(client_ip)
        return True, ""
    
    state.record_failed_attempt(client_ip)
    return False, "Invalid PIN or token."


def reset_config_and_pin() -> tuple[bool, str]:
    """Reset PIN and wipe all secrets. Only works in reset window.
    
    Returns (success, message).
    """
    state = get_setup_state()
    
    if not state.is_in_reset_window():
        remaining = RESET_WINDOW_MINUTES
        return False, f"Reset only available within {remaining} minutes after app restart. Restart the app from the Reachy Mini Control app to reset."
    
    config_dir = CONFIG_PATH.parent
    
    files_to_remove = [
        config_dir / ".setup_pin",
        config_dir / "config.json",
        config_dir / "service-account.json",
    ]
    
    removed = []
    for f in files_to_remove:
        if f.exists():
            f.unlink()
            removed.append(f.name)
    
    global _setup_state
    _setup_state = SetupState()
    
    if removed:
        return True, f"Reset complete. Removed: {', '.join(removed)}. You can now set a new PIN."
    return True, "Nothing to reset. You can now set a new PIN."


def mask_secret(value: str | None, show_last: int = 4) -> str:
    """Return masked secret: 'set (****abcd)' or 'not set'."""
    if not value:
        return "not set"
    if len(value) <= show_last:
        return "set (****)"
    return f"set (****{value[-show_last:]})"


def check_gemini_key(api_key: str) -> dict[str, Any]:
    """Test a Gemini API key by making a simple request."""
    try:
        response = httpx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "contents": [{"role": "user", "parts": [{"text": "Say 'OK'"}]}],
                "generationConfig": {"maxOutputTokens": 10},
            },
            timeout=15.0,
        )
        if response.status_code == 200:
            return {"valid": True, "status": "OK", "status_code": 200}
        error_detail = response.text[:200] if response.text else "No details"
        return {"valid": False, "status": "API error", "status_code": response.status_code, "detail": error_detail}
    except httpx.TimeoutException:
        return {"valid": False, "status": "Timeout", "detail": "Request timed out"}
    except httpx.RequestError as e:
        return {"valid": False, "status": "Network error", "detail": str(e)}


def parse_service_account_json(raw_json: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse and validate service account JSON.
    
    Returns (parsed_data, None) on success or (None, error_message) on failure.
    """
    try:
        if raw_json.startswith("ey") or "{" in raw_json[:20]:
            sa_json = raw_json
        else:
            sa_json = base64.b64decode(raw_json).decode("utf-8")
        
        sa_data = json.loads(sa_json)
        
        if "type" not in sa_data or sa_data.get("type") != "service_account":
            return None, "Invalid service account JSON: missing or wrong 'type'"
        if "client_email" not in sa_data:
            return None, "Invalid service account JSON: missing 'client_email'"
        
        return sa_data, None
        
    except (json.JSONDecodeError, ValueError) as e:
        return None, f"Invalid JSON: {e}"


def save_service_account(sa_json: str, sa_data: dict[str, Any]) -> Path:
    """Save service account JSON to config directory with restricted permissions."""
    sa_path = CONFIG_PATH.parent / "service-account.json"
    sa_path.parent.mkdir(parents=True, exist_ok=True)
    sa_path.write_text(sa_json)
    os.chmod(sa_path, 0o600)
    return sa_path
