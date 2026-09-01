"""Bounded one-shot IPv4 loopback acceptance client for the reviewed M78 host.

The packaged boundary never chooses a real socket provider. A caller must supply
an exact runtime opt-in token, an exact M77 request, and an injected socket
constructor. One invocation connects only to 127.0.0.1, writes one bounded
HTTP/1.1 request, reads one bounded response, validates the M77 security/framing
contract, closes the socket, and returns metadata only.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from socket import AF_INET, IPPROTO_TCP, SOCK_STREAM

from .local_ui_http_v1 import MAX_LOCAL_UI_HTTP_BODY_BYTES, LocalUiHttpRequest


LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN = "EXECUTE_ONE_LOCAL_UI_LOOPBACK_CLIENT"
LOCAL_UI_LOOPBACK_CLIENT_HOST = "127.0.0.1"
MIN_LOCAL_UI_LOOPBACK_CLIENT_PORT = 1024
MAX_LOCAL_UI_LOOPBACK_CLIENT_PORT = 65535
MAX_LOCAL_UI_LOOPBACK_CLIENT_HEADER_BYTES = 8_192
MAX_LOCAL_UI_LOOPBACK_CLIENT_HEADERS = 32
MAX_LOCAL_UI_LOOPBACK_CLIENT_READ_CALLS = 64
MAX_LOCAL_UI_LOOPBACK_CLIENT_WRITE_CALLS = 64
LOCAL_UI_LOOPBACK_CLIENT_IO_CHUNK_BYTES = 4_096
LOCAL_UI_LOOPBACK_CLIENT_TIMEOUT_SECONDS = 5.0
_MAX_RESPONSE_BODY_BYTES = 65_536
_MAX_RESPONSE_WIRE_BYTES = MAX_LOCAL_UI_LOOPBACK_CLIENT_HEADER_BYTES + _MAX_RESPONSE_BODY_BYTES
_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"
_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
    "base-uri 'none'; frame-ancestors 'none'"
)
_ALLOWED_RESPONSE_HEADERS = frozenset(
    {
        "allow",
        "cache-control",
        "connection",
        "content-length",
        "content-security-policy",
        "content-type",
        "referrer-policy",
        "x-content-type-options",
    }
)
_REQUIRED_RESPONSE_HEADERS = {
    "cache-control": "no-store",
    "connection": "close",
    "content-security-policy": _CSP,
    "content-type": "text/html; charset=utf-8",
    "referrer-policy": "no-referrer",
    "x-content-type-options": "nosniff",
}


class LocalUiLoopbackClientError(RuntimeError):
    """Stable client failure that never reflects request/response content."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class LocalUiLoopbackClientPlan:
    """Authority-negative dry-run description for one future client transaction."""

    host: str
    port: int
    request_method: str
    request_target: str
    one_shot: bool
    network_invoked: bool
    external_authorization_established: bool
    deployment_authorized: bool


@dataclass(frozen=True, slots=True)
class LocalUiLoopbackClientResult:
    """Metadata-only facts after one terminal client transaction."""

    host: str
    port: int
    request_method: str
    request_target: str
    status_code: int
    bytes_sent: int
    bytes_received: int
    network_invoked: bool
    external_authorization_established: bool
    deployment_authorized: bool


def _fail(code: str, message: str) -> None:
    raise LocalUiLoopbackClientError(code, message) from None


def _validate_port(port: object) -> int:
    if type(port) is not int or not MIN_LOCAL_UI_LOOPBACK_CLIENT_PORT <= port <= MAX_LOCAL_UI_LOOPBACK_CLIENT_PORT:
        _fail("PORT_INVALID", "local UI loopback client port is outside the reviewed non-privileged range")
    return port


