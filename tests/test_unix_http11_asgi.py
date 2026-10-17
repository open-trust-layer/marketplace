"""Local real-kernel Unix HTTP/1.1 to ASGI tests; no external sockets."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest

from marketplace.application.attested_caddy_edge import MarketplaceAttestedCaddyEdgeAsgiAdapter
from marketplace.application.canonical_origin_guard import (
    CANONICAL_HOST,
    MarketplaceCanonicalOriginAsgiGuard,
)
from marketplace.application.linux_unix_caddy_peer import (
    ACCEPTED_UNIX_SOCKET_SCOPE_KEY,
    MarketplaceLinuxUnixCaddyPeerVerifier,
)
from marketplace.application.unix_http11_asgi import serve_one_attested_unix_http11


IS_LINUX_UNPRIVILEGED = (
    sys.platform.startswith("linux")
    and hasattr(socket, "SO_PEERCRED")
    and hasattr(os, "geteuid")
    and os.geteuid() > 0
    and os.getegid() > 0
)

HOST = b"Host: marketplace.open-trust-layer.org\r\n"
FHOST = b"X-Forwarded-Host: marketplace.open-trust-layer.org\r\n"
FPROTO = b"X-Forwarded-Proto: https\r\n"
FFOR = b"X-Forwarded-For: 203.0.113.5\r\n"
ORIGIN = b"Origin: https://marketplace.open-trust-layer.org\r\n"
BASE = HOST + FHOST + FPROTO + FFOR


def req(method=b"GET", path=b"/api/agreements", headers=BASE, body=b""):
    return method + b" " + path + b" HTTP/1.1\r\n" + headers + b"\r\n" + body


@unittest.skipUnless(IS_LINUX_UNPRIVILEGED, "Linux nonroot local Unix socket required")
class RealUnixHttp11AsgiTests(unittest.IsolatedAsyncioTestCase):
    async def run_request(self, request, *, wrong_uid=False, app=None):
        seen = []
        if app is None:
            async def app(scope, receive, send):
                seen.append(scope)
                await send({"type": "http.response.start", "status": 200,
                            "headers": [(b"content-type", b"text/plain")]})
                await send({"type": "http.response.body", "body": b"OK", "more_body": False})

        with tempfile.TemporaryDirectory(prefix="mkt-one-http-") as folder:
            path = str(Path(folder) / "private.sock")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(path)
                listener.listen(1)
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.connect(path)
                    accepted, _addr = listener.accept()
                    verifier = MarketplaceLinuxUnixCaddyPeerVerifier(
                        socket_path=path,
                        caddy_uid=os.geteuid() + (1 if wrong_uid else 0),
                        caddy_gid=os.getegid(),
                    )
                    edge = MarketplaceAttestedCaddyEdgeAsgiAdapter(
                        guard=MarketplaceCanonicalOriginAsgiGuard(app=app),
                        verifier=verifier,
                    )
                    task = asyncio.create_task(
                        serve_one_attested_unix_http11(accepted_socket=accepted, edge=edge)
                    )
                    client.setblocking(False)
                    await asyncio.get_running_loop().sock_sendall(client, request)
                    received = bytearray()
                    while True:
                        chunk = await asyncio.wait_for(
                            asyncio.get_running_loop().sock_recv(client, 4096), timeout=4
                        )
                        if not chunk:
                            break
                        received.extend(chunk)
                    status = await asyncio.wait_for(task, timeout=4)
                    self.assertEqual(accepted.fileno(), -1)
        return status, bytes(received), seen

    async def test_real_kernel_verified_get_reaches_asgi_without_socket_or_forwarding(self):
        status, response, seen = await self.run_request(req())
        self.assertEqual(status, 200)
        self.assertTrue(response.startswith(b"HTTP/1.1 200 OK\r\n"))
        self.assertIn(b"Content-Length: 2\r\n", response)
        self.assertIn(b"Connection: close\r\n", response)
        self.assertTrue(response.endswith(b"\r\n\r\nOK"))
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["scheme"], "https")
        self.assertEqual(seen[0]["path"], "/api/agreements")
        self.assertEqual(seen[0]["headers"], [(b"Host", CANONICAL_HOST)])
        self.assertNotIn(ACCEPTED_UNIX_SOCKET_SCOPE_KEY, seen[0])

    async def test_real_kernel_credentials_deny_wrong_uid_before_http(self):
        status, response, seen = await self.run_request(req(), wrong_uid=True)
        self.assertEqual(status, 403)
        self.assertIn(b"MARKETPLACE_EDGE_REQUEST_REJECTED", response)
        self.assertFalse(seen)

    async def test_signed_request_body_and_query_survive_to_asgi(self):
        recorded = []
        async def app(scope, receive, send):
            event = await receive()
            recorded.append((scope["method"], scope["query_string"], event["body"],
                             ACCEPTED_UNIX_SOCKET_SCOPE_KEY in scope))
            await send({"type": "http.response.start", "status": 201,
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": b"{}", "more_body": False})

        payload = b'{"signed":true}'
        headers = BASE + ORIGIN + b"Content-Type: application/json\r\nContent-Length: " + str(len(payload)).encode() + b"\r\n"
        status, response, seen = await self.run_request(
            req(b"POST", b"/api/agreements?ticket=hello", headers, payload), app=app
        )
        self.assertEqual(status, 201)
        self.assertEqual(recorded, [("POST", b"ticket=hello", payload, False)])
        self.assertTrue(response.endswith(b"\r\n\r\n{}"))

    async def test_missing_or_foreign_origin_rejected_downstream(self):
        for headers in (BASE, BASE + b"Origin: https://evil.example\r\n"):
            with self.subTest(headers=headers):
                status, response, seen = await self.run_request(
                    req(b"POST", headers=headers)
                )
                self.assertEqual(status, 403)
                self.assertFalse(seen)
                self.assertTrue(
                    response.endswith(b"ORIGIN_REQUIRED")
                    or response.endswith(b"ORIGIN_REJECTED")
                )

    async def test_wrong_forwarded_proto_and_duplicate_host_denied(self):
        variants = (
            HOST + FHOST + b"X-Forwarded-Proto: http\r\n",
            BASE + HOST,
            HOST + FHOST,
            HOST + FHOST + FPROTO + b"X-Forwarded-Host: evil.example\r\n",
            HOST + FHOST + FPROTO + b"X-Real-IP: 127.0.0.1\r\n",
        )
        for headers in variants:
            with self.subTest(headers=headers):
                status, _response, seen = await self.run_request(req(headers=headers))
                self.assertEqual(status, 403)
                self.assertFalse(seen)

    async def test_http_request_smuggling_and_oversize_rejected(self):
        cases = (
            (req(headers=BASE + b"Transfer-Encoding: chunked\r\n"), 400),
            (req(headers=BASE + b"Expect: 100-continue\r\n"), 400),
            (req(headers=BASE + b"Content-Length: 262145\r\n"), 413),
            (req(headers=BASE + b"Content-Length: 1\r\nContent-Length: 1\r\n", body=b"a"), 400),
            (req(headers=BASE + b"Content-Length: 0\r\n", body=b"pipelined"), 400),
            (req(path=b"http://evil.example/"), 400),
            (req(path=b"/api/%2e%2e/"), 400),
            (req(headers=BASE + b"X-Note: " + b"a"*9000 + b"\r\n"), 400),
            (req(headers=BASE + b"X-Note: safe\r\n evil: fold\r\n"), 400),
        )
        for payload, expected in cases:
            with self.subTest(expected=expected, length=len(payload)):
                status, response, seen = await self.run_request(payload)
                self.assertEqual(status, expected)
                self.assertFalse(seen)
                self.assertIn(b"Cache-Control: no-store", response)

    async def test_private_input_not_reflected_in_http_rejection(self):
        secret = b"PRIVATE-SESSION-TOKEN-X"
        status, response, seen = await self.run_request(
            req(headers=BASE + b"X-Real-IP: " + secret + b"\r\n")
        )
        self.assertEqual(status, 403)
        self.assertNotIn(secret, response)
        self.assertFalse(seen)

    async def test_untrusted_asgi_bad_response_is_503_and_not_reflected(self):
        async def bad_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"set-cookie", b"not-allowed")]})
            await send({"type": "http.response.body", "body": b"secret", "more_body": False})

        status, response, _ = await self.run_request(req(), app=bad_app)
        self.assertEqual(status, 503)
        self.assertNotIn(b"secret", response)
        self.assertNotIn(b"not-allowed", response)


if __name__ == "__main__":
    unittest.main()
