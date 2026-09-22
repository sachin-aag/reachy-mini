"""POST utterances to a Grok Bot chief-of-staff routine webhook."""

from __future__ import annotations

import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)

SOURCE = "reachy_mini"


def build_payload(utterance: str, session_id: str = "main") -> dict[str, Any]:
    """Build the JSON body the chief-of-staff routine is told to expect."""
    text = utterance.strip()
    if not text:
        raise ValueError("utterance must not be empty")
    return {
        "utterance": text,
        "source": SOURCE,
        "session_id": session_id,
    }


def notify_chief_of_staff(
    webhook_url: str,
    webhook_key: str,
    utterance: str,
    session_id: str = "main",
    timeout_s: float = 20.0,
) -> dict[str, Any]:
    """Fire the routine. HTTP 200 means the run started, not that it finished."""
    if not webhook_url or not webhook_key:
        raise RuntimeError("GROK_BOT_WEBHOOK_URL and GROK_BOT_WEBHOOK_KEY must be set")

    payload = build_payload(utterance, session_id=session_id)
    headers = {
        "Authorization": f"Bearer {webhook_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout_s) as client:
        response = client.post(webhook_url, json=payload, headers=headers)

    accepted = response.status_code == 200
    logger.info(
        "Chief-of-staff webhook status=%s accepted=%s",
        response.status_code,
        accepted,
    )
    return {
        "accepted": accepted,
        "status_code": response.status_code,
        "detail": (
            "Grok Bot accepted the call and started a run. The spoken reply is not "
            "in this response — the Bot must call Reachy speak/show tools."
            if accepted
            else response.text[:500]
        ),
        "payload": payload,
    }
