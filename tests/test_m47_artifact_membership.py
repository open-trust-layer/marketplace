from __future__ import annotations

import pathlib
import unittest
import zipfile


class M47ArtifactMembershipTests(unittest.TestCase):
    def test_m47_runtime_and_document_are_required_repository_artifacts(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        self.assertTrue(
            (root / "src/marketplace/runtime/inbound_http_response_write_outcome.py").is_file()
        )
        self.assertTrue(
            (root / "docs/bounded-inbound-http-response-write-outcome.md").is_file()
        )

    def test_built_distribution_contains_m47_runtime(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        wheels = tuple((root / "dist").glob("open_layer_marketplace-*.whl"))
        if not wheels:
            self.skipTest("wheel is built by the artifact gate")
        with zipfile.ZipFile(wheels[0]) as archive:
            self.assertIn(
                "marketplace/runtime/inbound_http_response_write_outcome.py",
                archive.namelist(),
            )


if __name__ == "__main__":
    unittest.main()
