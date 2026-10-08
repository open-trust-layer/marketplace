"""Read-only, exact-checkout preflight for public Marketplace localhost Web assets.

Only literal static GET paths and the exact IPv4 loopback host are permitted.
No authentication, environment, database, process, or runtime activation.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys
from urllib import request

ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
MAX_ASSET_BYTES = 2 * 1024 * 1024
ASSETS = (
    ("/", "web/index.html"),
    ("/app.js", "web/app.js"),
    ("/styles.css", "web/styles.css"),
    ("/auth_bootstrap.js", "web/auth_bootstrap.js"),
    ("/agreement_publication_client.js", "web/agreement_publication_client.js"),
    ("/fulfillment_completion_client.js", "web/fulfillment_completion_client.js"),
    ("/authenticated_local_flight_evidence.js", "web/authenticated_local_flight_evidence.js"),
)


class AssetPreflightError(RuntimeError):
    """Stable error without response content, credentials, paths, or command lines."""

    def __init__(self, code: str, asset: str | None = None):
        super().__init__(code)
        self.code = code
        self.asset = asset


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _validate_inputs(expected_sha: str, port: int) -> None:
    if type(port) is not int or not 1024 <= port <= 65535:
        raise AssetPreflightError("PORT_INVALID")
    if type(expected_sha) is not str or re.fullmatch(r"[0-9a-f]{40}", expected_sha) is None:
        raise AssetPreflightError("EXPECTED_SHA_INVALID")


def _checkout_head(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True, timeout=5,
        )
        sha = result.stdout.strip()
        if re.fullmatch(r"[0-9a-f]{40}", sha) is None:
            raise ValueError("invalid checkout head")
        return sha
    except (OSError, subprocess.SubprocessError, ValueError):
        raise AssetPreflightError("CHECKOUT_HEAD_UNAVAILABLE") from None


def _read_asset(port: int, asset: str) -> bytes:
    # Discard all environment proxy settings, and reject every redirect.
    opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())
    req = request.Request(
        f"http://{HOST}:{port}{asset}",
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        method="GET",
    )
    try:
        with opener.open(req, timeout=5) as response:
            if response.status != 200:
                raise AssetPreflightError("HTTP_FAILED", asset)
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise AssetPreflightError("ENCODING_UNSUPPORTED", asset)
            content = response.read(MAX_ASSET_BYTES + 1)
    except AssetPreflightError:
        raise
    except (OSError, ValueError):
        raise AssetPreflightError("HTTP_FAILED", asset) from None
    if len(content) > MAX_ASSET_BYTES:
        raise AssetPreflightError("ASSET_TOO_LARGE", asset)
    return content


def verify_assets(
    root: Path,
    expected_sha: str,
    port: int,
    *,
    head_reader=_checkout_head,
    asset_reader=_read_asset,
) -> int:
    """Compare local exact-head static files against public loopback responses.

    The check proves byte parity for the selected assets, not process provenance,
    database state, authentication, or acceptance of the live browser flight.
    """
    _validate_inputs(expected_sha, port)
    if head_reader(root) != expected_sha:
        raise AssetPreflightError("CHECKOUT_HEAD_MISMATCH")
    for url_path, relative_path in ASSETS:
        try:
            local = (root / relative_path).read_bytes()
        except OSError:
            raise AssetPreflightError("LOCAL_ASSET_UNAVAILABLE", url_path) from None
        if len(local) > MAX_ASSET_BYTES:
            raise AssetPreflightError("LOCAL_ASSET_TOO_LARGE", url_path)
        remote = asset_reader(port, url_path)
        if hashlib.sha256(local).digest() != hashlib.sha256(remote).digest():
            raise AssetPreflightError("ASSET_MISMATCH", url_path)
    return len(ASSETS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare exact-checkout public static assets with the running IPv4 localhost UI (read-only)."
    )
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--expected-main-sha", required=True)
    args = parser.parse_args(argv)
    try:
        count = verify_assets(ROOT, args.expected_main_sha, args.port)
    except AssetPreflightError as error:
        suffix = f" asset={error.asset}" if error.asset is not None else ""
        print(f"status=FAIL code={error.code}{suffix}", file=sys.stderr)
        return 1
    print(f"status=PASS host={HOST} port={args.port} checked_assets={count} "
          "public_static_only=true runtime_activated=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
