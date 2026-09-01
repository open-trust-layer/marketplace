"""Explicit one-shot IPv4 loopback transport for the reviewed M77 local UI adapter.

The packaged boundary never chooses a socket provider by itself. A caller must
supply an exact execution opt-in token and a socket-constructor capability. One
invocation constructs one IPv4/TCP listener, binds only 127.0.0.1, accepts one
connection, handles one bounded HTTP/1.1 request through M77, writes one bounded
response, and closes both connection and listener before returning.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from socket import AF_INET, IPPROTO_TCP, SOCK_STREAM

from .local_ui_http_v1 import (
    MAX_LOCAL_UI_HTTP_BODY_BYTES,
    LocalUiHttpError,
    LocalUiHttpRequest,
    LocalUiHttpResponse,
    handle_local_ui_http_request,
)


LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN = "EXECUTE_ONE_LOCAL_UI_LOOPBACK_SESSION"
LOCAL_UI_LOOPBACK_HOST = "127.0.0.1"
MIN_LOCAL_UI_LOOPBACK_PORT = 1024
MAX_LOCAL_UI_LOOPBACK_PORT = 65535
MAX_LOCAL_UI_LOOPBACK_HEADER_BYTES = 8_192
MAX_LOCAL_UI_LOOPBACK_HEADERS = 32
MAX_LOCAL_UI_LOOPBACK_READ_CALLS = 64
MAX_LOCAL_UI_LOOPBACK_WRITE_CALLS = 128
LOCAL_UI_LOOPBACK_IO_CHUNK_BYTES = 4_096
LOCAL_UI_LOOPBACK_TIMEOUT_SECONDS = 5.0
_MAX_REQUEST_BYTES = MAX_LOCAL_UI_LOOPBACK_HEADER_BYTES + MAX_LOCAL_UI_HTTP_BODY_BYTES
_MAX_RESPONSE_WIRE_BYTES = 70_000
_FORBIDDEN_REQUEST_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "expect",
        "proxy-authorization",
        "proxy-connection",
        "set-cookie",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)


class LocalUiLoopbackError(RuntimeError):
    """Stable one-shot transport failure that never reflects caller payload text."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class LocalUiLoopbackPlan:
    """Authority-negative dry-run description for one future loopback session."""

    host: str
    port: int
    one_shot: bool
    network_invoked: bool
    external_authorization_established: bool
    deployment_authorized: bool


@dataclass(frozen=True, slots=True)
class LocalUiLoopbackResult:
    """Metadata-only result after one terminal loopback transaction."""

    host: str
    port: int
    request_method: str
    request_target: str
    status_code: int
    bytes_received: int
    bytes_sent: int
    network_invoked: bool
    external_authorization_established: bool
    deployment_authorized: bool


def _fail(code: str, message: str) -> None:
    raise LocalUiLoopbackError(code, message) from None


def _validate_port(port: object) -> int:
    if type(port) is not int or not MIN_LOCAL_UI_LOOPBACK_PORT <= port <= MAX_LOCAL_UI_LOOPBACK_PORT:
        _fail("PORT_INVALID", "local UI loopback port is outside the reviewed non-privileged range")
    return port


def plan_local_ui_loopback_once(port: int) -> LocalUiLoopbackPlan:
    """Validate the endpoint and return an inert plan without selecting network authority."""
    checked_port = _validate_port(port)
    return LocalUiLoopbackPlan(
        host=LOCAL_UI_LOOPBACK_HOST,
        port=checked_port,
        one_shot=True,
        network_invoked=False,
        external_authorization_established=False,
        deployment_authorized=False,
    )


def _exact_callable(owner: object, name: str, error_code: str) -> Callable[..., object]:
    try:
        value = getattr(owner, name)
    except Exception:
        _fail(error_code, "local UI loopback transport capability is unavailable")
    if not callable(value):
        _fail(error_code, "local UI loopback transport capability is unavailable")
    return value


