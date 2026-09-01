from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SOURCE = ROOT / "src" / "marketplace" / "reference" / "local_demo_v1.py"
REFERENCE_INIT = ROOT / "src" / "marketplace" / "reference" / "__init__.py"
DOC = ROOT / "docs" / "local-buy-sell-demo.md"


class M74ArtifactMembershipTests(unittest.TestCase):
    def test_required_source_tests_and_document_are_present(self):
        required = (
            REFERENCE_SOURCE,
            DOC,
            ROOT / "tests" / "test_m74_local_buy_sell_demo.py",
            ROOT / "tests" / "test_m74_artifact_membership.py",
        )
        for path in required:
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_m74_keeps_zero_declared_runtime_dependencies(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)

    def test_demo_composition_adds_no_external_io_background_or_browser_surface(self):
        source = REFERENCE_SOURCE.read_text(encoding="utf-8")
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
        for token in ("socket.", "bind(", "listen(", "connect(", "open(", "requests."):
            self.assertNotIn(token, source)

    def test_demo_reuses_reviewed_m71_through_m73_surfaces(self):
        source = REFERENCE_SOURCE.read_text(encoding="utf-8")
        for required in (
            "LocalMarketplaceApplication",
            "create_in_memory_runtime",
            "build_product_listing_record",
            "extract_product_listing",
            "evaluate_discovery",
            "evaluate_match",
            "render_product_listing_record_page",
        ):
            self.assertIn(required, source)
        self.assertIn("with runtime:", source)
        self.assertIn('base_status="SATISFIED"', source)
        self.assertIn('evidence_completeness="COMPLETE_FOR_METHOD_INPUTS"', source)

    def test_reference_public_surface_exports_demo_without_application_layer_olp_import(self):
        reference_init = REFERENCE_INIT.read_text(encoding="utf-8")
        for name in (
            "LocalBuySellDemoError",
            "LocalBuySellDemoResult",
            "run_local_buy_sell_demo",
        ):
            self.assertIn(f'"{name}"', reference_init)
        application_init = (
            ROOT / "src" / "marketplace" / "application" / "__init__.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("local_demo_v1", application_init)


if __name__ == "__main__":
    unittest.main()
