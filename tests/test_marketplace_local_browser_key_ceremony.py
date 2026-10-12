"""Inert local browser-key ceremony tests; never bind any listener."""
from __future__ import annotations

import ast
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest

from tools.marketplace_local_browser_key_ceremony import (
    BrowserKeyCeremonyError,
    CSP,
    EXECUTION_OPT_IN,
    HOST,
    REPO_ROOT,
    WEB_FILES,
    load_static_assets,
    main,
    make_handler,
    serve_browser_key_ceremony,
)


def inspect_request(handler_type, path: str, method: str):
    handler = object.__new__(handler_type)
    handler.path = path
    handler.wfile = BytesIO()
    status: list[int] = []
    headers: dict[str, str] = {}
    handler.send_response = lambda code: status.append(code)
    handler.send_header = lambda key, value: headers.__setitem__(key.lower(), value)
    handler.end_headers = lambda: None
    getattr(handler, method)()
    return status[0], headers, handler.wfile.getvalue()


class LocalBrowserKeyCeremonyTests(unittest.TestCase):
    def test_asset_allowlist_matches_reviewed_authenticated_bootstrap(self):
        module = ast.parse((REPO_ROOT / "tools/marketplace_localhost.py").read_text(encoding="utf-8"))
        auth_map = None
        for node in module.body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id == "_AUTH_WEB_MODULE_ASSETS":
                    auth_map = ast.literal_eval(node.value)
        self.assertIsNotNone(auth_map)
        expected = {"index.html", "app.js", "styles.css"}
        expected.update(name.removeprefix("web/") for _, name in auth_map)
        self.assertEqual(set(WEB_FILES), expected)
        self.assertEqual(len(WEB_FILES), len(expected))

    def test_exact_source_bytes_and_nonempty_bounded_preflight(self):
        assets = load_static_assets()
        self.assertEqual(set(assets), {"/", *("/" + name for name in WEB_FILES)})
        self.assertIs(assets["/"], assets["/index.html"])
        for name in WEB_FILES:
            self.assertEqual(assets["/" + name].content, (REPO_ROOT / "web" / name).read_bytes())
            self.assertGreater(len(assets["/" + name].content), 0)
        self.assertEqual(assets["/index.html"].content_type, "text/html; charset=utf-8")
        self.assertEqual(assets["/styles.css"].content_type, "text/css; charset=utf-8")
        self.assertEqual(assets["/app.js"].content_type, "text/javascript; charset=utf-8")

    def test_get_head_and_failure_paths_are_bounded(self):
        assets = load_static_assets()
        handler = make_handler(assets)
        for path in ("/", "/index.html", "/app.js", "/auth_bootstrap.js", "/styles.css"):
            code, headers, body = inspect_request(handler, path, "do_GET")
            self.assertEqual(code, 200)
            self.assertEqual(body, assets[path].content)
            self.assertEqual(headers["content-length"], str(len(body)))
            self.assertEqual(headers["content-security-policy"], CSP)
            self.assertEqual(headers["cache-control"], "no-store, max-age=0")
            self.assertEqual(headers["cross-origin-resource-policy"], "same-origin")
            self.assertNotIn("access-control-allow-origin", headers)
            code, headers, body = inspect_request(handler, path, "do_HEAD")
            self.assertEqual(code, 200)
            self.assertEqual(body, b"")
            self.assertEqual(headers["content-length"], str(len(assets[path].content)))
        for path in (
            "/api/auth/challenges", "/api/records", "/no-such-page",
            "/../web/app.js", "/%61pp.js", "/app.js?unsafe=1",
            "/app.js#fragment", "//app.js", "/.git/config",
        ):
            code, headers, body = inspect_request(handler, path, "do_GET")
            self.assertEqual(code, 404)
            self.assertEqual(headers["content-length"], "0")
            self.assertEqual(body, b"")

    def test_write_methods_unconditionally_rejected_without_input_echo(self):
        handler = make_handler(load_static_assets())
        for method in ("do_POST", "do_PUT", "do_PATCH", "do_DELETE", "do_OPTIONS"):
            code, headers, body = inspect_request(handler, "/api/auth/sessions?secret=dont-echo", method)
            self.assertEqual(code, 405)
            self.assertEqual(headers["content-length"], "0")
            self.assertEqual(body, b"")
            self.assertNotIn("dont-echo", repr(headers))

    def test_cli_inert_preflight_and_wrong_ack_never_bind(self):
        out, err = StringIO(), StringIO()
        with patch("tools.marketplace_local_browser_key_ceremony.ThreadingHTTPServer", side_effect=AssertionError("socket")):
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(main(["--preflight-static-assets"]), 0)
        self.assertIn("status=LOCAL_BROWSER_KEY_CEREMONY_ASSETS_PRESENT", out.getvalue())
        self.assertIn("socket_bound=false", out.getvalue())
        self.assertEqual(err.getvalue(), "")
        with patch("tools.marketplace_local_browser_key_ceremony.load_static_assets", side_effect=AssertionError("should not read assets")):
            out, err = StringIO(), StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(main(["--execute-browser-key-ceremony", "WRONG"]), 1)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(err.getvalue().strip(), "status=BLOCKED code=EXECUTION_OPT_IN_REQUIRED")

    def test_bad_port_before_any_socket(self):
        for port in (0, 1023, 65536, -1, True, None, 3.14):
            with self.assertRaises(BrowserKeyCeremonyError) as raised:
                serve_browser_key_ceremony(port, load_static_assets())
            self.assertEqual(raised.exception.code, "PORT_INVALID")
        for port in ("0", "1023", "65536"):
            out, err = StringIO(), StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(main(["--port", port, "--preflight-static-assets"]), 1)
            self.assertIn("PORT_INVALID", err.getvalue())

    def test_missing_or_symlinked_assets_rejected_without_directory_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "web").mkdir()
            with self.assertRaises(BrowserKeyCeremonyError) as raised:
                load_static_assets(root)
            self.assertEqual(raised.exception.code, "ASSET_UNAVAILABLE")

    def test_socket_execution_binds_ipv4_loopback_only_with_exact_ack(self):
        out, err = StringIO(), StringIO()
        class FakeServer:
            received = None
            daemon_threads = False
            def __init__(self, bind, handler):
                self.received = bind
                self.handler = handler
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return None
            def serve_forever(self, **kwargs):
                raise KeyboardInterrupt()
        with patch("tools.marketplace_local_browser_key_ceremony.ThreadingHTTPServer", FakeServer):
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(
                    main(["--port", "18484", "--execute-browser-key-ceremony", EXECUTION_OPT_IN]), 0
                )
        self.assertIn("host=127.0.0.1 port=18484", out.getvalue())
        self.assertIn("postgres_connection_invoked=false", out.getvalue())
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(HOST, "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
