from __future__ import annotations

import ast
import contextlib
import io
import pathlib
import unittest
from unittest.mock import Mock, patch

from olp.encoding.record_identity import record_identity_text

import tools.inbound_http_loopback_acceptance as tool
from marketplace.runtime.inbound_http_execution_gate import LOOPBACK_EXECUTION_OPT_IN
from test_inbound_http_connection import _Connection
from test_inbound_http_single_session import _Constructor, _Listener

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/inbound_http_loopback_acceptance.py"


class InboundHttpLoopbackAcceptanceToolTests(unittest.TestCase):
    def test_help_is_inert_and_describes_external_effect_boundary(self):
        output = io.StringIO()
        with patch.object(tool, "_real_socket_constructor") as socket_provider:
            with contextlib.redirect_stdout(output):
                with self.assertRaises(SystemExit) as caught:
                    tool.main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        socket_provider.assert_not_called()
        self.assertIn("NETWORK_EXTERNAL", output.getvalue())

    def test_dry_run_never_selects_real_socket_constructor(self):
        stdout = io.StringIO()
        with patch.object(tool, "_real_socket_constructor") as socket_provider:
            with contextlib.redirect_stdout(stdout):
                code = tool.main(["--port", "18080", "--dry-run"])
        self.assertEqual(code, 0)
        socket_provider.assert_not_called()
        self.assertEqual(stdout.getvalue().strip(), "M62_DRY_RUN_READY")

    def test_invalid_port_fails_before_root_or_socket_selection(self):
        stderr = io.StringIO()
        with patch.object(tool, "build_source_root") as build_root:
            with patch.object(tool, "_real_socket_constructor") as socket_provider:
                with contextlib.redirect_stderr(stderr):
                    code = tool.main(["--port", "80", "--dry-run"])
        self.assertEqual(code, 2)
        build_root.assert_not_called()
        socket_provider.assert_not_called()
        self.assertEqual(stderr.getvalue().strip(), "M62_PORT_INVALID")

    def test_bad_execution_token_fails_before_socket_selection(self):
        stderr = io.StringIO()
        with patch.object(tool, "_real_socket_constructor") as socket_provider:
            with contextlib.redirect_stderr(stderr):
                code = tool.main([
                    "--port", "18080",
                    "--execute-one-loopback-network-session", "execute",
                ])
        self.assertEqual(code, 2)
        socket_provider.assert_not_called()
        self.assertEqual(stderr.getvalue().strip(), "LOOPBACK_EXECUTION_OPT_IN_REQUIRED")

    def test_execute_path_runs_exactly_one_injected_session(self):
        sample = tool._sample_record()
        identity = record_identity_text(sample)
        connection = _Connection()
        connection.input_bytes = (
            f"GET /v1/records/{identity} HTTP/1.1\r\n"
            f"Host: {tool.AUTHORITY}\r\n"
            "Accept: application/json\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        listener = _Listener(connection)
        constructor = _Constructor(listener)
        stdout = io.StringIO()
        with patch.object(tool, "_real_socket_constructor", return_value=constructor) as provider:
            with contextlib.redirect_stdout(stdout):
                code = tool.main([
                    "--port", "18080",
                    "--execute-one-loopback-network-session", LOOPBACK_EXECUTION_OPT_IN,
                ])
        self.assertEqual(code, 0)
        provider.assert_called_once_with()
        self.assertEqual(len(constructor.calls), 1)
        self.assertEqual(listener.bind_calls, [("127.0.0.1", 18080)])
        self.assertEqual(listener.listen_calls, [1])
        self.assertEqual(listener.accept_calls, 1)
        self.assertEqual(connection.close_calls, 1)
        self.assertEqual(stdout.getvalue().strip(), "M62_ONE_SHOT_LOOPBACK_SESSION_COMPLETE")

    def test_execute_output_never_reflects_request_or_record_identity(self):
        stderr = io.StringIO()
        with patch.object(tool, "_real_socket_constructor", side_effect=RuntimeError("SECRET-SOCKET-TEXT")):
            with contextlib.redirect_stderr(stderr):
                code = tool.main([
                    "--port", "18080",
                    "--execute-one-loopback-network-session", LOOPBACK_EXECUTION_OPT_IN,
                ])
        self.assertEqual(code, 1)
        text = stderr.getvalue()
        self.assertNotIn("SECRET-SOCKET-TEXT", text)
        self.assertNotIn(record_identity_text(tool._sample_record()), text)


class InboundHttpLoopbackAcceptanceToolSourceTests(unittest.TestCase):
    def test_socket_import_exists_only_inside_explicit_provider(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        socket_imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                if any(name.split(".")[0] == "socket" for name in names):
                    socket_imports.append(node)
        self.assertEqual(len(socket_imports), 1)
        provider = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_real_socket_constructor"
        )
        self.assertIn(socket_imports[0], list(ast.walk(provider)))

    def test_tool_has_no_background_process_or_retry_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        blocked = {"asyncio", "threading", "multiprocessing", "subprocess", "concurrent", "logging"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name.split(".")[0] not in blocked for alias in node.names))
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], blocked)
            self.assertNotIsInstance(node, (ast.For, ast.While, ast.AsyncFor))


if __name__ == "__main__":
    unittest.main()
