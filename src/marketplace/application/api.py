"""Transport-independent Marketplace application API contract.

This module defines application operations that future HTTP/Web/Android adapters may
invoke.  It deliberately does not bind sockets, choose an HTTP framework, or perform
protocol-semantic validation beyond endpoint/application binding invariants.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .postgres_state import ApplicationStatePutResult, ExpiryResult, SyncPage
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


class MarketplaceApplicationApiService:
    """Pure application API facade for future transport adapters."""

    def __init__(
        self,
        *,
        state: MarketplaceApplicationStateService,
        intent_query: IntentQueryPort,
        response_parent_ids: ResponseParentExtractor,
    ) -> None:
        if not callable(response_parent_ids):
            raise TypeError("response_parent_ids MUST be callable")
        if not hasattr(intent_query, "list_intent_ids"):
            raise TypeError("intent_query MUST provide list_intent_ids")
        self._state = state
        self._intent_query = intent_query
        self._response_parent_ids = response_parent_ids
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
        if _parent_ids(self._response_parent_ids, record):
            raise ApplicationApiError(
                "ROOT_INTENT_RESPONSE_FORBIDDEN",
                "root intent creation cannot publish a response-bound record",
            )
        return self._state.publish(record)

    def get_intent(self, record_id: str) -> Any | None:
        self._require_initialized()
        return self._state.get(_record_id(record_id, name="record_id"))

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
        parents = _parent_ids(self._response_parent_ids, response_record)
        if parent_id not in parents:
            raise ApplicationApiError(
                "RESPONSE_PARENT_MISMATCH",
                "response record is not bound to the requested parent intent",
            )
        if self._state.get(parent_id) is None:
            raise ApplicationApiError(
                "PARENT_INTENT_NOT_FOUND",
                "response parent intent is not present in local application state",
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
        if type(values) is not tuple:
            raise TypeError("state response_ids MUST return an exact tuple")
        if any(type(value) is not str or not value for value in values):
            raise ValueError("response identities MUST be non-empty exact text")
        return values

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
        if type(page) is not SyncPage:
            raise TypeError("state sync_since MUST return exact SyncPage")
        return page


__all__ = [
    "ApplicationApiError",
    "DEFAULT_INTENT_PAGE_SIZE",
    "DEFAULT_RESPONSE_PAGE_SIZE",
    "DEFAULT_SYNC_PAGE_SIZE",
    "IntentIndexPage",
    "IntentQueryPort",
    "MAX_INTENT_PAGE_SIZE",
    "MAX_RESPONSE_PAGE_SIZE",
    "MAX_SYNC_PAGE_SIZE",
    "MarketplaceApplicationApiService",
    "ResponseParentExtractor",
]
