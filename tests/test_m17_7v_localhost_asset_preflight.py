"""Offline contracts for M17.7V/W public localhost asset preflight."""
import ast
from io import BytesIO
from pathlib import Path
from subprocess import CompletedProcess
import tempfile
import unittest
from unittest.mock import patch

from tools.marketplace_localhost_asset_preflight import (
    ASSETS,
    ROOT,
    HOST,
    MAX_ASSET_BYTES,
    AssetPreflightError,
    _NoRedirect,
    _read_asset,
    _checkout_head,
    verify_assets,
)

SHA = "e" * 40


class M177VLocalhostAssetPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payloads = {}
        for i, (path, relative) in enumerate(ASSETS):
            content = f"static asset {i}\n".encode("utf-8")
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            self.payloads[path] = content
        self.requests = []

    def _head(self, _root):
        return SHA

    def _asset(self, port, path):
        self.requests.append((port, path))
        return self.payloads[path]

    def _verify(self, sha=SHA, port=18080):
        return verify_assets(
            self.root, sha, port, head_reader=self._head, asset_reader=self._asset
        )

    def test_exact_assets_pass_and_only_expected_paths_are_requested(self):
        self.assertEqual(self._verify(), len(ASSETS))
        self.assertEqual(self.requests, [(18080, path) for path, _ in ASSETS])
        self.assertEqual(HOST, "127.0.0.1")

    def test_asset_map_exactly_covers_reviewed_server_web_allowlist(self):
        # Read syntax only; never import/initialize the live runtime.
        source = (ROOT / "tools" / "marketplace_localhost.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        required = {
            "_INDEX_ASSET", "_APP_JS_ASSET", "_STYLES_ASSET",
            "_AUTH_WEB_MODULE_ASSETS",
        }
        constants = {}
        for statement in tree.body:
            if (
                isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
                and statement.target.id in required
            ):
                constants[statement.target.id] = ast.literal_eval(statement.value)
        self.assertEqual(set(constants), required)
        expected = (
            ("/", constants["_INDEX_ASSET"]),
            ("/app.js", constants["_APP_JS_ASSET"]),
            ("/styles.css", constants["_STYLES_ASSET"]),
            *constants["_AUTH_WEB_MODULE_ASSETS"],
        )
        self.assertEqual(len(expected), 14)
        self.assertEqual(ASSETS, expected)
        self.assertEqual(len({path for path, _ in ASSETS}), len(ASSETS))
        self.assertEqual(len({path for _, path in ASSETS}), len(ASSETS))

    def test_stale_secondary_auth_module_fails_closed(self):
        asset = "/agreement_ed25519_assent_provider.js"
        self.payloads[asset] += b"// unexpected old module"
        with self.assertRaises(AssetPreflightError) as caught:
            self._verify()
        self.assertEqual((caught.exception.code, caught.exception.asset), ("ASSET_MISMATCH", asset))

    def test_missing_buyer_session_module_fails_closed(self):
        asset = "/client_session.js"
        def missing(port, path):
            if path == asset:
                raise AssetPreflightError("HTTP_FAILED", asset)
            return self._asset(port, path)
        with self.assertRaises(AssetPreflightError) as caught:
            verify_assets(self.root, SHA, 18080, head_reader=self._head, asset_reader=missing)
        self.assertEqual((caught.exception.code, caught.exception.asset), ("HTTP_FAILED", asset))

    def test_stale_served_html_fails_closed(self):
        self.payloads["/"] = b"<html>older Marketplace UI</html>"
        with self.assertRaises(AssetPreflightError) as caught:
            self._verify()
        self.assertEqual((caught.exception.code, caught.exception.asset), ("ASSET_MISMATCH", "/"))

    def test_missing_flight_module_fails_closed(self):
        def missing(port, path):
            if path == "/authenticated_local_flight_evidence.js":
                raise AssetPreflightError("HTTP_FAILED", path)
            return self._asset(port, path)
        with self.assertRaises(AssetPreflightError) as caught:
            verify_assets(self.root, SHA, 18080, head_reader=self._head, asset_reader=missing)
        self.assertEqual(caught.exception.code, "HTTP_FAILED")

    def test_hash_matches_bytes_not_presence_of_marker(self):
        self.payloads["/app.js"] += b"// unreviewed delta"
        with self.assertRaises(AssetPreflightError) as caught:
            self._verify()
        self.assertEqual(caught.exception.asset, "/app.js")

    def test_checkout_head_requires_clean_committed_assets(self):
        for diff_exit, expected in ((0, None), (1, "CHECKOUT_ASSETS_DIRTY"), (128, "CHECKOUT_ASSETS_DIRTY")):
            with self.subTest(diff_exit=diff_exit):
                with patch(
                    "tools.marketplace_localhost_asset_preflight.subprocess.run",
                    side_effect=[
                        CompletedProcess(args=[], returncode=0, stdout=SHA, stderr=""),
                        CompletedProcess(args=[], returncode=diff_exit, stdout="", stderr=""),
                    ],
                ) as runner:
                    if expected is None:
                        self.assertEqual(_checkout_head(self.root), SHA)
                    else:
                        with self.assertRaises(AssetPreflightError) as caught:
                            _checkout_head(self.root)
                        self.assertEqual(caught.exception.code, expected)
                    self.assertEqual(runner.call_count, 2)
                    diff_args = runner.call_args.args[0]
                    self.assertEqual(diff_args[:7], [
                        "git", "-C", str(self.root), "diff", "--quiet", "HEAD", "--",
                    ])
                    self.assertEqual(diff_args[7:], [relative for _, relative in ASSETS])

    def test_head_mismatch_fails_before_any_http(self):
        with self.assertRaises(AssetPreflightError) as caught:
            self._verify("a" * 40)
        self.assertEqual(caught.exception.code, "CHECKOUT_HEAD_MISMATCH")
        self.assertEqual(self.requests, [])

    def test_invalid_sha_and_ports_fail_before_any_http(self):
        for sha, port, code in (
            ("E" * 40, 18080, "EXPECTED_SHA_INVALID"),
            ("bad", 18080, "EXPECTED_SHA_INVALID"),
            (SHA, 80, "PORT_INVALID"),
            (SHA, 65536, "PORT_INVALID"),
            (SHA, True, "PORT_INVALID"),
        ):
            with self.subTest(sha=sha, port=port):
                with self.assertRaises(AssetPreflightError) as caught:
                    self._verify(sha, port)
                self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.requests, [])

    def test_missing_or_oversized_local_asset_fails(self):
        first = self.root / ASSETS[0][1]
        first.unlink()
        with self.assertRaises(AssetPreflightError) as caught:
            self._verify()
        self.assertEqual(caught.exception.code, "LOCAL_ASSET_UNAVAILABLE")
        first.write_bytes(b"x" * (MAX_ASSET_BYTES + 1))
        with self.assertRaises(AssetPreflightError) as caught:
            self._verify()
        self.assertEqual(caught.exception.code, "LOCAL_ASSET_TOO_LARGE")

    def test_redirect_is_rejected(self):
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "", {}, "http://elsewhere/"))

    def test_actual_reader_is_loopback_only_and_proxy_free(self):
        class Response(BytesIO):
            status = 200
            headers = {"Content-Encoding": "identity"}
        class FakeOpener:
            def open(self, req, timeout):
                self_url = req.full_url
                self_method = req.get_method()
                self.assertEqual(self_url, "http://127.0.0.1:18080/app.js")
                self.assertEqual(self_method, "GET")
                self.assertEqual(timeout, 5)
                return Response(b"reviewed")
            def __init__(self, test):
                self.assertEqual = test.assertEqual
        def factory(*handlers):
            self.assertEqual(len(handlers), 2)
            self.assertEqual(handlers[0].proxies, {})
            self.assertIsInstance(handlers[1], _NoRedirect)
            return FakeOpener(self)
        with patch("tools.marketplace_localhost_asset_preflight.request.build_opener", side_effect=factory):
            self.assertEqual(_read_asset(18080, "/app.js"), b"reviewed")


if __name__ == "__main__":
    unittest.main()
