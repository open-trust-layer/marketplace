"""Linux kernel-backed Unix transport peer verifier for a future private edge.

An ASGI server must supply the *actual accepted Unix socket object* under the
reserved in-process scope key. HTTP headers, remote IP, and user input cannot
create this object. This module has no socket/listener/startup side effects.
"""
from __future__ import annotations

import socket
import struct
import sys
from typing import Any, Final


ACCEPTED_UNIX_SOCKET_SCOPE_KEY: Final = "marketplace.internal.accepted_unix_socket"
_UCRED_SIZE: Final = struct.calcsize("=3i")
_MAX_UNIX_PATH_BYTES: Final = 107


def _review_socket_path(value: object) -> str:
    if (
        type(value) is not str
        or not value.startswith("/")
        or value.startswith("//")
        or value.endswith("/")
        or any(ord(c) < 33 or ord(c) == 127 for c in value)
        or any(part in ("", ".", "..") for part in value.split("/")[1:])
    ):
        raise ValueError("UNIX_PEER_SOCKET_PATH_INVALID")
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeError:
        raise ValueError("UNIX_PEER_SOCKET_PATH_INVALID") from None
    if len(encoded) > _MAX_UNIX_PATH_BYTES:
        raise ValueError("UNIX_PEER_SOCKET_PATH_INVALID")
    return value


def _review_nonroot_id(value: object) -> int:
    if type(value) is not int or value <= 0 or value > 2147483647:
        raise ValueError("UNIX_PEER_ID_INVALID")
    return value


class MarketplaceLinuxUnixCaddyPeerVerifier:
    """Check a real accepted AF_UNIX stream's local path and SO_PEERCRED.

    A future source-reviewed HTTP server must attach the accepted socket
    directly to trusted in-process ASGI scope. This code does not offer
    a server, file descriptor passing, Caddy setup or socket-permission policy.
    """

    __slots__ = ("_socket_path", "_uid", "_gid")

    def __init__(self, *, socket_path: str, caddy_uid: int, caddy_gid: int) -> None:
        self._socket_path = _review_socket_path(socket_path)
        self._uid = _review_nonroot_id(caddy_uid)
        self._gid = _review_nonroot_id(caddy_gid)

    def verify_connection(self, scope: dict[str, Any]) -> bool:
        if (
            not sys.platform.startswith("linux")
            or not hasattr(socket, "SO_PEERCRED")
            or type(scope) is not dict
        ):
            return False
        peer = scope.get(ACCEPTED_UNIX_SOCKET_SCOPE_KEY)
        if (
            type(peer) is not socket.socket
            or peer.family != socket.AF_UNIX
            or peer.type != socket.SOCK_STREAM
            or peer.fileno() < 0
        ):
            return False
        try:
            if peer.getsockname() != self._socket_path:
                return False
            # An accepted/connected socket, not merely a listening socket.
            peer.getpeername()
            raw = peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, _UCRED_SIZE)
            if type(raw) is not bytes or len(raw) != _UCRED_SIZE:
                return False
            pid, uid, gid = struct.unpack("=3i", raw)
            return pid > 0 and uid == self._uid and gid == self._gid
        except (OSError, ValueError, TypeError, struct.error):
            return False


__all__ = [
    "ACCEPTED_UNIX_SOCKET_SCOPE_KEY",
    "MarketplaceLinuxUnixCaddyPeerVerifier",
]
