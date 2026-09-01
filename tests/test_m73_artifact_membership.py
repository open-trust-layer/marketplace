from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "src" / "marketplace" / "application" / "web_map.py"
REFERENCE_SOURCE = ROOT / "src" / "marketplace" / "reference" / "web_map_v1.py"
DOC = ROOT / "docs" / "local-offline-web-map-projection.md"


class M73ArtifactMembershipTests(unittest.TestCase):
    def test_required_sources_tests_and_document_are_present(self):
        required = (
            APP_SOURCE,
            REFERENCE_SOURCE,
            DOC,
            ROOT / "tests" / "test_m73_offline_web_map.py",
            ROOT / "tests" / "test_m73_offline_web_map_integration.py",
        )
        for path in required:
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_m73_keeps_zero_declared_runtime_dependencies(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)

    def test_application_projection_has_no_external_io_or_browser_surface(self):
        source = APP_SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_roots = {
            "asyncio",
            "concurrent",
            "http",
            "os",
            "pathlib",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "threading",
            "urllib",
            "webbrowser",
        }
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertTrue(imported.isdisjoint(forbidden_roots))
        for forbidden in ("<script", "<iframe", "<link", "<img", " src=", " href="):
            self.assertNotIn(forbidden, source.lower())

    def test_public_application_surface_exports_offline_projection(self):
        source = (ROOT / "src" / "marketplace" / "application" / "__init__.py").read_text(encoding="utf-8")
        for name in (
            "DEFAULT_OFFLINE_MAP_FIXTURE",
            "MAX_RENDERED_LISTINGS",
            "OfflineMapFixture",
            "project_wgs84_e6",
            "render_product_listing_page",
        ):
            self.assertIn(f'"{name}"', source)

    def test_reference_bridge_adds_no_network_server_or_browser_surface(self):
        source = REFERENCE_SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden = ("socket", "urllib", "http", "requests", "webbrowser", "subprocess", "selenium")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name.split(".", 1)[0], forbidden)
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".", 1)[0], forbidden)


if __name__ == "__main__":
    unittest.main()
