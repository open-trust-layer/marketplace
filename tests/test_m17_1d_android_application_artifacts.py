from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android"
KOTLIN = ANDROID / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace"
APP = KOTLIN / "MarketplaceApp.kt"
CLIENT = KOTLIN / "MarketplaceApiClient.kt"
STATE = KOTLIN / "MarketplaceState.kt"
MANIFEST = ANDROID / "app" / "src" / "main" / "AndroidManifest.xml"
DOC = ROOT / "docs" / "m17-1d-android-application.md"


class M17AndroidApplicationArtifactTests(unittest.TestCase):
    def test_android_source_artifacts_exist(self):
        for path in (APP, CLIENT, STATE, MANIFEST, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_compose_shell_exposes_browse_detail_create_and_respond(self):
        text = APP.read_text(encoding="utf-8")
        for marker in (
            "@Composable",
            "MarketplaceScreen",
            "Intent list",
            "Intent detail",
            "Create intent",
            "Respond to intent",
        ):
            self.assertIn(marker, text)

    def test_api_client_uses_only_reviewed_relative_product_routes(self):
        text = CLIENT.read_text(encoding="utf-8")
        for marker in (
            '"/api/intents"',
            '"/api/sync"',
            '"/responses"',
            "MarketplaceTransport",
            "suspend fun execute",
        ):
            self.assertIn(marker, text)
        lowered = text.lower()
        for forbidden in (
            "http://",
            "https://",
            "okhttp",
            "ktor",
            "httpurlconnection",
            "websocket",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_first_checkpoint_has_no_runtime_network_or_persistent_state_authority(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in (APP, CLIENT, STATE, MANIFEST)
        ).lower()
        for forbidden in (
            "android.permission.internet",
            "sharedpreferences",
            "datastore",
            "roomdatabase",
            "workmanager",
            "serviceworker",
            "packageinstaller",
            "downloadmanager",
        ):
            self.assertNotIn(forbidden, combined)

    def test_authoring_remains_raw_reviewed_record_json_boundary(self):
        text = CLIENT.read_text(encoding="utf-8") + STATE.read_text(encoding="utf-8")
        for marker in ("rawRecordJson", "createIntent", "respondToIntent"):
            self.assertIn(marker, text)
        for forbidden in (
            "buildMarketIntent",
            "validateMarketIntent",
            "recordIdentity",
            "signRecord",
        ):
            self.assertNotIn(forbidden, text)

    def test_sync_recovery_is_bounded_and_truthful(self):
        text = STATE.read_text(encoding="utf-8")
        for marker in (
            "captureSyncWatermark",
            "fullResync",
            "MAX_LIST_PAGES",
            "MAX_SYNC_PAGES",
            "SYNC_CURSOR_EXPIRED",
            "more changes remain",
        ):
            self.assertIn(marker, text)

    def test_design_document_preserves_android_authority_boundary(self):
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "M17.1D Android",
            "same application API",
            "in-memory only",
            "no Android runtime",
            "no live network",
            "no app signing",
            "no self-update",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
