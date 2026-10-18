"""Opt-in real HTTPS Caddy under a separate Linux UID from attested backend.

The caller must enter a new unprivileged *subordinate-ID* user namespace and
supply a previously checksum-verified Caddy binary. Nothing executes on import
or by normal CI discovery, and no global Caddy, VPS or DNS state is touched.
"""
from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from tests.test_marketplace_caddy_unix_interop import (
    CANONICAL_HOST,
    _create_test_certificate,
    _get_free_local_port,
    _test_caddyfile,
    _tls_request,
)
from tests.test_unix_distinct_peer_userns import (
    BACKEND_GID,
    BACKEND_UID,
    CADDY_GID,
    CADDY_UID,
    FOREIGN_GID,
    FOREIGN_UID,
    SAME_GROUP_UNTRUSTED_UID,
    _drop_to,
    _isolated_subordinate_id_mapping,
)

OPT_IN = "RUN_MARKETPLACE_REAL_CADDY_DISTINCT_USERNS_V1"
BIN_ENV = "MARKETPLACE_CADDY_INTEROP_BIN"
CAN_RUN = (
    sys.platform.startswith("linux")
    and hasattr(socket, "SO_PEERCRED")
    and os.environ.get("MARKETPLACE_CADDY_DISTINCT_USERNS_TEST") == OPT_IN
    and os.geteuid() == 0
    and os.getegid() == 0
    and _isolated_subordinate_id_mapping()
    and bool(os.environ.get(BIN_ENV))
)
REAL_HTTPS_GET = (
    b"GET /api/agreements HTTP/1.1\r\n"
    b"Host: marketplace.open-trust-layer.org\r\n"
    b"X-Forwarded-Proto: http\r\n"
    b"X-Forwarded-Host: attacker.example\r\n"
    b"Connection: close\r\n\r\n"
)


def _subprocess_environment(root: Path) -> dict[str, str]:
    result = dict(os.environ)
    result["HOME"] = str(root / "caddy-home")
    result["XDG_CONFIG_HOME"] = str(root / "caddy-home" / "config")
    result["XDG_DATA_HOME"] = str(root / "caddy-home" / "data")
    return result


