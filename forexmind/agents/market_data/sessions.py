"""Forex session detection - pure functions of a UTC datetime, no I/O.

Session hours are the standard, widely-cited UTC windows. DST is NOT modeled:
London/New York shift by an hour across their respective DST transitions, and
modeling that precisely needs a real timezone-aware holiday/DST calendar per
city. Documented simplification for V1; revisit if session misclassification
near DST boundaries turns out to matter for the agents that consume this.
"""

from __future__ import annotations

from datetime import datetime, timezone

# name -> (start_hour_utc, end_hour_utc), end exclusive. Sydney wraps midnight.
SESSION_HOURS_UTC: dict[str, tuple[int, int]] = {
    "Sydney": (21, 6),
    "Tokyo": (0, 9),
    "London": (7, 16),
    "New York": (12, 21),
}

KNOWN_OVERLAPS: list[tuple[str, str]] = [
    ("Sydney", "Tokyo"),
    ("Tokyo", "London"),
    ("London", "New York"),
]


def active_sessions(at: datetime) -> list[str]:
    at_utc = at.astimezone(timezone.utc) if at.tzinfo else at.replace(tzinfo=timezone.utc)
    hour = at_utc.hour
    active = []
    for name, (start, end) in SESSION_HOURS_UTC.items():
        if start < end:
            in_session = start <= hour < end
        else:  # wraps midnight
            in_session = hour >= start or hour < end
        if in_session:
            active.append(name)
    return active


def session_overlaps(active: list[str]) -> list[str]:
    active_set = set(active)
    return [
        f"{a}-{b}" for a, b in KNOWN_OVERLAPS if a in active_set and b in active_set
    ]
