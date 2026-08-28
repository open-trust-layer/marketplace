from __future__ import annotations

import unittest
from pathlib import Path

from artifact_membership_test_cache import built_distribution_names


class M37ArtifactMembershipTests(unittest.TestCase):
    def test_m37_runtime_and_security_document_are_required_repository_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "src/marketplace/runtime/inbound_http_read_plan.py").is_file())
        self.assertTrue((root / "docs/bounded-inbound-http-read-planning.md").is_file())

    def test_built_distribution_contains_m37_runtime(self):
        root = Path(__file__).resolve().parents[1]
        names = built_distribution_names(root)
        self.assertIn("marketplace/runtime/inbound_http_read_plan.py", names)


if __name__ == "__main__":
    unittest.main()
