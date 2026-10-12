"""Check operator CLI entrypoint and documented root import path, without subprocess I/O.

A separate real-process CLI smoke was performed on Linux and Windows at PR #561's
initial head. Full 3,000+ unit discovery must not depend on child-process startup
and cleanup timing on a shared Windows CI runner.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.marketplace_local_two_party_provisioning import main

ROOT = Path(__file__).resolve().parents[1]
MODULE = "tools.marketplace_local_two_party_provisioning"
DOC = ROOT / "docs" / "local-two-party-signed-provisioning.md"


class LocalTwoPartyOperatorCliLaunchTests(unittest.TestCase):
    def test_cli_help_from_real_parser_without_spawning_python(self) -> None:
        output = StringIO()
        with patch.object(sys, "argv", [MODULE, "--help"]):
            with redirect_stdout(output):
                with self.assertRaises(SystemExit) as result:
                    main()
        self.assertEqual(result.exception.code, 0)
        self.assertIn("--execute-local-test-provisioning", output.getvalue())

    def test_wrong_ack_is_fail_closed_before_bundle_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target = Path(tempdir) / "no-bundle-created"
            stderr = StringIO()
            stdout = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main([
                    "--output-directory", str(target),
                    "--seller-browser-public-key", "invalid-public-input",
                    "--buyer-browser-public-key", "invalid-public-input",
                    "--execute-local-test-provisioning", "WRONG",
                ])
            self.assertNotEqual(code, 0)
            self.assertIn("status=BLOCKED code=EXECUTION_OPT_IN_REQUIRED", stderr.getvalue())
            self.assertEqual(stdout.getvalue(), "")
            self.assertFalse(target.exists())

    def test_documented_command_uses_module_and_repo_root(self) -> None:
        docs = DOC.read_text(encoding="utf-8")
        self.assertIn('PYTHONPATH = "src;."', docs)
        self.assertIn("python -m " + MODULE, docs)
        self.assertIn(
            "python -m tools.marketplace_authentication_lease_preflight", docs
        )
        self.assertNotIn('PYTHONPATH = "src;tools"', docs)


if __name__ == "__main__":
    unittest.main()
