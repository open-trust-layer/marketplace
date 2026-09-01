from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SOURCE = ROOT / "src" / "marketplace" / "reference" / "local_visual_v1.py"
REFERENCE_INIT = ROOT / "src" / "marketplace" / "reference" / "__init__.py"
DOC = ROOT / "docs" / "local-visual-buy-sell-contract.md"


class M76ArtifactMembershipTests(unittest.TestCase):
    def test_required_source_tests_and_document_are_present(self):
        required = (
            REFERENCE_SOURCE,
            DOC,
            ROOT / "tests" / "test_m76_local_visual_interaction.py",
            ROOT / "tests" / "test_m76_artifact_membership.py",
        )
        for path in required:
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_m76_keeps_zero_declared_runtime_dependencies(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)

    def test_visual_adapter_adds_no_network_browser_process_thread_or_persistence_surface(self):
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
            "accept(",
            "connect(",
            "requests.",
            "webbrowser.",
            "input(",
            "print(",
            "open(",
        ):
            self.assertNotIn(token, source)

    def test_visual_adapter_reuses_m75_without_alternate_human_or_marketplace_path(self):
        source = REFERENCE_SOURCE.read_text(encoding="utf-8")
        self.assertIn("run_local_buy_sell_console", source)
        self.assertIn("LocalConsoleInteractionError", source)
        for forbidden in (
            "run_local_buy_sell_demo",
            "ProductListingDraft",
            "ExactDecimal",
            "re.compile",
            "_parse_exact_decimal",
            "_parse_wgs84_e6",
        ):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("transcript", source.lower())

    def test_visual_html_contract_is_inert_and_local_only(self):
        source = REFERENCE_SOURCE.read_text(encoding="utf-8").lower()
        for forbidden in (
            "<script",
            "<iframe",
            "http://",
            "https://",
            "javascript:",
            "target=",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('action="{_form_action}"', source)
        self.assertIn('_form_action = "/local-buy-sell"', source)

    def test_reference_exports_visual_contract_without_application_or_runtime_dependency(self):
        reference_init = REFERENCE_INIT.read_text(encoding="utf-8")
        for name in (
            "LocalVisualInteractionError",
            "LocalVisualSubmission",
            "render_local_buy_sell_form",
            "submit_local_buy_sell_form",
        ):
            self.assertIn(f'"{name}"', reference_init)
        for package in ("application", "runtime"):
            init_text = (
                ROOT / "src" / "marketplace" / package / "__init__.py"
            ).read_text(encoding="utf-8")
            self.assertNotIn("local_visual_v1", init_text)
            self.assertNotIn("submit_local_buy_sell_form", init_text)


if __name__ == "__main__":
    unittest.main()
