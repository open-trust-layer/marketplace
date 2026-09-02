"""Shared Marketplace application-state service over an injected state store."""
from __future__ import annotations

from typing import Any, Callable, Protocol

from .postgres_state import (
    ApplicationStatePutResult,
    ExpiryResult,
    PreparedApplicationRecord,
    SyncPage,
)


class ApplicationStateStore(Protocol):
    def initialize(self) -> ExpiryResult: ...
    def put(self, prepared: PreparedApplicationRecord) -> ApplicationStatePutResult: ...
    def get(self, record_id: str) -> PreparedApplicationRecord | None: ...
    def list_response_ids(self, parent_record_id: str, *, limit: int) -> tuple[str, ...]: ...
    def sync_since(self, cursor_value: int, *, limit: int) -> SyncPage: ...


RecordPreparer = Callable[[Any], PreparedApplicationRecord]
RecordDecoder = Callable[[bytes], Any]


class ApplicationStateServiceError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class MarketplaceApplicationStateService:
    """One shared product service for Web, Android, agents, and later HTTP adapters."""

    def __init__(
        self,
        *,
        store: ApplicationStateStore,
        prepare_record: RecordPreparer,
        decode_record: RecordDecoder,
    ) -> None:
        if not callable(prepare_record):
            raise TypeError("prepare_record MUST be callable")
        if not callable(decode_record):
            raise TypeError("decode_record MUST be callable")
        self._store = store
        self._prepare_record = prepare_record
        self._decode_record = decode_record
        self._initialized = False

    def initialize(self) -> ExpiryResult:
        self._initialized = False
        result = self._store.initialize()
        if type(result) is not ExpiryResult:
            raise TypeError("state store initialize MUST return exact ExpiryResult")
        self._initialized = True
        return result

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise ApplicationStateServiceError(
                "APPLICATION_STATE_NOT_INITIALIZED",
                "application state must complete startup initialization before use",
            )

    def publish(self, record: Any) -> ApplicationStatePutResult:
        self._require_initialized()
        prepared = self._prepare_record(record)
        if type(prepared) is not PreparedApplicationRecord:
            raise TypeError("prepare_record MUST return exact PreparedApplicationRecord")
        return self._store.put(prepared)

    def get(self, record_id: str) -> Any | None:
        self._require_initialized()
        if type(record_id) is not str or not record_id:
            raise ValueError("record_id MUST be non-empty exact text")
        prepared = self._store.get(record_id)
        if prepared is None:
            return None
        if type(prepared) is not PreparedApplicationRecord:
            raise TypeError("state store MUST return exact PreparedApplicationRecord")
        return self._decode_record(prepared.canonical_record)

    def response_ids(self, parent_record_id: str, *, limit: int = 64) -> tuple[str, ...]:
        self._require_initialized()
        return self._store.list_response_ids(parent_record_id, limit=limit)

    def sync_since(self, cursor_value: int, *, limit: int = 128) -> SyncPage:
        self._require_initialized()
        return self._store.sync_since(cursor_value, limit=limit)


__all__ = [
    "ApplicationStateServiceError",
    "ApplicationStateStore",
    "MarketplaceApplicationStateService",
    "RecordDecoder",
    "RecordPreparer",
]
