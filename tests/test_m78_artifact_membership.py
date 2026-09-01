from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "reference" / "local_ui_loopback_v1.py"
TOOL = ROOT / "tools" / "local_ui_loopback_acceptance.py"
DOC = ROOT / "docs" / "local-ui-loopback-transport.md"
REFERENCE_INIT = ROOT / "src" / "marketplace" / "reference" / "__init__.py"


class M78ArtifactMembershipTests(unittest.TestCase):
    def test_required_source_tests_tool_and_document_are_present(self):
        required = (
            SOURCE,
            TOOL,
            DOC,
            ROOT / "tests" / "test_m78_local_ui_loopback_transport.py",
            ROOT / "tests" / "test_m78_artifact_membership.py",
        )
        for path in required:
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_m78_keeps_zero_declared_runtime_dependencies(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)

    def test_packaged_transport_is_loopback_only_and_reuses_exact_m77_path(self):
        source = SOURCE.read_text(encoding="utf-8")
        for required in (
            'LOCAL_UI_LOOPBACK_HOST = "127.0.0.1"',
            'LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN = "EXECUTE_ONE_LOCAL_UI_LOOPBACK_SESSION"',
            "handle_local_ui_http_request",
            "LocalUiHttpRequest",
            "LocalUiHttpResponse",
            "listen(1)",
            "MAX_LOCAL_UI_LOOPBACK_READ_CALLS",
            "MAX_LOCAL_UI_LOOPBACK_WRITE_CALLS",
        ):
            self.assertIn(required, source)
        for forbidden in (
            "localhost",
            "0.0.0.0",
            "::",
            ".connect(",
            "getaddrinfo",
            "requests.",
            "urllib",
            "webbrowser",
            "subprocess",
            "threading",
            "asyncio",
            "inbound_federation",
            "inbound_http_execution_gate",
            "run_local_buy_sell_demo",
        ):
            self.assertNotIn(forbidden, source)

    def test_packaged_transport_does_not_choose_real_socket_provider(self):
        source = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        socket_from_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "socket":
                socket_from_names.update(alias.name for alias in node.names)
            if isinstance(node, ast.Import):
                self.assertNotIn("socket", {alias.name for alias in node.names})
        self.assertEqual(socket_from_names, {"AF_INET", "IPPROTO_TCP", "SOCK_STREAM"})
        self.assertNotIn("socket.socket", source)
        self.assertIn("socket_constructor(AF_INET, SOCK_STREAM, IPPROTO_TCP)", source)

    def test_manual_tool_selects_real_socket_only_after_exact_execute_opt_in(self):
        tool = TOOL.read_text(encoding="utf-8")
        tree = ast.parse(tool)
        top_level_socket_import = False
        provider_socket_import = False
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_level_socket_import |= any(alias.name == "socket" for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                top_level_socket_import |= node.module == "socket"
            if isinstance(node, ast.FunctionDef) and node.name == "_real_socket_constructor":
                provider_socket_import = any(
                    isinstance(child, ast.Import) and any(alias.name == "socket" for alias in child.names)
                    for child in ast.walk(node)
                )
        self.assertFalse(top_level_socket_import)
        self.assertTrue(provider_socket_import)
        self.assertIn("--dry-run", tool)
        self.assertIn("--execute-one-local-ui-loopback-session", tool)
        self.assertIn("LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN", tool)
        self.assertLess(
            tool.index("token != LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN"),
            tool.index("constructor = _real_socket_constructor()"),
        )
        for forbidden in ("webbrowser", "subprocess", "threading", "asyncio", "requests", "open("):
            self.assertNotIn(forbidden, tool)

    def test_result_and_errors_are_content_retention_negative(self):
        source = SOURCE.read_text(encoding="utf-8")
        result_start = source.index("class LocalUiLoopbackResult")
        result_end = source.index("\n\ndef _fail", result_start)
        result_source = source[result_start:result_end]
        for forbidden in ("request_bytes", "response_bytes", "body:", "transcript", "form_values", "description"):
            self.assertNotIn(forbidden, result_source)
        self.assertNotIn("raise exc", source)
        self.assertNotIn("str(exc)", source)

    def test_reference_exports_m78_without_application_or_runtime_dependency(self):
        reference_init = REFERENCE_INIT.read_text(encoding="utf-8")
        for name in (
            "LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN",
            "LOCAL_UI_LOOPBACK_HOST",
            "LocalUiLoopbackError",
            "LocalUiLoopbackPlan",
            "LocalUiLoopbackResult",
            "plan_local_ui_loopback_once",
            "serve_local_ui_loopback_once",
        ):
            self.assertIn(f'"{name}"', reference_init)
        for package in ("application", "runtime"):
            init_text = (ROOT / "src" / "marketplace" / package / "__init__.py").read_text(encoding="utf-8")
            self.assertNotIn("local_ui_loopback_v1", init_text)
            self.assertNotIn("serve_local_ui_loopback_once", init_text)


if __name__ == "__main__":
    unittest.main()
