from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).parents[1]
SOURCE = REPO_ROOT / "src" / "marketplace" / "runtime" / "inbound_federation.py"
SECURITY_DOC = REPO_ROOT / "docs" / "bounded-inbound-federation-retained-binding-hardening.md"
M60_TESTS = REPO_ROOT / "tests" / "test_inbound_federation_m60_hardening.py"


class M60ArtifactMembershipTests(unittest.TestCase):
    def test_m60_required_source_tests_and_security_document_are_present(self):
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(M60_TESTS.is_file())
        self.assertTrue(SECURITY_DOC.is_file())

    def test_m60_source_exposes_stable_drift_codes(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("INBOUND_FEDERATION_BINDING_DRIFT", source)
        self.assertIn("INBOUND_FEDERATION_CONFIGURATION_DRIFT", source)


if __name__ == "__main__":
    unittest.main()
