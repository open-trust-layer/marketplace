from __future__ import annotations

import subprocess
import sys
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "android" / "toolchain.toml"
VALIDATOR = ROOT / "tools" / "validate_android_toolchain.py"
DOC = ROOT / "docs" / "m17-1e-android-build-contract.md"


class M17AndroidBuildContractTests(unittest.TestCase):
    def test_required_build_contract_artifacts_exist(self):
        for path in (MANIFEST, VALIDATOR, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_reviewed_toolchain_versions_are_exactly_pinned(self):
        data = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["jdk_major"], 17)
        self.assertEqual(data["gradle"], "9.6.0")
        self.assertEqual(data["android_gradle_plugin"], "9.4.0")
        self.assertEqual(data["kotlin"], "2.4.10")
        self.assertEqual(data["compile_sdk"], 37)
        self.assertEqual(data["target_sdk"], 37)
        self.assertEqual(data["build_tools"], "36.0.0")
        self.assertEqual(data["compose"], "1.12.0")
        self.assertEqual(data["material3"], "1.4.0")
        self.assertEqual(data["activity_compose"], "1.13.0")

    def test_manifest_only_validation_is_deterministic_and_inert(self):
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR), "--manifest-only"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "ANDROID_TOOLCHAIN_MANIFEST_OK")

    def test_validator_has_no_download_install_or_signing_authority(self):
        text = VALIDATOR.read_text(encoding="utf-8").lower()
        for forbidden in (
            "requests", "urllib", "http://", "https://", "curl ", "wget ",
            "choco ", "winget ", "sdkmanager", "gradlew", "keystore", "signingconfig",
        ):
            self.assertNotIn(forbidden, text)

    def test_document_is_truthful_about_current_build_boundary(self):
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "M17.1E Android build contract", "no APK/AAB build claim",
            "no automatic toolchain installation", "exact version pins",
            "future compile CI", "no signing or distribution authority",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
