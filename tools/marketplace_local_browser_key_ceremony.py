"""Explicit loopback-only, static Marketplace browser-key ceremony host.

Previewing reviewed Web assets permits *browser-owned*, non-extractable Ed25519
key creation before an authenticated local server is running. The preview is
never the authenticated server and does not accept API writes or read secrets.
Import and asset preflight never bind a socket.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from typing import Final

HOST: Final = "127.0.0.1"
MIN_PORT: Final = 1024
MAX_PORT: Final = 65535
MAX_FILE_BYTES: Final = 1024 * 1024
EXECUTION_OPT_IN: Final = "EXECUTE_MARKETPLACE_LOCAL_BROWSER_KEY_CEREMONY_V1"
REPO_ROOT: Final = Path(__file__).resolve().parents[1]

# Exact static Web surface served by the reviewed localhost application.
# All other paths, query strings and encodings fail closed.
WEB_FILES: Final = (
    "index.html",
    "app.js",
    "styles.css",
    "client_session.js",
    "auth_establishment.js",
    "auth_ed25519_proof_provider.js",
    "auth_ed25519_key_creation.js",
    "agreement_ed25519_assent_provider.js",
    "agreement_assent_client.js",
    "proposal_acceptance_client.js",
    "agreement_publication_client.js",
    "fulfillment_completion_client.js",
    "authenticated_local_flight_evidence.js",
    "auth_bootstrap.js",
)
CSP: Final = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; img-src 'self'; object-src 'none'; "
    "form-action 'none'; base-uri 'none'; frame-ancestors 'none'"
)


class BrowserKeyCeremonyError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class StaticAsset:
    content: bytes
    content_type: str


def load_static_assets(repo_root: Path = REPO_ROOT) -> dict[str, StaticAsset]:
    """Read only the exact regular reviewed files; no arbitrary path resolution."""
    if not isinstance(repo_root, Path) or not repo_root.is_absolute():
        raise BrowserKeyCeremonyError("ASSET_ROOT_INVALID")
    web_root = repo_root / "web"
    if web_root.is_symlink() or not web_root.is_dir():
        raise BrowserKeyCeremonyError("ASSET_ROOT_INVALID")
    assets: dict[str, StaticAsset] = {}
    for name in WEB_FILES:
        path = web_root / name
        if path.is_symlink() or not path.is_file():
            raise BrowserKeyCeremonyError("ASSET_UNAVAILABLE")
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                raise BrowserKeyCeremonyError("ASSET_TOO_LARGE")
            with path.open("rb") as stream:
                content = stream.read(MAX_FILE_BYTES + 1)
        except OSError:
            raise BrowserKeyCeremonyError("ASSET_UNAVAILABLE") from None
        if len(content) > MAX_FILE_BYTES or not content:
            raise BrowserKeyCeremonyError("ASSET_TOO_LARGE")
        content_type = (
            "text/html; charset=utf-8" if name.endswith(".html")
            else "text/css; charset=utf-8" if name.endswith(".css")
            else "text/javascript; charset=utf-8"
        )
        assets["/" + name] = StaticAsset(content, content_type)
    assets["/"] = assets["/index.html"]
    return assets


def make_handler(assets: dict[str, StaticAsset]) -> type[BaseHTTPRequestHandler]:
    """Create a no-directory-fallback HTTP handler from immutable asset bytes."""
    if not assets or set(assets) != {"/", *("/" + name for name in WEB_FILES)}:
        raise BrowserKeyCeremonyError("ASSET_SURFACE_INVALID")
    frozen = dict(assets)

    class CeremonyHandler(BaseHTTPRequestHandler):
        server_version = "MarketplaceLocalKeyCeremony"
        sys_version = ""

        def log_message(self, _format: str, *_args: object) -> None:
            # Never log paths, referers, inputs, local OS details or credentials.
            return

        def _reply(self, status: int, asset: StaticAsset | None = None, *, head: bool = False) -> None:
            self.send_response(status)
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            if asset is not None:
                self.send_header("Content-Type", asset.content_type)
                self.send_header("Content-Length", str(len(asset.content)))
            else:
                self.send_header("Content-Length", "0")
            self.end_headers()
            if asset is not None and not head:
                self.wfile.write(asset.content)

        def do_GET(self) -> None:
            self._reply(200, frozen[self.path]) if self.path in frozen else self._reply(404)

        def do_HEAD(self) -> None:
            self._reply(200, frozen[self.path], head=True) if self.path in frozen else self._reply(404)

        def do_POST(self) -> None:
            self._reply(405)

        do_PUT = do_POST
        do_PATCH = do_POST
        do_DELETE = do_POST
        do_OPTIONS = do_POST

    return CeremonyHandler


def serve_browser_key_ceremony(port: int, assets: dict[str, StaticAsset]) -> None:
    """Explicit execution-only operation; bind always exact IPv4 loopback."""
    if type(port) is not int or port < MIN_PORT or port > MAX_PORT:
        raise BrowserKeyCeremonyError("PORT_INVALID")
    handler = make_handler(assets)
    try:
        with ThreadingHTTPServer((HOST, port), handler) as server:
            server.daemon_threads = True
            print(
                f"status=LOCAL_BROWSER_KEY_CEREMONY_READY host={HOST} port={port} "
                "static_only=true api_writes=false credentials_loaded=false "
                "postgres_connection_invoked=false"
            )
            try:
                server.serve_forever(poll_interval=0.2)
            except KeyboardInterrupt:
                pass
    except OSError:
        # A port collision is not permission to stop or replace another service.
        raise BrowserKeyCeremonyError("LOOPBACK_BIND_UNAVAILABLE") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Explicit static localhost preview for two browser-owned Ed25519 test keys."
    )
    parser.add_argument("--port", type=int, default=18080)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-static-assets", action="store_true")
    mode.add_argument("--execute-browser-key-ceremony")
    args = parser.parse_args(argv)
    try:
        if type(args.port) is not int or not MIN_PORT <= args.port <= MAX_PORT:
            raise BrowserKeyCeremonyError("PORT_INVALID")
        if not args.preflight_static_assets and args.execute_browser_key_ceremony != EXECUTION_OPT_IN:
            raise BrowserKeyCeremonyError("EXECUTION_OPT_IN_REQUIRED")
        assets = load_static_assets()
        if args.preflight_static_assets:
            print(
                f"status=LOCAL_BROWSER_KEY_CEREMONY_ASSETS_PRESENT count={len(WEB_FILES)} "
                "socket_bound=false server_invoked=false browser_invoked=false"
            )
        else:
            serve_browser_key_ceremony(args.port, assets)
    except BrowserKeyCeremonyError as error:
        print("status=BLOCKED code=" + error.code, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
