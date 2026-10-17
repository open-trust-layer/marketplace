"""Real Linux AF_UNIX/SO_PEERCRED and ASGI boundary tests, no VPS access."""
from __future__ import annotations

import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path

from marketplace.application.linux_unix_caddy_peer import (
    ACCEPTED_UNIX_SOCKET_SCOPE_KEY,
    MarketplaceLinuxUnixCaddyPeerVerifier,
)
from marketplace.application.attested_caddy_edge import (
    MarketplaceAttestedCaddyEdgeAsgiAdapter,
)
from marketplace.application.canonical_origin_guard import (
    CANONICAL_HOST,
    CANONICAL_ORIGIN,
    MarketplaceCanonicalOriginAsgiGuard,
)


def _scope(peer=None, *, method="GET", origin=None):
    headers = [
        (b"host", CANONICAL_HOST),
        (b"x-forwarded-host", CANONICAL_HOST),
        (b"x-forwarded-proto", b"https"),
        (b"x-forwarded-for", b"203.0.113.6"),
    ]
    if origin is not None:
        headers.append((b"origin", origin))
    value = {
        "type": "http", "asgi": {"version": "3.0"},
        "http_version": "1.1", "scheme": "http",
        "root_path": "", "method": method, "path": "/api/agreements",
        "headers": headers,
        "client": ("127.0.0.1", 9876),
    }
    if peer is not None:
        value[ACCEPTED_UNIX_SOCKET_SCOPE_KEY] = peer
    return value


class UnixCaddyPeerValidationTests(unittest.TestCase):
    def test_configuration_requires_exact_nonroot_uid_gid_and_absolute_path(self):
        for kw in (
            {"socket_path": "", "caddy_uid": 1000, "caddy_gid": 1000},
            {"socket_path": "relative.sock", "caddy_uid": 1000, "caddy_gid": 1000},
            {"socket_path": "/tmp/../run/socket", "caddy_uid": 1000, "caddy_gid": 1000},
            {"socket_path": "//run/marketplace/socket", "caddy_uid": 1000, "caddy_gid": 1000},
            {"socket_path": "/run/marketplace//socket", "caddy_uid": 1000, "caddy_gid": 1000},
            {"socket_path": "/run/marketplace/socket\0", "caddy_uid": 1000, "caddy_gid": 1000},
            {"socket_path": "/run/marketplace/socket", "caddy_uid": 0, "caddy_gid": 1000},
            {"socket_path": "/run/marketplace/socket", "caddy_uid": 1000, "caddy_gid": 0},
            {"socket_path": "/run/marketplace/socket", "caddy_uid": True, "caddy_gid": 1000},
            {"socket_path": "/run/marketplace/socket", "caddy_uid": 1000, "caddy_gid": 2**31},
        ):
            with self.subTest(kw=kw):
                with self.assertRaises(ValueError):
                    MarketplaceLinuxUnixCaddyPeerVerifier(**kw)

    def test_request_headers_and_loopback_scope_cannot_impersonate_peer_socket(self):
        verifier = MarketplaceLinuxUnixCaddyPeerVerifier(
            socket_path="/run/marketplace/private/edge.sock",
            caddy_uid=1000, caddy_gid=1000,
        )
        for data in (
            _scope(),
            {**_scope(), "headers": _scope()["headers"] +
             [(b"marketplace.internal.accepted_unix_socket", b"attested")]},
            _scope(peer=object()),
            _scope(peer="socket-secret-string"),
            _scope(peer=123),
        ):
            with self.subTest(scope=data):
                self.assertIs(verifier.verify_connection(data), False)


_LINUX_NONROOT = (
    sys.platform.startswith("linux")
    and hasattr(socket, "SO_PEERCRED")
    and hasattr(os, "geteuid")
    and os.geteuid() > 0
    and os.getegid() > 0
)


@unittest.skipUnless(_LINUX_NONROOT, "Linux nonroot peer credentials required")
class RealLinuxUnixCaddyPeerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="mkt-unix-peer-")
        self.addCleanup(self.directory.cleanup)
        self.socket_path = str(Path(self.directory.name) / "edge.sock")
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(self.listener.close)
        self.listener.bind(self.socket_path)
        self.listener.listen(1)
        self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(self.client.close)
        self.client.connect(self.socket_path)
        self.accepted, _ = self.listener.accept()
        self.addCleanup(self.accepted.close)
        self.verifier = MarketplaceLinuxUnixCaddyPeerVerifier(
            socket_path=self.socket_path,
            caddy_uid=os.geteuid(),
            caddy_gid=os.getegid(),
        )

    def test_real_accepted_peer_uses_kernel_credentials(self):
        self.assertIs(self.verifier.verify_connection(_scope(self.accepted)), True)

    def test_uid_and_gid_mismatch_rejected_by_actual_os_peer_identity(self):
        other_uid = os.geteuid() + 1
        other_gid = os.getegid() + 1
        self.assertFalse(MarketplaceLinuxUnixCaddyPeerVerifier(
            socket_path=self.socket_path, caddy_uid=other_uid,
            caddy_gid=os.getegid(),
        ).verify_connection(_scope(self.accepted)))
        self.assertFalse(MarketplaceLinuxUnixCaddyPeerVerifier(
            socket_path=self.socket_path, caddy_uid=os.geteuid(),
            caddy_gid=other_gid,
        ).verify_connection(_scope(self.accepted)))

    def test_wrong_accepted_listener_path_denied(self):
        verifier = MarketplaceLinuxUnixCaddyPeerVerifier(
            socket_path=str(Path(self.directory.name) / "other.sock"),
            caddy_uid=os.geteuid(), caddy_gid=os.getegid(),
        )
        self.assertFalse(verifier.verify_connection(_scope(self.accepted)))

    def test_listener_and_client_sockets_do_not_count_as_accepted_peer(self):
        self.assertFalse(self.verifier.verify_connection(_scope(self.listener)))
        self.assertFalse(self.verifier.verify_connection(_scope(self.client)))

    def test_closed_peer_socket_denied(self):
        self.accepted.close()
        self.assertFalse(self.verifier.verify_connection(_scope(self.accepted)))

    async def test_real_peer_composes_with_edge_and_does_not_leak_socket(self):
        invoked = []
        sent = []

        async def app(scope, receive, send):
            invoked.append(scope)
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b"", "more_body": False})

        async def receive():
            self.fail("body receive must not happen in this test")

        async def send(event):
            sent.append(event)

        edge = MarketplaceAttestedCaddyEdgeAsgiAdapter(
            guard=MarketplaceCanonicalOriginAsgiGuard(app=app),
            verifier=self.verifier,
        )
        original = _scope(self.accepted, method="POST", origin=CANONICAL_ORIGIN)
        await edge(original, receive, send)
        self.assertEqual(sent[0]["status"], 204)
        self.assertEqual(len(invoked), 1)
        self.assertNotIn(ACCEPTED_UNIX_SOCKET_SCOPE_KEY, invoked[0])
        self.assertNotIn(b"x-forwarded-for", [name for name, _ in invoked[0]["headers"]])
        self.assertEqual(invoked[0]["scheme"], "https")
        self.assertIs(original[ACCEPTED_UNIX_SOCKET_SCOPE_KEY], self.accepted)


if __name__ == "__main__":
    unittest.main()
