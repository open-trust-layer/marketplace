"""One-shot bounded HTTP/1.1 to ASGI over an already accepted Linux Unix socket.

No bind/listen/accept, daemon, server activation, network egress or database
operations occur in this module. The operator-owned listener and peer-identity
capability are separate, unimplemented deployment dependencies.
"""
from __future__ import annotations

import asyncio
from http import HTTPStatus
import socket
from typing import Any, Final

from .attested_caddy_edge import MarketplaceAttestedCaddyEdgeAsgiAdapter
from .linux_unix_caddy_peer import (
    ACCEPTED_UNIX_SOCKET_SCOPE_KEY,
    MarketplaceLinuxUnixCaddyPeerVerifier,
)


MAX_REQUEST_HEAD_BYTES: Final = 32768
MAX_REQUEST_BODY_BYTES: Final = 256 * 1024
MAX_RESPONSE_BODY_BYTES: Final = 1024 * 1024
MAX_REQUEST_HEADER_COUNT: Final = 64
MAX_RESPONSE_HEADER_COUNT: Final = 64
MAX_RESPONSE_EVENTS: Final = 32
MAX_HEADER_LINE_BYTES: Final = 8192
MAX_TARGET_BYTES: Final = 4096
TOTAL_TIMEOUT_SECONDS: Final = 6.0
_READ_CHUNK: Final = 4096
_HTTP_TOKEN: Final = frozenset(b"!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
_FORBIDDEN_REQUEST_HEADERS: Final = frozenset((
    b"transfer-encoding", b"expect", b"upgrade", b"trailer",
    b"proxy-authorization",
))
_FORBIDDEN_RESPONSE_HEADERS: Final = frozenset((
    b"connection", b"transfer-encoding", b"set-cookie",
    b"proxy-authenticate", b"proxy-authorization", b"upgrade",
    b"trailer", b"keep-alive", b"te",
))


class _RejectedHttpRequest(Exception):
    def __init__(self, status: int) -> None:
        self.status = status


def _header_fields(lines: list[bytes]) -> list[tuple[bytes, bytes]]:
    if len(lines) > MAX_REQUEST_HEADER_COUNT:
        raise _RejectedHttpRequest(400)
    fields: list[tuple[bytes, bytes]] = []
    for item in lines:
        if len(item) > MAX_HEADER_LINE_BYTES or b":" not in item or item.startswith((b" ", b"\t")):
            raise _RejectedHttpRequest(400)
        name, value = item.split(b":", 1)
        if not name or any(char not in _HTTP_TOKEN for char in name):
            raise _RejectedHttpRequest(400)
        if any(char in value for char in (0, 10, 13, 127)) or b"\t" in value:
            raise _RejectedHttpRequest(400)
        normalized = name.lower()
        if normalized in _FORBIDDEN_REQUEST_HEADERS:
            raise _RejectedHttpRequest(400)
        fields.append((name, value.strip(b" ")))
    return fields


def _parse_start_and_headers(head: bytes) -> tuple[dict[str, Any], int]:
    if b"\n" in head.replace(b"\r\n", b""):
        raise _RejectedHttpRequest(400)
    lines = head.split(b"\r\n")
    if not lines or len(lines[0]) > MAX_HEADER_LINE_BYTES:
        raise _RejectedHttpRequest(400)
    tokens = lines[0].split(b" ")
    if len(tokens) != 3 or tokens[2] != b"HTTP/1.1":
        raise _RejectedHttpRequest(400)
    raw_method, target, _version = tokens
    if not raw_method or len(raw_method) > 8 or any(c not in _HTTP_TOKEN for c in raw_method):
        raise _RejectedHttpRequest(400)
    if not (target.startswith(b"/") and not target.startswith(b"//")):
        raise _RejectedHttpRequest(400)
    if len(target) > MAX_TARGET_BYTES or any(c <= 32 or c >= 127 for c in target):
        raise _RejectedHttpRequest(400)
    if b"#" in target or b"\\" in target:
        raise _RejectedHttpRequest(400)
    raw_path, _sep, query = target.partition(b"?")
    # Raw paths are intentionally non-decoding; canonical percent escapes in
    # query values are validated later by the existing reviewed ASGI parser.
    if not raw_path or b"%" in raw_path or b"?" in query:
        raise _RejectedHttpRequest(400)
    fields = _header_fields(lines[1:])
    body_size: int | None = None
    for name, value in fields:
        if name.lower() == b"content-length":
            if body_size is not None or not value or not value.isascii() or not value.isdigit():
                raise _RejectedHttpRequest(400)
            if len(value) > 1 and value.startswith(b"0"):
                raise _RejectedHttpRequest(400)
            if len(value) > 8:
                raise _RejectedHttpRequest(413)
            body_size = int(value)
            if body_size > MAX_REQUEST_BODY_BYTES:
                raise _RejectedHttpRequest(413)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "scheme": "http",
        "root_path": "",
        "method": raw_method.decode("ascii"),
        "path": raw_path.decode("ascii"),
        "raw_path": raw_path,
        "query_string": query,
        "headers": fields,
    }
    return scope, 0 if body_size is None else body_size


