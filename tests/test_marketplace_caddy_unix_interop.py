"""Opt-in, isolated real-Caddy HTTPS to kernel-attested Unix ASGI smoke.

Never runs in normal CI or on import. Requires an explicitly provisioned
Caddy binary via environment; binds TLS only to local 127.0.0.1, uses
ephemeral certificates and AF_UNIX paths, and tears every process down.
This tests interoperability, NOT live production Caddy or separate UIDs.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import unittest

from marketplace.application.attested_caddy_edge import MarketplaceAttestedCaddyEdgeAsgiAdapter
from marketplace.application.canonical_origin_guard import MarketplaceCanonicalOriginAsgiGuard
from marketplace.application.linux_unix_caddy_peer import MarketplaceLinuxUnixCaddyPeerVerifier
from marketplace.application.unix_listener import (
    EXACT_FOREGROUND_OPT_IN,
    serve_bounded_marketplace_unix_foreground,
)
from tools.marketplace_caddy_unix_review_candidate import (
    CANONICAL_HOST,
    REVIEW_UNIX_UPSTREAM,
    render_caddy_unix_review_candidate,
)


CADDY_BINARY = os.environ.get("MARKETPLACE_CADDY_INTEROP_BIN", "")
CAN_RUN = (
    sys.platform.startswith("linux")
    and hasattr(socket, "SO_PEERCRED")
    and hasattr(os, "geteuid")
    and os.geteuid() > 0
    and os.getegid() > 0
    and bool(CADDY_BINARY)
)
REQUESTS = (
    (
        b"GET /api/agreements?ticket=hello%2Fworld HTTP/1.1\r\n"
        b"Host: marketplace.open-trust-layer.org\r\n"
        b"Connection: close\r\n\r\n",
        200,
        b"MARKETPLACE_INTEROP_READY",
    ),
    (
        b"POST /api/agreements HTTP/1.1\r\n"
        b"Host: marketplace.open-trust-layer.org\r\n"
        b"Origin: https://marketplace.open-trust-layer.org\r\n"
        b"Content-Length: 2\r\n"
        b"Connection: close\r\n\r\n{}",
        201,
        b"MARKETPLACE_INTEROP_CREATED",
    ),
    (
        b"POST /api/agreements HTTP/1.1\r\n"
        b"Host: marketplace.open-trust-layer.org\r\n"
        b"Content-Length: 2\r\n"
        b"Connection: close\r\n\r\n{}",
        403,
        b"ORIGIN_REQUIRED",
    ),
)


def _get_free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _create_test_certificate(base: Path) -> tuple[Path, Path]:
    cert, key = base / "cert.pem", base / "key.pem"
    subprocess.run(
        (
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-days", "1", "-keyout", str(key), "-out", str(cert),
            "-subj", "/CN=marketplace.open-trust-layer.org",
            "-addext", "subjectAltName=DNS:marketplace.open-trust-layer.org",
        ),
        check=True, timeout=15, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    key.chmod(0o600)
    return cert, key


def _test_caddyfile(base: Path, port: int, cert: Path, key: Path) -> str:
    # Retain the exact review snippet's backend directives; only replace
    # private test route, temporary socket path and local-only TLS bind.
    original = render_caddy_unix_review_candidate()
    rewritten = original.replace(
        f"{CANONICAL_HOST} {{\n",
        f"https://{CANONICAL_HOST}:{port} {{\n"
        "    bind 127.0.0.1\n"
        f"    tls {cert} {key}\n",
        1,
    )
    rewritten = rewritten.replace(
        REVIEW_UNIX_UPSTREAM,
        "unix/" + str(base / "marketplace-edge.sock"),
        1,
    )
    if rewritten == original or rewritten.count("reverse_proxy") != 1:
        raise AssertionError("Caddy snippet rewrite did not match reviewed source")
    return "{\n    admin off\n    auto_https disable_redirects\n}\n" + rewritten


def _tls_request(port: int, cert: Path, raw: bytes) -> bytes:
    context = ssl.create_default_context(cafile=str(cert))
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    with socket.create_connection(("127.0.0.1", port), timeout=3) as raw_socket:
        with context.wrap_socket(
            raw_socket, server_hostname=CANONICAL_HOST,
        ) as tls:
            tls.settimeout(4)
            tls.sendall(raw)
            received = bytearray()
            while True:
                piece = tls.recv(4096)
                if not piece:
                    break
                received.extend(piece)
            return bytes(received)


@unittest.skipUnless(CAN_RUN, "Opt-in Linux test requires MARKETPLACE_CADDY_INTEROP_BIN")
class RealCaddyUnixInteropTest(unittest.IsolatedAsyncioTestCase):
    async def test_verified_https_caddy_to_unix_asgi(self):
        binary = Path(CADDY_BINARY)
        self.assertTrue(binary.is_absolute() and binary.is_file())
        self.assertTrue(os.access(binary, os.X_OK))
        self.assertTrue(shutil.which("openssl"))
        with tempfile.TemporaryDirectory(prefix="marketplace-caddy-interop-") as scratch:
            root = Path(scratch)
            sock_path = root / "marketplace-edge.sock"
            cert, key = await asyncio.to_thread(_create_test_certificate, root)
            port = _get_free_local_port()
            conf = root / "Caddyfile"
            conf.write_text(_test_caddyfile(root, port, cert, key), encoding="utf-8")
            settings = dict(os.environ)
            settings["XDG_CONFIG_HOME"] = str(root / "xdg-config")
            settings["XDG_DATA_HOME"] = str(root / "xdg-data")
            settings["HOME"] = str(root)
            seen = []

            async def app(scope, receive, send):
                data = await receive()
                seen.append((scope["method"], scope["path"], scope["query_string"], data["body"]))
                response_status = 201 if scope["method"] == "POST" else 200
                response_body = (
                    b"MARKETPLACE_INTEROP_CREATED" if response_status == 201
                    else b"MARKETPLACE_INTEROP_READY"
                )
                await send({"type": "http.response.start", "status": response_status,
                            "headers": [(b"content-type", b"text/plain")]})
                await send({"type": "http.response.body", "body": response_body})

            verifier = MarketplaceLinuxUnixCaddyPeerVerifier(
                socket_path=str(sock_path),
                caddy_uid=os.geteuid(),
                caddy_gid=os.getegid(),
            )
            edge = MarketplaceAttestedCaddyEdgeAsgiAdapter(
                guard=MarketplaceCanonicalOriginAsgiGuard(app=app), verifier=verifier,
            )
            listener = asyncio.create_task(serve_bounded_marketplace_unix_foreground(
                directory=str(root), edge=edge, execute_token=EXACT_FOREGROUND_OPT_IN,
                max_accepts=len(REQUESTS), max_concurrent=2, max_lifetime=20,
            ))
            caddy: subprocess.Popen | None = None
            try:
                # caddy adapt: local parse only, then launch the isolated
                # local-only TLS test proxy; never use Caddy's global config.
                adapted = await asyncio.to_thread(
                    subprocess.run,
                    (str(binary), "adapt", "--config", str(conf), "--adapter", "caddyfile"),
                    capture_output=True, timeout=12,
                )
                self.assertEqual(adapted.returncode, 0, adapted.stderr.decode(errors="replace")[-2000:])
                caddy = subprocess.Popen(
                    (str(binary), "run", "--config", str(conf), "--adapter", "caddyfile"),
                    cwd=str(root), env=settings, stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                results = []
                for raw, expected_status, expected_body in REQUESTS:
                    response = None
                    for _ in range(60):
                        if caddy.poll() is not None:
                            self.fail("isolated Caddy exited before test requests")
                        try:
                            response = await asyncio.to_thread(_tls_request, port, cert, raw)
                            break
                        except (OSError, ssl.SSLError):
                            await asyncio.sleep(0.05)
                    self.assertIsNotNone(response, "local-only Caddy listener never became ready")
                    assert response is not None
                    first = response.split(b"\r\n", 1)[0]
                    self.assertEqual(int(first.split(b" ")[1]), expected_status, response[:800])
                    self.assertIn(expected_body, response, response[:800])
                    results.append(expected_status)
                self.assertEqual(results, [200, 201, 403])
                self.assertEqual(
                    seen,
                    [
                        ("GET", "/api/agreements", b"ticket=hello%2Fworld", b""),
                        ("POST", "/api/agreements", b"", b"{}"),
                    ],
                )
                finished = await asyncio.wait_for(listener, timeout=8)
                self.assertEqual(sorted(finished), [200, 201, 403])
            finally:
                if caddy is not None:
                    caddy.terminate()
                    try:
                        await asyncio.to_thread(caddy.communicate, timeout=5)
                    except subprocess.TimeoutExpired:
                        caddy.kill()
                        await asyncio.to_thread(caddy.communicate, timeout=5)
                if not listener.done():
                    listener.cancel()
                    await asyncio.gather(listener, return_exceptions=True)
            self.assertFalse(sock_path.exists(), "temporary Unix listener was not removed")


if __name__ == "__main__":
    unittest.main()
