from __future__ import annotations

import pathlib
import unittest
import zipfile


class M45ArtifactMembershipTests(unittest.TestCase):
    def test_m45_runtime_and_document_are_required_repository_artifacts(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        self.assertTrue((root / "src/marketplace/runtime/inbound_http_response_write_transition.py").is_file())
        self.assertTrue((root / "docs/bounded-inbound-http-response-write-transition.md").is_file())

    def test_built_distribution_contains_m45_runtime(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        wheels = tuple((root / "dist").glob("open_layer_marketplace-*.whl"))
        if not wheels:
            self.skipTest("wheel is built by the artifact gate")
        with zipfile.ZipFile(wheels[0]) as archive:
            self.assertIn("marketplace/runtime/inbound_http_response_write_transition.py", archive.namelist())


if __name__ == "__main__":
    unittest.main()
