"""Source-only tests for bounded historical localhost Web asset comparisons."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib import error

from tools.marketplace_historical_public_assets import (
    HistoricalAssetError,
    _public_asset,
    _git_asset,
    main,
    verify_historical_assets,
)
from tools.marketplace_localhost_asset_preflight import ASSETS

SHA = "a" * 40
ROOT = Path("unused")


class HistoricalPublicAssetsTests(unittest.TestCase):
    def _verify(
        self, expected: dict[str, bytes | None], actual: dict[str, bytes | None], *,
        reader=None,
    ) -> tuple[int, int]:
        names = {route: path for route, path in ASSETS}
        assert names["/"] == "web/index.html"
        return verify_historical_assets(
            ROOT, SHA, 18480,
            revision_check=Mock(),
            historical_reader=lambda _root, _sha, rel: expected.get(rel),
            public_reader=reader or (lambda _port, route: actual.get(route)),
        )

    def test_matched_historical_snapshot_with_expected_absent_module(self) -> None:
        expected = {
            "web/index.html": b"old index",
            "web/app.js": b"old client",
        }
        actual = {"/": b"old index", "/app.js": b"old client"}
        self.assertEqual(self._verify(expected, actual), (2, len(ASSETS) - 2))

    def test_match_entire_public_snapshot(self) -> None:
        expected = {rel: rel.encode("ascii") for _, rel in ASSETS}
        actual = {route: rel.encode("ascii") for route, rel in ASSETS}
        self.assertEqual(self._verify(expected, actual), (len(ASSETS), 0))

    def test_reject_modified_body(self) -> None:
        with self.assertRaises(HistoricalAssetError) as ctx:
            self._verify({"web/index.html": b"old"}, {"/": b"new"})
        self.assertEqual(ctx.exception.code, "PUBLIC_ASSET_MISMATCH")

    def test_reject_unexpected_module_when_commit_lacks_it(self) -> None:
        with self.assertRaises(HistoricalAssetError) as ctx:
            self._verify({"web/index.html": b"old"}, {
                "/": b"old", "/authenticated_local_flight_evidence.js": b"new module"
            })
        self.assertEqual(ctx.exception.code, "UNEXPECTED_PUBLIC_ASSET")

    def test_reject_missing_public_route(self) -> None:
        with self.assertRaises(HistoricalAssetError) as ctx:
            self._verify({"web/index.html": b"old"}, {})
        self.assertEqual(ctx.exception.code, "PUBLIC_ASSET_MISSING")

    def test_reject_empty_repository_snapshot(self) -> None:
        with self.assertRaises(HistoricalAssetError) as ctx:
            self._verify({}, {})
        self.assertEqual(ctx.exception.code, "SNAPSHOT_EMPTY")

    def test_detect_web_shell_changing_during_check(self) -> None:
        calls = 0

        def changing(_port, route):
            nonlocal calls
            if route != "/":
                return None
            calls += 1
            return b"original" if calls == 1 else b"changed"

        with self.assertRaises(HistoricalAssetError) as ctx:
            self._verify({"web/index.html": b"original"}, {}, reader=changing)
        self.assertEqual(ctx.exception.code, "PUBLIC_ASSETS_CHANGED")

    def test_invalid_sha_and_port_do_not_invoke_git_or_http(self) -> None:
        source = Mock(side_effect=AssertionError("source unexpectedly consulted"))
        remote = Mock(side_effect=AssertionError("socket unexpectedly consulted"))
        for sha, port, code in (
            ("../etc/passwd", 18480, "REVISION_INVALID"),
            (SHA, 0, "PORT_INVALID"),
            (SHA, 99999, "PORT_INVALID"),
            (SHA, True, "PORT_INVALID"),
        ):
            with self.subTest(sha=sha, port=port):
                with self.assertRaises(HistoricalAssetError) as ctx:
                    verify_historical_assets(
                        ROOT, sha, port,
                        revision_check=source,
                        historical_reader=source,
                        public_reader=remote,
                    )
                self.assertEqual(ctx.exception.code, code)
        source.assert_not_called()
        remote.assert_not_called()

    def test_reject_oversize_fixture(self) -> None:
        large = b"x" * (2 * 1024 * 1024 + 1)
        with self.assertRaises(HistoricalAssetError) as ctx:
            self._verify({"web/index.html": large}, {"/": large})
        self.assertEqual(ctx.exception.code, "PUBLIC_ASSET_TOO_LARGE")

    def test_http_404_is_only_accepted_as_missing(self) -> None:
        failure = error.HTTPError("http://127.0.0.1:18480/", 404, "missing", {}, None)
        mock_opener = Mock()
        mock_opener.open.side_effect = failure
        with patch("tools.marketplace_historical_public_assets.request.build_opener", return_value=mock_opener):
            self.assertIsNone(_public_asset(18480, "/"))
        failure = error.HTTPError("http://127.0.0.1:18480/", 302, "redirect", {}, None)
        mock_opener.open.side_effect = failure
        with patch("tools.marketplace_historical_public_assets.request.build_opener", return_value=mock_opener):
            with self.assertRaises(HistoricalAssetError) as ctx:
                _public_asset(18480, "/")
        self.assertEqual(ctx.exception.code, "HTTP_UNAVAILABLE")

    def test_regular_git_blob_required(self) -> None:
        with patch("tools.marketplace_historical_public_assets._git", return_value=b"120000 blob " + b"a" * 40 + b"\tweb/index.html\n"):
            with self.assertRaises(HistoricalAssetError) as ctx:
                _git_asset(ROOT, SHA, "web/index.html")
        self.assertEqual(ctx.exception.code, "REVISION_ASSET_INVALID")

    def test_cli_does_not_echo_supplied_paths_or_content(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--historical-sha", "secret_path_token", "--port", "18480", "--source-root", "secret_path_token"])
        self.assertEqual(code, 1)
        self.assertIn("REVISION_INVALID", err.getvalue())
        self.assertNotIn("secret_path_token", out.getvalue() + err.getvalue())


if __name__ == "__main__":
    unittest.main()
