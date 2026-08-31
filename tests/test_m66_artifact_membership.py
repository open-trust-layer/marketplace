from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).parents[1]
SOURCE = REPO_ROOT / "src" / "marketplace" / "runtime" / "inbound_http_execution_gate.py"
SECURITY_DOC = REPO_ROOT / "docs" / "bounded-inbound-http-execution-gate-begin-binding.md"
M66_TESTS = REPO_ROOT / "tests" / "test_inbound_http_execution_gate_m66_begin_binding.py"


class M66ArtifactMembershipTests(unittest.TestCase):
    def test_m66_required_source_tests_and_security_document_are_present(self):
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(M66_TESTS.is_file())
        self.assertTrue(SECURITY_DOC.is_file())

    def test_m66_source_retains_validates_and_releases_reviewed_begin_binding(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'self._begin_once_function = BoundedInboundHttpLoopbackExecutionGate.__dict__["_begin_once"]',
            source,
        )
        self.assertIn(
            'self._begin_once_function is not self._gate_type.__dict__.get("_begin_once")',
            source,
        )
        self.assertIn("self._begin_once_function = None", source)
        self.assertGreaterEqual(source.count("begin(self)"), 2)
        self.assertNotIn("self._begin_once()", source)
        self.assertIn("len(witness) == 28", source)
        self.assertIn("witness[26]", source)


if __name__ == "__main__":
    unittest.main()
