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
    / "fulfillment_completion_publication.py"
)
TESTS = ROOT / "tests" / "test_m17_7b_fulfillment_completion_publication.py"
ARTIFACTS = (
    ROOT
    / "tests"
    / "test_m17_7b_fulfillment_completion_publication_artifacts.py"
)
DOC = ROOT / "docs" / "m17-7b-fulfillment-completion-publication.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

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


class M177BFulfillmentCompletionPublicationArtifactTests(unittest.TestCase):
    def test_exact_m17_7b_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_application_state_contracts(self) -> None:
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
                "re",
                "typing",
                "postgres_state",
                "state",
            },
        )

    def test_source_has_one_state_read_and_one_state_write_site(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(text.count("self._state.peek("), 1)
        self.assertEqual(text.count("self._state.publish("), 1)
        self.assertIn("target_agreement_id != agreement_id", text)
        self.assertIn(
            "target_commitment_id != reviewed_commitment_id",
            text,
        )
        self.assertIn("type(put) is not ApplicationStatePutResult", text)

    def test_source_does_not_import_reference_auth_http_runtime_or_evaluator(self) -> None:
        text = SOURCE.read_text(encoding="utf-8").lower()
        for marker in (
            "marketplace.reference",
            "fulfillment_completion_evidence_v1",
            "http",
            "asgi",
            "uvicorn",
            "socket",
            "requests",
            "httpx",
            "urlopen",
            "postgresql",
            "psycopg",
            "sqlite",
            "private_key",
            "privatekey",
            ".sign(",
            "create_proof",
            "evaluate_commitment_fulfillment",
            "authorizationfor",
            "bearer ",
            "localstorage",
            "indexeddb",
            "settimeout",
            "setinterval",
            "thread",
            "asyncio",
            "retry",
        ):
            self.assertNotIn(marker, text)

    def test_existing_transports_clients_runtime_and_demo_do_not_select_b(self) -> None:
        marker = "fulfillment_completion_publication"
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            self.assertNotIn(marker, path.read_text(encoding="utf-8"), str(path))

    def test_package_controls_require_b_application_module(self) -> None:
        member = "marketplace/application/fulfillment_completion_publication.py"
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_publication_and_nonselection_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_FULFILLMENT_COMPLETION_PUBLICATION_V1",
            "MODERATE application-state write capability",
            "exactly one application-state publication",
            "does not authenticate callers",
            "does not decide issuer authority",
            "unselected",
            "no HTTP endpoint",
            "no Web control",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
