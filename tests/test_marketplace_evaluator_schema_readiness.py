from __future__ import annotations

import contextlib
from io import StringIO
import sys
import types
import unittest
from unittest.mock import patch

from tools import marketplace_evaluator_schema_readiness as schema
from tools import marketplace_evaluator_operator_db_probe as identity


class FakeCursor:
    def __init__(self, responses):
        self.responses = responses
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query):
        assert query in (identity.IDENTITY_QUERY, identity.ROLE_QUERY,
                         schema.SCHEMA_QUERY, schema.TABLE_QUERY)
        self.executed.append(query)

    def fetchone(self):
        return self.responses.pop(0)

    def fetchall(self):
        return self.responses.pop(0)


class FakeConnection:
    def __init__(self, responses):
        self.cursor_instance = FakeCursor(list(responses))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self.cursor_instance


def good_responses(tables=()):
    return [
        (identity.USER, identity.DATABASE, identity.HOST, identity.PORT, "on"),
        (False, False, False, False, False),
        ("public", True),
        list(tables),
    ]


class SchemaReadinessTests(unittest.TestCase):
    def test_restricted_exact_readonly_identity_and_schema_ok(self):
        connection = FakeConnection(good_responses())
        calls = []
        def connect(**kwargs):
            calls.append(kwargs)
            return connection
        result = schema.execute_schema_readiness(
            "SYNTHETIC_PASSWORD_FOR_TESTS_123456789", connector=connect
        )
        self.assertIsNone(result)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["host"], identity.HOST)
        self.assertEqual(calls[0]["port"], identity.PORT)
        self.assertEqual(calls[0]["user"], identity.USER)
        self.assertEqual(calls[0]["dbname"], identity.DATABASE)
        self.assertIn("default_transaction_read_only=on", calls[0]["options"])
        self.assertEqual(connection.cursor_instance.executed, [
            identity.IDENTITY_QUERY, identity.ROLE_QUERY,
            schema.SCHEMA_QUERY, schema.TABLE_QUERY,
        ])

    def test_missing_schema_create_privilege_blocks(self):
        rows = good_responses()
        rows[2] = ("public", False)
        self.assertEqual(
            schema.assess_schema_readiness(FakeConnection(rows)),
            "EVALUATOR_SCHEMA_CREATE_PRIVILEGE_MISSING"
        )

    def test_unexpected_schema_blocks(self):
        rows = good_responses()
        rows[2] = ("custom", True)
        self.assertEqual(
            schema.assess_schema_readiness(FakeConnection(rows)),
            "EVALUATOR_SCHEMA_NOT_PUBLIC"
        )

    def test_existing_table_requires_owner_and_dml_rights(self):
        first = "marketplace_app_records"
        rows = good_responses([(first, True, True)])
        self.assertIsNone(schema.assess_schema_readiness(FakeConnection(rows)))
        for entry, expected in (
            ((first, False, True), "EVALUATOR_EXISTING_TABLE_OWNERSHIP_MISMATCH"),
            ((first, True, False), "EVALUATOR_EXISTING_TABLE_PRIVILEGES_MISSING"),
        ):
            with self.subTest(entry=entry):
                self.assertEqual(
                    schema.assess_schema_readiness(FakeConnection(good_responses([entry]))),
                    expected
                )

    def test_ambiguous_or_unexpected_catalog_rows_fail_closed(self):
        cases = (
            [("marketplace_app_records", True, True)] * 2,
            [("unrelated_table", True, True)],
            [("marketplace_app_records", True)],
            [("marketplace_app_records", 1, True)],
        )
        for rows in cases:
            with self.subTest(rows=rows):
                self.assertEqual(
                    schema.assess_schema_readiness(FakeConnection(good_responses(rows))),
                    "EVALUATOR_SCHEMA_FOOTPRINT_UNVERIFIED"
                    if rows != [("marketplace_app_records", 1, True)]
                    else "EVALUATOR_EXISTING_TABLE_OWNERSHIP_MISMATCH",
                )

    def test_rejects_failed_identity_before_schema_queries(self):
        rows = good_responses()
        rows[0] = ("wrong", identity.DATABASE, identity.HOST, identity.PORT, "on")
        connection = FakeConnection(rows)
        self.assertEqual(
            schema.assess_schema_readiness(connection),
            "DATABASE_IDENTITY_OR_READONLY_MISMATCH"
        )
        self.assertEqual(connection.cursor_instance.executed, [identity.IDENTITY_QUERY])

    def test_invalid_password_never_connects(self):
        called = []
        for value in (None, "", "short", "x" * 4097, "x" * 31 + "\n"):
            self.assertEqual(
                schema.execute_schema_readiness(value, connector=lambda **kw: called.append(kw)),
                "OPERATOR_CREDENTIAL_UNAVAILABLE"
            )
        self.assertFalse(called)

    def test_inert_no_driver_or_connection(self):
        out = StringIO()
        with patch.dict(sys.modules, {"psycopg": None}), contextlib.redirect_stdout(out):
            self.assertEqual(schema.main(["--dry-run"]), 0)
        self.assertIn("postgres_connection_invoked=false", out.getvalue())

    def test_redact_connection_failure_and_injected_option(self):
        secret = "SYNTHETIC_PRIVATE_MATERIAL"
        output = StringIO()
        with patch.dict("os.environ", {identity.PASSWORD_ENV: "SYNTHETIC_PASSWORD_FOR_TESTS_123456789"}), \
             patch.dict(sys.modules, {"psycopg": types.SimpleNamespace(
                 connect=lambda **kw: (_ for _ in ()).throw(RuntimeError(secret))
             )}), contextlib.redirect_stdout(output):
            self.assertEqual(schema.main(["--execute-schema-readiness", schema.EXECUTION_TOKEN]), 1)
        self.assertEqual(output.getvalue().strip(), "status=BLOCKED code=EVALUATOR_SCHEMA_READINESS_CHECK_FAILED")
        with contextlib.redirect_stderr(output):
            with self.assertRaises(SystemExit) as caught:
                schema.main(["--unknown", secret])
        self.assertEqual(caught.exception.code, 2)
        self.assertNotIn(secret, output.getvalue())

    def test_no_data_mutation_statements(self):
        sql = schema.SCHEMA_QUERY + " " + schema.TABLE_QUERY
        upper = sql.upper()
        for forbidden in ("DROP ", "UPDATE ", "DELETE ", "INSERT ", "CREATE ", "ALTER "):
            # Privilege labels are SQL string literals, not executable statements.
            self.assertNotIn(forbidden, upper)


if __name__ == "__main__":
    unittest.main()
