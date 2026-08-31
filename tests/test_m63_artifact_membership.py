from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).parents[1]
SOURCE = REPO_ROOT / "src" / "marketplace" / "runtime" / "inbound_http_execution_gate.py"
SECURITY_DOC = REPO_ROOT / "docs" / "bounded-inbound-http-execution-gate-retained-binding-hardening.md"
M63_TESTS = REPO_ROOT / "tests" / "test_inbound_http_execution_gate_m63_hardening.py"


class M63ArtifactMembershipTests(unittest.TestCase):
    def test_m63_required_source_tests_and_security_document_are_present(self):
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(M63_TESTS.is_file())
        self.assertTrue(SECURITY_DOC.is_file())

    def test_m63_source_retains_exact_opt_in_and_drift_code(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('self._opt_in_token = "EXECUTE_ONE_LOOPBACK_NETWORK_SESSION"', source)
        self.assertIn("LOOPBACK_EXECUTION_BINDING_DRIFT", source)


if __name__ == "__main__":
    unittest.main()
