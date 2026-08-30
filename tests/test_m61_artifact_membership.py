from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).parents[1]
SOURCE = REPO_ROOT / "src" / "marketplace" / "runtime" / "inbound_record.py"
SECURITY_DOC = REPO_ROOT / "docs" / "bounded-inbound-record-retained-binding-hardening.md"
M61_TESTS = REPO_ROOT / "tests" / "test_inbound_record_m61_hardening.py"


class M61ArtifactMembershipTests(unittest.TestCase):
    def test_m61_required_source_tests_and_security_document_are_present(self):
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(M61_TESTS.is_file())
        self.assertTrue(SECURITY_DOC.is_file())

    def test_m61_source_exposes_stable_drift_codes(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("INBOUND_RECORD_BINDING_DRIFT", source)
        self.assertIn("INBOUND_RECORD_CONFIGURATION_DRIFT", source)


if __name__ == "__main__":
    unittest.main()
