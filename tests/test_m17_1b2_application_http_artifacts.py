from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "http.py"
DOC = ROOT / "docs" / "m17-1b2-http-transport-binding.md"


class M17ApplicationHttpArtifactTests(unittest.TestCase):
    def test_http_adapter_source_has_no_runtime_transport_or_database_authority(self):
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        for forbidden in ("socket", "http", "urllib", "requests", "fastapi", "starlette", "uvicorn", "psycopg"):
            self.assertNotIn(forbidden, imported_roots)
        lowered = text.lower()
        for forbidden in ("bind(", "listen(", "accept(", "connect(", "serve_forever", "database_url", "dsn="):
            self.assertNotIn(forbidden, lowered)

    def test_application_package_exports_http_contract(self):
        from marketplace import application
        for name in (
            "ApplicationHttpRequest",
            "ApplicationHttpResponse",
            "MarketplaceApplicationHttpAdapter",
        ):
            self.assertTrue(hasattr(application, name), name)

    def test_http_binding_document_records_routes_and_exclusions(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "GET /api/intents",
            "POST /api/intents",
            "GET /api/intents/{id}",
            "POST /api/intents/{id}/responses",
            "GET /api/intents/{id}/responses",
            "GET /api/sync",
            "framework-neutral",
            "no live HTTP server",
            "no socket",
            "M17.1C Web",
            "M17.1D Android",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
