"""Bounded read-only filtering of PostgreSQL roots to genuine Marketplace Intents.

The original PostgreSQL state schema does not store a separately indexed record
type. The raw root query is therefore only a set of non-response records; it
also includes acceptance Events and published Agreements. This adapter checks
canonical record types on read without migrating or deleting existing data.
"""
from __future__ import annotations

from collections.abc import Callable

from .api import (
    ApplicationApiError,
    IntentIndexPage,
    IntentQueryPort,
    MAX_INTENT_CURSOR_CHARS,
    MAX_INTENT_PAGE_SIZE,
)


MAX_ROOT_INTENT_FILTER_SCAN_PAGES = 16


class MarketplaceRootIntentQueryFilter:
    """Classify bounded root pages while retaining visible keyset pagination."""

    def __init__(
        self,
        *,
        root_query: IntentQueryPort,
        is_root_intent: Callable[[str], bool],
    ) -> None:
        if not callable(getattr(root_query, "list_intent_ids", None)):
            raise TypeError("root_query MUST implement list_intent_ids")
        if not callable(is_root_intent):
            raise TypeError("is_root_intent MUST be callable")
        self._root_query = root_query
        self._is_root_intent = is_root_intent

    def _classify(self, record_id: str) -> bool:
        try:
            result = self._is_root_intent(record_id)
            if type(result) is not bool:
                raise TypeError("root intent classifier MUST return exact bool")
            return result
        except Exception:
            raise ApplicationApiError(
                "INTENT_CLASSIFICATION_FAILED",
                "root record could not be classified safely",
            ) from None

    def list_intent_ids(
        self,
        *,
        cursor: str | None = None,
        limit: int = 64,
    ) -> IntentIndexPage:
        if type(limit) is not int or not 1 <= limit <= MAX_INTENT_PAGE_SIZE:
            raise ValueError("limit MUST be a bounded exact integer")
        if cursor is not None and (
            type(cursor) is not str or not cursor or len(cursor) > MAX_INTENT_CURSOR_CHARS
        ):
            raise ValueError("cursor MUST be a bounded non-empty string")
        # A caller-supplied cursor must refer to a genuine Intent, not an
        # acceptance Event that the underlying raw PostgreSQL index also sees.
        if cursor is not None and not self._classify(cursor):
            raise ApplicationApiError(
                "INTENT_CURSOR_INVALID",
                "cursor is not a live Marketplace root Intent",
            )

        found: list[str] = []
        scanned_cursor = cursor
        seen_cursors = set()
        for _ in range(MAX_ROOT_INTENT_FILTER_SCAN_PAGES):
            page = self._root_query.list_intent_ids(
                cursor=scanned_cursor,
                limit=MAX_INTENT_PAGE_SIZE,
            )
            if type(page) is not IntentIndexPage or len(page.record_ids) > MAX_INTENT_PAGE_SIZE:
                raise ApplicationApiError(
                    "INTENT_FILTER_PAGE_INVALID",
                    "underlying root index page is invalid",
                )
            if page.record_ids != tuple(sorted(page.record_ids)) or any(
                scanned_cursor is not None and record_id <= scanned_cursor
                for record_id in page.record_ids
            ):
                raise ApplicationApiError(
                    "INTENT_FILTER_PAGE_INVALID",
                    "underlying root index ordering is invalid",
                )
            for record_id in page.record_ids:
                if self._classify(record_id):
                    if len(found) == limit:
                        # Return only true Intents. The continuation cursor is
                        # the last *visible* Intent, never an Event/Agreement.
                        return IntentIndexPage(tuple(found), found[-1])
                    found.append(record_id)

            if page.next_cursor is None:
                return IntentIndexPage(tuple(found), None)
            if (
                not page.record_ids
                or page.next_cursor != page.record_ids[-1]
                or page.next_cursor in seen_cursors
            ):
                raise ApplicationApiError(
                    "INTENT_FILTER_PAGE_INVALID",
                    "underlying root index continuation is invalid",
                )
            seen_cursors.add(page.next_cursor)
            scanned_cursor = page.next_cursor

        # Do not silently truncate or misstate has_more when there are too
        # many excluded root records; fail closed with a stable non-secret code.
        raise ApplicationApiError(
            "INTENT_FILTER_SCAN_LIMIT",
            "root index classification requires more than the bounded page scan",
        )


__all__ = [
    "MAX_ROOT_INTENT_FILTER_SCAN_PAGES",
    "MarketplaceRootIntentQueryFilter",
]
