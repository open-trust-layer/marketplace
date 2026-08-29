from __future__ import annotations

import unittest
from pathlib import Path

from artifact_membership_test_cache import built_distribution_names


class M58ArtifactMembershipTests(unittest.TestCase):
    def test_m58_source_tests_and_security_document_are_required_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "src/marketplace/runtime/inbound_http.py").is_file())
        self.assertTrue((root / "tests/test_inbound_http_m58_hardening.py").is_file())
        self.assertTrue(
            (
                root
                / "docs/bounded-inbound-http-application-retained-binding-hardening.md"
            ).is_file()
        )

    def test_built_distribution_contains_hardened_m34_runtime(self):
        root = Path(__file__).resolve().parents[1]
        names = built_distribution_names(root)
        self.assertIn("marketplace/runtime/inbound_http.py", names)


if __name__ == "__main__":
    unittest.main()