def _parse_request_head(head: bytes, *, port: int) -> tuple[str, str, str | None, int]:
    if type(head) is not bytes or not head:
        _fail("REQUEST_INVALID", "local UI loopback request head is invalid")
    if len(head) > MAX_LOCAL_UI_LOOPBACK_HEADER_BYTES:
        _fail("REQUEST_TOO_LARGE", "local UI loopback request head exceeded the reviewed bound")
    if b"\r" in head.replace(b"\r\n", b"") or b"\n" in head.replace(b"\r\n", b""):
        _fail("REQUEST_INVALID", "local UI loopback request line endings are invalid")
    try:
        text = head.decode("ascii", errors="strict")
    except UnicodeDecodeError:
        _fail("REQUEST_INVALID", "local UI loopback request head must use exact ASCII")

    lines = text.split("\r\n")
    if not lines or len(lines[0].split(" ")) != 3:
        _fail("REQUEST_INVALID", "local UI loopback request line is invalid")
    method, target, version = lines[0].split(" ")
    if version != "HTTP/1.1" or not method or len(method) > 8 or not target or len(target) > 64:
        _fail("REQUEST_INVALID", "local UI loopback request line is outside the reviewed profile")
    if any(ord(ch) < 0x21 or ord(ch) > 0x7E for ch in method + target):
        _fail("REQUEST_INVALID", "local UI loopback request metadata contains invalid bytes")

    header_lines = lines[1:]
    if len(header_lines) > MAX_LOCAL_UI_LOOPBACK_HEADERS:
        _fail("REQUEST_TOO_LARGE", "local UI loopback request has too many headers")
    headers: dict[str, str] = {}
    for line in header_lines:
        if not line or line.startswith((" ", "\t")) or line.count(":") != 1:
            _fail("REQUEST_INVALID", "local UI loopback request header is invalid")
        raw_name, raw_value = line.split(":", 1)
        if not raw_name or len(raw_name) > 64:
            _fail("REQUEST_INVALID", "local UI loopback request header name is invalid")
        if any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-" for ch in raw_name):
            _fail("REQUEST_INVALID", "local UI loopback request header name is invalid")
        if not raw_value.startswith(" ") or raw_value.startswith("  "):
            _fail("REQUEST_INVALID", "local UI loopback request header spacing is invalid")
        value = raw_value[1:]
        if len(value) > 4_096 or any(ord(ch) < 0x20 or ord(ch) > 0x7E for ch in value):
            _fail("REQUEST_INVALID", "local UI loopback request header value is invalid")
        name = raw_name.lower()
        if name in headers:
            _fail("REQUEST_INVALID", "local UI loopback request contains duplicate headers")
        if name in _FORBIDDEN_REQUEST_HEADERS:
            _fail("REQUEST_INVALID", "local UI loopback request contains a forbidden header")
        headers[name] = value

    expected_host = f"{LOCAL_UI_LOOPBACK_HOST}:{port}"
    if headers.get("host") != expected_host:
        _fail("REQUEST_INVALID", "local UI loopback Host authority is invalid")
    if "connection" in headers and headers["connection"].lower() not in {"close", "keep-alive"}:
        _fail("REQUEST_INVALID", "local UI loopback Connection header is invalid")

    content_length_text = headers.get("content-length")
    if content_length_text is None:
        content_length = 0
    else:
        if (
            not content_length_text
            or len(content_length_text) > 5
            or not content_length_text.isdecimal()
            or (len(content_length_text) > 1 and content_length_text.startswith("0"))
        ):
            _fail("REQUEST_INVALID", "local UI loopback Content-Length is invalid")
        content_length = int(content_length_text)
        if content_length > MAX_LOCAL_UI_HTTP_BODY_BYTES:
            _fail("REQUEST_TOO_LARGE", "local UI loopback request body exceeded the reviewed bound")

    return method, target, headers.get("content-type"), content_length


def _read_request(connection: object, *, port: int) -> tuple[LocalUiHttpRequest, int]:
    recv = _exact_callable(connection, "recv", "CONNECTION_INVALID")
    buffer = bytearray()
    parsed: tuple[str, str, str | None, int] | None = None
    expected_total: int | None = None

    for _call in range(MAX_LOCAL_UI_LOOPBACK_READ_CALLS):
        if expected_total is not None and len(buffer) == expected_total:
            break
        remaining = _MAX_REQUEST_BYTES - len(buffer)
        if remaining <= 0:
            _fail("REQUEST_TOO_LARGE", "local UI loopback request exceeded the reviewed byte bound")
        try:
            chunk = recv(min(LOCAL_UI_LOOPBACK_IO_CHUNK_BYTES, remaining))
        except Exception:
            _fail("READ_FAILED", "local UI loopback request read failed")
        if type(chunk) is not bytes:
            _fail("READ_FAILED", "local UI loopback request read returned an invalid result")
        if not chunk:
            _fail("REQUEST_INCOMPLETE", "local UI loopback connection ended before one request completed")
        buffer.extend(chunk)

        if parsed is None:
            marker = buffer.find(b"\r\n\r\n")
            if marker < 0:
                if len(buffer) >= MAX_LOCAL_UI_LOOPBACK_HEADER_BYTES:
                    _fail("REQUEST_TOO_LARGE", "local UI loopback request head exceeded the reviewed bound")
                continue
            head_end = marker + 4
            if head_end > MAX_LOCAL_UI_LOOPBACK_HEADER_BYTES:
                _fail("REQUEST_TOO_LARGE", "local UI loopback request head exceeded the reviewed bound")
            parsed = _parse_request_head(bytes(buffer[:marker]), port=port)
            expected_total = head_end + parsed[3]
            if expected_total > _MAX_REQUEST_BYTES:
                _fail("REQUEST_TOO_LARGE", "local UI loopback request exceeded the reviewed byte bound")

        if expected_total is not None and len(buffer) > expected_total:
            _fail("REQUEST_TRAILING_BYTES", "local UI loopback request contained trailing or pipelined bytes")
    else:
        _fail("READ_LIMIT_EXHAUSTED", "local UI loopback request exceeded the reviewed read-call bound")

    if parsed is None or expected_total is None or len(buffer) != expected_total:
        _fail("REQUEST_INCOMPLETE", "local UI loopback request did not complete within reviewed bounds")
    marker = buffer.find(b"\r\n\r\n")
    body = bytes(buffer[marker + 4 :])
    method, target, content_type, content_length = parsed
    if len(body) != content_length:
        _fail("REQUEST_INVALID", "local UI loopback request body length is invalid")
    return LocalUiHttpRequest(method, target, content_type, body), len(buffer)


