from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SOURCE = ROOT / "src" / "marketplace" / "reference" / "local_console_v1.py"
REFERENCE_INIT = ROOT / "src" / "marketplace" / "reference" / "__init__.py"
DOC = ROOT / "docs" / "local-console-buy-sell-interaction.md"


class M75ArtifactMembershipTests(unittest.TestCase):
    def test_required_source_tests_and_document_are_present(self):
        required = (
            REFERENCE_SOURCE,
            DOC,
            ROOT / "tests" / "test_m75_local_console_interaction.py",
            ROOT / "tests" / "test_m75_artifact_membership.py",
        )
        for path in required:
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_m75_keeps_zero_declared_runtime_dependencies(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)

    def test_console_adapter_adds_no_network_browser_process_thread_or_persistence_surface(self):
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
        for token in (
            "socket.",
            "bind(",
            "listen(",
            "connect(",
            "open(",
            "requests.",
            "input(",
            "print(",
        ):
            self.assertNotIn(token, source)

    def test_console_adapter_reuses_m72_and_m74_without_alternate_semantic_path(self):
        source = REFERENCE_SOURCE.read_text(encoding="utf-8")
        for required in (
            "ExactDecimal",
            "ProductListingDraft",
            "run_local_buy_sell_demo",
            "LocalBuySellDemoResult",
        ):
            self.assertIn(required, source)
        self.assertNotIn("seller_listing_html", source)
        self.assertNotIn("transcript", source.lower())

    def test_reference_exports_console_adapter_without_application_layer_console_dependency(self):
        reference_init = REFERENCE_INIT.read_text(encoding="utf-8")
        for name in (
            "LocalConsoleInteractionError",
            "run_local_buy_sell_console",
        ):
            self.assertIn(f'"{name}"', reference_init)
        application_init = (
            ROOT / "src" / "marketplace" / "application" / "__init__.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("local_console_v1", application_init)
        self.assertNotIn("run_local_buy_sell_console", application_init)


if __name__ == "__main__":
    unittest.main()
