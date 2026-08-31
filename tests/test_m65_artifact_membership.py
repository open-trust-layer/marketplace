from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).parents[1]
SOURCE = REPO_ROOT / "src" / "marketplace" / "runtime" / "inbound_http_execution_gate.py"
SECURITY_DOC = REPO_ROOT / "docs" / "bounded-inbound-http-execution-gate-terminal-release-binding.md"
M65_TESTS = REPO_ROOT / "tests" / "test_inbound_http_execution_gate_m65_release_binding.py"


class M65ArtifactMembershipTests(unittest.TestCase):
    def test_m65_required_source_tests_and_security_document_are_present(self):
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(M65_TESTS.is_file())
        self.assertTrue(SECURITY_DOC.is_file())

    def test_m65_source_uses_and_releases_reviewed_terminal_cleanup_binding(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'self._release_function = BoundedInboundHttpLoopbackExecutionGate.__dict__["_release"]',
            source,
        )
        self.assertIn("self._release_function = None", source)
        self.assertGreaterEqual(source.count("release(self)"), 3)
        self.assertNotIn("self._release()", source)


if __name__ == "__main__":
    unittest.main()
