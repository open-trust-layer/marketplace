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
    / "fulfillment_completion_launch.py"
)
TESTS = (
    ROOT
    / "tests"
    / "test_m17_7f_fulfillment_completion_loopback_launch.py"
)
DOC = ROOT / "docs" / "m17-7f-fulfillment-completion-loopback-launch.md"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_runtime_server.py",
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


class M177FFulfillmentCompletionLoopbackLaunchArtifactTests(unittest.TestCase):
    def test_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_launch_metadata_boundaries(self) -> None:
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
                "auth_session_asgi",
                "fulfillment_completion_startup_composition",
                "launch",
            },
        )

    def test_source_reuses_exact_loopback_policy_without_execution(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("LOOPBACK_LAUNCH_HOST", text)
        self.assertIn("MIN_LAUNCH_PORT", text)
        self.assertIn("MAX_LAUNCH_PORT", text)
        self.assertNotIn("uvicorn", text.lower())
        self.assertNotIn("socket", text.lower())
        self.assertNotIn("run(", text)
        self.assertNotIn("serve(", text)

    def test_existing_entry_points_do_not_select_f(self) -> None:
        marker = "fulfillment_completion_launch"
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            self.assertNotIn(marker, path.read_text(encoding="utf-8"), str(path))

    def test_document_records_exact_inert_launch_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_FULFILLMENT_COMPLETION_LOOPBACK_LAUNCH_PLAN_V1",
            "MODERATE launch metadata",
            "zero socket creation or binding",
            "zero provider/server execution",
            "do not select this launch plan",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
