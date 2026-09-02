"""Transport-independent Marketplace application API contract.

This module defines application operations that future HTTP/Web/Android adapters may
invoke.  It deliberately does not bind sockets, choose an HTTP framework, or perform
protocol-semantic validation beyond endpoint/application binding invariants.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .postgres_state import ApplicationStatePutResult, ExpiryResult, SyncChange, SyncPage
from .state import MarketplaceApplicationStateService

DEFAULT_INTENT_PAGE_SIZE = 64
MAX_INTENT_PAGE_SIZE = 256
DEFAULT_RESPONSE_PAGE_SIZE = 64
MAX_RESPONSE_PAGE_SIZE = 256
DEFAULT_SYNC_PAGE_SIZE = 128
MAX_SYNC_PAGE_SIZE = 256


class ApplicationApiError(RuntimeError):
    """Stable application-API failure without payload reflection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class IntentIndexPage:
    record_ids: tuple[str, ...]
    next_cursor: str | None = None

    def __post_init__(self) -> None:
        if type(self.record_ids) is not tuple:
            raise TypeError("record_ids MUST be an exact tuple")
        if any(type(value) is not str or not value for value in self.record_ids):
            raise ValueError("record_ids entries MUST be non-empty exact text")
        if len(set(self.record_ids)) != len(self.record_ids):
            raise ValueError("record_ids MUST NOT contain duplicates")
        if self.next_cursor is not None and (
            type(self.next_cursor) is not str or not self.next_cursor
        ):
            raise ValueError("next_cursor MUST be non-empty exact text when present")


class IntentQueryPort(Protocol):
    def list_intent_ids(self, *, cursor: str | None, limit: int) -> IntentIndexPage: ...


IntentRecordPredicate = Callable[[Any], bool]
ResponseParentExtractor = Callable[[Any], tuple[str, ...]]