def _validate_request(request: object) -> LocalUiHttpRequest:
    if type(request) is not LocalUiHttpRequest:
        _fail("REQUEST_INVALID", "local UI loopback client requires an exact M77 request")
    if type(request.method) is not str or type(request.target) is not str:
        _fail("REQUEST_INVALID", "local UI loopback client request metadata is invalid")
    if type(request.body) is not bytes:
        _fail("REQUEST_INVALID", "local UI loopback client request body is invalid")
    if request.method == "GET" and request.target == "/":
        if request.content_type is not None or request.body:
            _fail("REQUEST_INVALID", "local UI loopback GET request is outside the reviewed profile")
        return request
    if request.method == "POST" and request.target == "/local-buy-sell":
        if request.content_type != _FORM_CONTENT_TYPE or not request.body:
            _fail("REQUEST_INVALID", "local UI loopback POST request is outside the reviewed profile")
        if len(request.body) > MAX_LOCAL_UI_HTTP_BODY_BYTES:
            _fail("REQUEST_TOO_LARGE", "local UI loopback client request body exceeded the reviewed bound")
        return request
    _fail("REQUEST_INVALID", "local UI loopback client route is outside the reviewed M77 profile")


def plan_local_ui_loopback_client_once(port: int, request: LocalUiHttpRequest) -> LocalUiLoopbackClientPlan:
    """Return an inert exact-loopback plan without selecting a socket provider."""
    checked_port = _validate_port(port)
    checked_request = _validate_request(request)
    return LocalUiLoopbackClientPlan(
        host=LOCAL_UI_LOOPBACK_CLIENT_HOST,
        port=checked_port,
        request_method=checked_request.method,
        request_target=checked_request.target,
        one_shot=True,
        network_invoked=False,
        external_authorization_established=False,
        deployment_authorized=False,
    )


def _serialize_request(request: LocalUiHttpRequest, *, port: int) -> bytes:
    host = f"{LOCAL_UI_LOOPBACK_CLIENT_HOST}:{port}"
    if request.method == "GET":
        return f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode("ascii")
    head = (
        f"POST /local-buy-sell HTTP/1.1\r\nHost: {host}\r\n"
        f"Content-Type: {_FORM_CONTENT_TYPE}\r\nContent-Length: {len(request.body)}\r\n"
        "Connection: close\r\n\r\n"
    ).encode("ascii")
    return head + request.body


def _exact_callable(owner: object, name: str, code: str) -> Callable[..., object]:
    try:
        value = getattr(owner, name)
    except Exception:
        _fail(code, "local UI loopback client capability is unavailable")
    if not callable(value):
        _fail(code, "local UI loopback client capability is unavailable")
    return value


def _write_request(sock: object, wire: bytes) -> int:
    send = _exact_callable(sock, "send", "SOCKET_INVALID")
    offset = 0
    for _call in range(MAX_LOCAL_UI_LOOPBACK_CLIENT_WRITE_CALLS):
        if offset == len(wire):
            break
        try:
            sent = send(wire[offset:])
        except Exception:
            _fail("WRITE_FAILED", "local UI loopback client request write failed")
        if type(sent) is not int or sent <= 0 or sent > len(wire) - offset:
            _fail("WRITE_FAILED", "local UI loopback client request write returned an invalid count")
        offset += sent
    else:
        _fail("WRITE_LIMIT_EXHAUSTED", "local UI loopback client request exceeded the reviewed write-call bound")
    if offset != len(wire):
        _fail("WRITE_FAILED", "local UI loopback client request did not complete")
    return offset


