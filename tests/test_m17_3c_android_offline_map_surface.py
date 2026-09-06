from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KOTLIN = ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace"
MAP = KOTLIN / "MarketplaceMapSurface.kt"
APP = KOTLIN / "MarketplaceApp.kt"
APP_BUILD = ROOT / "android" / "app" / "build.gradle.kts"
MANIFEST = ROOT / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
DOC = ROOT / "docs" / "m17-3c-android-offline-map-surface.md"


class M173CAndroidOfflineMapSurfaceTests(unittest.TestCase):
    def test_required_map_surface_artifacts_exist(self):
        for path in (MAP, APP, APP_BUILD, MANIFEST, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_projection_matches_bounded_m73_wgs84_contract(self):
        text = MAP.read_text(encoding="utf-8")
        for marker in (
            "MAP_WIDTH = 720",
            "MAP_HEIGHT = 360",
            "latitudeE6 in -90_000_000..90_000_000",
            "longitudeE6 in -180_000_000..180_000_000",
            "360_000_000L",
            "180_000_000L",
        ):
            self.assertIn(marker, text)
    def test_marker_extraction_is_bounded_and_profile_specific(self):
        text = MAP.read_text(encoding="utf-8")
        for marker in (
            "MAX_ANDROID_MAP_MARKERS = 64",
            "if (markers.size == MAX_ANDROID_MAP_MARKERS) break",
            "JSONObject(record.rawJson)",
            "MARKET_INTENT_TYPE",
            "PRODUCT_PROFILE",
            "hasReviewedProductProfile",
            "PRODUCT_ACTION",
            "LOCATION_TERM",
            "LOCATION_SCHEME",
            'value.opt("latitude_e6")',
            'value.opt("longitude_e6")',
            "exactJsonInt",
            "is Int",
            "is Long",
        ):
            self.assertIn(marker, text)

    def test_screen_renders_real_local_marker_surface_and_keeps_selection(self):
        app = APP.read_text(encoding="utf-8")
        map_text = MAP.read_text(encoding="utf-8")
        self.assertIn("MarketplaceMapSurface(", app)
        self.assertIn("records = uiState.rootRecords", app)
        self.assertIn("onSelectIntent = onSelectIntent", app)
        self.assertIn("remember(records) { extractAndroidMapMarkers(records) }", map_text)
        self.assertNotIn("Presentation-only map surface", app)
        for marker in ("Canvas(", "BoxWithConstraints(", "Map marker ${index + 1}", ".clickable { onSelectIntent(marker.recordId) }"):
            self.assertIn(marker, map_text)
    def test_map_surface_uses_box_scope_match_parent_size_without_invalid_import(self):
        text = MAP.read_text(encoding="utf-8")
        self.assertIn("Modifier.matchParentSize()", text)
        self.assertNotIn("import androidx.compose.foundation.layout.matchParentSize", text)
    def test_map_surface_adds_no_external_map_or_location_authority(self):
        map_text = MAP.read_text(encoding="utf-8").lower()
        build_text = APP_BUILD.read_text(encoding="utf-8").lower()
        manifest_text = MANIFEST.read_text(encoding="utf-8").lower()
        for forbidden in (
            "java.net", "httpurlconnection", "webview", "mapview", "googlemap",
            "mapbox", "osmdroid", "tileprovider", "fusedlocationprovider",
        ):
            self.assertNotIn(forbidden, map_text)
        self.assertEqual(build_text.count("implementation("), 5)
        self.assertNotIn("access_fine_location", manifest_text)
        self.assertNotIn("access_coarse_location", manifest_text)

    def test_empty_and_bounded_view_language_is_nonadverse(self):
        text = MAP.read_text(encoding="utf-8")
        self.assertIn("Offline deterministic coordinate view; issuer-attributed, not verified.", text)
        self.assertIn("No local listings in this bounded map view; this is not global nonexistence.", text)
        self.assertIn("local listing marker(s) in this bounded view", text)

    def test_document_keeps_build_runtime_and_server_mutation_out_of_scope(self):
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "M17.3C Android offline map surface",
            "source-only",
            "no Android build",
            "no Android runtime",
            "no server or PostgreSQL mutation",
            "no external map provider",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