def _record_id(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{name} MUST be non-empty exact text")
    return value


def _bounded_limit(value: object, *, name: str, maximum: int) -> int:
    if type(value) is not int or value < 1 or value > maximum:
        raise ValueError(f"{name} MUST be an exact integer in range 1..{maximum}")
    return value


def _cursor(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value:
        raise ValueError("cursor MUST be non-empty exact text when present")
    return value


def _sync_cursor(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("sync cursor MUST be a non-negative exact integer")
    return value


def _parent_ids(extractor: ResponseParentExtractor, record: Any) -> tuple[str, ...]:
    values = extractor(record)
    if type(values) is not tuple:
        raise TypeError("response_parent_ids MUST return an exact tuple")
    if any(type(value) is not str or not value for value in values):
        raise ValueError("response parent identities MUST be non-empty exact text")
    if len(set(values)) != len(values):
        raise ValueError("response parent identities MUST NOT contain duplicates")
    return values


def _require_intent_record(
    predicate: IntentRecordPredicate,
    record: Any,
    *,
    code: str,
    message: str,
) -> None:
    result = predicate(record)
    if type(result) is not bool:
        raise TypeError("is_intent_record MUST return exact bool")
    if not result:
        raise ApplicationApiError(code, message)


def _review_response_ids(values: object, *, limit: int) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise TypeError("state response_ids MUST return an exact tuple")
    if len(values) > limit:
        raise ApplicationApiError(
            "RESPONSE_QUERY_LIMIT_EXCEEDED",
            "response query returned more identities than the requested page limit",
        )
    if any(type(value) is not str or not value for value in values):
        raise ValueError("response identities MUST be non-empty exact text")
    if len(set(values)) != len(values):
        raise ApplicationApiError(
            "RESPONSE_QUERY_DUPLICATE_ID",
            "response query returned duplicate record identities",
        )
    return values


def _review_sync_page(page: object, *, cursor: int, limit: int) -> SyncPage:
    if type(page) is not SyncPage:
        raise TypeError("state sync_since MUST return exact SyncPage")
    if type(page.changes) is not tuple:
        raise ApplicationApiError("SYNC_PAGE_INVALID", "sync page shape is invalid")
    if len(page.changes) > limit:
        raise ApplicationApiError(
            "SYNC_QUERY_LIMIT_EXCEEDED",
            "sync query returned more changes than the requested page limit",
        )
    if type(page.next_cursor) is not int or page.next_cursor < cursor:
        raise ApplicationApiError("SYNC_PAGE_INVALID", "sync page shape is invalid")
    if type(page.has_more) is not bool:
        raise ApplicationApiError("SYNC_PAGE_INVALID", "sync page shape is invalid")
    prior = cursor
    for change in page.changes:
        if type(change) is not SyncChange:
            raise ApplicationApiError("SYNC_PAGE_INVALID", "sync page shape is invalid")
        if type(change.seq) is not int or change.seq <= prior:
            raise ApplicationApiError("SYNC_PAGE_INVALID", "sync page shape is invalid")
        if type(change.record_id) is not str or not change.record_id:
            raise ApplicationApiError("SYNC_PAGE_INVALID", "sync page shape is invalid")
        if type(change.change_kind) is not str or change.change_kind not in ("UPSERT", "DELETE"):
            raise ApplicationApiError("SYNC_PAGE_INVALID", "sync page shape is invalid")
        prior = change.seq
    if page.next_cursor != prior or (page.has_more and not page.changes):
        raise ApplicationApiError("SYNC_PAGE_INVALID", "sync page shape is invalid")
    return page


class MarketplaceApplicationApiService:
    """Pure application API facade for future transport adapters."""

    def __init__(
        self,
        *,
        state: MarketplaceApplicationStateService,
        intent_query: IntentQueryPort,
        response_parent_ids: ResponseParentExtractor,
        is_intent_record: IntentRecordPredicate,
    ) -> None:
        if not callable(response_parent_ids):
            raise TypeError("response_parent_ids MUST be callable")
        if not callable(is_intent_record):
            raise TypeError("is_intent_record MUST be callable")
        if not hasattr(intent_query, "list_intent_ids"):
            raise TypeError("intent_query MUST provide list_intent_ids")
        self._state = state
        self._intent_query = intent_query
        self._response_parent_ids = response_parent_ids
        self._is_intent_record = is_intent_record
        self._initialized = False

    def initialize(self) -> ExpiryResult:
        self._initialized = False
        result = self._state.initialize()
        if type(result) is not ExpiryResult:
            raise TypeError("state initialize MUST return exact ExpiryResult")
        self._initialized = True
        return result

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise ApplicationApiError(
                "APPLICATION_API_NOT_INITIALIZED",
                "application API must complete startup initialization before use",
            )

    def create_intent(self, record: Any) -> ApplicationStatePutResult:
        self._require_initialized()
        _require_intent_record(
            self._is_intent_record,
            record,
            code="INTENT_RECORD_REQUIRED",
            message="intent creation requires a Marketplace intent record",
        )
        if _parent_ids(self._response_parent_ids, record):
            raise ApplicationApiError(
                "ROOT_INTENT_RESPONSE_FORBIDDEN",
                "root intent creation cannot publish a response-bound record",
            )
        return self._state.publish(record)

    def get_intent(self, record_id: str) -> Any | None:
        self._require_initialized()
        record = self._state.get(_record_id(record_id, name="record_id"))
        if record is None:
            return None
        _require_intent_record(
            self._is_intent_record,
            record,
            code="INTENT_RECORD_REQUIRED",
            message="intent lookup resolved to a non-intent Marketplace record",
        )
        return record

    def list_intents(
        self,
        *,
        cursor: str | None = None,
        limit: int = DEFAULT_INTENT_PAGE_SIZE,
    ) -> IntentIndexPage:
        self._require_initialized()
        reviewed_cursor = _cursor(cursor)
        reviewed_limit = _bounded_limit(
            limit,
            name="limit",
            maximum=MAX_INTENT_PAGE_SIZE,
        )
        page = self._intent_query.list_intent_ids(
            cursor=reviewed_cursor,
            limit=reviewed_limit,
        )
        if type(page) is not IntentIndexPage:
            raise TypeError("intent query MUST return exact IntentIndexPage")
        if len(page.record_ids) > reviewed_limit:
            raise ApplicationApiError(
                "INTENT_QUERY_LIMIT_EXCEEDED",
                "intent query returned more identities than the requested page limit",
            )
        return page

    def respond_to_intent(
        self,
        parent_record_id: str,
        response_record: Any,
    ) -> ApplicationStatePutResult:
        self._require_initialized()
        parent_id = _record_id(parent_record_id, name="parent_record_id")
        _require_intent_record(
            self._is_intent_record,
            response_record,
            code="RESPONSE_RECORD_NOT_INTENT",
            message="response publication requires a Marketplace intent record",
        )
        parents = _parent_ids(self._response_parent_ids, response_record)
        if parent_id not in parents:
            raise ApplicationApiError(
                "RESPONSE_PARENT_MISMATCH",
                "response record is not bound to the requested parent intent",
            )
        parent = self._state.get(parent_id)
        if parent is None:
            raise ApplicationApiError(
                "PARENT_INTENT_NOT_FOUND",
                "response parent intent is not present in local application state",
            )
        _require_intent_record(
            self._is_intent_record,
            parent,
            code="PARENT_RECORD_NOT_INTENT",
            message="response parent identity resolved to a non-intent Marketplace record",
        )
        return self._state.publish(response_record)

    def list_responses(
        self,
        parent_record_id: str,
        *,
        limit: int = DEFAULT_RESPONSE_PAGE_SIZE,
    ) -> tuple[str, ...]:
        self._require_initialized()
        parent_id = _record_id(parent_record_id, name="parent_record_id")
        reviewed_limit = _bounded_limit(
            limit,
            name="limit",
            maximum=MAX_RESPONSE_PAGE_SIZE,
        )
        values = self._state.response_ids(parent_id, limit=reviewed_limit)
        return _review_response_ids(values, limit=reviewed_limit)

    def sync(
        self,
        *,
        cursor: int = 0,
        limit: int = DEFAULT_SYNC_PAGE_SIZE,
    ) -> SyncPage:
        self._require_initialized()
        reviewed_cursor = _sync_cursor(cursor)
        reviewed_limit = _bounded_limit(
            limit,
            name="limit",
            maximum=MAX_SYNC_PAGE_SIZE,
        )
        page = self._state.sync_since(reviewed_cursor, limit=reviewed_limit)
        return _review_sync_page(page, cursor=reviewed_cursor, limit=reviewed_limit)


__all__ = [
    "ApplicationApiError",
    "DEFAULT_INTENT_PAGE_SIZE",
    "DEFAULT_RESPONSE_PAGE_SIZE",
    "DEFAULT_SYNC_PAGE_SIZE",
    "IntentIndexPage",
    "IntentQueryPort",
    "IntentRecordPredicate",
    "MAX_INTENT_PAGE_SIZE",
    "MAX_RESPONSE_PAGE_SIZE",
    "MAX_SYNC_PAGE_SIZE",
    "MarketplaceApplicationApiService",
    "ResponseParentExtractor",
]
