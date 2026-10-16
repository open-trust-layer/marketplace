from __future__ import annotations

import contextlib
from io import StringIO
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from tools import marketplace_evaluator_operator_db_probe as probe


ROOT = Path(__file__).resolve().parents[1]


class FakeCursor:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query):
        self.queries.append(query)
        assert query in (probe.IDENTITY_QUERY, probe.ROLE_QUERY)

    def fetchone(self):
        return next(self.responses)


class FakeConnection:
    def __init__(self, responses):
        self.cursor_instance = FakeCursor(responses)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self.cursor_instance


def valid_rows():
    return [
        (probe.USER, probe.DATABASE, probe.HOST, probe.PORT, "on"),
        (False, False, False, False, False),
    ]


class MarketplaceEvaluatorOperatorProbeTests(unittest.TestCase):
    def test_readonly_exact_identity_and_restricted_role(self):
        calls = []
        connection = FakeConnection(valid_rows())

        def connect(**kwargs):
            calls.append(kwargs)
            return connection

        result = probe.execute_operator_probe("test-credential-not-real-1234567890", connector=connect)
        self.assertIsNone(result)
        self.assertEqual(connection.cursor_instance.queries, [probe.IDENTITY_QUERY, probe.ROLE_QUERY])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["host"], "127.0.0.1")
        self.assertEqual(calls[0]["port"], 15432)
        self.assertEqual(calls[0]["user"], "marketplace_evaluator")
        self.assertEqual(calls[0]["dbname"], "marketplace_evaluator")
        self.assertEqual(calls[0]["connect_timeout"], 6)
        self.assertIn("default_transaction_read_only=on", calls[0]["options"])
        self.assertIn("statement_timeout=5000", calls[0]["options"])

    def test_fails_closed_for_wrong_host_port_user_database_or_readonly_state(self):
        indices = [0, 1, 2, 3, 4]
        bad = ["someone_else", "another_db", "0.0.0.0", 5432, "off"]
        for index, value in zip(indices, bad):
            with self.subTest(index=index):
                rows = valid_rows()
                identity = list(rows[0])
                identity[index] = value
                rows[0] = tuple(identity)
                self.assertEqual(
                    probe.execute_operator_probe("long-synthetic-credential-1234567", connector=lambda **_: FakeConnection(rows)),
                    "DATABASE_IDENTITY_OR_READONLY_MISMATCH",
                )

    def test_fails_closed_for_elevated_role_flags(self):
        for index in range(5):
            with self.subTest(index=index):
                rows = valid_rows()
                role_flags = list(rows[1])
                role_flags[index] = True
                rows[1] = tuple(role_flags)
                self.assertEqual(
                    probe.execute_operator_probe("long-synthetic-credential-1234567", connector=lambda **_: FakeConnection(rows)),
                    "DATABASE_ROLE_NOT_RESTRICTED",
                )

    def test_bad_credentials_do_not_connect_or_echo(self):
        attempts = []
        for pwd in (None, "", "short", "x" * 4097, "x" * 30 + "\n"):
            result = probe.execute_operator_probe(pwd, connector=lambda **kwargs: attempts.append(kwargs))
            self.assertEqual(result, "OPERATOR_CREDENTIAL_UNAVAILABLE")
        self.assertFalse(attempts)

    def test_exception_is_redacted(self):
        secret = "SYNTHETIC_SECRET_DO_NOT_LOG"
        def failed(**_kwargs):
            raise RuntimeError(secret)
        output = StringIO()
        with patch.dict("os.environ", {probe.PASSWORD_ENV: "long-synthetic-credential-1234567"}), patch.dict(sys.modules, {"psycopg": types.SimpleNamespace(connect=failed)}), contextlib.redirect_stdout(output):
            status = probe.main(["--execute-operator-probe", probe.EXECUTION_TOKEN])
        self.assertEqual(status, 1)
        self.assertEqual(output.getvalue().strip(), "status=BLOCKED code=DATABASE_PROBE_FAILED")
        self.assertNotIn(secret, output.getvalue())

    def test_dry_run_never_imports_driver_or_reads_password(self):
        output = StringIO()
        with patch.dict("os.environ", {probe.PASSWORD_ENV: "synthetic-do-not-print-123456789"}), patch.dict(sys.modules, {"psycopg": None}), contextlib.redirect_stdout(output):
            status = probe.main(["--dry-run"])
        self.assertEqual(status, 0)
        self.assertIn("postgres_connection_invoked=false", output.getvalue())
        self.assertNotIn("synthetic-do-not-print", output.getvalue())

    def test_unknown_option_redacted_before_credentials(self):
        output = StringIO()
        with contextlib.redirect_stderr(output):
            with self.assertRaises(SystemExit) as caught:
                probe.main(["--injected", "SYNTHETIC_SECRET_DO_NOT_LOG"])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(output.getvalue(), "status=BLOCKED code=ARGUMENT_INVALID\n")

    def test_without_explicit_optin_does_not_import_driver(self):
        output = StringIO()
        with patch.dict(sys.modules, {"psycopg": None}), contextlib.redirect_stdout(output):
            self.assertEqual(probe.main(["--execute-operator-probe", "NO"]), 1)
        self.assertEqual(output.getvalue().strip(), "status=BLOCKED code=EXECUTION_OPT_IN_REQUIRED")

    def test_operator_script_requires_console_and_protects_password(self):
        script = (ROOT / "tools" / "marketplace_evaluator_operator_probe.ps1").read_text("utf-8")
        for marker in (
            "LOCAL_INTERACTIVE_OPERATOR_REQUIRED",
            "RUN LOCAL READONLY PROBE",
            "SOURCE_REVISION_MISMATCH",
            "SOURCE_TREE_UNVERIFIED",
            "ISOLATED_POSTGRES_PROCESS_UNVERIFIED",
            "ConvertTo-SecureString",
            "ZeroFreeBSTR",
            "Env:' + $secretVariable",
            "--execute-operator-probe",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, script)
        self.assertNotIn("Start-Process -Verb RunAs", script)
        self.assertNotIn("Start-Transcript", script)
        self.assertNotIn("Write-Output $password", script)
        self.assertNotIn("--password", script)

    def test_operator_doc_never_claims_runtime_acceptance(self):
        document = (ROOT / "docs" / "marketplace-evaluator-local-operator-probe.md").read_text("utf-8")
        normalized = " ".join(document.replace("**", "").lower().split())
        for marker in (
            "#525",
            "operator console",
            "never run through remote execution",
            "not an authenticated buyer/seller flight",
            "15432",
            "5432",
        ):
            self.assertIn(marker.lower(), normalized)


if __name__ == "__main__":
    unittest.main()