@unittest.skipUnless(
    CAN_RUN, "Requires explicit opt-in, verified Caddy and subordinate-ID Linux namespace"
)
class RealCaddyDistinctUidUnixTests(unittest.TestCase):
    def test_real_caddy_https_to_other_uid_kernel_attested_asgi(self) -> None:
        binary = Path(os.environ[BIN_ENV])
        self.assertTrue(binary.is_absolute() and binary.is_file())
        self.assertTrue(os.access(binary, os.X_OK))
        with tempfile.TemporaryDirectory(prefix="mkt-caddy-distinct-userns-") as temp:
            root = Path(temp)
            path = root / "marketplace-edge.sock"
            self.assertLessEqual(len(os.fsencode(str(path))), 107)
            port = _get_free_local_port()
            cert, key = _create_test_certificate(root)
            config = root / "Caddyfile"
            config.write_text(_test_caddyfile(root, port, cert, key), encoding="utf-8")
            home = root / "caddy-home"
            home.mkdir(mode=0o700)
            for file in (cert, key, config):
                os.chown(file, CADDY_UID, CADDY_GID)
                os.chmod(file, 0o600)
            os.chown(home, CADDY_UID, CADDY_GID)
            os.chmod(home, 0o700)
            # Every other UID is prevented from traversing the private path.
            # Only the Caddy GID may traverse and connect; the verifier
            # independently checks the *exact Caddy UID and GID*.
            os.chown(root, BACKEND_UID, CADDY_GID)
            os.chmod(root, 0o2750)
            self.assertEqual(root.stat().st_uid, BACKEND_UID)
            self.assertEqual(root.stat().st_gid, CADDY_GID)

            env = _subprocess_environment(root)
            backend_script = str(
                Path(__file__).with_name("test_unix_distinct_peer_userns.py")
            )
            backend: subprocess.Popen[str] | None = None
            caddy: subprocess.Popen[str] | None = None
            try:
                # Assert Caddyfile adaptation under the actual Caddy-like UID.
                adapted = subprocess.run(
                    [str(binary), "adapt", "--config", str(config),
                     "--adapter", "caddyfile"],
                    preexec_fn=_drop_to(CADDY_UID, CADDY_GID),
                    cwd=root, env=env, capture_output=True,
                    text=True, timeout=10,
                )
                self.assertEqual(
                    adapted.returncode, 0,
                    adapted.stderr[-1500:],
                )

                backend = subprocess.Popen(
                    [sys.executable, backend_script, "--server", str(path)],
                    preexec_fn=_drop_to(BACKEND_UID, BACKEND_GID),
                    env=env, cwd=root, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True,
                )
                for _ in range(160):
                    if backend.poll() is not None:
                        break
                    if os.path.lexists(path):
                        break
                    time.sleep(0.025)
                self.assertTrue(os.path.lexists(path), "isolated backend did not bind")
                self.assertEqual(path.stat().st_uid, BACKEND_UID)
                self.assertEqual(path.stat().st_gid, CADDY_GID)
                self.assertEqual(path.stat().st_mode & 0o777, 0o660)

                def client(uid: int, gid: int, scenario: str) -> str:
                    child = subprocess.run(
                        [sys.executable, backend_script, "--client", str(path),
                         scenario],
                        preexec_fn=_drop_to(uid, gid),
                        env=env, cwd=root,
                        capture_output=True, text=True, timeout=6,
                    )
                    self.assertEqual(child.returncode, 0, child.stderr[-1500:])
                    return child.stdout.strip()

                self.assertEqual(
                    client(FOREIGN_UID, FOREIGN_GID, "filesystem_denied"),
                    "UNAUTHORIZED_FILESYSTEM_DENIED",
                )
                self.assertEqual(
                    client(SAME_GROUP_UNTRUSTED_UID, CADDY_GID, "kernel_denied"),
                    "UNTRUSTED_SAME_GROUP_KERNEL_DENIED",
                )

                caddy = subprocess.Popen(
                    [str(binary), "run", "--config", str(config),
                     "--adapter", "caddyfile"],
                    preexec_fn=_drop_to(CADDY_UID, CADDY_GID),
                    env=env, cwd=root,
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    text=True,
                )
                self.assertEqual(
                    Path(f"/proc/{caddy.pid}").stat().st_uid,
                    CADDY_UID,
                )
                response: bytes | None = None
                for _ in range(80):
                    if caddy.poll() is not None:
                        self.fail("real separate-UID Caddy stopped before HTTPS request")
                    try:
                        response = _tls_request(port, cert, REAL_HTTPS_GET)
                        break
                    except OSError:
                        time.sleep(0.05)
                self.assertIsNotNone(response, "Caddy local-only HTTPS unavailable")
                assert response is not None
                self.assertTrue(
                    response.startswith(b"HTTP/1.1 200 ") or
                    response.startswith(b"HTTP/2 200 "),
                    response[:500],
                )
                self.assertIn(b"OK", response, response[-500:])
                stdout, stderr = backend.communicate(timeout=7)
                self.assertEqual(backend.returncode, 0, stderr[-1800:])
                self.assertIn("BACKEND_ATTESTED_RESULTS=200,403", stdout)
                self.assertFalse(os.path.lexists(path))
            finally:
                if caddy is not None:
                    caddy.terminate()
                    try:
                        caddy.communicate(timeout=4)
                    except subprocess.TimeoutExpired:
                        caddy.kill()
                        caddy.communicate(timeout=4)
                if backend is not None:
                    if backend.poll() is None:
                        backend.kill()
                    backend.communicate(timeout=4)


if __name__ == "__main__":
    unittest.main()
