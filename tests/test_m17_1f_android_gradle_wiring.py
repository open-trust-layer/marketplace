from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN = ROOT / "android" / "toolchain.toml"
SETTINGS = ROOT / "android" / "settings.gradle.kts"
ROOT_BUILD = ROOT / "android" / "build.gradle.kts"
APP_BUILD = ROOT / "android" / "app" / "build.gradle.kts"
DOC = ROOT / "docs" / "m17-1f-android-gradle-wiring.md"


class M17AndroidGradleWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = tomllib.loads(TOOLCHAIN.read_text(encoding="utf-8"))

    def test_required_source_wiring_artifacts_exist(self):
        for path in (SETTINGS, ROOT_BUILD, APP_BUILD, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_settings_define_only_reviewed_module_and_standard_repositories(self):
        text = SETTINGS.read_text(encoding="utf-8")
        self.assertIn('rootProject.name = "Marketplace"', text)
        self.assertIn('include(":app")', text)
        for marker in ("google()", "mavenCentral()", "gradlePluginPortal()"):
            self.assertIn(marker, text)
        lowered = text.lower()
        for forbidden in ("http://", "https://", "maven { url", "flatdir", "jcenter"):
            self.assertNotIn(forbidden, lowered)

    def test_root_plugins_match_reviewed_toolchain_pins(self):
        text = ROOT_BUILD.read_text(encoding="utf-8")
        expected = (
            f'id("com.android.application") version "{self.pins["android_gradle_plugin"]}" apply false',
            f'id("org.jetbrains.kotlin.android") version "{self.pins["kotlin"]}" apply false',
            f'id("org.jetbrains.kotlin.plugin.compose") version "{self.pins["kotlin"]}" apply false',
        )
        for marker in expected:
            self.assertIn(marker, text)

    def test_app_android_identity_and_sdk_contract_match_reviewed_profile(self):
        text = APP_BUILD.read_text(encoding="utf-8")
        for marker in (
            'namespace = "org.opentrustlayer.marketplace"',
            'applicationId = "org.opentrustlayer.marketplace"',
            f'compileSdk = {self.pins["compile_sdk"]}',
            f'targetSdk = {self.pins["target_sdk"]}',
            f'buildToolsVersion = "{self.pins["build_tools"]}"',
        ):
            self.assertIn(marker, text)

    def test_java_kotlin_and_compose_source_configuration_is_exact(self):
        text = APP_BUILD.read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("JavaVersion.VERSION_17"), 2)
        self.assertIn("JvmTarget.JVM_17", text)
        self.assertIn("compose = true", text)

    def test_declared_ui_dependencies_match_reviewed_pins_exactly(self):
        text = APP_BUILD.read_text(encoding="utf-8")
        expected = (
            f'implementation("androidx.activity:activity-compose:{self.pins["activity_compose"]}")',
            f'implementation("androidx.compose.ui:ui:{self.pins["compose"]}")',
            f'implementation("androidx.compose.material3:material3:{self.pins["material3"]}")',
        )
        for marker in expected:
            self.assertIn(marker, text)
        self.assertEqual(text.count("implementation("), len(expected))

    def test_wiring_has_no_wrapper_signing_install_or_runtime_authority(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in (SETTINGS, ROOT_BUILD, APP_BUILD)
        )
        for forbidden in (
            "signingconfig", "keystore", "storefile", "packageinstaller",
            "downloadmanager", "exec(", "javaexec", "http://", "https://",
        ):
            self.assertNotIn(forbidden, combined)
        for path in (ROOT / "gradlew", ROOT / "gradlew.bat", ROOT / "gradle" / "wrapper"):
            self.assertFalse(path.exists(), str(path))

    def test_document_distinguishes_declaration_from_build_evidence(self):
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "M17.1F source-only Android Gradle wiring",
            "declared build configuration",
            "not resolved dependency evidence",
            "no APK/AAB claim",
            "no signing, installation, distribution, or runtime authority",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