async def _read_one_request(sock: socket.socket, deadline: float) -> tuple[dict[str, Any], bytes]:
    loop = asyncio.get_running_loop()
    data = bytearray()
    head_end = -1
    while head_end < 0:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise _RejectedHttpRequest(408)
        chunk = await asyncio.wait_for(loop.sock_recv(sock, _READ_CHUNK), timeout=remaining)
        if not chunk:
            raise _RejectedHttpRequest(400)
        data.extend(chunk)
        head_end = data.find(b"\r\n\r\n")
        if head_end < 0 and len(data) > MAX_REQUEST_HEAD_BYTES + 3:
            raise _RejectedHttpRequest(431)
        if head_end > MAX_REQUEST_HEAD_BYTES:
            raise _RejectedHttpRequest(431)
    scope, expected = _parse_start_and_headers(bytes(data[:head_end]))
    body = bytearray(data[head_end + 4:])
    if len(body) > expected:
        # Refuse pipelining, request smuggling, trailing bytes and chunking.
        raise _RejectedHttpRequest(400)
    while len(body) < expected:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise _RejectedHttpRequest(408)
        chunk = await asyncio.wait_for(
            loop.sock_recv(sock, min(_READ_CHUNK, expected - len(body))),
            timeout=remaining,
        )
        if not chunk:
            raise _RejectedHttpRequest(400)
        body.extend(chunk)
    return scope, bytes(body)


def _fixed_reply(status: int) -> bytes:
    reason = HTTPStatus(status).phrase.encode("ascii")
    body = b"MARKETPLACE_EDGE_REQUEST_REJECTED" if status < 500 else b"MARKETPLACE_EDGE_UNAVAILABLE"
    return (
        b"HTTP/1.1 " + str(status).encode("ascii") + b" " + reason + b"\r\n"
        + b"Content-Type: text/plain; charset=utf-8\r\n"
        + b"Cache-Control: no-store\r\n"
        + b"X-Content-Type-Options: nosniff\r\n"
        + b"Connection: close\r\n"
        + b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n"
        + body
    )


