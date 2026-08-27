from __future__ import annotations

import pathlib
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


class M48ArtifactMembershipTests(unittest.TestCase):
    def test_m48_runtime_and_document_are_required_repository_artifacts(self):
        self.assertTrue((ROOT / "src/marketplace/runtime/inbound_http_response_write_invoke.py").is_file())
        self.assertTrue((ROOT / "docs/bounded-inbound-http-response-write-invocation.md").is_file())

    def test_built_distribution_contains_m48_runtime(self):
        wheels = sorted((ROOT / "dist").glob("*.whl"))
        if not wheels:
            self.skipTest("wheel is built by the artifact gate")
        with zipfile.ZipFile(wheels[-1]) as archive:
            self.assertIn("marketplace/runtime/inbound_http_response_write_invoke.py", archive.namelist())


if __name__ == "__main__":
    unittest.main()