def _parse_response_head(head: bytes) -> tuple[int, int]:
    if type(head) is not bytes or not head or len(head) > MAX_LOCAL_UI_LOOPBACK_CLIENT_HEADER_BYTES:
        _fail("RESPONSE_INVALID", "local UI loopback response head is invalid")
    if b"\r" in head.replace(b"\r\n", b"") or b"\n" in head.replace(b"\r\n", b""):
        _fail("RESPONSE_INVALID", "local UI loopback response line endings are invalid")
    try:
        text = head.decode("ascii", errors="strict")
    except UnicodeDecodeError:
        _fail("RESPONSE_INVALID", "local UI loopback response head must use exact ASCII")

    lines = text.split("\r\n")
    status_parts = lines[0].split(" ", 2) if lines else []
    if len(status_parts) != 3 or status_parts[0] != "HTTP/1.1":
        _fail("RESPONSE_INVALID", "local UI loopback response status line is invalid")
    status_text, reason = status_parts[1], status_parts[2]
    if len(status_text) != 3 or not status_text.isdecimal() or not reason:
        _fail("RESPONSE_INVALID", "local UI loopback response status line is invalid")
    status_code = int(status_text)
    if not 100 <= status_code <= 599 or any(ord(ch) < 0x20 or ord(ch) > 0x7E for ch in reason):
        _fail("RESPONSE_INVALID", "local UI loopback response status is outside the reviewed profile")

    header_lines = lines[1:]
    if len(header_lines) > MAX_LOCAL_UI_LOOPBACK_CLIENT_HEADERS:
        _fail("RESPONSE_INVALID", "local UI loopback response has too many headers")
    headers: dict[str, str] = {}
    for line in header_lines:
        if not line or line.startswith((" ", "\t")) or ":" not in line:
            _fail("RESPONSE_INVALID", "local UI loopback response header is invalid")
        raw_name, raw_value = line.split(":", 1)
        if not raw_name or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-" for ch in raw_name):
            _fail("RESPONSE_INVALID", "local UI loopback response header name is invalid")
        if not raw_value.startswith(" ") or raw_value.startswith("  "):
            _fail("RESPONSE_INVALID", "local UI loopback response header spacing is invalid")
        value = raw_value[1:]
        if len(value) > 4_096 or any(ord(ch) < 0x20 or ord(ch) > 0x7E for ch in value):
            _fail("RESPONSE_INVALID", "local UI loopback response header value is invalid")
        name = raw_name.lower()
        if name in headers or name not in _ALLOWED_RESPONSE_HEADERS:
            _fail("RESPONSE_INVALID", "local UI loopback response header set is invalid")
        headers[name] = value

    for name, expected in _REQUIRED_RESPONSE_HEADERS.items():
        if headers.get(name) != expected:
            _fail("RESPONSE_INVALID", "local UI loopback response security headers are invalid")
    length_text = headers.get("content-length")
    if (
        length_text is None
        or not length_text
        or len(length_text) > 5
        or not length_text.isdecimal()
        or (len(length_text) > 1 and length_text.startswith("0"))
    ):
        _fail("RESPONSE_INVALID", "local UI loopback response Content-Length is invalid")
    body_length = int(length_text)
    if body_length > _MAX_RESPONSE_BODY_BYTES:
        _fail("RESPONSE_INVALID", "local UI loopback response body exceeded the reviewed bound")
    return status_code, body_length


def _read_response(sock: object) -> tuple[int, int]:
    recv = _exact_callable(sock, "recv", "SOCKET_INVALID")
    buffer = bytearray()
    status_code: int | None = None
    expected_total: int | None = None

    for _call in range(MAX_LOCAL_UI_LOOPBACK_CLIENT_READ_CALLS):
        if expected_total is not None and len(buffer) == expected_total:
            try:
                trailing = recv(1)
            except Exception:
                _fail("READ_FAILED", "local UI loopback response read failed")
            if type(trailing) is not bytes:
                _fail("READ_FAILED", "local UI loopback response read returned an invalid result")
            if trailing:
                _fail("RESPONSE_TRAILING_BYTES", "local UI loopback response contained trailing bytes")
            break
        remaining = _MAX_RESPONSE_WIRE_BYTES - len(buffer)
        if remaining <= 0:
            _fail("RESPONSE_INVALID", "local UI loopback response exceeded the reviewed wire bound")
        try:
            chunk = recv(min(LOCAL_UI_LOOPBACK_CLIENT_IO_CHUNK_BYTES, remaining))
        except Exception:
            _fail("READ_FAILED", "local UI loopback response read failed")
        if type(chunk) is not bytes:
            _fail("READ_FAILED", "local UI loopback response read returned an invalid result")
        if not chunk:
            _fail("RESPONSE_INCOMPLETE", "local UI loopback connection ended before one response completed")
        buffer.extend(chunk)

        if expected_total is None:
            marker = buffer.find(b"\r\n\r\n")
            if marker < 0:
                if len(buffer) >= MAX_LOCAL_UI_LOOPBACK_CLIENT_HEADER_BYTES:
                    _fail("RESPONSE_INVALID", "local UI loopback response head exceeded the reviewed bound")
                continue
            head_end = marker + 4
            if head_end > MAX_LOCAL_UI_LOOPBACK_CLIENT_HEADER_BYTES:
                _fail("RESPONSE_INVALID", "local UI loopback response head exceeded the reviewed bound")
            status_code, body_length = _parse_response_head(bytes(buffer[:marker]))
            expected_total = head_end + body_length
            if expected_total > _MAX_RESPONSE_WIRE_BYTES:
                _fail("RESPONSE_INVALID", "local UI loopback response exceeded the reviewed wire bound")

        if len(buffer) > expected_total:
            _fail("RESPONSE_TRAILING_BYTES", "local UI loopback response contained trailing bytes")
    else:
        _fail("READ_LIMIT_EXHAUSTED", "local UI loopback response exceeded the reviewed read-call bound")

    if status_code is None or expected_total is None or len(buffer) != expected_total:
        _fail("RESPONSE_INCOMPLETE", "local UI loopback response did not complete within reviewed bounds")
    marker = buffer.find(b"\r\n\r\n")
    try:
        bytes(buffer[marker + 4 :]).decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _fail("RESPONSE_INVALID", "local UI loopback response body is not valid UTF-8")
    return status_code, len(buffer)


