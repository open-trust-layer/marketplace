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
    / "fulfillment_completion_launch_v1.py"
)
TESTS = (
    ROOT
    / "tests"
    / "test_m17_7g_reference_fulfillment_completion_launch.py"
)
DOC = ROOT / "docs" / "m17-7g-reference-fulfillment-completion-launch.md"

NONSELECTING = (
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


class M177GReferenceFulfillmentCompletionLaunchArtifactTests(unittest.TestCase):
    def test_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_reviewed_composition_and_reference_boundaries(self) -> None:
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
                "olp.encoding.record_identity",
                "agreement_publication",
                "agreement_publication_write",
                "fulfillment_completion_launch",
                "fulfillment_completion_publication",
                "fulfillment_completion_startup_composition",
                "agreement_assent_postgres_v1",
                "agreement_candidate_v1",
                "fulfillment_completion_evidence_v1",
            },
        )

    def test_source_uses_only_reviewed_reference_evidence_builders(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "build_claimed_complete_performance_event",
            "build_commitment_acceptance_event",
            "build_commitment_completion_event",
            "fulfillment_event_target",
            "agreement_candidate_record_id",
            "record_identity_text",
        ):
            self.assertIn(marker, text)
        self.assertEqual(
            text.count("compose_marketplace_fulfillment_completion_startup("),
            1,
        )
        self.assertEqual(
            text.count(
                "build_marketplace_fulfillment_completion_loopback_launch_plan("
            ),
            1,
        )

    def test_existing_entry_points_do_not_select_g(self) -> None:
        marker = "fulfillment_completion_launch_v1"
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            self.assertNotIn(marker, path.read_text(encoding="utf-8"), str(path))

    def test_source_contains_no_external_io_or_execution_capability(self) -> None:
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
            ".initialize(",
            ".run(",
            ".serve(",
            ".sign(",
            "evaluate_commitment_fulfillment",
            "thread",
            "asyncio",
            "retry",
        ):
            self.assertNotIn(marker, text)

    def test_document_records_exact_reference_nonselection_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_REFERENCE_FULFILLMENT_COMPLETION_LAUNCH_V1",
            "MODERATE reference composition",
            "zero database initialization",
            "zero provider/server execution",
            "do not select M17.7G",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
