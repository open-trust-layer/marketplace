from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTTP_SOURCE = (
    ROOT
    / "src"
    / "marketplace"
    / "application"
    / "fulfillment_completion_http.py"
)
COMPOSITION_SOURCE = (
    ROOT
    / "src"
    / "marketplace"
    / "application"
    / "fulfillment_completion_http_composition.py"
)
HTTP_TESTS = (
    ROOT
    / "tests"
    / "test_m17_7c_authenticated_fulfillment_completion_http.py"
)
COMPOSITION_TESTS = (
    ROOT
    / "tests"
    / "test_m17_7c_fulfillment_completion_http_composition.py"
)
DOC = ROOT / "docs" / "m17-7c-authenticated-fulfillment-completion-http.md"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "http.py",
    ROOT / "tools" / "marketplace_localhost.py",
    ROOT / "tools" / "marketplace_mvp_flight_acceptance.py",
    ROOT / "web" / "app.js",
    ROOT / "web" / "auth_bootstrap.js",
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


class M177CAuthenticatedFulfillmentCompletionHttpArtifactTests(unittest.TestCase):
    def test_exact_m17_7c_artifacts_exist(self) -> None:
        for path in (
            HTTP_SOURCE,
            COMPOSITION_SOURCE,
            HTTP_TESTS,
            COMPOSITION_TESTS,
            DOC,
        ):
            self.assertTrue(path.is_file(), str(path))

    def test_http_source_uses_only_existing_application_boundaries(self) -> None:
        tree = ast.parse(HTTP_SOURCE.read_text(encoding="utf-8"))
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
                "re",
                "typing",
                "agreement_publication_http",
                "auth",
                "auth_http",
                "fulfillment_completion_publication",
                "http",
                "postgres_state",
            },
        )

    def test_route_derives_issuer_only_from_authenticated_session(self) -> None:
        text = HTTP_SOURCE.read_text(encoding="utf-8")
        self.assertIn("issuer=session.principal", text)
        self.assertEqual(text.count("issuer=session.principal"), 3)
        self.assertIn('_REQUEST_FIELDS = frozenset({"evidence_kind"})', text)
        self.assertNotIn('document["issuer"]', text)
        self.assertNotIn('document.get("issuer")', text)

    def test_route_calls_only_reviewed_m17_7b_publication_methods(self) -> None:
        text = HTTP_SOURCE.read_text(encoding="utf-8")
        self.assertEqual(text.count("publish_claimed_complete_performance("), 1)
        self.assertEqual(text.count("publish_commitment_acceptance("), 1)
        self.assertEqual(text.count("publish_commitment_completion("), 1)
        self.assertIn("result.agreement_record_id != agreement_record_id", text)
        self.assertIn("result.commitment_id != commitment_id", text)
        self.assertIn("result.evidence_kind != evidence_kind", text)

    def test_existing_runtime_clients_and_demo_do_not_select_c(self) -> None:
        marker = "fulfillment_completion_http"
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            self.assertNotIn(marker, path.read_text(encoding="utf-8"), str(path))

    def test_http_source_contains_no_runtime_provider_or_crypto_capability(self) -> None:
        text = HTTP_SOURCE.read_text(encoding="utf-8").lower()
        for marker in (
            "uvicorn",
            "socket",
            "requests",
            "httpx",
            "urlopen",
            "psycopg",
            "sqlite",
            "private_key",
            "privatekey",
            ".sign(",
            "create_proof",
            "evaluate_commitment_fulfillment",
            "localstorage",
            "indexeddb",
            "settimeout",
            "setinterval",
            "thread",
            "asyncio",
            "retry",
        ):
            self.assertNotIn(marker, text)

    def test_document_freezes_route_authority_and_nonselection_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_AUTHENTICATED_FULFILLMENT_COMPLETION_HTTP_V1",
            "MODERATE application-state write",
            "/api/agreements/{agreement_record_id}/commitments/{commitment_id}/completion-evidence",
            "issuer only from the validated session principal",
            "exactly one reviewed M17.7B publication method",
            "unselected",
            "does not change the deterministic MVP flight",
            "Revert the exact M17.7C merge",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
