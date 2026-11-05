"""Helper functions for the settings API.

These are separate from main.py to allow testing without the reachy_mini SDK.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from reachy_mini_grokbot.config import CONFIG_PATH

if TYPE_CHECKING:
    from reachy_mini_grokbot.config import Settings


def mask_secret(value: str | None, show_last: int = 4) -> str:
    """Return masked secret: 'set (****abcd)' or 'not set'."""
    if not value:
        return "not set"
    if len(value) <= show_last:
        return "set (****)"
    return f"set (****{value[-show_last:]})"


def verify_auth_token(provided: str, settings: "Settings") -> bool:
    """Verify the provided auth token against control token or setup PIN.
    
    Accepts:
    - The REACHY_CONTROL_TOKEN if configured
    - A setup PIN stored in ~/.reachy_grokbot/.setup_pin (auto-generated if missing)
    """
    if not provided:
        return False
    
    if settings.control_token and secrets.compare_digest(provided, settings.control_token):
        return True
    
    pin_path = CONFIG_PATH.parent / ".setup_pin"
    if pin_path.exists():
        stored_pin = pin_path.read_text().strip()
        if stored_pin and secrets.compare_digest(provided, stored_pin):
            return True
    
    return False


def get_or_create_setup_pin() -> str:
    """Get existing setup PIN or create a new one."""
    pin_path = CONFIG_PATH.parent / ".setup_pin"
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    
    if pin_path.exists():
        pin = pin_path.read_text().strip()
        if pin:
            return pin
    
    pin = secrets.token_urlsafe(8)
    pin_path.write_text(pin)
    os.chmod(pin_path, 0o600)
    return pin


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
