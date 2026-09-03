"""Dependency-free source-only ASGI 3 HTTP host adapter for Marketplace."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Final

from .http import (
    ApplicationHttpRequest,
    ApplicationHttpResponse,
    MAX_APPLICATION_HTTP_BODY_BYTES,
    MAX_APPLICATION_HTTP_PATH_CHARS,
    MAX_APPLICATION_HTTP_QUERY_ITEMS,
    MAX_APPLICATION_HTTP_QUERY_VALUE_CHARS,
    MAX_APPLICATION_HTTP_RESPONSE_BYTES,
)
from .site_host import MarketplaceSiteHostAdapter


MAX_ASGI_HEADER_COUNT: Final = 64
MAX_ASGI_HEADER_BYTES: Final = 32 * 1024
MAX_ASGI_QUERY_BYTES: Final = 4 * 1024
MAX_ASGI_REQUEST_EVENTS: Final = 64

_SENSITIVE_REQUEST_HEADERS = frozenset(
    {"authorization", "cookie", "proxy-authorization"}
)
_FORBIDDEN_RESPONSE_HEADERS = frozenset({"set-cookie"})
_HEX_DIGITS = frozenset(b"0123456789abcdefABCDEF")
_HTTP_TOKEN = frozenset("!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

AsgiReceive = Callable[[], Awaitable[dict[str, Any]]]
AsgiSend = Callable[[dict[str, Any]], Awaitable[None]]


class AsgiHttpAdapterError(RuntimeError):
    """Stable fail-closed M17.1L host-boundary error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AsgiHttpAdapterError(code, message) from None


def _decode_query_component(raw: bytes) -> str:
    if not raw or b"+" in raw:
        _fail("ASGI_QUERY_INVALID", "query component is empty or ambiguous")
    decoded = bytearray()
    index = 0
    while index < len(raw):
        value = raw[index]
        if value == 0x25:
            if index + 2 >= len(raw):
                _fail("ASGI_QUERY_INVALID", "query percent escape is incomplete")
            high = raw[index + 1]
            low = raw[index + 2]
            if high not in _HEX_DIGITS or low not in _HEX_DIGITS:
                _fail("ASGI_QUERY_INVALID", "query percent escape is invalid")
            decoded.append(int(bytes((high, low)), 16))
            index += 3
            continue
        if value < 0x21 or value > 0x7E:
            _fail("ASGI_QUERY_INVALID", "query contains noncanonical raw bytes")
        decoded.append(value)
        index += 1
    try:
        text = bytes(decoded).decode("utf-8", "strict")
    except UnicodeDecodeError:
        _fail("ASGI_QUERY_INVALID", "query is not strict UTF-8")
    if (
        not text
        or len(text) > MAX_APPLICATION_HTTP_QUERY_VALUE_CHARS
        or any(ord(char) < 32 or ord(char) == 127 for char in text)
    ):
        _fail("ASGI_QUERY_INVALID", "query component is outside the reviewed bound")
    return text


def _parse_query(raw: object) -> tuple[tuple[str, str], ...]:
    if type(raw) is not bytes or len(raw) > MAX_ASGI_QUERY_BYTES:
        _fail("ASGI_QUERY_INVALID", "query string is outside the reviewed byte bound")
    if not raw:
        return ()
    pairs = raw.split(b"&")
    if len(pairs) > MAX_APPLICATION_HTTP_QUERY_ITEMS:
        _fail("ASGI_QUERY_INVALID", "query contains too many members")
    result: list[tuple[str, str]] = []
    names: set[str] = set()
    for pair in pairs:
        if pair.count(b"=") != 1:
            _fail("ASGI_QUERY_INVALID", "query member is not canonical name=value")
        raw_name, raw_value = pair.split(b"=", 1)
        name = _decode_query_component(raw_name)
        value = _decode_query_component(raw_value)
        if name in names:
            _fail("ASGI_QUERY_INVALID", "duplicate query name is forbidden")
        names.add(name)
        result.append((name, value))
    return tuple(result)