async def _run_app(edge, scope: dict[str, Any], body: bytes, deadline: float) -> bytes:
    events: list[dict[str, Any]] = []
    received = False

    async def receive() -> dict[str, Any]:
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        if type(message) is not dict or len(events) >= MAX_RESPONSE_EVENTS:
            raise ValueError("invalid ASGI event stream")
        events.append(message)

    remaining = deadline - asyncio.get_running_loop().time()
    if remaining <= 0:
        raise TimeoutError()
    await asyncio.wait_for(edge(scope, receive, send), timeout=remaining)
    if len(events) < 2 or events[0].get("type") != "http.response.start":
        raise ValueError("missing response start")
    start = events[0]
    status = start.get("status")
    if type(status) is not int or not 200 <= status <= 599 or status in (204, 304) and len(events) > 2:
        raise ValueError("invalid ASGI response status")
    raw_headers = start.get("headers")
    if type(raw_headers) not in (list, tuple) or len(raw_headers) > MAX_RESPONSE_HEADER_COUNT:
        raise ValueError("response header count invalid")
    result_headers: list[tuple[bytes, bytes]] = []
    total = 0
    for pair in raw_headers:
        if type(pair) not in (list, tuple) or len(pair) != 2:
            raise ValueError("response header pair invalid")
        name, value = pair
        if type(name) is not bytes or type(value) is not bytes:
            raise ValueError("response header bytes required")
        total += len(name) + len(value) + 4
        if (
            not name or any(c not in _HTTP_TOKEN for c in name)
            or any(c in value for c in (0, 10, 13, 127))
            or len(value) > MAX_HEADER_LINE_BYTES
            or total > MAX_REQUEST_HEAD_BYTES
        ):
            raise ValueError("response header invalid")
        name_lower = name.lower()
        if name_lower in _FORBIDDEN_RESPONSE_HEADERS:
            raise ValueError("hop-by-hop or sensitive response header forbidden")
        if name_lower != b"content-length":
            result_headers.append((name, value))
    chunks: list[bytes] = []
    size = 0
    completed = False
    for event in events[1:]:
        if completed or event.get("type") != "http.response.body":
            raise ValueError("response events invalid")
        part = event.get("body", b"")
        if type(part) is not bytes:
            raise ValueError("response body must be exact bytes")
        size += len(part)
        if size > MAX_RESPONSE_BODY_BYTES:
            raise ValueError("response body exceeded")
        chunks.append(part)
        if event.get("more_body", False) is not True:
            completed = True
    if not completed or status in (204, 304) and size:
        raise ValueError("incomplete response")
    payload = b"".join(chunks)
    if scope["method"] == "HEAD" or status in (204, 304):
        payload_to_send = b""
    else:
        payload_to_send = payload
    reason = HTTPStatus(status).phrase.encode("ascii") if status in HTTPStatus._value2member_map_ else b"Response"
    response = (
        b"HTTP/1.1 " + str(status).encode("ascii") + b" " + reason + b"\r\n"
        + b"".join(name + b": " + value + b"\r\n" for name, value in result_headers)
        + b"Content-Length: " + str(len(payload_to_send)).encode("ascii") + b"\r\n"
        + b"Connection: close\r\n"
        + b"Cache-Control: no-store\r\n"
        + b"X-Content-Type-Options: nosniff\r\n\r\n"
        + payload_to_send
    )
    return response


async def serve_one_attested_unix_http11(
    *,
    accepted_socket: socket.socket,
    edge: MarketplaceAttestedCaddyEdgeAsgiAdapter,
) -> int:
    """Serve exactly one request on the caller-owned already accepted AF_UNIX socket.

    The peer is kernel-verified before any HTTP bytes are read; the normalized
    scope is verified again by the edge and the private socket never reaches
    product handlers. Every outcome closes this accepted connection.
    """
    if type(accepted_socket) is not socket.socket:
        raise TypeError("exact accepted Unix socket required")
    if (
        accepted_socket.family != getattr(socket, "AF_UNIX", None)
        or accepted_socket.type != socket.SOCK_STREAM
        or type(edge) is not MarketplaceAttestedCaddyEdgeAsgiAdapter
        or type(edge._verifier) is not MarketplaceLinuxUnixCaddyPeerVerifier
    ):
        raise TypeError("exact trusted Linux Unix edge provider required")
    loop = asyncio.get_running_loop()
    deadline = loop.time() + TOTAL_TIMEOUT_SECONDS
    accepted_socket.setblocking(False)
    status = 503
    reply: bytes
    try:
        peer_scope = {ACCEPTED_UNIX_SOCKET_SCOPE_KEY: accepted_socket}
        if not edge._verifier.verify_connection(peer_scope):
            status = 403
            reply = _fixed_reply(status)
        else:
            scope, body = await _read_one_request(accepted_socket, deadline)
            scope[ACCEPTED_UNIX_SOCKET_SCOPE_KEY] = accepted_socket
            reply = await _run_app(edge, scope, body, deadline)
            status = int(reply.split(b" ", 2)[1])
    except _RejectedHttpRequest as error:
        status = error.status
        reply = _fixed_reply(status)
    except Exception:
        status = 503
        reply = _fixed_reply(status)
    try:
        remaining = deadline - loop.time()
        if remaining > 0:
            await asyncio.wait_for(
                loop.sock_sendall(accepted_socket, reply), timeout=remaining
            )
    except (OSError, TimeoutError, asyncio.TimeoutError):
        pass
    finally:
        accepted_socket.close()
    return status


__all__ = ["serve_one_attested_unix_http11"]
