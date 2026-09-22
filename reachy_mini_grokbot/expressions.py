"""Built-in expressions adapted from ClawBody / reachy-mini-mcp.

Head pose values are degrees. Antennas are degrees [left, right].
z is metres for the Stewart platform (usually 0).
"""

from __future__ import annotations

from typing import TypedDict


class HeadPose(TypedDict):
    """Head pose in degrees / metres."""

    z: float
    roll: float
    pitch: float
    yaw: float


class Expression(TypedDict):
    """One named gesture."""

    head: HeadPose
    antennas: list[float]
    duration: float
    method: str


EXPRESSIONS: dict[str, Expression] = {
    "neutral": {
        "head": {"z": 0, "roll": 0, "pitch": 0, "yaw": 0},
        "antennas": [0, 0],
        "duration": 1.5,
        "method": "minjerk",
    },
    "curious": {
        "head": {"z": 0, "roll": 0, "pitch": 10, "yaw": 8},
        "antennas": [20, 20],
        "duration": 1.2,
        "method": "ease_in_out",
    },
    "uncertain": {
        "head": {"z": 0, "roll": 8, "pitch": -3, "yaw": 3},
        "antennas": [-15, 15],
        "duration": 2.0,
        "method": "minjerk",
    },
    "recognition": {
        "head": {"z": 0, "roll": 0, "pitch": 5, "yaw": 0},
        "antennas": [30, 30],
        "duration": 0.8,
        "method": "cartoon",
    },
    "joy": {
        "head": {"z": 0, "roll": -3, "pitch": 8, "yaw": 0},
        "antennas": [40, 40],
        "duration": 1.0,
        "method": "cartoon",
    },
    "happy": {
        "head": {"z": 0, "roll": -3, "pitch": 8, "yaw": 0},
        "antennas": [40, 40],
        "duration": 1.0,
        "method": "cartoon",
    },
    "thinking": {
        "head": {"z": 0, "roll": 5, "pitch": 3, "yaw": 12},
        "antennas": [8, -8],
        "duration": 1.5,
        "method": "ease_in_out",
    },
    "listening": {
        "head": {"z": 0, "roll": -3, "pitch": 8, "yaw": 0},
        "antennas": [25, 25],
        "duration": 1.0,
        "method": "minjerk",
    },
    "agreeing": {
        "head": {"z": 0, "roll": 0, "pitch": 8, "yaw": 0},
        "antennas": [20, 20],
        "duration": 0.5,
        "method": "ease_in_out",
    },
    "disagreeing": {
        "head": {"z": 0, "roll": 0, "pitch": 0, "yaw": 12},
        "antennas": [-8, -8],
        "duration": 0.4,
        "method": "ease_in_out",
    },
    "sleepy": {
        "head": {"z": 0, "roll": 8, "pitch": -10, "yaw": 0},
        "antennas": [-20, -20],
        "duration": 2.5,
        "method": "minjerk",
    },
    "surprised": {
        "head": {"z": 0, "roll": 0, "pitch": -8, "yaw": 0},
        "antennas": [45, 45],
        "duration": 0.3,
        "method": "cartoon",
    },
    "focused": {
        "head": {"z": 0, "roll": 0, "pitch": 6, "yaw": 0},
        "antennas": [18, 18],
        "duration": 1.0,
        "method": "minjerk",
    },
}

LOOK_DIRECTIONS: dict[str, tuple[float, float, float]] = {
    "front": (0.0, 0.0, 0.0),
    "left": (0.0, 0.0, 25.0),
    "right": (0.0, 0.0, -25.0),
    "up": (0.0, 15.0, 0.0),
    "down": (0.0, -15.0, 0.0),
}

MOVE_LIBRARIES = {
    "emotions": "pollen-robotics/reachy-mini-emotions-library",
    "dances": "pollen-robotics/reachy-mini-dances-library",
}

BUILTIN_EMOTIONS = tuple(EXPRESSIONS.keys())


def list_builtin_emotions() -> list[str]:
    """Return built-in expression names."""
    return sorted(EXPRESSIONS)
