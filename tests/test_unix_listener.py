"""Real local bounded Unix listener tests; never touch shared or public hosts."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import socket
import stat
import sys
import tempfile
import unittest

from marketplace.application.attested_caddy_edge import MarketplaceAttestedCaddyEdgeAsgiAdapter
from marketplace.application.canonical_origin_guard import (
    CANONICAL_HOST, CANONICAL_ORIGIN, MarketplaceCanonicalOriginAsgiGuard,
)
from marketplace.application.linux_unix_caddy_peer import MarketplaceLinuxUnixCaddyPeerVerifier
from marketplace.application.unix_listener import (
    EXACT_FOREGROUND_OPT_IN, serve_bounded_marketplace_unix_foreground,
)


RUN_LINUX = (
    sys.platform.startswith("linux") and hasattr(socket, "SO_PEERCRED")
    and hasattr(os, "geteuid") and 0 < os.geteuid()
    and 0 < os.getegid()
)

HOST = b"Host: marketplace.open-trust-layer.org\r\n"
FORWARD = (b"X-Forwarded-Host: marketplace.open-trust-layer.org\r\n"
           b"X-Forwarded-Proto: https\r\n"
           b"X-Forwarded-For: 198.51.100.1\r\n")
ORIGIN = b"Origin: https://marketplace.open-trust-layer.org\r\n"


def request(*, method=b"GET", host=HOST, origin=b""):
    return (method + b" /api/agreements HTTP/1.1\r\n"
            + host + FORWARD + origin + b"\r\n")


@unittest.skipUnless(RUN_LINUX, "non-root Linux AF_UNIX verification required")
class BoundedUnixListenerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="marketplace-bounded-listener-")
        self.addCleanup(self.tmp.cleanup)
        self.directory = self.tmp.name
        self.path = self.directory + "/marketplace-edge.sock"
        self.events = []

        async def app(scope, receive, send):
            self.events.append(scope)
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": b"READY",
                        "more_body": False})

        self.app = app

    def edge(self, *, wrong_uid=False):
        verifier = MarketplaceLinuxUnixCaddyPeerVerifier(
            socket_path=self.path,
            caddy_uid=os.geteuid() + int(wrong_uid),
            caddy_gid=os.getegid(),
        )
        return MarketplaceAttestedCaddyEdgeAsgiAdapter(
            guard=MarketplaceCanonicalOriginAsgiGuard(app=self.app),
            verifier=verifier,
        )

    async def send_one(self, raw):
        loop = asyncio.get_running_loop()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.setblocking(False)
            for _ in range(500):
                try:
                    await loop.sock_connect(client, self.path)
                    break
                except (FileNotFoundError, ConnectionRefusedError):
                    await asyncio.sleep(0.002)
            else:
                self.fail("local test listener did not bind")
            try:
                await loop.sock_sendall(client, raw)
            except (ConnectionResetError, BrokenPipeError):
                pass
            result = bytearray()
            while True:
                try:
                    chunk = await asyncio.wait_for(loop.sock_recv(client, 4096), 3)
                except ConnectionResetError:
                    break
                if not chunk:
                    break
                result.extend(chunk)
            return bytes(result)

    async def test_two_real_requests_then_exact_inode_socket_removed(self):
        task = asyncio.create_task(serve_bounded_marketplace_unix_foreground(
            directory=self.directory,
            edge=self.edge(),
            execute_token=EXACT_FOREGROUND_OPT_IN,
            max_accepts=2,
            max_concurrent=2,
            max_lifetime=7,
        ))
        first, second = await asyncio.gather(
            self.send_one(request()), self.send_one(request(method=b"POST", origin=ORIGIN))
        )
        result = await asyncio.wait_for(task, 9)
        self.assertEqual(result, (200, 200))
        self.assertTrue(first.endswith(b"\r\n\r\nREADY"))
        self.assertTrue(second.endswith(b"\r\n\r\nREADY"))
        self.assertEqual(len(self.events), 2)
        self.assertFalse(os.path.lexists(self.path))
        self.assertTrue(all(s["scheme"] == "https" for s in self.events))

    async def test_unsafe_cross_origin_denied_and_does_not_enter_app(self):
        task = asyncio.create_task(serve_bounded_marketplace_unix_foreground(
            directory=self.directory, edge=self.edge(),
            execute_token=EXACT_FOREGROUND_OPT_IN, max_accepts=1,
        ))
        result = await self.send_one(request(method=b"POST"))
        scores = await asyncio.wait_for(task, 9)
        self.assertEqual(scores, (403,))
        self.assertIn(b"ORIGIN_REQUIRED", result)
        self.assertEqual(self.events, [])
        self.assertFalse(os.path.lexists(self.path))

    async def test_kernel_rejects_wrong_uid_with_correct_headers(self):
        task = asyncio.create_task(serve_bounded_marketplace_unix_foreground(
            directory=self.directory, edge=self.edge(wrong_uid=True),
            execute_token=EXACT_FOREGROUND_OPT_IN, max_accepts=1,
        ))
        await self.send_one(request())
        scores = await asyncio.wait_for(task, 9)
        self.assertEqual(scores, (403,))
        self.assertFalse(self.events)

    async def test_missing_authorization_no_socket_or_side_effect(self):
        with self.assertRaises(PermissionError):
            await serve_bounded_marketplace_unix_foreground(
                directory=self.directory, edge=self.edge(),
                execute_token="invalid-secret",
            )
        self.assertFalse(os.path.lexists(self.path))

    async def test_existing_socket_path_never_unlinked_or_replaced(self):
        with open(self.path, "wb") as stream:
            stream.write(b"KEEP")
        inode = os.lstat(self.path).st_ino
        with self.assertRaises(FileExistsError):
            await serve_bounded_marketplace_unix_foreground(
                directory=self.directory, edge=self.edge(),
                execute_token=EXACT_FOREGROUND_OPT_IN,
            )
        self.assertEqual(Path(self.path).read_bytes(), b"KEEP")
        self.assertEqual(os.lstat(self.path).st_ino, inode)

    async def test_world_accessible_dir_refused(self):
        os.chmod(self.directory, 0o777)
        with self.assertRaises(PermissionError):
            await serve_bounded_marketplace_unix_foreground(
                directory=self.directory, edge=self.edge(),
                execute_token=EXACT_FOREGROUND_OPT_IN,
            )
        self.assertFalse(os.path.lexists(self.path))

    async def test_bad_limits_no_socket_created(self):
        for options in (
            {"max_accepts": 0}, {"max_accepts": 17}, {"max_concurrent": 0},
            {"max_concurrent": 3}, {"max_lifetime": 0},
            {"max_lifetime": 21}, {"max_lifetime": True},
        ):
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    await serve_bounded_marketplace_unix_foreground(
                        directory=self.directory, edge=self.edge(),
                        execute_token=EXACT_FOREGROUND_OPT_IN, **options,
                    )
                self.assertFalse(os.path.lexists(self.path))

    async def test_no_connections_times_out_and_cleans_up(self):
        finished = await asyncio.wait_for(
            serve_bounded_marketplace_unix_foreground(
                directory=self.directory, edge=self.edge(),
                execute_token=EXACT_FOREGROUND_OPT_IN,
                max_accepts=1, max_lifetime=1,
            ),
            timeout=3,
        )
        self.assertEqual(finished, ())
        self.assertFalse(os.path.lexists(self.path))


if __name__ == "__main__":
    unittest.main()
