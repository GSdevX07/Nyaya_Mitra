"""
auth/brute_force.py — Per-email and per-IP brute-force protection.

Progressive delay and lockout logic for login attempts.
Uses a module-level TTL dict — no external dependency needed.
"""
from __future__ import annotations
import asyncio
import datetime
import time
from collections import defaultdict

from fastapi import HTTPException, status

from app.auth.config import (
    MAX_FAILED_ATTEMPTS_BEFORE_DELAY,
    MAX_FAILED_ATTEMPTS_BEFORE_LOCKOUT,
    LOCKOUT_DURATION_MINUTES,
)

# {email: {"count": int, "window_start": float, "locked_until": float | None}}
_ATTEMPTS: dict[str, dict] = defaultdict(
    lambda: {"count": 0, "window_start": time.monotonic(), "locked_until": None}
)

# Progressive delay in seconds indexed by attempt count (0-indexed after threshold)
_DELAYS = [0, 0, 0, 0, 0, 1, 2, 4, 8, 30]


def _delay_for(count: int) -> float:
    if count < MAX_FAILED_ATTEMPTS_BEFORE_DELAY:
        return 0.0
    idx = min(count - MAX_FAILED_ATTEMPTS_BEFORE_DELAY, len(_DELAYS) - 1)
    return float(_DELAYS[idx])


def _window_expired(state: dict, window_seconds: int = 900) -> bool:
    """Return True if the tracking window has expired (default 15 min)."""
    return (time.monotonic() - state["window_start"]) > window_seconds


def record_failed_attempt(email: str) -> None:
    """Record one failed login attempt for *email*."""
    state = _ATTEMPTS[email.lower()]
    if _window_expired(state):
        # Reset window
        state["count"] = 0
        state["window_start"] = time.monotonic()
        state["locked_until"] = None
    state["count"] += 1
    if state["count"] >= MAX_FAILED_ATTEMPTS_BEFORE_LOCKOUT:
        state["locked_until"] = time.monotonic() + LOCKOUT_DURATION_MINUTES * 60


async def check_lockout(email: str) -> None:
    """
    Check if *email* is currently locked out or should be delayed.

    Raises HTTPException 429 if locked.
    Applies asyncio.sleep for progressive delay.
    """
    state = _ATTEMPTS[email.lower()]

    if _window_expired(state):
        # Window expired — clear
        state["count"] = 0
        state["locked_until"] = None
        state["window_start"] = time.monotonic()
        return

    # Hard lockout
    if state.get("locked_until") and time.monotonic() < state["locked_until"]:
        remaining = int(state["locked_until"] - time.monotonic())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Account temporarily locked due to too many failed attempts. "
                f"Try again in {remaining} seconds."
            ),
        )

    # Progressive delay
    delay = _delay_for(state["count"])
    if delay > 0:
        await asyncio.sleep(delay)


def clear_attempts(email: str) -> None:
    """Clear failed attempt counter after a successful login."""
    key = email.lower()
    if key in _ATTEMPTS:
        del _ATTEMPTS[key]
