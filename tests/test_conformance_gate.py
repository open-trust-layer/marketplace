from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from conformance_gate import GateConfig, GateError, run_checked, run_diff_check, verify_olp_pin
from conformance_manifest import EXPECTED_TOTAL, SUITES

PIN = "41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c"


class FakeExecutor:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def run(self, argv, *, cwd, env, timeout):
        self.calls.append((tuple(argv), Path(cwd), dict(env), timeout))
        if not self.outcomes:
            raise AssertionError("unexpected executor call")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(["fake"], returncode, stdout=stdout, stderr=stderr)


class ConformanceGateTests(unittest.TestCase):
    def _config(self, root: Path, *, timeout: float = 3.0) -> GateConfig:
        repo = root / "marketplace"
        olp = root / "olp"
        (repo / "conformance").mkdir(parents=True)
        (repo / "conformance" / "olp-source-pin.txt").write_text(PIN + "\n", encoding="utf-8")
        (olp / "src" / "olp").mkdir(parents=True)
        return GateConfig(repo_root=repo, olp_root=olp, timeout_seconds=timeout)

    def test_suite_order_and_total_are_deterministic(self):
        self.assertEqual(tuple(suite.key for suite in SUITES), ("m3", "m4", "m5", "m6", "m7", "m8", "m9", "m10", "m11"))
        self.assertEqual(EXPECTED_TOTAL, 472)

    def test_verify_olp_pin_accepts_exact_checkout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(Path(temp_dir))
            executor = FakeExecutor([completed(stdout=PIN + "\n")])
            self.assertEqual(verify_olp_pin(config, executor), PIN)
            self.assertEqual(executor.calls[0][0][-2:], ("rev-parse", "HEAD"))

    def test_verify_olp_pin_rejects_wrong_checkout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(Path(temp_dir))
            executor = FakeExecutor([completed(stdout="0" * 40 + "\n")])
            with self.assertRaises(GateError) as caught:
                verify_olp_pin(config, executor)
            self.assertEqual(caught.exception.code, "OLP_PIN_MISMATCH")
            self.assertIn(PIN, str(caught.exception))

    def test_verify_olp_pin_rejects_missing_source_root_before_execution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo = root / "marketplace"
            (repo / "conformance").mkdir(parents=True)
            (repo / "conformance" / "olp-source-pin.txt").write_text(PIN + "\n", encoding="utf-8")
            executor = FakeExecutor([])
            config = GateConfig(repo_root=repo, olp_root=root / "missing", timeout_seconds=3.0)
            with self.assertRaises(GateError) as caught:
                verify_olp_pin(config, executor)
            self.assertEqual(caught.exception.code, "OLP_ROOT_MISSING")
            self.assertEqual(executor.calls, [])

    def test_run_checked_preserves_validator_failure_diagnostics(self):
        executor = FakeExecutor([completed(returncode=7, stdout="vector 4 failed", stderr="bad record")])
        with self.assertRaises(GateError) as caught:
            run_checked(
                executor,
                ("python", "validator.py"),
                cwd=Path.cwd(),
                env={},
                timeout=3.0,
                label="m3 validator",
            )
        self.assertEqual(caught.exception.code, "COMMAND_FAILED")
        self.assertIn("vector 4 failed", str(caught.exception))
        self.assertIn("bad record", str(caught.exception))

    def test_run_checked_maps_timeout_to_explicit_failure(self):
        executor = FakeExecutor([subprocess.TimeoutExpired(["python", "validator.py"], timeout=1.5)])
        with self.assertRaises(GateError) as caught:
            run_checked(
                executor,
                ("python", "validator.py"),
                cwd=Path.cwd(),
                env={},
                timeout=1.5,
                label="m3 validator",
            )
        self.assertEqual(caught.exception.code, "COMMAND_TIMEOUT")
        self.assertIn("1.5s", str(caught.exception))

    def test_git_whitespace_gate_checks_worktree_index_and_committed_head(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(Path(temp_dir))
            executor = FakeExecutor([completed(), completed(), completed()])
            run_diff_check(config, executor)
            commands = [call[0] for call in executor.calls]
            self.assertEqual(commands, [
                ("git", "diff", "--check"),
                ("git", "diff", "--cached", "--check"),
                ("git", "diff", "--check", "HEAD^", "HEAD"),
            ])
    def test_run_checked_rejects_nonpositive_timeout(self):
        executor = FakeExecutor([])
        with self.assertRaises(GateError) as caught:
            run_checked(
                executor,
                ("python", "validator.py"),
                cwd=Path.cwd(),
                env={},
                timeout=0,
                label="validator",
            )
        self.assertEqual(caught.exception.code, "INVALID_TIMEOUT")
        self.assertEqual(executor.calls, [])


if __name__ == "__main__":
    unittest.main()
