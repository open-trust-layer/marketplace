"""Explicit bounded Unix listener for an already reviewed Marketplace ASGI edge.

No service, process, path, socket, network or customer data is created on
import or construction. A caller must opt into a short foreground session.
Not a production daemon, public interface, or VPS deployment capability.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import socket
import stat
from typing import Final

from .attested_caddy_edge import MarketplaceAttestedCaddyEdgeAsgiAdapter
from .linux_unix_caddy_peer import MarketplaceLinuxUnixCaddyPeerVerifier
from .unix_http11_asgi import serve_one_attested_unix_http11


EXACT_FOREGROUND_OPT_IN: Final = "EXECUTE_BOUNDED_MARKETPLACE_UNIX_EDGE_FOREGROUND_V1"
MAX_ACCEPTS: Final = 16
MAX_CONCURRENT_CONNECTIONS: Final = 2
MAX_LIFETIME_SECONDS: Final = 20
LISTENER_SOCKET_MODE: Final = 0o660
LISTENER_BACKLOG: Final = 4


def _review_execution(*, directory: str, edge: object, execute_token: object) -> str:
    if type(execute_token) is not str or execute_token != EXACT_FOREGROUND_OPT_IN:
        raise PermissionError("UNIX_EDGE_EXECUTION_NOT_AUTHORIZED")
    if not hasattr(os, "geteuid") or os.geteuid() == 0:
        raise PermissionError("UNIX_EDGE_ROOT_EXECUTION_FORBIDDEN")
    if type(edge) is not MarketplaceAttestedCaddyEdgeAsgiAdapter:
        raise TypeError("UNIX_EDGE_ADAPTER_INVALID")
    verifier = edge._verifier
    if type(verifier) is not MarketplaceLinuxUnixCaddyPeerVerifier:
        raise TypeError("UNIX_EDGE_VERIFIER_INVALID")
    if type(directory) is not str or not directory.startswith("/") or directory.startswith("//"):
        raise ValueError("UNIX_EDGE_DIRECTORY_INVALID")
    path = Path(directory)
    if str(path) != directory or any(p in (".", "..") for p in directory.split("/")):
        raise ValueError("UNIX_EDGE_DIRECTORY_INVALID")
    try:
        info = os.lstat(directory)
        resolved = os.path.realpath(directory)
    except OSError:
        raise ValueError("UNIX_EDGE_DIRECTORY_UNAVAILABLE") from None
    if (
        not stat.S_ISDIR(info.st_mode)
        or resolved != directory
        or info.st_uid != os.geteuid()
        or (stat.S_IMODE(info.st_mode) & 0o027) != 0
    ):
        # Reject symlink, nonowner, group-writable or world-accessible directories.
        raise PermissionError("UNIX_EDGE_DIRECTORY_NOT_PRIVATE")
    socket_path = directory + "/marketplace-edge.sock"
    if len(os.fsencode(socket_path)) > 107 or socket_path != verifier._socket_path:
        raise ValueError("UNIX_EDGE_PATH_BINDING_INVALID")
    if os.path.lexists(socket_path):
        # Never unlink another process's socket, file or symlink.
        raise FileExistsError("UNIX_EDGE_SOCKET_ALREADY_EXISTS")
    return socket_path


def _review_limits(*, max_accepts: object, max_concurrent: object, max_lifetime: object) -> None:
    if (
        type(max_accepts) is not int or not 1 <= max_accepts <= MAX_ACCEPTS
        or type(max_concurrent) is not int
        or not 1 <= max_concurrent <= MAX_CONCURRENT_CONNECTIONS
        or type(max_lifetime) is not int or not 1 <= max_lifetime <= MAX_LIFETIME_SECONDS
    ):
        raise ValueError("UNIX_EDGE_LIMIT_INVALID")


async def serve_bounded_marketplace_unix_foreground(
    *,
    directory: str,
    edge: MarketplaceAttestedCaddyEdgeAsgiAdapter,
    execute_token: str,
    max_accepts: int = 4,
    max_concurrent: int = 2,
    max_lifetime: int = 12,
) -> tuple[int, ...]:
    """Serve a capped number of already accepted Unix connections, then stop.

    The caller owns the process and foreground lifetime. The listener binds
    only inside a pre-created private directory and never replaces a path.
    """
    socket_path = _review_execution(
        directory=directory, edge=edge, execute_token=execute_token,
    )
    _review_limits(
        max_accepts=max_accepts,
        max_concurrent=max_concurrent,
        max_lifetime=max_lifetime,
    )
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    bound_inode: int | None = None
    tasks: set[asyncio.Task[int]] = set()
    accepted_count = 0
    results: list[int] = []
    try:
        server.bind(socket_path)
        bound_inode = os.lstat(socket_path).st_ino
        os.chmod(socket_path, LISTENER_SOCKET_MODE)
        server.listen(LISTENER_BACKLOG)
        server.setblocking(False)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + max_lifetime

        while accepted_count < max_accepts and loop.time() < deadline:
            if len(tasks) >= max_concurrent:
                completed, tasks = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED,
                )
                results.extend(int(task.result()) for task in completed)
                continue
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                client, _ = await asyncio.wait_for(
                    loop.sock_accept(server), timeout=remaining,
                )
            except asyncio.TimeoutError:
                break
            accepted_count += 1
            tasks.add(asyncio.create_task(
                serve_one_attested_unix_http11(accepted_socket=client, edge=edge)
            ))

        if tasks:
            done, pending = await asyncio.wait(tasks, timeout=7)
            results.extend(int(task.result()) for task in done)
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
        return tuple(results)
    finally:
        server.close()
        if bound_inode is not None:
            try:
                info = os.lstat(socket_path)
                if stat.S_ISSOCK(info.st_mode) and info.st_ino == bound_inode:
                    os.unlink(socket_path)
            except FileNotFoundError:
                pass


__all__ = ["EXACT_FOREGROUND_OPT_IN", "serve_bounded_marketplace_unix_foreground"]
