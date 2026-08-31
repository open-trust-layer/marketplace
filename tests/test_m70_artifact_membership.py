from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).parents[1]
SOURCE = REPO_ROOT / "src" / "marketplace" / "runtime" / "inbound_http_execution_gate.py"
SECURITY_DOC = REPO_ROOT / "docs" / "bounded-inbound-http-execution-gate-close-preflight-gate-type.md"
M70_TESTS = REPO_ROOT / "tests" / "test_inbound_http_execution_gate_m70_close_preflight.py"


class M70ArtifactMembershipTests(unittest.TestCase):
    def test_m70_required_source_tests_and_security_document_are_present(self):
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(M70_TESTS.is_file())
        self.assertTrue(SECURITY_DOC.is_file())

    def test_m70_close_preflight_never_dereferences_retained_gate_type(self):
        source = SOURCE.read_text(encoding="utf-8")
        close = source.split("    def close(self) -> None:", 1)[1]
        self.assertNotIn('validate is gate_type.__dict__.get("_validate_bindings")', close)
        identity_check = close.index("gate_type is actual_gate_type")
        validator_lookup = close.index('actual_gate_type.__dict__.get("_validate_bindings")')
        self.assertLess(identity_check, validator_lookup)


if __name__ == "__main__":
    unittest.main()
