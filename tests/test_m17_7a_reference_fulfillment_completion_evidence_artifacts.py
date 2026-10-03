from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src"
    / "marketplace"
    / "reference"
    / "fulfillment_completion_evidence_v1.py"
)
TESTS = (
    ROOT
    / "tests"
    / "test_m17_7a_reference_fulfillment_completion_evidence.py"
)
ARTIFACTS = (
    ROOT
    / "tests"
    / "test_m17_7a_reference_fulfillment_completion_evidence_artifacts.py"
)
DOC = ROOT / "docs" / "m17-7a-reference-fulfillment-completion-evidence.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "http.py",
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


class M177AReferenceFulfillmentCompletionEvidenceArtifactTests(unittest.TestCase):
    def test_exact_m17_7a_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_olp_and_existing_reference_record_contract(self) -> None:
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
                "collections.abc",
                "re",
                "typing",
                "olp",
                "olp.encoding.record_identity",
                "olp.evidence",
                "olp.model.evidence",
                "olp.transport",
                "olp.values",
                "record_v1",
            },
        )

    def test_source_builds_only_three_exact_fulfillment_event_identifiers(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(text.count('f"{BASE}/event/commitment-performance"'), 1)
        self.assertEqual(text.count('f"{BASE}/event/commitment-acceptance"'), 1)
        self.assertEqual(
            text.count('f"{BASE}/event/commitment-completion-assertion"'),
            1,
        )
        self.assertEqual(
            text.count('f"{BASE}/outcome/performance-claimed-complete"'),
            1,
        )
        for marker in (
            "build_claimed_complete_performance_event",
            "build_commitment_acceptance_event",
            "build_commitment_completion_event",
            "fulfillment_event_target",
        ):
            self.assertIn(marker, text)

    def test_source_has_no_publication_signing_io_runtime_or_evaluation(self) -> None:
        text = SOURCE.read_text(encoding="utf-8").lower()
        for marker in (
            ".publish(",
            ".put(",
            "postgres",
            "sqlite",
            "open(",
            "path(",
            "os.environ",
            "getenv(",
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urlopen",
            "privatekey",
            "private_key",
            ".sign(",
            "create_proof",
            "evaluate_commitment_fulfillment",
            "uvicorn",
            "settimeout",
            "setinterval",
            "thread",
            "asyncio",
            "sleep(",
            "retry",
            "payment",
            "settlement",
        ):
            self.assertNotIn(marker, text)

    def test_existing_application_demo_web_and_android_do_not_select_a(self) -> None:
        module = "fulfillment_completion_evidence_v1"
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            self.assertNotIn(module, path.read_text(encoding="utf-8"), str(path))

    def test_package_controls_require_a_reference_module(self) -> None:
        member = "marketplace/reference/fulfillment_completion_evidence_v1.py"
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_attributable_nontruth_and_source_only_boundary(
        self,
    ) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_REFERENCE_FULFILLMENT_COMPLETION_EVIDENCE_V1",
            "MODERATE semantic",
            "attributable evidence",
            "does not establish objective performance",
            "does not establish universal completion",
            "does not run evaluate_commitment_fulfillment",
            "unselected",
            "no publication",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
