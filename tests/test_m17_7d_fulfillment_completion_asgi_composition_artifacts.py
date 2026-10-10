from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "fulfillment_completion_asgi_composition.py"
SESSION_ASGI = ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py"
TESTS = ROOT / "tests" / "test_m17_7d_fulfillment_completion_asgi_composition.py"
DOC = ROOT / "docs" / "m17-7d-fulfillment-completion-asgi-composition.md"
NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_runtime_server.py",
    ROOT / "src" / "marketplace" / "application" / "auth_launch.py",
    ROOT / "tools" / "marketplace_localhost.py",
    ROOT / "web" / "app.js",
)


class M177DFulfillmentCompletionAsgiCompositionArtifactTests(unittest.TestCase):
    def test_artifacts_exist(self) -> None:
        for path in (SOURCE, SESSION_ASGI, TESTS, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_composition_boundaries(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.add(node.module or "")
        self.assertEqual(
            modules,
            {
                "__future__",
                "dataclasses",
                "typing",
                "auth_http_composition",
                "auth_runtime_inputs",
                "auth_session_asgi",
                "fulfillment_completion_http_composition",
            },
        )

    def test_session_asgi_admits_exact_fulfillment_adapter(self) -> None:
        text = SESSION_ASGI.read_text(encoding="utf-8")
        marker = "MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter"
        self.assertIn(marker, text)
        self.assertIn(
            "marketplace_http MUST be an exact reviewed authenticated HTTP adapter",
            text,
        )

    def test_existing_entry_points_do_not_select_d(self) -> None:
        marker = "fulfillment_completion_asgi_composition"
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            self.assertNotIn(marker, path.read_text(encoding="utf-8"), str(path))

    def test_document_records_exact_inert_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_FULFILLMENT_COMPLETION_ASGI_COMPOSITION_V1",
            "MODERATE transport composition",
            "zero credential-material generation",
            "zero wall-clock reads",
            "zero request handling",
            "zero socket binding",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
