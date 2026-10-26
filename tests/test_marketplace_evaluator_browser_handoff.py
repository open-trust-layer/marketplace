from __future__ import annotations

import contextlib
from io import StringIO
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools import marketplace_evaluator_browser_handoff as handoff
from tools.marketplace_browser_bundle_binding_preflight import BrowserBundleBindingError


class LocalConsole(StringIO):
    def isatty(self):
        return True


class BrowserHandoffTests(unittest.TestCase):
    def test_inert_does_not_prompt_or_invoke_verifier(self):
        out = StringIO()
        with patch.object(handoff.getpass, "getpass", side_effect=AssertionError("prompt")), \
             patch.object(handoff, "check_browser_bundle_binding", side_effect=AssertionError("binding")), \
             contextlib.redirect_stdout(out):
            self.assertEqual(handoff.main(["--authentication-provisioning-directory", r"D:\synthetic", "--inert"]), 0)
        self.assertIn("keys_read=false", out.getvalue())

    def test_requires_real_console_before_collecting_carriers(self):
        out = StringIO()
        with patch.object(handoff.getpass, "getpass", side_effect=AssertionError("prompt")), \
             contextlib.redirect_stdout(out):
            self.assertEqual(handoff.main(["--authentication-provisioning-directory", r"D:\synthetic"]), 1)
        self.assertIn("LOCAL_INTERACTIVE_CONSOLE_REQUIRED", out.getvalue())

    def test_prompts_locally_and_never_prints_public_carriers(self):
        out = LocalConsole()
        seller, buyer = "mkpk1_SYNTHETIC_SELLER", "mkpk1_SYNTHETIC_BUYER"
        with patch.object(handoff.sys, "stdin", LocalConsole()), \
             patch.object(handoff.getpass, "getpass", side_effect=[seller, buyer]), \
             patch.object(handoff, "check_browser_bundle_binding", return_value=3599) as check, \
             contextlib.redirect_stdout(out):
            self.assertEqual(handoff.main(["--authentication-provisioning-directory", r"D:\synthetic"]), 0)
        check.assert_called_once()
        kwargs = check.call_args.kwargs
        self.assertEqual(kwargs["seller_browser_public_key"], seller)
        self.assertEqual(kwargs["buyer_browser_public_key"], buyer)
        self.assertEqual(kwargs["minimum_remaining_seconds"], 1800)
        self.assertNotIn(seller, out.getvalue())
        self.assertNotIn(buyer, out.getvalue())
        self.assertIn("status=BROWSER_BINDING_VERIFIED", out.getvalue())

    def test_verifier_error_is_redacted(self):
        out = LocalConsole()
        with patch.object(handoff.sys, "stdin", LocalConsole()), \
             patch.object(handoff.getpass, "getpass", side_effect=["mkpk1_SELLER", "mkpk1_BUYER"]), \
             patch.object(handoff, "check_browser_bundle_binding", side_effect=BrowserBundleBindingError("LEASE_EXPIRED")), \
             contextlib.redirect_stdout(out):
            self.assertEqual(handoff.main(["--authentication-provisioning-directory", r"D:\synthetic"]), 1)
        self.assertEqual(out.getvalue().strip(), "status=BLOCKED code=LEASE_EXPIRED")

    def test_unexpected_failure_does_not_echo_exception(self):
        out = LocalConsole()
        with patch.object(handoff.sys, "stdin", LocalConsole()), \
             patch.object(handoff.getpass, "getpass", side_effect=["mkpk1_SELLER", "mkpk1_BUYER"]), \
             patch.object(handoff, "check_browser_bundle_binding", side_effect=RuntimeError("SYNTHETIC_PRIVATE_MARKER")), \
             contextlib.redirect_stdout(out):
            self.assertEqual(handoff.main(["--authentication-provisioning-directory", r"D:\synthetic"]), 1)
        self.assertEqual(out.getvalue().strip(), "status=BLOCKED code=BROWSER_HANDOFF_FAILED")

    @unittest.skipUnless(sys.platform == "win32" and shutil.which("powershell"), "Windows PowerShell required")
    def test_operator_runtime_source_parses_without_execution(self):
        path = Path(__file__).resolve().parents[1] / "tools" / "marketplace_evaluator_operator_runtime.ps1"
        check = (
            "$tokens=$null; $errors=$null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "'{}',[ref]$tokens,[ref]$errors) | Out-Null; "
            "if ($errors.Count -ne 0) {{ exit 1 }}".format(str(path).replace("'", "''"))
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", check],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, "operator runtime source failed PowerShell parsing")


if __name__ == "__main__":
    unittest.main()
