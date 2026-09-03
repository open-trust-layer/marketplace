from __future__ import annotations

from datetime import datetime, timezone
import json
import traceback
import unittest

from marketplace.application.api import IntentIndexPage
from marketplace.application.http import ApplicationHttpRequest
from marketplace.application.postgres_query import (
    ApplicationIntentQueryError,
    PostgresIntentQuery,
)
from marketplace.application.postgres_state import ExpiryResult
from marketplace.application.composition import compose_marketplace_application

NOW = datetime(2026, 9, 3, 7, 0, tzinfo=timezone.utc)


class ScriptedCursor:
    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []
        self.rows = []

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.calls.append((normalized, params))
        if not self.steps:
            raise AssertionError(f"unexpected SQL: {normalized}")
        fragment, result = self.steps.pop(0)
        if fragment not in normalized:
            raise AssertionError(f"expected {fragment!r}, got {normalized!r}")
        if isinstance(result, Exception):
            raise result
        self.rows = list(result)

    def fetchall(self):
        return list(self.rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def close(self):
        pass


class ScriptedConnection:
    def __init__(self, steps):
        self.cursor_obj = ScriptedCursor(steps)
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1


class Factory:
    def __init__(self, connection):
        self.connection = connection
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.connection


def make_query(steps):
    connection = ScriptedConnection(steps)
    factory = Factory(connection)
    query = PostgresIntentQuery(connection_factory=factory, clock=lambda: NOW)
    return query, connection, factory


class MinimalStore:
    def __init__(self):
        self.initialize_calls = 0

    def initialize(self):
        self.initialize_calls += 1
        return ExpiryResult((), ())


class StaticIntentQuery:
    def list_intent_ids(self, *, cursor=None, limit=64):
        return IntentIndexPage(("r-root",), None)


def decode_json(body: bytes):
    return json.loads(body.decode("utf-8"))


def encode_json(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


class M17PostgresQueryCompositionTests(unittest.TestCase):
    def test_root_query_filters_responses_and_returns_bounded_cursor(self):
        query, connection, factory = make_query([
            ("SELECT record_id", [("r-a",), ("r-b",), ("r-c",)]),
        ])
        page = query.list_intent_ids(cursor=None, limit=2)
        self.assertEqual(page, IntentIndexPage(("r-a", "r-b"), "r-b"))
        self.assertEqual(factory.calls, 1)
        sql, params = connection.cursor_obj.calls[0]
        self.assertIn("NOT EXISTS", sql)
        self.assertIn("marketplace_app_response_links", sql)
        self.assertIn("expires_at > %s", sql)
        self.assertEqual(params, (NOW, None, None, 3))
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertEqual(connection.closes, 1)

    def test_continuation_cursor_must_still_identify_live_root_intent(self):
        query, connection, _ = make_query([
            ("SELECT EXISTS", [(True,)]),
            ("SELECT record_id", [("r-c",)]),
        ])
        page = query.list_intent_ids(cursor="r-b", limit=2)
        self.assertEqual(page, IntentIndexPage(("r-c",), None))
        self.assertEqual(connection.cursor_obj.calls[0][1], ("r-b", NOW))

    def test_stale_or_response_cursor_fails_closed(self):
        query, connection, _ = make_query([("SELECT EXISTS", [(False,)])])
        with self.assertRaises(ApplicationIntentQueryError) as caught:
            query.list_intent_ids(cursor="r-response", limit=2)
        self.assertEqual(caught.exception.code, "INTENT_CURSOR_INVALID")
        self.assertEqual(connection.rollbacks, 1)

    def test_invalid_cursor_and_limit_fail_before_database_open(self):
        query, _, factory = make_query([])
        for cursor, limit in (("", 2), (None, 0), (None, 257), (None, True)):
            with self.subTest(cursor=cursor, limit=limit):
                with self.assertRaises((TypeError, ValueError)):
                    query.list_intent_ids(cursor=cursor, limit=limit)
        self.assertEqual(factory.calls, 0)

    def test_provider_failure_is_stable_and_non_reflective(self):
        query, connection, _ = make_query([
            ("SELECT record_id", RuntimeError("postgres://user:secret@host/db")),
        ])
        with self.assertRaises(ApplicationIntentQueryError) as caught:
            query.list_intent_ids(cursor=None, limit=2)
        self.assertEqual(caught.exception.code, "INTENT_QUERY_FAILED")
        self.assertEqual(connection.rollbacks, 1)
        rendered = "".join(traceback.format_exception(caught.exception))
        self.assertNotIn("user:secret", rendered)
        self.assertIsNone(caught.exception.__cause__)

    def test_composition_is_inert_until_explicit_initialize(self):
        store = MinimalStore()
        composition = compose_marketplace_application(
            store=store,
            intent_query=StaticIntentQuery(),
            prepare_record=lambda record: record,
            decode_record=lambda payload: payload,
            response_parent_ids=lambda record: (),
            is_intent_record=lambda record: True,
            decode_record_json=decode_json,
            encode_record_json=encode_json,
        )
        request = ApplicationHttpRequest("GET", "/api/intents", (), None, b"")
        before = composition.http.handle(request)
        self.assertEqual(before.status_code, 503)
        self.assertEqual(store.initialize_calls, 0)
        self.assertEqual(composition.initialize(), ExpiryResult((), ()))
        after = composition.http.handle(request)
        self.assertEqual(after.status_code, 200)
        self.assertEqual(decode_json(after.body)["record_ids"], ["r-root"])
        self.assertEqual(store.initialize_calls, 1)

    def test_document_preserves_source_only_authority_boundary(self):
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        doc = root / "docs" / "m17-1h-postgres-query-composition.md"
        self.assertTrue(doc.is_file())
        text = doc.read_text(encoding="utf-8")
        for marker in (
            "source-only application composition",
            "no live PostgreSQL connection",
            "no HTTP socket/server execution",
            "local application coordination only",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
