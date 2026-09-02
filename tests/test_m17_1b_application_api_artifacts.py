from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "api.py"
DOC = ROOT / "docs" / "m17-1b-application-api-contract.md"


class M17ApplicationApiArtifactTests(unittest.TestCase):
    def test_application_api_source_is_transport_and_database_inert(self):
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        for forbidden in (
            "fastapi",
            "starlette",
            "socket",
            "http",
            "urllib",
            "requests",
            "psycopg",
        ):
            self.assertNotIn(forbidden, imported_roots)
        lowered = text.lower()
        for forbidden in (
            "uvicorn",
            "bind(",
            "listen(",
            "accept(",
            "connect(",
            "database_url",
            "dsn=",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_application_public_surface_exports_api_contract(self):
        from marketplace import application

        for name in (
            "ApplicationApiError",
            "IntentIndexPage",
            "IntentQueryPort",
            "MarketplaceApplicationApiService",
        ):
            self.assertTrue(hasattr(application, name), name)

    def test_product_api_contract_document_is_required(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "GET /api/intents",
            "POST /api/intents",
            "GET /api/intents/{id}",
            "POST /api/intents/{id}/responses",
            "GET /api/intents/{id}/responses",
            "GET /api/sync",
            "transport-independent",
            "IntentQueryPort",
            "response_to",
            "not protocol truth",
            "no HTTP server",
            "no live database",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