def _review_headers(raw_headers: object) -> tuple[str | None, int | None]:
    if type(raw_headers) not in {list, tuple} or len(raw_headers) > MAX_ASGI_HEADER_COUNT:
        _fail("ASGI_HEADER_INVALID", "ASGI headers are outside the reviewed count bound")
    content_type: str | None = None
    content_length: int | None = None
    total = 0
    for pair in raw_headers:
        if type(pair) not in {list, tuple} or len(pair) != 2:
            _fail("ASGI_HEADER_INVALID", "ASGI header pair is invalid")
        raw_name, raw_value = pair
        if type(raw_name) is not bytes or type(raw_value) is not bytes:
            _fail("ASGI_HEADER_INVALID", "ASGI headers must be exact bytes")
        total += len(raw_name) + len(raw_value) + 4
        if total > MAX_ASGI_HEADER_BYTES:
            _fail("ASGI_HEADER_INVALID", "ASGI headers exceed the reviewed byte bound")
        try:
            name = raw_name.decode("ascii", "strict")
        except UnicodeDecodeError:
            _fail("ASGI_HEADER_INVALID", "ASGI header name is not ASCII")
        if not name or any(char not in _HTTP_TOKEN for char in name):
            _fail("ASGI_HEADER_INVALID", "ASGI header name is not a valid HTTP token")
        name = name.lower()
        if name in _SENSITIVE_REQUEST_HEADERS:
            _fail(
                "ASGI_SENSITIVE_HEADER_FORBIDDEN",
                "credentials and session headers are outside the M17.1L boundary",
            )
        if name == "content-type":
            if content_type is not None:
                _fail("ASGI_HEADER_INVALID", "duplicate content-type is forbidden")
            try:
                value = raw_value.decode("ascii", "strict")
            except UnicodeDecodeError:
                _fail("ASGI_HEADER_INVALID", "content-type is not ASCII")
            if (
                not value
                or len(value) > 128
                or any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)
            ):
                _fail("ASGI_HEADER_INVALID", "content-type is outside the reviewed bound")
            content_type = value
        elif name == "content-length":
            if content_length is not None:
                _fail("ASGI_HEADER_INVALID", "duplicate content-length is forbidden")
            try:
                value = raw_value.decode("ascii", "strict")
            except UnicodeDecodeError:
                _fail("ASGI_HEADER_INVALID", "content-length is not ASCII")
            if (
                not value
                or not value.isdecimal()
                or not value.isascii()
                or (len(value) > 1 and value.startswith("0"))
            ):
                _fail("ASGI_HEADER_INVALID", "content-length is not canonical decimal")
            content_length = int(value)
            if content_length > MAX_APPLICATION_HTTP_BODY_BYTES:
                _fail("ASGI_REQUEST_TOO_LARGE", "request body exceeds the reviewed bound")
    return content_type, content_length


def _review_scope(scope: object) -> tuple[str, str, tuple[tuple[str, str], ...], str | None, int | None]:
    if type(scope) is not dict:
        _fail("ASGI_SCOPE_INVALID", "ASGI scope must be an exact dict")
    if scope.get("type") != "http":
        _fail("ASGI_SCOPE_UNSUPPORTED", "M17.1L accepts HTTP scope only")
    asgi = scope.get("asgi")
    if type(asgi) is not dict or asgi.get("version") != "3.0":
        _fail("ASGI_SCOPE_INVALID", "M17.1L requires the ASGI 3 callable contract")
    if scope.get("root_path", "") != "":
        _fail("ASGI_SCOPE_INVALID", "mounted root_path is outside the same-origin root contract")
    http_version = scope.get("http_version")
    if http_version not in {"1.0", "1.1", "2"}:
        _fail("ASGI_SCOPE_INVALID", "HTTP version is outside the reviewed ASGI profile")
    method = scope.get("method")
    path = scope.get("path")
    if (
        type(method) is not str
        or not method
        or len(method) > 8
        or not method.isascii()
        or method != method.upper()
        or any(char not in _HTTP_TOKEN for char in method)
    ):
        _fail("ASGI_SCOPE_INVALID", "HTTP method is outside the reviewed profile")
    if (
        type(path) is not str
        or not path.startswith("/")
        or path.startswith("//")
        or len(path) > MAX_APPLICATION_HTTP_PATH_CHARS
        or any(ord(char) < 32 or ord(char) == 127 for char in path)
    ):
        _fail("ASGI_SCOPE_INVALID", "decoded HTTP path is outside the reviewed profile")
    raw_path = scope.get("raw_path")
    if raw_path is not None and type(raw_path) is not bytes:
        _fail("ASGI_SCOPE_INVALID", "raw_path must be bytes when supplied")
    query = _parse_query(scope.get("query_string", b""))
    content_type, content_length = _review_headers(scope.get("headers", []))
    return method, path, query, content_type, content_length


async def _read_request_body(
    receive: AsgiReceive,
    *,
    expected_length: int | None,
) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for _ in range(MAX_ASGI_REQUEST_EVENTS):
        event = await receive()
        if type(event) is not dict or type(event.get("type")) is not str:
            _fail("ASGI_EVENT_INVALID", "ASGI receive event is invalid")
        if event["type"] == "http.disconnect":
            _fail("ASGI_REQUEST_DISCONNECTED", "request disconnected before completion")
        if event["type"] != "http.request":
            _fail("ASGI_EVENT_INVALID", "unexpected ASGI receive event")
        body = event.get("body", b"")
        more_body = event.get("more_body", False)
        if type(body) is not bytes or type(more_body) is not bool:
            _fail("ASGI_EVENT_INVALID", "http.request body fields are invalid")
        total += len(body)
        if total > MAX_APPLICATION_HTTP_BODY_BYTES:
            _fail("ASGI_REQUEST_TOO_LARGE", "request body exceeds the reviewed bound")
        chunks.append(body)
        if not more_body:
            result = b"".join(chunks)
            if expected_length is not None and len(result) != expected_length:
                _fail("ASGI_CONTENT_LENGTH_MISMATCH", "content-length does not match request body")
            return result
    _fail("ASGI_EVENT_LIMIT_EXCEEDED", "request body did not complete within the reviewed event bound")


