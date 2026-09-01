from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "reference" / "local_ui_http_v1.py"
REFERENCE_INIT = ROOT / "src" / "marketplace" / "reference" / "__init__.py"
DOC = ROOT / "docs" / "local-ui-http-application-adapter.md"


class M77ArtifactMembershipTests(unittest.TestCase):
    def test_required_source_tests_and_document_are_present(self):
        required = (
            SOURCE,
            DOC,
            ROOT / "tests" / "test_m77_local_ui_http_adapter.py",
            ROOT / "tests" / "test_m77_artifact_membership.py",
        )
        for path in required:
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_m77_keeps_zero_declared_runtime_dependencies(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)

    def test_http_adapter_adds_no_network_browser_process_thread_or_persistence_surface(self):
        source = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_roots = {
            "asyncio",
            "concurrent",
            "http",
            "os",
            "pathlib",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "threading",
            "urllib",
            "webbrowser",
        }
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertTrue(imported.isdisjoint(forbidden_roots))
        for token in (
            "socket.",
            "bind(",
            "listen(",
            "accept(",
            "connect(",
            ".recv(",
            ".send(",
            "requests.",
            "webbrowser.",
            "input(",
            "print(",
            "open(",
            "subprocess",
        ):
            self.assertNotIn(token, source)

    def test_http_adapter_reuses_m76_without_federation_or_alternate_marketplace_path(self):
        source = SOURCE.read_text(encoding="utf-8")
        for required in (
            "LocalVisualSubmission",
            "render_local_buy_sell_form",
            "submit_local_buy_sell_form",
            "LocalVisualInteractionError",
        ):
            self.assertIn(required, source)
        for forbidden in (
            "run_local_buy_sell_console",
            "run_local_buy_sell_demo",
            "ProductListingDraft",
            "ExactDecimal",
            "inbound_http",
            "LOOPBACK_EXECUTION_OPT_IN",
        ):
            self.assertNotIn(forbidden, source)

    def test_http_surface_is_exact_bounded_and_retention_negative(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('MAX_LOCAL_UI_HTTP_BODY_BYTES = 49_152', source)
        self.assertIn('request.target == "/"', source)
        self.assertIn('request.target == "/local-buy-sell"', source)
        self.assertIn('request.method != "GET"', source)
        self.assertIn('request.method != "POST"', source)
        self.assertIn('"Cache-Control", "no-store"', source)
        self.assertIn('"Content-Security-Policy", _CSP', source)
        for forbidden in ("Set-Cookie", "Access-Control-Allow-Origin", "transcript", "session_id"):
            self.assertNotIn(forbidden, source)

    def test_reference_exports_http_adapter_without_application_or_runtime_dependency(self):
        reference_init = REFERENCE_INIT.read_text(encoding="utf-8")
        for name in (
            "MAX_LOCAL_UI_HTTP_BODY_BYTES",
            "LocalUiHttpError",
            "LocalUiHttpRequest",
            "LocalUiHttpResponse",
            "handle_local_ui_http_request",
        ):
            self.assertIn(f'"{name}"', reference_init)
        for package in ("application", "runtime"):
            init_text = (ROOT / "src" / "marketplace" / package / "__init__.py").read_text(encoding="utf-8")
            self.assertNotIn("local_ui_http_v1", init_text)
            self.assertNotIn("handle_local_ui_http_request", init_text)


if __name__ == "__main__":
    unittest.main()
