from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from package_artifact_gate import _build_wheel


class M34ArtifactMembershipTests(unittest.TestCase):
    def test_m34_runtime_reference_and_security_document_are_required_repository_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "src/marketplace/runtime/inbound_http.py").is_file())
        self.assertTrue((root / "src/marketplace/reference/inbound_http_v1.py").is_file())
        self.assertTrue((root / "docs/bounded-inbound-http-application-adapter.md").is_file())

    def test_built_distribution_contains_m34_runtime_and_reference_adapter(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            wheel = _build_wheel(
                root,
                Path(temp_dir),
                90.0,
                "M34 wheel membership test",
            )
            with zipfile.ZipFile(wheel, "r") as archive:
                names = set(archive.namelist())
            self.assertIn("marketplace/runtime/inbound_http.py", names)
            self.assertIn("marketplace/reference/inbound_http_v1.py", names)


if __name__ == "__main__":
    unittest.main()