def _serialize_response(response: LocalUiHttpResponse) -> bytes:
    if type(response) is not LocalUiHttpResponse:
        _fail("APPLICATION_FAILED", "M77 returned an invalid local UI HTTP response")
    if type(response.status_code) is not int or not 100 <= response.status_code <= 599:
        _fail("APPLICATION_FAILED", "M77 returned an invalid local UI HTTP status")
    if type(response.reason) is not str or not response.reason:
        _fail("APPLICATION_FAILED", "M77 returned an invalid local UI HTTP reason")
    try:
        reason = response.reason.encode("ascii", errors="strict")
    except UnicodeEncodeError:
        _fail("APPLICATION_FAILED", "M77 returned a non-ASCII local UI HTTP reason")
    if any(byte < 0x20 or byte > 0x7E for byte in reason):
        _fail("APPLICATION_FAILED", "M77 returned an invalid local UI HTTP reason")
    if type(response.headers) is not tuple or type(response.body) is not bytes:
        _fail("APPLICATION_FAILED", "M77 returned an invalid local UI HTTP response shape")

    lines = [f"HTTP/1.1 {response.status_code} {response.reason}\r\n".encode("ascii")]
    seen: set[str] = set()
    for item in response.headers:
        if type(item) is not tuple or len(item) != 2 or type(item[0]) is not str or type(item[1]) is not str:
            _fail("APPLICATION_FAILED", "M77 returned an invalid local UI HTTP header")
        name, value = item
        lowered = name.lower()
        if lowered in seen or lowered == "connection":
            _fail("APPLICATION_FAILED", "M77 returned an invalid local UI HTTP header set")
        seen.add(lowered)
        try:
            encoded_name = name.encode("ascii", errors="strict")
            encoded_value = value.encode("ascii", errors="strict")
        except UnicodeEncodeError:
            _fail("APPLICATION_FAILED", "M77 returned a non-ASCII local UI HTTP header")
        if (
            not encoded_name
            or any(byte not in b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-" for byte in encoded_name)
            or any(byte < 0x20 or byte > 0x7E for byte in encoded_value)
        ):
            _fail("APPLICATION_FAILED", "M77 returned an invalid local UI HTTP header")
        lines.append(encoded_name + b": " + encoded_value + b"\r\n")

    if "content-length" not in seen or "content-type" not in seen:
        _fail("APPLICATION_FAILED", "M77 response omitted required framing headers")
    try:
        declared = dict((name.lower(), value) for name, value in response.headers)["content-length"]
    except Exception:
        _fail("APPLICATION_FAILED", "M77 response framing headers are invalid")
    if declared != str(len(response.body)):
        _fail("APPLICATION_FAILED", "M77 response Content-Length is invalid")

    wire = b"".join(lines) + b"Connection: close\r\n\r\n" + response.body
    if len(wire) > _MAX_RESPONSE_WIRE_BYTES:
        _fail("RESPONSE_TOO_LARGE", "local UI loopback response exceeded the reviewed wire bound")
    return wire


def _write_response(connection: object, wire: bytes) -> int:
    send = _exact_callable(connection, "send", "CONNECTION_INVALID")
    offset = 0
    for _call in range(MAX_LOCAL_UI_LOOPBACK_WRITE_CALLS):
        if offset == len(wire):
            break
        try:
            sent = send(wire[offset:])
        except Exception:
            _fail("WRITE_FAILED", "local UI loopback response write failed")
        if type(sent) is not int or sent <= 0 or sent > len(wire) - offset:
            _fail("WRITE_FAILED", "local UI loopback response write returned an invalid count")
        offset += sent
    else:
        _fail("WRITE_LIMIT_EXHAUSTED", "local UI loopback response exceeded the reviewed write-call bound")
    if offset != len(wire):
        _fail("WRITE_FAILED", "local UI loopback response did not complete")
    return offset


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


def serve_local_ui_loopback_once(
    *,
    port: int,
    execution_opt_in: str,
    socket_constructor: Callable[[object, object, object], object],
) -> LocalUiLoopbackResult:
    """Execute exactly one explicitly opted-in local UI loopback transaction."""
    checked_port = _validate_port(port)
    if type(execution_opt_in) is not str or execution_opt_in != LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN:
        _fail("EXECUTION_NOT_AUTHORIZED", "exact local UI loopback execution opt-in is required")
    if not callable(socket_constructor):
        _fail("SOCKET_CONSTRUCTOR_INVALID", "local UI loopback socket constructor must be callable")

    listener: object | None = None
    connection: object | None = None
    result: LocalUiLoopbackResult | None = None
    failure: LocalUiLoopbackError | None = None

    try:
        try:
            listener = socket_constructor(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        except Exception:
            _fail("SOCKET_CONSTRUCTION_FAILED", "local UI loopback socket construction failed")
        set_listener_timeout = _exact_callable(listener, "settimeout", "LISTENER_INVALID")
        bind = _exact_callable(listener, "bind", "LISTENER_INVALID")
        listen = _exact_callable(listener, "listen", "LISTENER_INVALID")
        accept = _exact_callable(listener, "accept", "LISTENER_INVALID")
        try:
            set_listener_timeout(LOCAL_UI_LOOPBACK_TIMEOUT_SECONDS)
            bind((LOCAL_UI_LOOPBACK_HOST, checked_port))
            listen(1)
            accepted = accept()
        except LocalUiLoopbackError:
            raise
        except Exception:
            _fail("LISTENER_FAILED", "local UI loopback listener operation failed")
        if type(accepted) is not tuple or len(accepted) != 2:
            _fail("ACCEPT_FAILED", "local UI loopback accept returned an invalid result")
        connection, peer = accepted
        if (
            type(peer) is not tuple
            or len(peer) < 2
            or type(peer[0]) is not str
            or peer[0] != LOCAL_UI_LOOPBACK_HOST
        ):
            _fail("PEER_NOT_LOOPBACK", "local UI loopback accepted a non-loopback peer")
        set_connection_timeout = _exact_callable(connection, "settimeout", "CONNECTION_INVALID")
        try:
            set_connection_timeout(LOCAL_UI_LOOPBACK_TIMEOUT_SECONDS)
        except Exception:
            _fail("CONNECTION_INVALID", "local UI loopback connection timeout configuration failed")

        request, bytes_received = _read_request(connection, port=checked_port)
        try:
            response = handle_local_ui_http_request(request)
        except LocalUiHttpError:
            _fail("APPLICATION_FAILED", "reviewed M77 local UI HTTP handling failed")
        except Exception:
            _fail("APPLICATION_FAILED", "reviewed M77 local UI HTTP handling failed")
        wire = _serialize_response(response)
        bytes_sent = _write_response(connection, wire)
        result = LocalUiLoopbackResult(
            host=LOCAL_UI_LOOPBACK_HOST,
            port=checked_port,
            request_method=request.method,
            request_target=request.target,
            status_code=response.status_code,
            bytes_received=bytes_received,
            bytes_sent=bytes_sent,
            network_invoked=True,
            external_authorization_established=False,
            deployment_authorized=False,
        )
    except LocalUiLoopbackError as exc:
        failure = exc
    except Exception:
        failure = LocalUiLoopbackError("TRANSPORT_FAILED", "local UI loopback transport failed")

    connection_closed = _close_once(connection)
    listener_closed = _close_once(listener)
    if not connection_closed or not listener_closed:
        raise LocalUiLoopbackError(
            "CLEANUP_UNCERTAIN",
            "local UI loopback cleanup could not be verified",
        ) from None
    if failure is not None:
        raise failure from None
    if result is None:
        _fail("TRANSPORT_FAILED", "local UI loopback transport completed without a result")
    return result


__all__ = [
    "LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN",
    "LOCAL_UI_LOOPBACK_HOST",
    "MAX_LOCAL_UI_LOOPBACK_PORT",
    "MIN_LOCAL_UI_LOOPBACK_PORT",
    "LocalUiLoopbackError",
    "LocalUiLoopbackPlan",
    "LocalUiLoopbackResult",
    "plan_local_ui_loopback_once",
    "serve_local_ui_loopback_once",
]
