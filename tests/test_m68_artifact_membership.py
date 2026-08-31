from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).parents[1]
SOURCE = REPO_ROOT / "src" / "marketplace" / "runtime" / "inbound_http_execution_gate.py"
SECURITY_DOC = REPO_ROOT / "docs" / "bounded-inbound-http-execution-gate-preflight-failure-binding.md"
M68_TESTS = REPO_ROOT / "tests" / "test_inbound_http_execution_gate_m68_preflight_binding.py"


class M68ArtifactMembershipTests(unittest.TestCase):
    def test_m68_required_source_tests_and_security_document_are_present(self):
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(M68_TESTS.is_file())
        self.assertTrue(SECURITY_DOC.is_file())

    def test_m68_preflight_never_dispatches_through_unvalidated_fail_binding(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("fail_begin = self._fail_function", source)
        self.assertNotIn("fail_begin(\"LOOPBACK_EXECUTION_BINDING_DRIFT\"", source)
        self.assertGreaterEqual(source.count("actual_gate_type = type(self)"), 2)
        self.assertGreaterEqual(source.count("gate_type is not actual_gate_type"), 2)
        self.assertGreaterEqual(
            source.count('actual_gate_type.__dict__.get("_validate_bindings")'),
            2,
        )

    def test_m68_preflight_reuses_only_inert_m67_error_anchors(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("terminal_template = self._terminal_error_template"), 4)
        self.assertGreaterEqual(source.count("terminal_witness = self._terminal_error_witness"), 4)
        self.assertGreaterEqual(
            source.count("terminal_type_identity = self._terminal_error_type_identity"),
            4,
        )
        self.assertGreaterEqual(source.count("BaseException.__new__(error_type)"), 2)
        self.assertGreaterEqual(
            source.count('object.__setattr__(error, "code", "LOOPBACK_EXECUTION_BINDING_DRIFT")'),
            2,
        )
        self.assertIn("self._fail_function = None", source)
        self.assertIn("self._gate_type = None", source)


if __name__ == "__main__":
    unittest.main()
