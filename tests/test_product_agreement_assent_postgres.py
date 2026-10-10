from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import traceback
import unittest

from marketplace.application.agreement_assent_coordination import (
    DEFAULT_AGREEMENT_ASSENT_RETENTION_SECONDS,
    MAX_AGREEMENT_ASSENT_COORDINATION_ENTRIES,
    AgreementAssentCoordinationCollisionError,
    AgreementAssentCoordinationError,
    PreparedAgreementAssent,
    StoreDisposition,
)
from marketplace.application.postgres_agreement_assent import (
    AgreementAssentPostgresError,
    AgreementAssentPostgresRetentionError,
    POSTGRES_AGREEMENT_ASSENT_MIGRATIONS,
    PostgresAgreementAssentCoordinationStore,
)


NOW = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
AGREEMENT = "r1_" + "A" * 43
PRINCIPAL = "urn:marketplace:test:alice"
METHOD = "urn:marketplace:test:key-1"
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "postgres_agreement_assent.py"


class ScriptedCursor:
    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []
        self.current = []
        self.closes = 0

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        if not self.steps:
            raise AssertionError(f"unexpected SQL: {sql}")
        needle, result = self.steps.pop(0)
        if needle not in sql:
            raise AssertionError(f"expected {needle!r}, got {sql!r}")
        if isinstance(result, BaseException):
            raise result
        self.current = list(result)

    def fetchall(self):
        rows = self.current
        self.current = []
        return rows

    def fetchone(self):
        if not self.current:
            return None
        return self.current.pop(0)

    def close(self):
        self.closes += 1


class ScriptedConnection:
    def __init__(self, steps):
        self.cursor_obj = ScriptedCursor(steps)
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0
        self.rollback_error = None

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1
        if self.rollback_error is not None:
            raise self.rollback_error

    def close(self):
        self.closes += 1


class Factory:
    def __init__(self, connection):
        self.connection = connection
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.connection


def prepared(*, proof_bytes=b'{"proof":1}', method=METHOD, principal=PRINCIPAL):
    return PreparedAgreementAssent(
        agreement_record_id=AGREEMENT,
        principal=principal,
        verification_method=method,
        proof_identity=b"\x11" * 32,
        proof_bytes=proof_bytes,
    )


