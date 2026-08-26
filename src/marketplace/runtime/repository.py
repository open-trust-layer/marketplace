"""Bounded in-memory repository with mandatory EPHEMERAL retention."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any

from .contracts import StoreDisposition
from .retention import (
    DEFAULT_EPHEMERAL_RETENTION_SECONDS,
    ExpiryHandle,
    ExpiryScheduler,
    ThreadingExpiryScheduler,
)

RETENTION_CLASS_EPHEMERAL = "EPHEMERAL"
DEFAULT_MAX_ENTRIES = 1024
MAX_CONFIGURED_ENTRIES = 10_000


class RuntimeRepositoryError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class RepositoryClosedError(RuntimeRepositoryError):
    def __init__(self) -> None:
        super().__init__("REPOSITORY_CLOSED", "runtime repository is closed")


class RepositoryCapacityExceededError(RuntimeRepositoryError):
    def __init__(self, maximum: int) -> None:
        super().__init__(
            "REPOSITORY_CAPACITY_EXCEEDED",
            f"runtime repository reached bounded capacity {maximum}",
        )


class RepositoryReadLimitExceededError(RuntimeRepositoryError):
    def __init__(self, limit: int, available: int) -> None:
        super().__init__(
            "REPOSITORY_READ_LIMIT_EXCEEDED",
            f"runtime repository contains {available} records, exceeding read limit {limit}",
        )


class RecordIdentityCollisionError(RuntimeRepositoryError):
    def __init__(self, record_id: str) -> None:
        super().__init__(
            "RECORD_IDENTITY_COLLISION",
            f"record identity {record_id!r} is already bound to different content",
        )


@dataclass
class _Entry:
    record: Any
    generation: int
    expiry: ExpiryHandle


class InMemoryEphemeralRecordRepository:
    """Process-local evidence storage that expires content after last use.

    Retention cannot be configured above the project-wide 10-second EPHEMERAL
    maximum. Each successful put/get/snapshot refreshes expiry for records that
    were actually returned. Generation checks make a stale timer callback
    harmless after a later refresh.
    """

    retention_class = RETENTION_CLASS_EPHEMERAL

    def __init__(
        self,
        *,
        retention_seconds: float = DEFAULT_EPHEMERAL_RETENTION_SECONDS,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        scheduler: ExpiryScheduler | None = None,
    ) -> None:
        if retention_seconds <= 0 or retention_seconds > DEFAULT_EPHEMERAL_RETENTION_SECONDS:
            raise ValueError(
                "EPHEMERAL retention MUST be greater than zero and no more than 10 seconds"
            )
        if isinstance(max_entries, bool) or not isinstance(max_entries, int):
            raise TypeError("max_entries MUST be an integer")
        if not 1 <= max_entries <= MAX_CONFIGURED_ENTRIES:
            raise ValueError(
                f"max_entries MUST be between 1 and {MAX_CONFIGURED_ENTRIES}"
            )
        self._retention_seconds = float(retention_seconds)
        self._max_entries = max_entries
        self._scheduler = scheduler or ThreadingExpiryScheduler()
        self._entries: dict[str, _Entry] = {}
        self._closed = False
        self._lock = RLock()

    @property
    def retention_seconds(self) -> float:
        return self._retention_seconds

    @property
    def max_entries(self) -> int:
        return self._max_entries

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def _require_open(self) -> None:
        if self._closed:
            raise RepositoryClosedError()

    def _validate_snapshot_limit(self, limit: int) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("snapshot limit MUST be an integer")
        if not 1 <= limit <= self._max_entries:
            raise ValueError(
                f"snapshot limit MUST be between 1 and configured max_entries {self._max_entries}"
            )

    def _schedule(self, record_id: str, generation: int) -> ExpiryHandle:
        return self._scheduler.schedule(
            self._retention_seconds,
            lambda: self._expire_if_current(record_id, generation),
        )

    def _expire_if_current(self, record_id: str, generation: int) -> None:
        with self._lock:
            entry = self._entries.get(record_id)
            if entry is None or entry.generation != generation:
                return
            del self._entries[record_id]

    def _refresh_locked(self, record_id: str, entry: _Entry) -> None:
        next_generation = entry.generation + 1
        next_expiry = self._schedule(record_id, next_generation)
        previous_expiry = entry.expiry
        entry.generation = next_generation
        entry.expiry = next_expiry
        previous_expiry.cancel()

    def put(self, record_id: str, record: Any) -> StoreDisposition:
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("record_id MUST be non-empty text")
        with self._lock:
            self._require_open()
            existing = self._entries.get(record_id)
            if existing is not None:
                if existing.record != record:
                    raise RecordIdentityCollisionError(record_id)
                self._refresh_locked(record_id, existing)
                return StoreDisposition.DUPLICATE
            if len(self._entries) >= self._max_entries:
                raise RepositoryCapacityExceededError(self._max_entries)
            generation = 1
            expiry = self._schedule(record_id, generation)
            self._entries[record_id] = _Entry(
                record=record,
                generation=generation,
                expiry=expiry,
            )
            return StoreDisposition.STORED

    def get(self, record_id: str) -> Any | None:
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("record_id MUST be non-empty text")
        with self._lock:
            self._require_open()
            entry = self._entries.get(record_id)
            if entry is None:
                return None
            self._refresh_locked(record_id, entry)
            return entry.record

    def snapshot(self, limit: int) -> tuple[Any, ...]:
        """Return all current local records if they fit inside ``limit``.

        The method fails closed instead of truncating. Truncation could make a
        caller misinterpret a partial local source as complete for the declared
        source. Accepted snapshots are ordered by exact Record Identity text and
        refresh retention only for the returned records.
        """
        self._validate_snapshot_limit(limit)
        with self._lock:
            self._require_open()
            available = len(self._entries)
            if available > limit:
                raise RepositoryReadLimitExceededError(limit, available)
            ordered_ids = tuple(sorted(self._entries))
            records: list[Any] = []
            for record_id in ordered_ids:
                entry = self._entries[record_id]
                self._refresh_locked(record_id, entry)
                records.append(entry.record)
            return tuple(records)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            expiries = tuple(entry.expiry for entry in self._entries.values())
            self._entries.clear()
        for expiry in expiries:
            expiry.cancel()
