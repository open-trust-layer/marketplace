"""Automatic expiry scheduling for runtime-owned ephemeral content."""
from __future__ import annotations

from threading import Timer
from typing import Callable, Protocol


DEFAULT_EPHEMERAL_RETENTION_SECONDS = 10.0


class ExpiryHandle(Protocol):
    def cancel(self) -> None: ...


class ExpiryScheduler(Protocol):
    def schedule(self, delay_seconds: float, callback: Callable[[], None]) -> ExpiryHandle: ...


class ThreadingExpiryScheduler:
    """Bounded timer-backed scheduler used by the in-process reference runtime."""

    def schedule(self, delay_seconds: float, callback: Callable[[], None]) -> ExpiryHandle:
        if delay_seconds <= 0:
            raise ValueError("expiry delay MUST be greater than zero")
        timer = Timer(delay_seconds, callback)
        timer.daemon = True
        timer.start()
        return timer