def _response_headers(response: ApplicationHttpResponse) -> list[tuple[bytes, bytes]]:
    if type(response.headers) is not tuple or len(response.headers) > MAX_ASGI_HEADER_COUNT:
        _fail("ASGI_RESPONSE_INVALID", "application response headers are invalid")
    values: list[tuple[bytes, bytes]] = []
    names: set[str] = set()
    content_length: int | None = None
    total = 0
    for pair in response.headers:
        if type(pair) is not tuple or len(pair) != 2:
            _fail("ASGI_RESPONSE_INVALID", "application response header pair is invalid")
        name, value = pair
        if type(name) is not str or type(value) is not str:
            _fail("ASGI_RESPONSE_INVALID", "application response headers must be exact text")
        try:
            raw_name = name.encode("ascii", "strict")
            raw_value = value.encode("ascii", "strict")
        except UnicodeEncodeError:
            _fail("ASGI_RESPONSE_INVALID", "application response headers must be ASCII")
        lower_name = name.lower()
        if (
            not lower_name
            or any(char not in _HTTP_TOKEN for char in lower_name)
            or lower_name in names
            or b"\r" in raw_value
            or b"\n" in raw_value
            or any(byte < 0x20 or byte == 0x7F for byte in raw_value)
        ):
            _fail("ASGI_RESPONSE_INVALID", "application response header is not canonical")
        if lower_name in _FORBIDDEN_RESPONSE_HEADERS:
            _fail("ASGI_RESPONSE_INVALID", "session response headers are outside M17.1L")
        names.add(lower_name)
        total += len(raw_name) + len(raw_value) + 4
        if total > MAX_ASGI_HEADER_BYTES:
            _fail("ASGI_RESPONSE_INVALID", "application response headers exceed the reviewed bound")
        if lower_name == "content-length":
            if not value.isascii() or not value.isdecimal() or (len(value) > 1 and value.startswith("0")):
                _fail("ASGI_RESPONSE_INVALID", "response content-length is not canonical")
            content_length = int(value)
        values.append((lower_name.encode("ascii"), raw_value))
    if content_length is None or content_length != len(response.body):
        _fail("ASGI_RESPONSE_INVALID", "response content-length does not match response body")
    return values


class MarketplaceAsgiHttpAdapter:
    """Translate one ASGI HTTP request into the existing inert site host."""

    __slots__ = ("_site",)

    def __init__(self, *, site: MarketplaceSiteHostAdapter) -> None:
        if type(site) is not MarketplaceSiteHostAdapter:
            raise TypeError("site MUST be exact MarketplaceSiteHostAdapter")
        self._site = site

    async def __call__(self, scope: dict[str, Any], receive: AsgiReceive, send: AsgiSend) -> None:
        if not callable(receive) or not callable(send):
            raise TypeError("ASGI receive and send MUST be callable")
        method, path, query, content_type, content_length = _review_scope(scope)
        body = await _read_request_body(receive, expected_length=content_length)
        request = ApplicationHttpRequest(method, path, query, content_type, body)
        try:
            response = self._site.handle(request)
        except Exception:
            _fail("ASGI_SITE_FAILURE", "Marketplace site host could not complete safely")
        if (
            type(response) is not ApplicationHttpResponse
            or type(response.status_code) is not int
            or not 100 <= response.status_code <= 599
            or type(response.reason) is not str
            or type(response.body) is not bytes
            or len(response.body) > MAX_APPLICATION_HTTP_RESPONSE_BYTES
        ):
            _fail("ASGI_RESPONSE_INVALID", "Marketplace site host returned an invalid response")
        headers = _response_headers(response)
        await send(
            {
                "type": "http.response.start",
                "status": response.status_code,
                "headers": headers,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": response.body,
                "more_body": False,
            }
        )


__all__ = [
    "MAX_ASGI_HEADER_BYTES",
    "MAX_ASGI_HEADER_COUNT",
    "MAX_ASGI_QUERY_BYTES",
    "MAX_ASGI_REQUEST_EVENTS",
    "AsgiHttpAdapterError",
    "MarketplaceAsgiHttpAdapter",
]