class ProductAgreementAssentPostgresTests(unittest.TestCase):
    def store(
        self,
        steps,
        *,
        clock=lambda: NOW,
        retention_seconds=DEFAULT_AGREEMENT_ASSENT_RETENTION_SECONDS,
        max_entries=MAX_AGREEMENT_ASSENT_COORDINATION_ENTRIES,
    ):
        connection = ScriptedConnection(steps)
        factory = Factory(connection)
        store = PostgresAgreementAssentCoordinationStore(
            connection_factory=factory,
            clock=clock,
            retention_seconds=retention_seconds,
            max_entries=max_entries,
        )
        return store, connection, factory

    def test_constructor_is_inert_and_bounds_retention_and_capacity(self):
        connection = ScriptedConnection([])
        factory = Factory(connection)
        store = PostgresAgreementAssentCoordinationStore(
            connection_factory=factory,
            clock=lambda: NOW,
        )
        self.assertEqual(factory.calls, 0)
        self.assertEqual(store.retention_seconds, 30 * 24 * 60 * 60)
        with self.assertRaises(ValueError):
            PostgresAgreementAssentCoordinationStore(
                connection_factory=factory,
                clock=lambda: NOW,
                retention_seconds=30 * 24 * 60 * 60 + 1,
            )
        with self.assertRaises(ValueError):
            PostgresAgreementAssentCoordinationStore(
                connection_factory=factory,
                clock=lambda: NOW,
                max_entries=4097,
            )

    def test_schema_is_separate_additive_and_bounded(self):
        rendered = "\n".join(
            statement
            for migration in POSTGRES_AGREEMENT_ASSENT_MIGRATIONS
            for statement in migration.statements
        )
        self.assertIn("marketplace_agreement_assent_schema_migrations", rendered)
        self.assertIn("marketplace_agreement_assent_evidence", rendered)
        self.assertIn("marketplace_agreement_assent_expires_idx", rendered)
        self.assertIn("octet_length(proof_identity) = 32", rendered)
        self.assertIn("octet_length(proof_bytes) <= 16384", rendered)
        self.assertIn("expires_at <= accepted_at + INTERVAL '30 days'", rendered)
        self.assertNotIn("marketplace_app_records", rendered)
        self.assertNotIn("marketplace_app_changes", rendered)
        self.assertNotIn("FOREIGN KEY", rendered.upper())

    def test_apply_migrations_is_transactional_and_checks_footprint(self):
        steps = [
            ("CREATE TABLE IF NOT EXISTS marketplace_agreement_assent_schema_migrations", []),
            ("SELECT version", []),
            ("CREATE TABLE IF NOT EXISTS marketplace_agreement_assent_evidence", []),
            ("CREATE INDEX IF NOT EXISTS marketplace_agreement_assent_expires_idx", []),
            ("INSERT INTO marketplace_agreement_assent_schema_migrations", []),
            ("to_regclass", [(True, True, True)]),
        ]
        store, connection, _ = self.store(steps)
        self.assertEqual(store.apply_migrations(), (1,))
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertEqual(connection.cursor_obj.steps, [])

    def test_unsupported_schema_version_fails_closed(self):
        steps = [
            ("CREATE TABLE IF NOT EXISTS marketplace_agreement_assent_schema_migrations", []),
            ("SELECT version", [(2,)]),
        ]
        store, connection, _ = self.store(steps)
        with self.assertRaises(AgreementAssentPostgresError) as caught:
            store.apply_migrations()
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_SCHEMA_VERSION_UNSUPPORTED",
        )
        self.assertEqual(connection.rollbacks, 1)

    def test_new_put_cleans_expiry_checks_capacity_and_stores(self):
        steps = [
            ("LOCK TABLE marketplace_agreement_assent_evidence", []),
            ("AGREEMENT_ASSENT_RETENTION_MAINTENANCE", []),
            ("DELETE FROM marketplace_agreement_assent_evidence", []),
            ("SELECT verification_method", []),
            ("SELECT COUNT(*)", [(0,)]),
            ("INSERT INTO marketplace_agreement_assent_evidence", []),
        ]
        store, connection, _ = self.store(steps)
        result = store.put(prepared())
        self.assertEqual(result.disposition, StoreDisposition.STORED)
        self.assertEqual(result.accepted_at, int(NOW.timestamp()))
        self.assertEqual(
            result.expires_at,
            int((NOW + timedelta(days=30)).timestamp()),
        )
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)

    def test_duplicate_is_idempotent_and_never_extends_expiry(self):
        accepted = NOW - timedelta(hours=1)
        expires = NOW + timedelta(days=20)
        steps = [
            ("LOCK TABLE marketplace_agreement_assent_evidence", []),
            ("AGREEMENT_ASSENT_RETENTION_MAINTENANCE", []),
            ("DELETE FROM marketplace_agreement_assent_evidence", []),
            (
                "SELECT verification_method",
                [(METHOD, b"\x11" * 32, b'{"proof":1}', accepted, expires)],
            ),
        ]
        store, connection, _ = self.store(steps)
        result = store.put(prepared())
        self.assertEqual(result.disposition, StoreDisposition.DUPLICATE)
        self.assertEqual(result.accepted_at, int(accepted.timestamp()))
        self.assertEqual(result.expires_at, int(expires.timestamp()))
        self.assertFalse(
            any(
                "INSERT INTO marketplace_agreement_assent_evidence" in sql
                for sql, _ in connection.cursor_obj.calls
            )
        )
        self.assertEqual(connection.commits, 1)

    def test_conflicting_same_key_rolls_back(self):
        steps = [
            ("LOCK TABLE marketplace_agreement_assent_evidence", []),
            ("AGREEMENT_ASSENT_RETENTION_MAINTENANCE", []),
            ("DELETE FROM marketplace_agreement_assent_evidence", []),
            (
                "SELECT verification_method",
                [
                    (
                        METHOD,
                        b"\x11" * 32,
                        b"different",
                        NOW,
                        NOW + timedelta(days=30),
                    )
                ],
            ),
        ]
        store, connection, _ = self.store(steps)
        with self.assertRaises(AgreementAssentCoordinationCollisionError):
            store.put(prepared())
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_capacity_fails_closed_under_write_lock(self):
        steps = [
            ("LOCK TABLE marketplace_agreement_assent_evidence", []),
            ("AGREEMENT_ASSENT_RETENTION_MAINTENANCE", []),
            ("DELETE FROM marketplace_agreement_assent_evidence", []),
            ("SELECT verification_method", []),
            ("SELECT COUNT(*)", [(4096,)]),
        ]
        store, connection, _ = self.store(steps)
        with self.assertRaises(AgreementAssentCoordinationError) as caught:
            store.put(prepared())
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_COORDINATION_CAPACITY_EXCEEDED",
        )
        self.assertEqual(connection.rollbacks, 1)

    def test_peek_filters_expired_without_cleanup_or_retention_refresh(self):
        steps = [
            (
                "SELECT verification_method, proof_identity, proof_bytes",
                [
                    (
                        METHOD,
                        b"\x11" * 32,
                        b'{"proof":1}',
                        NOW - timedelta(hours=1),
                        NOW + timedelta(days=20),
                    )
                ],
            ),
        ]
        store, connection, _ = self.store(steps)
        self.assertEqual(store.peek(AGREEMENT, PRINCIPAL), prepared())
        sql, params = connection.cursor_obj.calls[0]
        self.assertIn("expires_at > %s", sql)
        self.assertEqual(params, (AGREEMENT, PRINCIPAL, NOW))
        self.assertFalse(
            any(
                "DELETE FROM" in call_sql or "UPDATE " in call_sql
                for call_sql, _ in connection.cursor_obj.calls
            )
        )
        self.assertEqual(connection.commits, 1)

    def test_list_is_sorted_bounded_and_has_no_hidden_cleanup(self):
        bob = "urn:marketplace:test:bob"
        steps = [
            (
                "SELECT principal, verification_method",
                [
                    (
                        PRINCIPAL,
                        METHOD,
                        b"\x11" * 32,
                        b'{"proof":1}',
                        NOW - timedelta(hours=1),
                        NOW + timedelta(days=20),
                    ),
                    (
                        bob,
                        "urn:marketplace:test:key-2",
                        b"\x22" * 32,
                        b'{"proof":2}',
                        NOW - timedelta(hours=1),
                        NOW + timedelta(days=20),
                    ),
                ],
            ),
        ]
        store, connection, _ = self.store(steps)
        values = store.list_for_agreement(AGREEMENT, limit=16)
        self.assertEqual(
            tuple(value.principal for value in values),
            (PRINCIPAL, bob),
        )
        sql, params = connection.cursor_obj.calls[0]
        self.assertIn('ORDER BY principal COLLATE "C"', sql)
        self.assertEqual(params, (AGREEMENT, NOW, 17))
        self.assertFalse(
            any(
                "DELETE FROM" in call_sql or "UPDATE " in call_sql
                for call_sql, _ in connection.cursor_obj.calls
            )
        )

    def test_list_overflow_fails_closed(self):
        rows = [
            (
                f"urn:marketplace:test:p{i:02d}",
                METHOD,
                bytes([i]) * 32,
                b"x",
                NOW - timedelta(hours=1),
                NOW + timedelta(days=20),
            )
            for i in range(17)
        ]
        store, connection, _ = self.store(
            [("SELECT principal, verification_method", rows)]
        )
        with self.assertRaises(AgreementAssentCoordinationError) as caught:
            store.list_for_agreement(AGREEMENT, limit=16)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_EVIDENCE_LIMIT_EXCEEDED",
        )
        self.assertEqual(connection.rollbacks, 1)

    def test_read_rejects_database_retention_wider_than_profile(self):
        steps = [
            (
                "SELECT verification_method, proof_identity, proof_bytes",
                [
                    (
                        METHOD,
                        b"\x11" * 32,
                        b'{"proof":1}',
                        NOW - timedelta(days=1),
                        NOW + timedelta(days=31),
                    )
                ],
            ),
        ]
        store, connection, _ = self.store(steps)
        with self.assertRaises(AgreementAssentPostgresError) as caught:
            store.peek(AGREEMENT, PRINCIPAL)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_DATABASE_ROW_INVALID",
        )
        self.assertEqual(connection.rollbacks, 1)

    def test_read_respects_narrower_configured_retention(self):
        steps = [
            (
                "SELECT verification_method, proof_identity, proof_bytes",
                [
                    (
                        METHOD,
                        b"\x11" * 32,
                        b'{"proof":1}',
                        NOW - timedelta(hours=12),
                        NOW + timedelta(hours=36),
                    )
                ],
            ),
        ]
        store, connection, _ = self.store(
            steps,
            retention_seconds=24 * 60 * 60,
        )
        with self.assertRaises(AgreementAssentPostgresError) as caught:
            store.peek(AGREEMENT, PRINCIPAL)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_DATABASE_ROW_INVALID",
        )
        self.assertEqual(connection.rollbacks, 1)

    def test_duplicate_rejects_future_accepted_timestamp(self):
        steps = [
            ("LOCK TABLE marketplace_agreement_assent_evidence", []),
            ("AGREEMENT_ASSENT_RETENTION_MAINTENANCE", []),
            ("DELETE FROM marketplace_agreement_assent_evidence", []),
            (
                "SELECT verification_method",
                [
                    (
                        METHOD,
                        b"\x11" * 32,
                        b'{"proof":1}',
                        NOW + timedelta(hours=1),
                        NOW + timedelta(days=20),
                    )
                ],
            ),
        ]
        store, connection, _ = self.store(steps)
        with self.assertRaises(AgreementAssentPostgresError) as caught:
            store.put(prepared())
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_DATABASE_ROW_INVALID",
        )
        self.assertEqual(connection.rollbacks, 1)

    def test_expire_due_is_bounded_observable_and_committed(self):
        steps = [
            (
                "AGREEMENT_ASSENT_RETENTION_MAINTENANCE",
                [
                    (AGREEMENT, PRINCIPAL),
                    ("r1_" + "B" * 43, "urn:marketplace:test:bob"),
                ],
            ),
        ]
        store, connection, _ = self.store(steps)
        result = store.expire_due()
        self.assertEqual(
            result.expired_keys,
            (
                (AGREEMENT, PRINCIPAL),
                ("r1_" + "B" * 43, "urn:marketplace:test:bob"),
            ),
        )
        sql, params = connection.cursor_obj.calls[0]
        self.assertIn("LIMIT 256", sql)
        self.assertEqual(params, (NOW,))
        self.assertEqual(connection.commits, 1)

    def test_retention_delete_failure_is_nonreflective_and_rolls_back(self):
        store, connection, _ = self.store(
            [
                (
                    "AGREEMENT_ASSENT_RETENTION_MAINTENANCE",
                    RuntimeError("provider retention secret"),
                )
            ]
        )
        with self.assertRaises(AgreementAssentPostgresRetentionError) as caught:
            store.expire_due()
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_RETENTION_DELETE_FAILED",
        )
        self.assertEqual(connection.rollbacks, 1)
        rendered = "".join(traceback.format_exception(caught.exception))
        self.assertNotIn("provider retention secret", rendered)
        self.assertIsNone(caught.exception.__cause__)

    def test_database_failure_is_nonreflective_and_rolls_back(self):
        store, connection, _ = self.store(
            [
                (
                    "SELECT verification_method, proof_identity, proof_bytes",
                    RuntimeError("dsn secret"),
                )
            ]
        )
        with self.assertRaises(AgreementAssentPostgresError) as caught:
            store.peek(AGREEMENT, PRINCIPAL)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_DATABASE_OPERATION_FAILED",
        )
        self.assertEqual(connection.rollbacks, 1)
        rendered = "".join(traceback.format_exception(caught.exception))
        self.assertNotIn("dsn secret", rendered)
        self.assertIsNone(caught.exception.__cause__)

    def test_connection_failure_is_stable_and_nonreflective(self):
        def fail_connection():
            raise RuntimeError("dsn provider secret")

        store = PostgresAgreementAssentCoordinationStore(
            connection_factory=fail_connection,
            clock=lambda: NOW,
        )
        with self.assertRaises(AgreementAssentPostgresError) as caught:
            store.peek(AGREEMENT, PRINCIPAL)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_DATABASE_CONNECTION_FAILED",
        )
        rendered = "".join(traceback.format_exception(caught.exception))
        self.assertNotIn("dsn provider secret", rendered)
        self.assertIsNone(caught.exception.__cause__)

    def test_rollback_failure_suppresses_primary_and_rollback_provider_details(self):
        store, connection, _ = self.store(
            [
                (
                    "SELECT verification_method, proof_identity, proof_bytes",
                    RuntimeError("primary provider secret"),
                )
            ]
        )
        connection.rollback_error = RuntimeError("rollback provider secret")
        with self.assertRaises(AgreementAssentPostgresError) as caught:
            store.peek(AGREEMENT, PRINCIPAL)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_TRANSACTION_ROLLBACK_FAILED",
        )
        rendered = "".join(traceback.format_exception(caught.exception))
        self.assertNotIn("primary provider secret", rendered)
        self.assertNotIn("rollback provider secret", rendered)
        self.assertIsNone(caught.exception.__cause__)

    def test_clock_requires_aware_whole_seconds(self):
        for bad in (
            datetime(2026, 9, 19, 10, 0, 0),
            datetime(2026, 9, 19, 10, 0, 0, 1, tzinfo=timezone.utc),
        ):
            with self.subTest(bad=bad):
                store, _, _ = self.store([], clock=lambda bad=bad: bad)
                with self.assertRaises(AgreementAssentPostgresError) as caught:
                    store.expire_due()
                self.assertEqual(
                    caught.exception.code,
                    "AGREEMENT_ASSENT_CLOCK_INVALID",
                )

    def test_source_has_no_provider_activation_or_existing_state_mutation(self):
        text = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "import psycopg",
            "import socket",
            "socket.",
            "subprocess",
            "os.environ",
            "getenv(",
            "marketplace_app_records",
            "marketplace_app_changes",
            "run_marketplace",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
