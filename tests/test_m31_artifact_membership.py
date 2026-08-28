from __future__ import annotations

import unittest
from pathlib import Path

from artifact_membership_test_cache import built_distribution_names


class M31ArtifactMembershipTests(unittest.TestCase):
    def test_m31_runtime_and_security_document_are_required_repository_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "src/marketplace/runtime/synchronization.py").is_file())
        self.assertTrue((root / "docs/bounded-multipage-federation-synchronization.md").is_file())

    def test_built_distribution_contains_m31_synchronization_runtime(self):
        root = Path(__file__).resolve().parents[1]
        names = built_distribution_names(root)
        self.assertIn("marketplace/runtime/synchronization.py", names)


if __name__ == "__main__":
    unittest.main()
