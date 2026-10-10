from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src"
    / "marketplace"
    / "application"
    / "fulfillment_completion_startup_composition.py"
)
TESTS = (
    ROOT
    / "tests"
    / "test_m17_7e_fulfillment_completion_startup_composition.py"
)
DOC = ROOT / "docs" / "m17-7e-fulfillment-completion-startup-composition.md"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_runtime_server.py",
    ROOT / "src" / "marketplace" / "application" / "agreement_assent_launch.py",
    ROOT / "tools" / "marketplace_localhost.py",
    ROOT / "web" / "app.js",
    ROOT
    / "android"
    / "app"
    / "src"
    / "main"
    / "java"
    / "org"
    / "opentrustlayer"
    / "marketplace"
    / "MainActivity.kt",
)


class M177EFulfillmentCompletionStartupCompositionArtifactTests(unittest.TestCase):
    def test_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_reviewed_composition_boundaries(self) -> None:
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
                "agreement_assent_startup_composition",
                "agreement_publication",
                "agreement_publication_http_composition",
                "agreement_publication_write",
                "auth_runtime_inputs",
                "fulfillment_completion_asgi_composition",
                "fulfillment_completion_http_composition",
                "fulfillment_completion_publication",
            },
        )

    def test_source_selects_only_nested_reviewed_compositions(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(
            text.count("compose_marketplace_agreement_publication_http("),
            1,
        )
        self.assertEqual(
            text.count("compose_marketplace_fulfillment_completion_http("),
            1,
        )
        self.assertEqual(
            text.count("compose_marketplace_fulfillment_completion_asgi("),
            1,
        )
        self.assertNotIn("MarketplaceSessionEstablishmentAsgiHttpAdapter(", text)
        self.assertNotIn("initialize(", text)
        self.assertNotIn(".publish(", text)

    def test_existing_entry_points_do_not_select_e(self) -> None:
        marker = "fulfillment_completion_startup_composition"
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            self.assertNotIn(marker, path.read_text(encoding="utf-8"), str(path))

    def test_source_contains_no_runtime_provider_or_external_io_capability(self) -> None:
        text = SOURCE.read_text(encoding="utf-8").lower()
        for marker in (
            "uvicorn",
            "socket",
            "requests",
            "httpx",
            "urlopen",
            "psycopg",
            "sqlite",
            "open(",
            "getenv",
            "environ",
            "private_key",
            ".sign(",
            "evaluate_commitment_fulfillment",
            "thread",
            "asyncio",
            "retry",
        ):
            self.assertNotIn(marker, text)

    def test_document_records_exact_inert_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_FULFILLMENT_COMPLETION_STARTUP_COMPOSITION_V1",
            "MODERATE startup composition",
            "zero request handling",
            "zero application-state initialization",
            "zero socket binding",
            "do not select this startup overlay",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
