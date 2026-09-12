"""Bounded process-memory reference composition for the local Marketplace MVP demo."""
from __future__ import annotations

from ..application.api import (
    ApplicationApiError,
    IntentIndexPage,
    MAX_INTENT_CURSOR_CHARS,
    MAX_INTENT_PAGE_SIZE,
)
from ..application.http import MvpFlightRunner
from ..application.launch import MarketplaceApplicationLaunchPlan
from ..application.postgres_state import (
    ApplicationStateCollisionError,
    ApplicationStatePutResult,
    ApplicationStateStoreError,
    ExpiryResult,
    MAX_RESPONSE_PAGE_SIZE,
    MAX_SYNC_PAGE_SIZE,
    PreparedApplicationRecord,
    SyncChange,
    SyncPage,
)
from ..runtime.contracts import StoreDisposition
from .application_record_v1 import (
    decode_marketplace_application_record,
    is_marketplace_intent_record,
)
from .application_v1 import build_reference_marketplace_application_launch_plan

MAX_DEMO_RECORDS = 256
MAX_DEMO_CANONICAL_BYTES = 16 * 1024 * 1024


class MemoryApplicationStateStore:
    """Process-local bounded application state with no filesystem or database I/O."""
    def __init__(self) -> None:
        self._records: dict[str, PreparedApplicationRecord] = {}
        self._changes: list[SyncChange] = []
        self._canonical_bytes = 0
        self._change_seq = 0

    def initialize(self) -> ExpiryResult:
        return ExpiryResult((), ())

    def put(self, prepared: PreparedApplicationRecord) -> ApplicationStatePutResult:
        if type(prepared) is not PreparedApplicationRecord:
            raise TypeError("prepared MUST be exact PreparedApplicationRecord")
        existing = self._records.get(prepared.record_id)
        if existing is not None:
            if existing.canonical_record != prepared.canonical_record:
                raise ApplicationStateCollisionError()
            if existing.response_to != prepared.response_to:
                raise ApplicationStateStoreError(
                    "APPLICATION_INDEX_COLLISION",
                    "canonical record and application response index disagree",
                )
            return ApplicationStatePutResult(StoreDisposition.DUPLICATE, None)
        next_bytes = self._canonical_bytes + len(prepared.canonical_record)
        if len(self._records) >= MAX_DEMO_RECORDS or next_bytes > MAX_DEMO_CANONICAL_BYTES:
            raise ApplicationStateStoreError(
                "DEMO_MEMORY_CAPACITY_EXCEEDED",
                "bounded local demo state capacity has been reached",
            )
        self._change_seq += 1
        self._records[prepared.record_id] = prepared
        self._canonical_bytes = next_bytes
        self._changes.append(SyncChange(self._change_seq, prepared.record_id, "UPSERT"))
        return ApplicationStatePutResult(StoreDisposition.STORED, self._change_seq)

    @staticmethod
    def _record_id(value: object) -> str:
        if type(value) is not str or not value:
            raise ValueError("record_id MUST be non-empty exact text")
        return value

    def get(self, record_id: str) -> PreparedApplicationRecord | None:
        return self._records.get(self._record_id(record_id))

    def peek(self, record_id: str) -> PreparedApplicationRecord | None:
        return self._records.get(self._record_id(record_id))

    def list_response_ids(self, parent_record_id: str, *, limit: int) -> tuple[str, ...]:
        parent = self._record_id(parent_record_id)
        if type(limit) is not int or isinstance(limit, bool) or not 1 <= limit <= MAX_RESPONSE_PAGE_SIZE:
            raise ValueError("limit is outside the reviewed response-page bound")
        values = tuple(
            record_id
            for record_id, prepared in sorted(self._records.items())
            if parent in prepared.response_to
        )
        return values[:limit]
    def sync_watermark(self) -> int:
        return self._change_seq

    def sync_since(self, cursor_value: int, *, limit: int) -> SyncPage:
        if type(cursor_value) is not int or isinstance(cursor_value, bool) or cursor_value < 0:
            raise ValueError("sync cursor MUST be a non-negative exact integer")
        if type(limit) is not int or isinstance(limit, bool) or not 1 <= limit <= MAX_SYNC_PAGE_SIZE:
            raise ValueError("limit is outside the reviewed sync-page bound")
        values = [change for change in self._changes if change.seq > cursor_value]
        has_more = len(values) > limit
        selected = tuple(values[:limit])
        next_cursor = selected[-1].seq if selected else cursor_value
        return SyncPage(selected, next_cursor, has_more)

    def snapshot(self) -> tuple[PreparedApplicationRecord, ...]:
        return tuple(prepared for _, prepared in sorted(self._records.items()))


class MemoryIntentQuery:
    def __init__(self, *, store: MemoryApplicationStateStore) -> None:
        if type(store) is not MemoryApplicationStateStore:
            raise TypeError("store MUST be exact MemoryApplicationStateStore")
        self._store = store

    @staticmethod
    def _review_cursor(cursor: object) -> str | None:
        if cursor is None:
            return None
        if type(cursor) is not str or not cursor or len(cursor) > MAX_INTENT_CURSOR_CHARS:
            raise ValueError("cursor MUST be bounded non-empty exact text when present")
        return cursor
    @staticmethod
    def _review_limit(limit: object) -> int:
        if type(limit) is not int:
            raise TypeError("limit MUST be an exact integer")
        if limit < 1 or limit > MAX_INTENT_PAGE_SIZE:
            raise ValueError(f"limit MUST be in range 1..{MAX_INTENT_PAGE_SIZE}")
        return limit

    def _root_intent_ids(self) -> tuple[str, ...]:
        values: list[str] = []
        for prepared in self._store.snapshot():
            if prepared.response_to:
                continue
            record = decode_marketplace_application_record(prepared.canonical_record)
            if is_marketplace_intent_record(record):
                values.append(prepared.record_id)
        return tuple(sorted(values))

    def list_intent_ids(self, *, cursor: str | None, limit: int) -> IntentIndexPage:
        reviewed_cursor = self._review_cursor(cursor)
        reviewed_limit = self._review_limit(limit)
        values = self._root_intent_ids()
        if reviewed_cursor is not None:
            if reviewed_cursor not in values:
                raise ApplicationApiError(
                    "INTENT_CURSOR_INVALID",
                    "intent cursor does not identify a current local root intent",
                )
            values = tuple(value for value in values if value > reviewed_cursor)
        visible = values[:reviewed_limit]
        next_cursor = visible[-1] if len(values) > reviewed_limit else None
        return IntentIndexPage(visible, next_cursor)


def build_reference_memory_marketplace_application_launch_plan(
    *,
    host: str,
    port: int,
    run_mvp_flight: MvpFlightRunner | None = None,
    index_html: bytes,
    app_js: bytes,
    styles_css: bytes,
) -> MarketplaceApplicationLaunchPlan:
    """Build the reviewed Web application over bounded process-memory state."""
    store = MemoryApplicationStateStore()
    return build_reference_marketplace_application_launch_plan(
        host=host,
        port=port,
        store=store,
        intent_query=MemoryIntentQuery(store=store),
        run_mvp_flight=run_mvp_flight,
        index_html=index_html,
        app_js=app_js,
        styles_css=styles_css,
    )


__all__ = [
    "MAX_DEMO_CANONICAL_BYTES",
    "MAX_DEMO_RECORDS",
    "MemoryApplicationStateStore",
    "MemoryIntentQuery",
    "build_reference_memory_marketplace_application_launch_plan",
]
