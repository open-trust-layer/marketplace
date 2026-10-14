"""Read-only historical-public-asset parity check for a running IPv4 localhost Marketplace.

Compares only the fixed reviewed public Web routes with an explicitly selected
ancestor Git commit. The result says nothing about the server's Python source,
authentication, production status, database, or Moon heartbeat.
"""
from __future__ import annotations

import argparse
import hashlib
from http.client import HTTPException
from pathlib import Path
import re
import subprocess
import sys
from urllib import error, request

from tools.marketplace_localhost_asset_preflight import ASSETS, HOST, MAX_ASSET_BYTES, ROOT


class HistoricalAssetError(RuntimeError):
    """Stable failure code; never incorporate fetched bytes, paths or secrets."""

    def __init__(self, code: str) -> None:
        super().__init__("Marketplace historical public asset check failed")
        self.code = code


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _git(root: Path, *args: str, timeout: int = 8) -> bytes:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        raise HistoricalAssetError("REVISION_UNAVAILABLE") from None
    if proc.returncode != 0:
        raise HistoricalAssetError("REVISION_UNAVAILABLE")
    return proc.stdout


def _check_revision(root: Path, sha: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise HistoricalAssetError("REVISION_INVALID")
    actual = _git(root, "rev-parse", "--verify", f"{sha}^{{commit}}").strip()
    if actual != sha.encode("ascii"):
        raise HistoricalAssetError("REVISION_UNAVAILABLE")
    _git(root, "merge-base", "--is-ancestor", sha, "HEAD")


def _git_asset(root: Path, sha: str, relative: str) -> bytes | None:
    listing = _git(root, "ls-tree", sha, "--", relative).strip()
    if not listing:
        return None
    # Never open a symlink, submodule, tree, device or unreviewed path.
    match = re.fullmatch(
        rb"(?:100644|100755) blob ([0-9a-f]{40})\t" + re.escape(relative.encode("ascii")),
        listing,
    )
    if match is None:
        raise HistoricalAssetError("REVISION_ASSET_INVALID")
    oid = match.group(1).decode("ascii")
    raw_size = _git(root, "cat-file", "-s", oid).strip()
    try:
        size = int(raw_size)
    except ValueError:
        raise HistoricalAssetError("REVISION_ASSET_INVALID") from None
    if not 0 <= size <= MAX_ASSET_BYTES:
        raise HistoricalAssetError("REVISION_ASSET_INVALID")
    value = _git(root, "cat-file", "blob", oid)
    if len(value) != size:
        raise HistoricalAssetError("REVISION_ASSET_INVALID")
    return value


def _public_asset(port: int, route: str) -> bytes | None:
    opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())
    req = request.Request(
        f"http://{HOST}:{port}{route}",
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        method="GET",
    )
    try:
        with opener.open(req, timeout=5) as response:
            if response.status != 200:
                raise HistoricalAssetError("HTTP_UNAVAILABLE")
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise HistoricalAssetError("HTTP_ENCODING_INVALID")
            data = response.read(MAX_ASSET_BYTES + 1)
    except error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise HistoricalAssetError("HTTP_UNAVAILABLE") from None
    except (OSError, ValueError, HTTPException):
        raise HistoricalAssetError("HTTP_UNAVAILABLE") from None
    if len(data) > MAX_ASSET_BYTES:
        raise HistoricalAssetError("HTTP_ASSET_TOO_LARGE")
    return data


def verify_historical_assets(
    root: Path,
    sha: str,
    port: int,
    *,
    revision_check=_check_revision,
    historical_reader=_git_asset,
    public_reader=_public_asset,
) -> tuple[int, int]:
    """Fail closed on any asset difference, including expected 404 vs HTTP 200."""
    if type(port) is not int or not 1024 <= port <= 65535:
        raise HistoricalAssetError("PORT_INVALID")
    if type(sha) is not str or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise HistoricalAssetError("REVISION_INVALID")
    revision_check(root, sha)
    matched = 0
    absent = 0
    index_first: bytes | None = None
    for route, relative in ASSETS:
        expected = historical_reader(root, sha, relative)
        observed = public_reader(port, route)
        if route == "/":
            index_first = observed
        if expected is None:
            if observed is not None:
                raise HistoricalAssetError("UNEXPECTED_PUBLIC_ASSET")
            absent += 1
        else:
            if observed is None:
                raise HistoricalAssetError("PUBLIC_ASSET_MISSING")
            if len(expected) > MAX_ASSET_BYTES or len(observed) > MAX_ASSET_BYTES:
                raise HistoricalAssetError("PUBLIC_ASSET_TOO_LARGE")
            if hashlib.sha256(expected).digest() != hashlib.sha256(observed).digest():
                raise HistoricalAssetError("PUBLIC_ASSET_MISMATCH")
            matched += 1
    if matched == 0:
        raise HistoricalAssetError("SNAPSHOT_EMPTY")
    # Catch a straightforward mid-probe Web-shell swap (not a race-free guarantee).
    if public_reader(port, "/") != index_first:
        raise HistoricalAssetError("PUBLIC_ASSETS_CHANGED")
    return matched, absent


class _RedactedParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "status=FAIL code=ARGUMENT_INVALID\n")


def main(argv: list[str] | None = None) -> int:
    parser = _RedactedParser(description="Read-only localhost historical public Web asset verification")
    parser.add_argument("--historical-sha", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--source-root", default=str(ROOT))
    arguments = parser.parse_args(argv)
    try:
        matched, missing = verify_historical_assets(
            Path(arguments.source_root), arguments.historical_sha, arguments.port
        )
    except HistoricalAssetError as exc:
        print(f"status=FAIL code={exc.code}", file=sys.stderr)
        return 1
    print(
        f"status=PASS historical_sha={arguments.historical_sha} "
        f"host={HOST} port={arguments.port} matched_public_assets={matched} "
        f"expected_absent_assets={missing} "
        "historical_web_snapshot_only=true backend_provenance_verified=false "
        "auth_verified=false production_verified=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
