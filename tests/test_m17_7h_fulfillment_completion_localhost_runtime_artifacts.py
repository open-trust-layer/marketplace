from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (
    ROOT
    / "src"
    / "marketplace"
    / "application"
    / "fulfillment_completion_runtime_server.py"
)
BOOTSTRAP = ROOT / "tools" / "marketplace_localhost.py"
RUNTIME_TESTS = ROOT / "tests" / "test_m17_7h_fulfillment_completion_runtime_server.py"
BOOTSTRAP_TESTS = (
    ROOT
    / "tests"
    / "test_m17_7h_fulfillment_completion_localhost_bootstrap.py"
)
DOC = ROOT / "docs" / "m17-7h-fulfillment-completion-localhost-runtime.md"
WEB = ROOT / "web" / "app.js"


class M177HFulfillmentCompletionLocalhostRuntimeArtifactTests(unittest.TestCase):
    def test_artifacts_exist(self) -> None:
        for path in (RUNTIME, BOOTSTRAP, RUNTIME_TESTS, BOOTSTRAP_TESTS, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_runtime_imports_only_reviewed_execution_boundaries(self) -> None:
        tree = ast.parse(RUNTIME.read_text(encoding="utf-8"))
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
                "typing",
                "auth_session_asgi",
                "fulfillment_completion_launch",
                "fulfillment_completion_startup_composition",
                "launch",
                "runtime_server",
            },
        )

    def test_runtime_is_loopback_exact_token_and_single_provider_delegate(self) -> None:
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("LOOPBACK_LAUNCH_HOST", text)
        self.assertIn(
            "EXECUTE_ONE_FULFILLMENT_COMPLETION_MARKETPLACE_LOOPBACK_SERVER",
            text,
        )
        self.assertEqual(text.count("run(application=plan.asgi, host=plan.host, port=plan.port)"), 1)
        self.assertNotIn("UvicornLoopbackServerProvider", text)

    def test_bootstrap_exposes_separate_preflight_and_exact_live_opt_in(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        for marker in (
            "--preflight-fulfillment-completion-localhost",
            "--execute-fulfillment-completion-localhost",
            "EXECUTE_FULFILLMENT_COMPLETION_AUTHENTICATED_MARKETPLACE_LOCALHOST_V1",
            "_wrap_marketplace_provider_with_moon_heartbeat",
            "_initialize_agreement_assent_coordination",
            "_run_fulfillment_completion_foreground",
        ):
            self.assertIn(marker, text)

    def test_web_surface_remains_unselected(self) -> None:
        text = WEB.read_text(encoding="utf-8")
        self.assertNotIn("completion-evidence", text)
        self.assertNotIn("fulfillment_completion", text)

    def test_document_records_high_loopback_only_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "HIGH local runtime execution",
            "127.0.0.1",
            "zero PostgreSQL connection calls",
            "new exact",
            "mode-specific opt-in",
            "does not establish",
            "universal completion",
            "does **not** add or activate a Web completion button",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