def _close_once(value: object | None) -> bool:
    if value is None:
        return True
    try:
        close = getattr(value, "close")
    except Exception:
        return False
    if not callable(close):
        return False
    try:
        close()
    except Exception:
        return False
    return True


def run_local_ui_loopback_client_once(
    *,
    port: int,
    request: LocalUiHttpRequest,
    execution_opt_in: str,
    socket_constructor: Callable[[object, object, object], object],
) -> LocalUiLoopbackClientResult:
    """Execute exactly one explicitly opted-in local loopback client transaction."""
    checked_port = _validate_port(port)
    checked_request = _validate_request(request)
    if type(execution_opt_in) is not str or execution_opt_in != LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN:
        _fail("EXECUTION_NOT_AUTHORIZED", "exact local UI loopback client execution opt-in is required")
    if not callable(socket_constructor):
        _fail("SOCKET_CONSTRUCTOR_INVALID", "local UI loopback client socket constructor must be callable")

    sock: object | None = None
    result: LocalUiLoopbackClientResult | None = None
    failure: LocalUiLoopbackClientError | None = None
    try:
        try:
            sock = socket_constructor(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        except Exception:
            _fail("SOCKET_CONSTRUCTION_FAILED", "local UI loopback client socket construction failed")
        settimeout = _exact_callable(sock, "settimeout", "SOCKET_INVALID")
        connect = _exact_callable(sock, "connect", "SOCKET_INVALID")
        try:
            settimeout(LOCAL_UI_LOOPBACK_CLIENT_TIMEOUT_SECONDS)
        except Exception:
            _fail("SOCKET_INVALID", "local UI loopback client timeout configuration failed")
        try:
            connect((LOCAL_UI_LOOPBACK_CLIENT_HOST, checked_port))
        except Exception:
            _fail("CONNECT_FAILED", "local UI loopback client connect failed")

        request_wire = _serialize_request(checked_request, port=checked_port)
        bytes_sent = _write_request(sock, request_wire)
        status_code, bytes_received = _read_response(sock)
        result = LocalUiLoopbackClientResult(
            host=LOCAL_UI_LOOPBACK_CLIENT_HOST,
            port=checked_port,
            request_method=checked_request.method,
            request_target=checked_request.target,
            status_code=status_code,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            network_invoked=True,
            external_authorization_established=False,
            deployment_authorized=False,
        )
    except LocalUiLoopbackClientError as exc:
        failure = exc

    cleanup_ok = _close_once(sock)
    if not cleanup_ok:
        _fail("CLEANUP_UNCERTAIN", "local UI loopback client socket cleanup could not be confirmed")
    if failure is not None:
        raise failure from None
    if result is None:
        _fail("CLIENT_FAILED", "local UI loopback client ended without a result")
    return result
