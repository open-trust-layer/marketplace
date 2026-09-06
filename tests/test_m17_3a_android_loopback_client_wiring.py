from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android"
KOTLIN = ANDROID / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace"
MAIN = KOTLIN / "MainActivity.kt"
TRANSPORT = KOTLIN / "LoopbackMarketplaceTransport.kt"
CODEC = KOTLIN / "AndroidMarketplaceJsonCodec.kt"
APP = KOTLIN / "MarketplaceApp.kt"
CLIENT = KOTLIN / "MarketplaceApiClient.kt"
STATE = KOTLIN / "MarketplaceState.kt"
MANIFEST = ANDROID / "app" / "src" / "main" / "AndroidManifest.xml"
NETWORK = ANDROID / "app" / "src" / "main" / "res" / "xml" / "network_security_config.xml"
APP_BUILD = ANDROID / "app" / "build.gradle.kts"
DOC = ROOT / "docs" / "m17-3a-android-loopback-client-wiring.md"


class M173AAndroidLoopbackClientWiringTests(unittest.TestCase):
    def test_required_launchable_client_artifacts_exist(self):
        for path in (MAIN, TRANSPORT, CODEC, APP, CLIENT, STATE, MANIFEST, NETWORK, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_manifest_exposes_one_launcher_and_local_network_config(self):
        text = MANIFEST.read_text(encoding="utf-8")
        for marker in (
            'android.permission.INTERNET',
            'android:name=".MainActivity"',
            'android:exported="true"',
            'android.intent.action.MAIN',
            'android.intent.category.LAUNCHER',
            'android:networkSecurityConfig="@xml/network_security_config"',
            'android:usesCleartextTraffic="false"',
        ):
            self.assertIn(marker, text)
        self.assertEqual(text.count('<activity'), 1)

    def test_cleartext_exception_is_localhost_only(self):
        tree = ET.parse(NETWORK)
        root = tree.getroot()
        base = root.find("base-config")
        self.assertIsNotNone(base)
        self.assertEqual(base.attrib.get("cleartextTrafficPermitted"), "false")
        domains = root.findall("./domain-config/domain")
        self.assertEqual([(item.text, item.attrib.get("includeSubdomains")) for item in domains], [("localhost", "false")])
        domain_config = root.find("domain-config")
        self.assertEqual(domain_config.attrib.get("cleartextTrafficPermitted"), "true")

    def test_transport_is_exact_loopback_only_and_bounded(self):
        text = TRANSPORT.read_text(encoding="utf-8")
        for marker in (
            'LOOPBACK_BASE_URL = "http://localhost:18080"',
            'resolved.host != "localhost"',
            'resolved.port != 18080',
            'connection.instanceFollowRedirects = false',
            'MAX_REQUEST_BYTES = 256 * 1024',
            'MAX_RESPONSE_BYTES = 300 * 1024',
            'CONNECT_TIMEOUT_MS = 5_000',
            'READ_TIMEOUT_MS = 5_000',
            'Dispatchers.IO',
            'APPLICATION_HTTP_ENTITY_INVALID',
        ):
            self.assertIn(marker, text)
        lowered = text.lower()
        for forbidden in ("0.0.0.0", "10.0.2.2", "https://", "println(", "log."):
            self.assertNotIn(forbidden, lowered)

    def test_record_route_identity_is_not_fabricated_from_body(self):
        client = CLIENT.read_text(encoding="utf-8")
        codec = CODEC.read_text(encoding="utf-8")
        self.assertIn("fun decodeRecord(rawJson: String, expectedRecordId: String): RawRecord", client)
        self.assertIn("RawRecord(expectedRecordId, rawJson)", codec)
        self.assertIn("JSONTokener(rawJson)", codec)
        self.assertIn("tokener.nextClean()", codec)
        block = codec[codec.index("override fun decodeRecord"):codec.index("override fun decodeSyncPage")]
        self.assertNotIn('"record_id"', block)
        self.assertIn("APPLICATION_RECORD_REQUIRED_FIELDS", block)
        self.assertIn("APPLICATION_RECORD_ALLOWED_FIELDS", block)
        for marker in ('"envelope_version"', '"type"', '"content"'):
            self.assertIn(marker, codec)

    def test_activity_wires_existing_state_and_surfaces_only_stable_errors(self):
        text = MAIN.read_text(encoding="utf-8")
        for marker in (
            "class MainActivity : ComponentActivity()",
            "setContent",
            "MarketplaceState(",
            "MarketplaceApiClient(",
            "LoopbackMarketplaceTransport()",
            "AndroidMarketplaceJsonCodec()",
            "LaunchedEffect(Unit)",
            "state.startupSync()",
            "state.incrementalSync()",
            "state.selectRootIntent(recordId)",
            "state.createProductListing(fields)",
            "state.createProposal(parentId, fields)",
            'operationStatus = "Operation failed: ${error.code}"',
        ):
            self.assertIn(marker, text)
        lowered = text.lower()
        for forbidden in ("error.message", "printstacktrace", "log."):
            self.assertNotIn(forbidden, lowered)

    def test_screen_keeps_authoring_controls_reachable(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("verticalScroll(rememberScrollState())", text)
        self.assertIn("uiState.rootRecords.forEach", text)
        self.assertNotIn("LazyColumn", text)
    def test_no_new_android_dependency_is_introduced(self):
        text = APP_BUILD.read_text(encoding="utf-8")
        self.assertEqual(text.count("implementation("), 5)
        for forbidden in ("okhttp", "ktor", "retrofit", "moshi", "gson"):
            self.assertNotIn(forbidden, text.lower())

    def test_new_source_has_no_persistence_background_install_or_signing_authority(self):
        combined = "\n".join(path.read_text(encoding="utf-8") for path in (MAIN, TRANSPORT, CODEC, MANIFEST, NETWORK)).lower()
        for forbidden in (
            "sharedpreferences", "datastore", "roomdatabase", "workmanager",
            "packageinstaller", "downloadmanager", "signingconfig", "keystore",
            "android.app.service", "startservice(", "startforegroundservice(",
        ):
            self.assertNotIn(forbidden, combined)

    def test_document_keeps_build_runtime_and_distribution_out_of_scope(self):
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "M17.3A Android loopback client wiring",
            "source-only",
            "http://localhost:18080",
            "adb reverse",
            "no Android build",
            "no Android runtime",
            "no signing or distribution",
            "same Marketplace application API",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
