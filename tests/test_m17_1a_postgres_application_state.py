from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import traceback
import unittest

from marketplace.application.postgres_state import (
    APPLICATION_STATE_RETENTION_CLASS,
    DEFAULT_APPLICATION_STATE_RETENTION_SECONDS,
    MAX_APPLICATION_STATE_RETENTION_SECONDS,
    ApplicationStateCollisionError,
    ApplicationStateRetentionError,
    ApplicationStateStoreError,
    PreparedApplicationRecord,
    PostgresApplicationStateStore,
    StoreDisposition,
    SyncChange,
    SyncPage,
)


NOW = datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc)


class ScriptedCursor:
    def __init__(self, steps: list[tuple[str, object]]) -> None:
        self.steps = list(steps)
        self.calls: list[tuple[str, object]] = []
        self.rows: list[tuple[object, ...]] = []

    def execute(self, sql: str, params: object = None) -> None:
        normalized = " ".join(sql.split())
        self.calls.append((normalized, params))
        if "M17_RETENTION_MAINTENANCE" in normalized:
            self.rows = []
            return
        if "M17_CHANGE_RETENTION_MAINTENANCE" in normalized:
            if not self.steps or self.steps[0][0] not in normalized:
                self.rows = []
                return
        if not self.steps:
            raise AssertionError(f"unexpected SQL: {normalized}")
        fragment, result = self.steps.pop(0)
        if fragment not in normalized:
            raise AssertionError(f"expected SQL containing {fragment!r}, got {normalized!r}")
        if isinstance(result, Exception):
            raise result
        self.rows = list(result)

    def fetchall(self):
        return list(self.rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def close(self) -> None:
        pass


class ScriptedConnection:
    def __init__(self, steps: list[tuple[str, object]]) -> None:
        self.cursor_obj = ScriptedCursor(steps)
        self.cursor_error = None
        self.commits = 0
        self.rollbacks = 0
        self.rollback_error = None
        self.close_error = None
        self.closes = 0

    def cursor(self):
        if self.cursor_error is not None:
            raise self.cursor_error
        return self.cursor_obj

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1
        if self.rollback_error is not None:
            raise self.rollback_error

    def close(self) -> None:
        self.closes += 1
        if self.close_error is not None:
            raise self.close_error


class Factory:
    def __init__(self, connection: ScriptedConnection) -> None:
        self.connection = connection
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.connection


def record(*, record_id: str = "r1_intent", payload: bytes = b'{"kind":"intent"}', response_to=()):
    return PreparedApplicationRecord(
        record_id=record_id,
        canonical_record=payload,
        response_to=tuple(response_to),
    )


class M17PostgresApplicationStateTests(unittest.TestCase):
    def store(self, steps: list[tuple[str, object]], **kwargs):
        connection = ScriptedConnection(steps)
        factory = Factory(connection)
        store = PostgresApplicationStateStore(
            connection_factory=factory,
            clock=lambda: NOW,
            **kwargs,
        )
        return store, connection, factory

    def test_cursor_creation_failure_closes_partially_opened_connection(self):
        connection = ScriptedConnection([])
        connection.cursor_error = RuntimeError("postgres://user:secret@host/db")
        store = PostgresApplicationStateStore(
            connection_factory=Factory(connection),
            clock=lambda: NOW,
        )
        with self.assertRaises(ApplicationStateStoreError) as caught:
            store.apply_migrations()
        self.assertEqual(caught.exception.code, "DATABASE_CONNECTION_FAILED")
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 0)
        self.assertEqual(connection.closes, 1)
        rendered = "".join(traceback.format_exception(caught.exception))
        self.assertNotIn("user:secret", rendered)

    def test_cursor_creation_cleanup_failure_is_observable_without_provider_reflection(self):
        connection = ScriptedConnection([])
        connection.cursor_error = RuntimeError("cursor secret")
        connection.close_error = RuntimeError("close secret")
        store = PostgresApplicationStateStore(
            connection_factory=Factory(connection),
            clock=lambda: NOW,
        )
        with self.assertRaises(ApplicationStateStoreError) as caught:
            store.apply_migrations()
        self.assertEqual(caught.exception.code, "DATABASE_CONNECTION_CLEANUP_FAILED")
        self.assertEqual(connection.closes, 1)
        rendered = "".join(traceback.format_exception(caught.exception))
        self.assertNotIn("cursor secret", rendered)
        self.assertNotIn("close secret", rendered)

    def test_retention_profile_is_bounded_to_thirty_days(self):
        self.assertEqual(APPLICATION_STATE_RETENTION_CLASS, "MARKETPLACE_APPLICATION_STATE_MVP")
        self.assertEqual(DEFAULT_APPLICATION_STATE_RETENTION_SECONDS, 30 * 24 * 60 * 60)
        self.assertEqual(MAX_APPLICATION_STATE_RETENTION_SECONDS, 30 * 24 * 60 * 60)
        with self.assertRaises(ValueError):
            self.store([], retention_seconds=MAX_APPLICATION_STATE_RETENTION_SECONDS + 1)

    def test_prepared_record_is_immutable_bounded_and_requires_exact_types(self):
        prepared = record(response_to=("r1_parent",))
        with self.assertRaises(FrozenInstanceError):
            prepared.record_id = "changed"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            PreparedApplicationRecord("r1", bytearray(b"x"))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            PreparedApplicationRecord("", b"x")
        with self.assertRaises(ValueError):
            PreparedApplicationRecord("r1", b"")
        with self.assertRaises(ValueError):
            PreparedApplicationRecord("r1", b"x", ("r1_parent", "r1_parent"))

    def test_migration_rejects_recorded_version_with_missing_schema_relation(self):
        steps = [
            ("CREATE TABLE IF NOT EXISTS marketplace_app_schema_migrations", []),
            ("SELECT version FROM marketplace_app_schema_migrations", [(1,)]),
            ("to_regclass", [(True, False, True, True, True, True, True, True)]),
        ]
        store, connection, _ = self.store(steps)
        with self.assertRaises(ApplicationStateStoreError) as caught:
            store.apply_migrations()
        self.assertEqual(caught.exception.code, "SCHEMA_INTEGRITY_INVALID")
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_put_new_record_is_transactional_and_indexes_response_to(self):
        steps = [
            ("SELECT record_id, canonical_record", []),
            ("INSERT INTO marketplace_app_records", []),
            ("INSERT INTO marketplace_app_response_links", []),
            ("INSERT INTO marketplace_app_changes", [(41,)]),
        ]
        store, connection, _ = self.store(steps)
        result = store.put(record(record_id="r1_response", response_to=("r1_parent",)))
        self.assertEqual(result.disposition, StoreDisposition.STORED)
        self.assertEqual(result.change_seq, 41)
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertEqual(connection.closes, 1)
        self.assertEqual(connection.cursor_obj.steps, [])

    def test_put_runs_bounded_retention_maintenance_before_and_after_write(self):
        steps = [
            ("SELECT record_id, canonical_record", []),
            ("INSERT INTO marketplace_app_records", []),
            ("INSERT INTO marketplace_app_changes", [(40,)]),
        ]
        store, connection, _ = self.store(steps)
        store.put(record())
        maintenance = [
            sql for sql, _ in connection.cursor_obj.calls
            if "M17_RETENTION_MAINTENANCE" in sql
        ]
        self.assertEqual(len(maintenance), 2)

    def test_duplicate_record_refreshes_retention_without_new_sync_change(self):
        expires = NOW + timedelta(days=30)
        steps = [
            ("SELECT record_id, canonical_record", [("r1_intent", b'{"kind":"intent"}')]),
            ("SELECT parent_record_id", []),
            ("UPDATE marketplace_app_records", []),
        ]
        store, connection, _ = self.store(steps)
        result = store.put(record())
        self.assertEqual(result.disposition, StoreDisposition.DUPLICATE)
        self.assertIsNone(result.change_seq)
        self.assertEqual(connection.commits, 1)
        update_params = next(
            params for sql, params in connection.cursor_obj.calls
            if "UPDATE marketplace_app_records" in sql
        )
        self.assertIn(expires, update_params)

    def test_identity_collision_rolls_back_without_reflecting_database_content(self):
        store, connection, _ = self.store(
            [("SELECT record_id, canonical_record", [("r1_intent", b"different")])]
        )
        with self.assertRaises(ApplicationStateCollisionError) as caught:
            store.put(record())
        self.assertEqual(caught.exception.code, "RECORD_IDENTITY_COLLISION")
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)
        self.assertNotIn("different", str(caught.exception))

    def test_get_returns_canonical_bytes_and_refreshes_only_exact_record(self):
        steps = [
            ("SELECT canonical_record", [(b'{"kind":"intent"}',)]),
            ("UPDATE marketplace_app_records", []),
            ("SELECT parent_record_id", [("r1_parent",)]),
        ]
        store, connection, _ = self.store(steps)
        result = store.get("r1_intent")
        self.assertEqual(result, record(response_to=("r1_parent",)))
        update_params = connection.cursor_obj.calls[1][1]
        self.assertEqual(update_params[-1], "r1_intent")

    def test_peek_returns_canonical_record_without_refreshing_retention(self):
        steps = [
            ("SELECT canonical_record", [(b'{"kind":"intent"}',)]),
            ("SELECT parent_record_id", [("r1_parent",)]),
        ]
        store, connection, _ = self.store(steps)
        result = store.peek("r1_intent")
        self.assertEqual(result, record(response_to=("r1_parent",)))
        self.assertFalse(any("UPDATE marketplace_app_records" in sql for sql, _ in connection.cursor_obj.calls))
        self.assertEqual(connection.commits, 1)

    def test_record_reads_exclude_expired_rows_before_any_retention_refresh(self):
        for method_name in ("get", "peek"):
            with self.subTest(method=method_name):
                store, connection, _ = self.store([("SELECT canonical_record", [])])
                result = getattr(store, method_name)("r1_intent")
                self.assertIsNone(result)
                sql, params = connection.cursor_obj.calls[0]
                self.assertIn("expires_at > %s", sql)
                self.assertEqual(params, ("r1_intent", NOW))
                self.assertFalse(any("UPDATE marketplace_app_records" in call_sql for call_sql, _ in connection.cursor_obj.calls))
                self.assertEqual(connection.commits, 1)

    def test_response_index_is_application_coordination_not_protocol_promotion(self):
        store, connection, _ = self.store(
            [("SELECT links.response_record_id", [("r1_b",), ("r1_a",)])]
        )
        result = store.list_response_ids("r1_parent", limit=8)
        self.assertEqual(result, ("r1_b", "r1_a"))
        sql, params = connection.cursor_obj.calls[0]
        self.assertIn("marketplace_app_response_links", sql)
        self.assertIn("marketplace_app_records", sql)
        self.assertIn("expires_at > %s", sql)
        self.assertEqual(params, ("r1_parent", NOW, 8))
        self.assertNotIn("current_response", sql.lower())
        self.assertNotIn("accepted", sql.lower())

    def test_sync_expires_change_metadata_before_reading_retained_floor(self):
        steps = [
            ("M17_CHANGE_RETENTION_MAINTENANCE", [(4,), (5,)]),
            ("UPDATE marketplace_app_sync_state", []),
            ("SELECT floor_seq", [(5,)]),
            ("M17_SYNC_RETENTION_GUARD", []),
            ("SELECT seq, record_id, change_kind", []),
        ]
        store, connection, _ = self.store(steps)
        page = store.sync_since(5, limit=8)
        self.assertEqual(page, SyncPage((), 5, False))
        self.assertIn("M17_CHANGE_RETENTION_MAINTENANCE", connection.cursor_obj.calls[0][0])
        self.assertEqual(connection.cursor_obj.calls[0][1], (NOW, 256))

    def test_sync_commits_retention_progress_before_stale_cursor_error(self):
        steps = [
            ("M17_CHANGE_RETENTION_MAINTENANCE", [(4,), (5,)]),
            ("UPDATE marketplace_app_sync_state", []),
            ("SELECT floor_seq", [(5,)]),
        ]
        store, connection, _ = self.store(steps)
        with self.assertRaises(ApplicationStateStoreError) as caught:
            store.sync_since(0, limit=8)
        self.assertEqual(caught.exception.code, "SYNC_CURSOR_EXPIRED")
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)

    def test_sync_fails_closed_if_expired_change_remains_after_bounded_cleanup(self):
        steps = [
            ("M17_CHANGE_RETENTION_MAINTENANCE", []),
            ("SELECT floor_seq", [(250,)]),
            ("M17_SYNC_RETENTION_GUARD", [(301,)]),
        ]
        store, connection, _ = self.store(steps)
        with self.assertRaises(ApplicationStateStoreError) as caught:
            store.sync_since(300, limit=8)
        self.assertEqual(caught.exception.code, "SYNC_CURSOR_EXPIRED")
        self.assertEqual(connection.rollbacks, 1)

    def test_sync_cursor_below_retained_floor_fails_closed(self):
        store, connection, _ = self.store(
            [("SELECT floor_seq", [(9,)])]
        )
        with self.assertRaises(ApplicationStateStoreError) as caught:
            store.sync_since(8, limit=16)
        self.assertEqual(caught.exception.code, "SYNC_CURSOR_EXPIRED")
        self.assertEqual(connection.rollbacks, 1)

    def test_sync_is_monotonic_bounded_and_makes_no_completeness_claim(self):
        steps = [
            ("SELECT floor_seq", [(5,)]),
            ("M17_SYNC_RETENTION_GUARD", []),
            ("SELECT seq, record_id, change_kind", [(6, "r1_a", "UPSERT"), (7, "r1_b", "DELETE"), (8, "r1_c", "UPSERT")]),
        ]
        store, _, _ = self.store(steps)
        page = store.sync_since(5, limit=2)
        self.assertEqual(page.changes, (SyncChange(6, "r1_a", "UPSERT"), SyncChange(7, "r1_b", "DELETE")))
        self.assertEqual(page.next_cursor, 7)
        self.assertTrue(page.has_more)
        self.assertFalse(hasattr(page, "global_completeness"))
        self.assertFalse(hasattr(page, "protocol_truth"))

    def test_expiry_deletion_failure_is_observable_and_rolls_back(self):
        store, connection, _ = self.store(
            [("DELETE FROM marketplace_app_records", RuntimeError("db payload should not leak"))]
        )
        with self.assertRaises(ApplicationStateRetentionError) as caught:
            store.expire_due()
        self.assertEqual(caught.exception.code, "RETENTION_DELETE_FAILED")
        self.assertEqual(connection.rollbacks, 1)
        self.assertNotIn("db payload", str(caught.exception))
        rendered = "".join(traceback.format_exception(caught.exception))
        self.assertNotIn("db payload", rendered)
        self.assertIsNone(caught.exception.__cause__)

    def test_expiry_deletes_local_copies_and_emits_tombstone_metadata(self):
        steps = [
            ("DELETE FROM marketplace_app_records", [("r1_old",)]),
            ("INSERT INTO marketplace_app_changes", [(52,)]),
        ]
        store, connection, _ = self.store(steps)
        result = store.expire_due()
        self.assertEqual(result.deleted_record_ids, ("r1_old",))
        self.assertEqual(result.tombstone_sequences, (52,))
        self.assertEqual(connection.commits, 1)

    def test_expiry_removes_old_sync_metadata_and_advances_fail_closed_floor(self):
        steps = [
            ("DELETE FROM marketplace_app_records", []),
            ("M17_CHANGE_RETENTION_MAINTENANCE", [(4,), (7,)]),
            ("UPDATE marketplace_app_sync_state", []),
        ]
        store, connection, _ = self.store(steps)
        store.expire_due()
        floor_call = next(
            (sql, params) for sql, params in connection.cursor_obj.calls
            if "UPDATE marketplace_app_sync_state" in sql
        )
        self.assertEqual(floor_call[1], (7,))
        self.assertEqual(connection.commits, 1)

    def test_rollback_failure_is_observable_and_suppresses_provider_details(self):
        store, connection, _ = self.store(
            [("SELECT canonical_record", RuntimeError("primary provider detail"))]
        )
        connection.rollback_error = RuntimeError("rollback provider secret")
        with self.assertRaises(ApplicationStateStoreError) as caught:
            store.get("r1_intent")
        self.assertEqual(caught.exception.code, "TRANSACTION_ROLLBACK_FAILED")
        self.assertEqual(connection.rollbacks, 1)
        rendered = "".join(traceback.format_exception(caught.exception))
        self.assertNotIn("primary provider detail", rendered)
        self.assertNotIn("rollback provider secret", rendered)

    def test_database_errors_are_stable_and_transaction_rolls_back(self):
        store, connection, _ = self.store(
            [("SELECT canonical_record", RuntimeError("secret dsn details"))]
        )
        with self.assertRaises(ApplicationStateStoreError) as caught:
            store.get("r1_intent")
        self.assertEqual(caught.exception.code, "DATABASE_OPERATION_FAILED")
        self.assertEqual(connection.rollbacks, 1)
        self.assertNotIn("secret dsn", str(caught.exception))
        rendered = "".join(traceback.format_exception(caught.exception))
        self.assertNotIn("secret dsn", rendered)
        self.assertIsNone(caught.exception.__cause__)


if __name__ == "__main__":
    unittest.main()