from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KOTLIN = ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace"
CACHE = KOTLIN / "MarketplaceOfflineCache.kt"
ANDROID_CACHE = KOTLIN / "AndroidFileMarketplaceOfflineCache.kt"
STATE = KOTLIN / "MarketplaceState.kt"
MAIN = KOTLIN / "MainActivity.kt"
BUILD = ROOT / "android" / "app" / "build.gradle.kts"
DOC = ROOT / "docs" / "m17-4b-android-offline-cache.md"


class M174BAndroidOfflineCacheTests(unittest.TestCase):
    def test_required_artifacts_exist(self):
        for path in (CACHE, ANDROID_CACHE, STATE, MAIN, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_retention_profile_is_exact_and_bounded(self):
        text = CACHE.read_text(encoding="utf-8")
        for marker in (
            "MAX_OFFLINE_CACHE_RECORDS = 320",
            "MAX_OFFLINE_ROOT_RECORDS = 256",
            "MAX_OFFLINE_RESPONSE_RECORDS = 64",
            "MAX_OFFLINE_CACHE_CANONICAL_BYTES = 32 * 1024 * 1024",
            "MAX_OFFLINE_CACHE_AGE_MILLIS = 24L * 60L * 60L * 1000L",
            "OFFLINE / CACHED",
        ):
            self.assertIn(marker, text)

    def test_cache_port_and_snapshot_are_transport_neutral(self):
        text = CACHE.read_text(encoding="utf-8")
        for marker in (
            "interface MarketplaceOfflineCache",
            "data class MarketplaceOfflineSnapshot",
            "suspend fun load(nowEpochMillis: Long)",
            "suspend fun replace(snapshot: MarketplaceOfflineSnapshot)",
            "suspend fun clear()",
            "selectedParentId: String?",
            "selectedResponses: List<RawRecord>",
        ):
            self.assertIn(marker, text)

    def test_platform_adapter_uses_fixed_private_file_and_fails_closed(self):
        text = ANDROID_CACHE.read_text(encoding="utf-8")
        for marker in (
            'CACHE_FILE_NAME = "marketplace_offline_cache_v1.json"',
            "context.filesDir",
            "withContext(Dispatchers.IO)",
            "MessageDigest.getInstance(\"SHA-256\")",
            "OFFLINE_CACHE_CORRUPT",
            "OFFLINE_CACHE_EXPIRED",
            "StandardCopyOption.ATOMIC_MOVE",
            "StandardCopyOption.REPLACE_EXISTING",
        ):
            self.assertIn(marker, text)
    def test_state_adopts_cache_only_as_explicit_offline_fallback(self):
        text = STATE.read_text(encoding="utf-8")
        for marker in (
            "suspend fun startupSync()",
            "adoptOfflineCache",
            "isOfflineCached = true",
            'syncStatus = "OFFLINE / CACHED',
            "OFFLINE_WRITE_UNAVAILABLE",
            "cache.replace",
            "if (!hasMore)",
        ):
            self.assertIn(marker, text)

    def test_main_wires_platform_cache_without_new_origin_or_background_work(self):
        main = MAIN.read_text(encoding="utf-8")
        build = BUILD.read_text(encoding="utf-8")
        self.assertIn("AndroidFileMarketplaceOfflineCache(", main)
        self.assertIn("System::currentTimeMillis", main)
        self.assertIn("state.startupSync()", main)
        self.assertEqual(build.lower().count("implementation("), 5)
        combined = (CACHE.read_text(encoding="utf-8") + ANDROID_CACHE.read_text(encoding="utf-8") + main).lower()
        for forbidden in (
            "workmanager", "jobservice", "alarmmanager", "service()", "roomdatabase",
            "datastore", "sharedpreferences", "httpurlconnection", "https://", "http://",
        ):
            self.assertNotIn(forbidden, combined)

    def test_document_records_exact_authority_and_retention_boundary(self):
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_ANDROID_OFFLINE_CACHE_MVP",
            "320 records",
            "32 MiB",
            "24 hours",
            "OFFLINE / CACHED",
            "online-only",
            "no background sync",
            "no Android build",
            "no adb",
            "no server or PostgreSQL mutation",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
