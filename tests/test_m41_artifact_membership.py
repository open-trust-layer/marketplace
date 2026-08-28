from __future__ import annotations

import unittest
from pathlib import Path

from artifact_membership_test_cache import built_distribution_names


class M41ArtifactMembershipTests(unittest.TestCase):
    def test_m41_runtime_and_security_document_are_required_repository_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "src/marketplace/runtime/inbound_http_read_invoke.py").is_file())
        self.assertTrue((root / "docs/bounded-inbound-http-read-invocation.md").is_file())

    def test_built_distribution_contains_m41_runtime(self):
        root = Path(__file__).resolve().parents[1]
        names = built_distribution_names(root)
        self.assertIn("marketplace/runtime/inbound_http_read_invoke.py", names)


if __name__ == "__main__":
    unittest.main()
