"""Opt-in independent Linux UID/GID Unix-edge integration via user namespace.

Never runs in standard CI. Requires an externally created subordinate-ID user
namespace; the test never invokes sudo, chown on pre-existing directories,
Docker or the real VPS. Only own temporary files/processes are affected.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from marketplace.application.attested_caddy_edge import MarketplaceAttestedCaddyEdgeAsgiAdapter
from marketplace.application.canonical_origin_guard import MarketplaceCanonicalOriginAsgiGuard
from marketplace.application.linux_unix_caddy_peer import MarketplaceLinuxUnixCaddyPeerVerifier
from marketplace.application.unix_listener import (
    EXACT_FOREGROUND_OPT_IN,
    serve_bounded_marketplace_unix_foreground,
)

BACKEND_UID = 1101
BACKEND_GID = 1101
CADDY_UID = 2101
CADDY_GID = 2101
FOREIGN_UID = 3101
FOREIGN_GID = 3101
SAME_GROUP_UNTRUSTED_UID = 2102
OPT_IN = "RUN_MARKETPLACE_DISTINCT_UNIX_USERNS_V1"
REQUEST = (
    b"GET /api/agreements HTTP/1.1\r\n"
    b"Host: marketplace.open-trust-layer.org\r\n"
    b"X-Forwarded-Host: marketplace.open-trust-layer.org\r\n"
    b"X-Forwarded-Proto: https\r\n"
    b"X-Forwarded-For: 198.51.100.55\r\n"
    b"\r\n"
)
CAN_RUN = (
    sys.platform.startswith("linux")
    and hasattr(socket, "SO_PEERCRED")
    and os.environ.get("MARKETPLACE_DISTINCT_USERNS_TEST") == OPT_IN
    and os.geteuid() == 0
    and os.getegid() == 0
)


def _drop_to(uid: int, gid: int):
    """Execute in a freshly forked child of a disposable user namespace."""
    def drop():
        os.setgroups([])
        os.setgid(gid)
        os.setuid(uid)
    return drop


async def _serve_private_socket(path: str) -> None:
    scopes: list[dict] = []

    async def app(scope, receive, send):
        scopes.append(scope)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK", "more_body": False})

    verifier = MarketplaceLinuxUnixCaddyPeerVerifier(
        socket_path=path, caddy_uid=CADDY_UID, caddy_gid=CADDY_GID,
    )
    edge = MarketplaceAttestedCaddyEdgeAsgiAdapter(
        guard=MarketplaceCanonicalOriginAsgiGuard(app=app),
        verifier=verifier,
    )
    results = await serve_bounded_marketplace_unix_foreground(
        directory=str(Path(path).parent),
        edge=edge,
        execute_token=EXACT_FOREGROUND_OPT_IN,
        max_accepts=2,
        max_concurrent=2,
        max_lifetime=12,
    )
    if sorted(results) != [200, 403] or len(scopes) != 1:
        raise AssertionError("private peer results or application count mismatch")
    print("BACKEND_ATTESTED_RESULTS=200,403", flush=True)


def _client(path: str, *, expected: str) -> int:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(3)
        for attempt in range(40):
            try:
                connection.connect(path)
                break
            except ConnectionRefusedError:
                if attempt == 39:
                    raise
                time.sleep(0.025)
            except PermissionError:
                if expected != "filesystem_denied":
                    raise
                print("UNAUTHORIZED_FILESYSTEM_DENIED", flush=True)
                return 0
        if expected == "filesystem_denied":
            raise AssertionError("unauthorized local process connected to private Unix socket")
        try:
            connection.sendall(REQUEST)
            data = bytearray()
            while True:
                piece = connection.recv(4096)
                if not piece:
                    break
                data.extend(piece)
        except ConnectionResetError:
            data = bytearray()
        if expected == "kernel_denied":
            if data and not data.startswith(b"HTTP/1.1 403 "):
                raise AssertionError("wrong UID was accepted by the attested backend")
            print("UNTRUSTED_SAME_GROUP_KERNEL_DENIED", flush=True)
            return 0
        if not data.startswith(b"HTTP/1.1 200 "):
            raise AssertionError("authorized Caddy identity did not pass Unix->ASGI: " + repr(bytes(data[:140])))
        print("CADDY_DISTINCT_UID_AUTHORIZED", flush=True)
        return 0


@unittest.skipUnless(CAN_RUN, "Requires opt-in subordinate-ID Linux user namespace")
class DistinctLinuxUnixPeerIdentityTests(unittest.TestCase):
    def test_private_directory_and_kernel_uid_are_both_enforced(self):
        # The outer test only chowns its OWN freshly created disposable path.
        with tempfile.TemporaryDirectory(prefix="mkt-uid-isolation-") as directory:
            os.chown(directory, BACKEND_UID, CADDY_GID)
            os.chmod(directory, 0o2750)  # Caddy group can traverse; world cannot.
            path = str(Path(directory) / "marketplace-edge.sock")
            if len(os.fsencode(path)) > 107:
                self.skipTest("temporary Unix socket path exceeds Linux sockaddr bound")
            executable = sys.executable
            module_path = str(Path(__file__).resolve())
            base_env = dict(os.environ)
            child_server = subprocess.Popen(
                [executable, module_path, "--server", path],
                preexec_fn=_drop_to(BACKEND_UID, BACKEND_GID),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=base_env,
            )
            try:
                for attempt in range(200):
                    if child_server.poll() is not None:
                        break
                    if os.path.lexists(path):
                        break
                    time.sleep(0.02)
                self.assertTrue(os.path.lexists(path), "isolated backend did not bind")
                socket_info = os.stat(path)
                self.assertEqual(socket_info.st_uid, BACKEND_UID)
                self.assertEqual(socket_info.st_gid, CADDY_GID)
                self.assertEqual(socket_info.st_mode & 0o777, 0o660)

                def run_client(uid, gid, scenario):
                    response = subprocess.run(
                        [executable, module_path, "--client", path, scenario],
                        preexec_fn=_drop_to(uid, gid),
                        capture_output=True, text=True, timeout=6, env=base_env,
                    )
                    self.assertEqual(response.returncode, 0, response.stderr[-1200:])
                    return response.stdout.strip()

                # OS cannot traverse private group-owned path for an unrelated UID.
                self.assertEqual(
                    run_client(FOREIGN_UID, FOREIGN_GID, "filesystem_denied"),
                    "UNAUTHORIZED_FILESYSTEM_DENIED",
                )
                # Can traverse/connect by group, yet kernel peer UID is wrong.
                self.assertEqual(
                    run_client(SAME_GROUP_UNTRUSTED_UID, CADDY_GID, "kernel_denied"),
                    "UNTRUSTED_SAME_GROUP_KERNEL_DENIED",
                )
                # Exact separate Caddy service identity is authorized.
                self.assertEqual(
                    run_client(CADDY_UID, CADDY_GID, "authorized"),
                    "CADDY_DISTINCT_UID_AUTHORIZED",
                )
                stdout, stderr = child_server.communicate(timeout=7)
                self.assertEqual(child_server.returncode, 0, stderr[-1600:])
                self.assertIn("BACKEND_ATTESTED_RESULTS=200,403", stdout)
                self.assertFalse(os.path.lexists(path), "source listener left socket after exit")
            finally:
                if child_server.poll() is None:
                    child_server.kill()
                child_server.communicate(timeout=4)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--server":
        asyncio.run(_serve_private_socket(sys.argv[2]))
    elif len(sys.argv) == 4 and sys.argv[1] == "--client":
        raise SystemExit(_client(sys.argv[2], expected=sys.argv[3]))
    else:
        raise SystemExit("RUN_ONLY_UNDER_ISOLATED_USER_NAMESPACE")
