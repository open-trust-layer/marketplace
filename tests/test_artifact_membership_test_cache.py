from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import artifact_membership_test_cache as cache


class ArtifactMembershipTestCacheTests(unittest.TestCase):
    def tearDown(self) -> None:
        cache._cached_distribution_names.cache_clear()

    def test_identical_repo_uses_one_real_wheel_result(self) -> None:
        calls: list[Path] = []

        def fake_build(repo_root: Path, build_root: Path, timeout: float, label: str) -> Path:
            calls.append(repo_root)
            wheel = build_root / "sample.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("marketplace/runtime/example.py", b"# example\n")
            return wheel

        with tempfile.TemporaryDirectory() as repo_dir:
            repo_root = Path(repo_dir)
            with patch.object(cache, "_build_wheel", side_effect=fake_build):
                first = cache.built_distribution_names(repo_root)
                second = cache.built_distribution_names(repo_root)

        self.assertEqual(len(calls), 1)
        self.assertIs(first, second)
        self.assertIn("marketplace/runtime/example.py", first)


if __name__ == "__main__":
    unittest.main()
