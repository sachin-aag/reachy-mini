"""Robot motion helpers using the Reachy Mini SDK.

Gesture maps come from ClawBody / reachy-mini-mcp. Long moves use goto_target
(interpolated). Recorded emotion and dance clips use the Pollen HF libraries.
"""

from __future__ import annotations

import logging
import math
import threading
from typing import Any

from reachy_mini.utils import create_head_pose

from reachy_mini_grokbot.choreography import parse_choreographed_text
from reachy_mini_grokbot.expressions import (
    BUILTIN_EMOTIONS,
    EXPRESSIONS,
    LOOK_DIRECTIONS,
    MOVE_LIBRARIES,
)


logger = logging.getLogger(__name__)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class RobotBody:
    """Single-threaded-enough wrapper around a live ReachyMini instance."""

    def __init__(self, mini: Any) -> None:
        self.mini = mini
        self._lock = threading.Lock()

    def look(
        self,
        direction: str | None = None,
        roll: float = 0.0,
        pitch: float = 0.0,
        yaw: float = 0.0,
        duration: float = 1.0,
    ) -> str:
        """Point the head. Prefer named directions; rpy is for precise poses."""
        if direction:
            key = direction.lower().strip()
            if key not in LOOK_DIRECTIONS:
                return f"Unknown direction {direction!r}. Use {sorted(LOOK_DIRECTIONS)}."
            roll, pitch, yaw = LOOK_DIRECTIONS[key]
        roll = _clamp(roll, -40, 40)
        pitch = _clamp(pitch, -40, 40)
        yaw = _clamp(yaw, -180, 180)
        duration = _clamp(duration, 0.3, 5.0)
        pose = create_head_pose(roll=roll, pitch=pitch, yaw=yaw, degrees=True)
        with self._lock:
            self.mini.goto_target(head=pose, duration=duration)
        return f"Looking roll={roll:.0f} pitch={pitch:.0f} yaw={yaw:.0f}"

    def show(self, emotion: str = "neutral", move: str = "") -> str:
        """Play a built-in expression or a recorded Pollen move."""
        if move:
            return self.play_recorded(move, library="emotions")
        name = emotion.lower().strip()
        if name not in EXPRESSIONS:
            return f"Unknown emotion {emotion!r}. Built-ins: {', '.join(BUILTIN_EMOTIONS)}"
        expr = EXPRESSIONS[name]
        head = expr["head"]
        pose = create_head_pose(
            z=head["z"],
            roll=head["roll"],
            pitch=head["pitch"],
            yaw=head["yaw"],
            degrees=True,
        )
        antennas = [math.radians(a) for a in expr["antennas"]]
        with self._lock:
            self.mini.goto_target(
                head=pose,
                antennas=antennas,
                duration=expr["duration"],
            )
        return f"Expressed {name}"

    def dance(self, name: str = "happy") -> str:
        """Play a recorded dance, falling back to a built-in expression."""
        played = self.play_recorded(name, library="dances")
        if played.startswith("Playing"):
            return played
        return self.show(emotion=name)

    def play_recorded(self, move_name: str, library: str = "emotions") -> str:
        """Play a named clip from a Pollen recorded-move dataset."""
        dataset = MOVE_LIBRARIES.get(library)
        if dataset is None:
            return f"Unknown library {library!r}. Use {list(MOVE_LIBRARIES)}."
        try:
            from reachy_mini.motion.recorded_move import RecordedMoves

            moves = RecordedMoves(dataset)
            clip = moves.get(move_name)
            with self._lock:
                self.mini.play_move(clip, initial_goto_duration=1.0)
            return f"Playing {library}/{move_name}"
        except Exception as exc:
            logger.warning("Recorded move failed: %s", exc)
            return f"Recorded move failed: {exc}"

    def discover(self, library: str = "emotions") -> str:
        """List recorded move names from a Pollen dataset."""
        dataset = MOVE_LIBRARIES.get(library)
        if dataset is None:
            return f"Unknown library {library!r}. Use {list(MOVE_LIBRARIES)}."
        try:
            from reachy_mini.motion.recorded_move import RecordedMoves

            moves = RecordedMoves(dataset)
            names = sorted(moves.list_moves()) if hasattr(moves, "list_moves") else sorted(getattr(moves, "moves", {}))
            if not names and hasattr(moves, "keys"):
                names = sorted(moves.keys())
            return f"Available {library} ({len(names)}): {', '.join(names)}"
        except Exception as exc:
            logger.warning("discover failed: %s", exc)
            return f"Could not list {library}: {exc}"

    def rest(self, mode: str = "neutral") -> str:
        """Return to a rest pose."""
        mode = mode.lower().strip()
        if mode == "sleep":
            with self._lock:
                if hasattr(self.mini, "goto_sleep"):
                    self.mini.goto_sleep()
                else:
                    self.show("sleepy")
            return "Robot sleeping"
        if mode == "wake":
            with self._lock:
                if hasattr(self.mini, "wake_up"):
                    self.mini.wake_up()
                else:
                    self.show("neutral")
            return "Robot awake"
        return self.show("neutral")

    def snap(self) -> str:
        """Capture a JPEG from the robot camera as a data URL, if media exists."""
        media = getattr(self.mini, "media", None)
        if media is None:
            return "Camera not available"
        try:
            import base64

            import cv2

            frame = media.get_frame()
            if frame is None:
                return "No camera frame"
            ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                return "JPEG encode failed"
            encoded = base64.b64encode(buffer.tobytes()).decode("ascii")
            return f"data:image/jpeg;base64,{encoded}"
        except Exception as exc:
            logger.warning("snap failed: %s", exc)
            return f"Capture failed: {exc}"

    def speak_markers(self, text: str) -> list[str]:
        """Run [move:name] markers that are embedded in spoken text."""
        notes: list[str] = []
        pending: str | None = None
        for segment in parse_choreographed_text(text):
            if segment["type"] == "move":
                pending = segment["name"]
                continue
            if pending:
                notes.append(self.show(move=pending) if pending not in EXPRESSIONS else self.show(emotion=pending))
                pending = None
        if pending:
            notes.append(self.show(move=pending) if pending not in EXPRESSIONS else self.show(emotion=pending))
        return notes
