from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from package_artifact_gate import _build_wheel


class M41ArtifactMembershipTests(unittest.TestCase):
    def test_m41_runtime_and_security_document_are_required_repository_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "src/marketplace/runtime/inbound_http_read_invoke.py").is_file())
        self.assertTrue((root / "docs/bounded-inbound-http-read-invocation.md").is_file())

    def test_built_distribution_contains_m41_runtime(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            wheel = _build_wheel(
                root,
                Path(temp_dir),
                90.0,
                "M41 wheel membership test",
            )
            with zipfile.ZipFile(wheel, "r") as archive:
                names = set(archive.namelist())
            self.assertIn("marketplace/runtime/inbound_http_read_invoke.py", names)


if __name__ == "__main__":
    unittest.main()
