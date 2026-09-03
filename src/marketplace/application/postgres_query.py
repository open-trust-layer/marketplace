"""Bounded PostgreSQL root-intent query adapter for the Marketplace application."""
from __future__ import annotations

from datetime import datetime, timezone

from .api import ApplicationApiError, IntentIndexPage, MAX_INTENT_CURSOR_CHARS, MAX_INTENT_PAGE_SIZE
from .postgres_state import Clock, Connection, ConnectionFactory, Cursor


class ApplicationIntentQueryError(ApplicationApiError):
    """Stable root-intent query failure without provider-detail reflection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)


_SELECT_ROOT_CURSOR = """
SELECT EXISTS (
    SELECT 1
    FROM marketplace_app_records AS record
    WHERE record.record_id = %s
      AND record.expires_at > %s
      AND NOT EXISTS (
          SELECT 1 FROM marketplace_app_response_links AS links
          WHERE links.response_record_id = record.record_id
      )
)
"""

_SELECT_ROOT_INTENTS = """
SELECT record_id
FROM marketplace_app_records AS record
WHERE record.expires_at > %s
  AND NOT EXISTS (
      SELECT 1 FROM marketplace_app_response_links AS links
      WHERE links.response_record_id = record.record_id
  )
  AND (%s IS NULL OR record.record_id > %s)
ORDER BY record.record_id
LIMIT %s
"""


class PostgresIntentQuery:
    """Read-only, bounded root-intent index over injected PostgreSQL connectivity."""

    def __init__(self, *, connection_factory: ConnectionFactory, clock: Clock) -> None:
        if not callable(connection_factory):
            raise TypeError("connection_factory MUST be callable")
        if not callable(clock):
            raise TypeError("clock MUST be callable")
        self._connection_factory = connection_factory
        self._clock = clock

    def _now(self) -> datetime:
        value = self._clock()
        if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
            raise ApplicationIntentQueryError(
                "INTENT_QUERY_CLOCK_INVALID",
                "intent query clock must return an aware datetime",
            )
        return value.astimezone(timezone.utc)

    def _open(self) -> tuple[Connection, Cursor]:
        try:
            connection = self._connection_factory()
        except Exception:
            raise ApplicationIntentQueryError(
                "INTENT_QUERY_CONNECTION_FAILED",
                "intent query database connection could not be established",
            ) from None
        try:
            cursor = connection.cursor()
        except Exception:
            try:
                connection.close()
            except Exception:
                raise ApplicationIntentQueryError(
                    "INTENT_QUERY_CONNECTION_CLEANUP_FAILED",
                    "partial intent query connection cleanup failed",
                ) from None
            raise ApplicationIntentQueryError(
                "INTENT_QUERY_CONNECTION_FAILED",
                "intent query database connection could not be established",
            ) from None
        return connection, cursor

    @staticmethod
    def _rollback(connection: Connection) -> None:
        try:
            connection.rollback()
        except Exception:
            raise ApplicationIntentQueryError(
                "INTENT_QUERY_ROLLBACK_FAILED",
                "intent query transaction rollback failed",
            ) from None

    @staticmethod
    def _close(cursor: Cursor | None, connection: Connection | None) -> None:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
    @staticmethod
    def _review_cursor(cursor: object) -> str | None:
        if cursor is None:
            return None
        if type(cursor) is not str or not cursor:
            raise ValueError("cursor MUST be non-empty exact text when present")
        if len(cursor) > MAX_INTENT_CURSOR_CHARS:
            raise ValueError(f"cursor MUST be at most {MAX_INTENT_CURSOR_CHARS} characters")
        return cursor

    @staticmethod
    def _review_limit(limit: object) -> int:
        if type(limit) is not int:
            raise TypeError("limit MUST be an exact integer")
        if limit < 1 or limit > MAX_INTENT_PAGE_SIZE:
            raise ValueError(f"limit MUST be in range 1..{MAX_INTENT_PAGE_SIZE}")
        return limit

    def list_intent_ids(self, *, cursor: str | None, limit: int) -> IntentIndexPage:
        reviewed_cursor = self._review_cursor(cursor)
        reviewed_limit = self._review_limit(limit)
        now = self._now()
        connection = None
        db_cursor = None
        try:
            connection, db_cursor = self._open()
            if reviewed_cursor is not None:
                db_cursor.execute(_SELECT_ROOT_CURSOR, (reviewed_cursor, now))
                row = db_cursor.fetchone()
                if type(row) is not tuple or len(row) != 1 or type(row[0]) is not bool:
                    raise ApplicationIntentQueryError(
                        "INTENT_CURSOR_CHECK_INVALID",
                        "intent cursor validation result is invalid",
                    )
                if not row[0]:
                    raise ApplicationIntentQueryError(
                        "INTENT_CURSOR_INVALID",
                        "intent cursor is stale or does not identify a live root intent",
                    )
            db_cursor.execute(
                _SELECT_ROOT_INTENTS,
                (now, reviewed_cursor, reviewed_cursor, reviewed_limit + 1),
            )
            raw_rows = db_cursor.fetchall()
            rows = list(raw_rows)
            if len(rows) > reviewed_limit + 1:
                raise ApplicationIntentQueryError(
                    "INTENT_QUERY_RESULT_INVALID",
                    "intent query returned more rows than the reviewed bound",
                )
            record_ids: list[str] = []
            for row in rows:
                if type(row) is not tuple or len(row) != 1:
                    raise ApplicationIntentQueryError(
                        "INTENT_QUERY_RESULT_INVALID",
                        "intent query row shape is invalid",
                    )
                record_id = row[0]
                if type(record_id) is not str or not record_id:
                    raise ApplicationIntentQueryError(
                        "INTENT_QUERY_RESULT_INVALID",
                        "intent query identity is invalid",
                    )
                record_ids.append(record_id)
            if record_ids != sorted(record_ids) or len(set(record_ids)) != len(record_ids):
                raise ApplicationIntentQueryError(
                    "INTENT_QUERY_RESULT_INVALID",
                    "intent query ordering is invalid",
                )
            visible = tuple(record_ids[:reviewed_limit])
            next_cursor = visible[-1] if len(record_ids) > reviewed_limit else None
            connection.commit()
            return IntentIndexPage(visible, next_cursor)
        except ApplicationIntentQueryError:
            if connection is not None:
                self._rollback(connection)
            raise
        except Exception:
            if connection is not None:
                self._rollback(connection)
            raise ApplicationIntentQueryError(
                "INTENT_QUERY_FAILED",
                "intent query could not be completed safely",
            ) from None
        finally:
            self._close(db_cursor, connection)


__all__ = [
    "ApplicationIntentQueryError",
    "PostgresIntentQuery",
]
