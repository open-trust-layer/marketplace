"""Exercise actual operator CLI launch in a fresh process; no provisioning or server."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = "tools.marketplace_local_two_party_provisioning"
DOC = ROOT / "docs" / "local-two-party-signed-provisioning.md"


def launch(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((str(ROOT / "src"), str(ROOT)))
    return subprocess.run(
        [sys.executable, "-m", MODULE, *args],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=25,
        check=False,
    )


class LocalTwoPartyOperatorCliLaunchTests(unittest.TestCase):
    def test_cli_help_imports_real_module(self) -> None:
        result = launch("--help")
        self.assertEqual(result.returncode, 0, result.stderr[:1200])
        self.assertIn("--execute-local-test-provisioning", result.stdout)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_wrong_ack_is_fail_closed_before_bundle_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target = Path(tempdir) / "no-bundle-created"
            result = launch(
                "--output-directory", str(target),
                "--seller-browser-public-key", "invalid-public-input",
                "--buyer-browser-public-key", "invalid-public-input",
                "--execute-local-test-provisioning", "WRONG",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("status=BLOCKED code=EXECUTION_OPT_IN_REQUIRED", result.stderr)
            self.assertEqual(result.stdout, "")
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
