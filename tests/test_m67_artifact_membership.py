from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).parents[1]
SOURCE = REPO_ROOT / "src" / "marketplace" / "runtime" / "inbound_http_execution_gate.py"
SECURITY_DOC = REPO_ROOT / "docs" / "bounded-inbound-http-execution-gate-terminal-error-artifact.md"
M67_TESTS = REPO_ROOT / "tests" / "test_inbound_http_execution_gate_m67_terminal_artifact.py"


class M67ArtifactMembershipTests(unittest.TestCase):
    def test_m67_required_source_tests_and_security_document_are_present(self):
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(M67_TESTS.is_file())
        self.assertTrue(SECURITY_DOC.is_file())

    def test_m67_terminal_artifact_is_identity_bound_without_restoring_m64_authority(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('"_terminal_error_witness"', source)
        self.assertIn('"_terminal_error_type_identity"', source)
        self.assertIn('"m67-terminal-error-artifact-v1"', source)
        self.assertIn("self._terminal_error_type_identity = id(self._error_type)", source)
        self.assertIn("terminal_witness[1] is not self._terminal_error_template", source)
        self.assertIn("self._error_type = None", source)
        self.assertIn("self._fail_function = None", source)
        self.assertNotIn("self._terminal_error_type =", source)

    def test_m67_terminal_paths_cross_check_inert_anchors(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("terminal_template is witnessed_template"), 2)
        self.assertGreaterEqual(
            source.count("id(type(terminal_template)) == terminal_type_identity"), 2
        )
        self.assertGreaterEqual(
            source.count("id(type(witnessed_template)) == terminal_type_identity"), 2
        )
        self.assertGreaterEqual(source.count("BaseException.__new__(terminal_error_type)"), 2)


if __name__ == "__main__":
    unittest.main()
