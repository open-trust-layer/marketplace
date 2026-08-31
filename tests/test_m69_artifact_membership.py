from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).parents[1]
SOURCE = REPO_ROOT / "src" / "marketplace" / "runtime" / "inbound_http_execution_gate.py"
SECURITY_DOC = REPO_ROOT / "docs" / "bounded-inbound-http-execution-gate-begin-preflight-gate-type.md"
M69_TESTS = REPO_ROOT / "tests" / "test_inbound_http_execution_gate_m69_begin_preflight.py"


class M69ArtifactMembershipTests(unittest.TestCase):
    def test_m69_required_source_tests_and_security_document_are_present(self):
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(M69_TESTS.is_file())
        self.assertTrue(SECURITY_DOC.is_file())

    def test_m69_begin_preflight_never_dereferences_retained_gate_type(self):
        source = SOURCE.read_text(encoding="utf-8")
        begin = source.split("    def _begin_once", 1)[1].split("    def dry_run", 1)[0]
        self.assertNotIn('validate is not gate_type.__dict__.get("_validate_bindings")', begin)
        identity_check = begin.index("if gate_type is not actual_gate_type:")
        validator_lookup = begin.index('actual_gate_type.__dict__.get("_validate_bindings")')
        self.assertLess(identity_check, validator_lookup)


if __name__ == "__main__":
    unittest.main()
