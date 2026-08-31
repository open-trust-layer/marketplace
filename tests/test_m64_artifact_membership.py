from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).parents[1]
SOURCE = REPO_ROOT / "src" / "marketplace" / "runtime" / "inbound_http_execution_gate.py"
SECURITY_DOC = REPO_ROOT / "docs" / "bounded-inbound-http-execution-gate-terminal-authority-release.md"
M64_TESTS = REPO_ROOT / "tests" / "test_inbound_http_execution_gate_m64_release.py"


class M64ArtifactMembershipTests(unittest.TestCase):
    def test_m64_required_source_tests_and_security_document_are_present(self):
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(M64_TESTS.is_file())
        self.assertTrue(SECURITY_DOC.is_file())

    def test_m64_source_clears_all_newly_required_terminal_authority(self):
        source = SOURCE.read_text(encoding="utf-8")
        for assignment in (
            "self._error_type = None",
            "self._bounded_lower_code_function = None",
            "self._fail_function = None",
        ):
            with self.subTest(assignment=assignment):
                self.assertIn(assignment, source)


if __name__ == "__main__":
    unittest.main()
