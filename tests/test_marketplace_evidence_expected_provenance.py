"""Offline comparison of evidence labels with operator-reviewed commit and CI run."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_m17_7r_authenticated_local_flight_evidence_validator import valid_evidence
from tools.marketplace_authenticated_local_flight_evidence import main


class ExpectedProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "local-flight-evidence.json"
        self.document = valid_evidence()
        self.path.write_text(json.dumps(self.document), encoding="utf-8")

    def evaluate(self, *options: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main([str(self.path), *options])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_expected_commit_and_run_match_without_external_attestation(self) -> None:
        code, out, err = self.evaluate(
            "--expected-main-sha", self.document["main_commit"],
            "--expected-ci-run-number", "958",
        )
        self.assertEqual((code, err), (0, ""))
        self.assertIn("status=PASS", out)
        self.assertIn("expected_provenance_fields_match=true", out)
        self.assertIn("actual_git_ci_provenance_verified=false", out)

    def test_unpinned_legacy_cli_compatibility(self) -> None:
        code, out, err = self.evaluate()
        self.assertEqual((code, err), (0, ""))
        self.assertIn("status=PASS", out)
        self.assertNotIn("expected_provenance_fields_match=true", out)

    def test_reject_wrong_main_sha_without_claiming_pass(self) -> None:
        code, out, err = self.evaluate(
            "--expected-main-sha", "b" * 40,
            "--expected-ci-run-number", "958",
        )
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertEqual(err.strip(), "status=FAIL code=EVIDENCE_MAIN_COMMIT_MISMATCH")

    def test_reject_wrong_ci_run_without_claiming_pass(self) -> None:
        code, out, err = self.evaluate(
            "--expected-main-sha", self.document["main_commit"],
            "--expected-ci-run-number", "959",
        )
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertEqual(err.strip(), "status=FAIL code=EVIDENCE_CI_RUN_MISMATCH")

    def test_incomplete_expected_provenance_fails_closed(self) -> None:
        for options in (
            ("--expected-main-sha", self.document["main_commit"]),
            ("--expected-ci-run-number", "958"),
        ):
            with self.subTest(options=options):
                code, out, err = self.evaluate(*options)
                self.assertEqual(code, 1)
                self.assertEqual(out, "")
                self.assertEqual(err.strip(), "status=FAIL code=EXPECTED_PROVENANCE_INCOMPLETE")

    def test_malformed_expected_values_are_rejected_without_reflection(self) -> None:
        invalid_cases = (
            ("SECRET_TOKEN", "958"),
            ("B" * 40, "958"),
            (self.document["main_commit"], "958;SECRET_TOKEN"),
            (self.document["main_commit"], "0"),
            (self.document["main_commit"], "-1"),
            (self.document["main_commit"], "9007199254740992"),
            (self.document["main_commit"], "9" * 5000),
        )
        for expected_sha, expected_run in invalid_cases:
            with self.subTest(run=expected_run[:8]):
                code, out, err = self.evaluate(
                    "--expected-main-sha", expected_sha,
                    "--expected-ci-run-number", expected_run,
                )
                self.assertEqual(code, 1)
                self.assertEqual(out, "")
                self.assertEqual(err.strip(), "status=FAIL code=EXPECTED_PROVENANCE_INVALID")
                self.assertNotIn("SECRET_TOKEN", err)


if __name__ == "__main__":
    unittest.main()
