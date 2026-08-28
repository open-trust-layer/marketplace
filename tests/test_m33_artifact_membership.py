from __future__ import annotations

import unittest
from pathlib import Path

from artifact_membership_test_cache import built_distribution_names


class M33ArtifactMembershipTests(unittest.TestCase):
    def test_m33_runtime_reference_and_security_document_are_required_repository_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "src/marketplace/runtime/inbound_record.py").is_file())
        self.assertTrue((root / "src/marketplace/reference/record_serving_v1.py").is_file())
        self.assertTrue((root / "docs/bounded-inbound-record-response-preparation.md").is_file())

    def test_built_distribution_contains_m33_runtime_and_reference_adapter(self):
        root = Path(__file__).resolve().parents[1]
        names = built_distribution_names(root)
        self.assertIn("marketplace/runtime/inbound_record.py", names)
        self.assertIn("marketplace/reference/record_serving_v1.py", names)


if __name__ == "__main__":
    unittest.main()
