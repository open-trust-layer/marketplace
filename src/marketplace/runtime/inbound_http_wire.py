"""Bounded transport-free HTTP/1.1 wire framing around the M34 application adapter.

M35 consumes one complete already-received request byte sequence, validates a
small canonical HTTP/1.1 profile, invokes M34 exactly once, frames one success
response, and stops before any network transmission.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Final

from .inbound_http import (
    DEFAULT_MAX_INBOUND_HTTP_HEADER_BYTES,
    DEFAULT_MAX_INBOUND_HTTP_REQUEST_BYTES,
    DEFAULT_MAX_INBOUND_HTTP_RESPONSE_BYTES,
    MAX_INBOUND_HTTP_BODY_BYTES,
    MAX_INBOUND_HTTP_HEADER_BYTES,
    MAX_INBOUND_HTTP_HEADERS,
    BoundedInboundHttpApplicationAdapter,
    InboundHttpError,
    InboundHttpRequest,
    PreparedInboundHttpResponse,
)

DEFAULT_MAX_INBOUND_HTTP_WIRE_HEADER_BYTES: Final = DEFAULT_MAX_INBOUND_HTTP_HEADER_BYTES
DEFAULT_MAX_INBOUND_HTTP_WIRE_BODY_BYTES: Final = DEFAULT_MAX_INBOUND_HTTP_REQUEST_BYTES
DEFAULT_MAX_INBOUND_HTTP_WIRE_RESPONSE_BODY_BYTES: Final = DEFAULT_MAX_INBOUND_HTTP_RESPONSE_BYTES
MAX_INBOUND_HTTP_WIRE_HEADER_BYTES: Final = MAX_INBOUND_HTTP_HEADER_BYTES
MAX_INBOUND_HTTP_WIRE_BODY_BYTES: Final = MAX_INBOUND_HTTP_BODY_BYTES
MAX_INBOUND_HTTP_WIRE_RESPONSE_BODY_BYTES: Final = MAX_INBOUND_HTTP_BODY_BYTES
MAX_INBOUND_HTTP_WIRE_HEADERS: Final = MAX_INBOUND_HTTP_HEADERS + 1
MAX_INBOUND_HTTP_WIRE_HEADER_NAME_BYTES: Final = 64
MAX_INBOUND_HTTP_WIRE_HEADER_VALUE_BYTES: Final = 4_096
MAX_INBOUND_HTTP_AUTHORITY_BYTES: Final = 255

_HEADER_TERMINATOR = b"\r\n\r\n"
_CANONICAL_WIRE_HEADER_NAMES = {
    "host": "Host",
    "accept": "Accept",
    "connection": "Connection",
    "content-length": "Content-Length",
    "content-type": "Content-Type",
}
_APPLICATION_HEADER_NAMES = frozenset(
    {"accept", "connection", "content-length", "content-type"}
)


class InboundHttpWireError(RuntimeError):
    """Fail-closed M35 error with a stable local reason code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise InboundHttpWireError(code, message)


def _canonical_authority(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("authority MUST be non-empty exact text")
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("authority MUST use exact ASCII") from exc
    if len(encoded) > MAX_INBOUND_HTTP_AUTHORITY_BYTES:
        raise ValueError("authority exceeds the M35 bound")
    if any(byte <= 0x20 or byte == 0x7F for byte in encoded):
        raise ValueError("authority contains whitespace/control bytes")
    if value.lower() != value:
        raise ValueError("authority MUST already be lowercase canonical text")
    if any(ch in value for ch in "/\\@?#%[]"):
        raise ValueError("authority contains forbidden delimiter text")
    if value.endswith(".") or value.startswith(".") or ".." in value:
        raise ValueError("authority has noncanonical dot placement")

    host = value
    port_text: str | None = None
    if ":" in value:
        if value.count(":") != 1:
            raise ValueError("authority supports at most one explicit port delimiter")
        host, port_text = value.rsplit(":", 1)
        if not port_text or len(port_text) > 5 or not port_text.isascii() or not port_text.isdecimal():
            raise ValueError("authority port MUST be canonical bounded decimal text")
        if len(port_text) > 1 and port_text.startswith("0"):
            raise ValueError("authority port MUST NOT contain leading zeroes")
        port = int(port_text)
        if not 1 <= port <= 65535:
            raise ValueError("authority port is outside 1..65535")

    if not host or len(host.encode("ascii")) > 253:
        raise ValueError("authority host is outside the M35 bound")
    labels = host.split(".")
    for label in labels:
        if not 1 <= len(label) <= 63:
            raise ValueError("authority label is outside DNS text bounds")
        if label[0] == "-" or label[-1] == "-":
            raise ValueError("authority label MUST NOT start or end with hyphen")
        if any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in label):
            raise ValueError("authority host is outside the M35 canonical subset")
    return value


@dataclass(frozen=True)
class InboundHttpWireLimits:
    max_header_bytes: int = DEFAULT_MAX_INBOUND_HTTP_WIRE_HEADER_BYTES
    max_body_bytes: int = DEFAULT_MAX_INBOUND_HTTP_WIRE_BODY_BYTES
    max_response_body_bytes: int = DEFAULT_MAX_INBOUND_HTTP_WIRE_RESPONSE_BODY_BYTES

    def __post_init__(self) -> None:
        for name, value, maximum in (
            ("max_header_bytes", self.max_header_bytes, MAX_INBOUND_HTTP_WIRE_HEADER_BYTES),
            ("max_body_bytes", self.max_body_bytes, MAX_INBOUND_HTTP_WIRE_BODY_BYTES),
            (
                "max_response_body_bytes",
                self.max_response_body_bytes,
                MAX_INBOUND_HTTP_WIRE_RESPONSE_BODY_BYTES,
            ),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError(f"{name} MUST be within 1..{maximum}")


def _request_snapshot(request: InboundHttpRequest) -> tuple[Any, ...]:
    return (
        "m35-canonical-request-v1",
        request.method,
        request.path,
        request.headers,
        request.body,
        request.request_authenticated,
        request.peer_identity_proven,
    )


def _response_prefix(body_length: int) -> bytes:
    return (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {body_length}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii")


@dataclass(frozen=True)
class PreparedInboundHttpWireExchange:
    """One fully framed response prepared in memory and never transmitted."""

    request: InboundHttpRequest
    host_authority: str
    route_kind: str
    route_operation: str
    status_code: int
    response_body_bytes: int
    response_bytes: bytes
    olp_message_type: str
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    host_authority_validated: bool = field(default=True, init=False)
    tls_sni_bound: bool = field(default=False, init=False)
    transmitted: bool = field(default=False, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    establishes_marketplace_truth: bool = field(default=False, init=False)
    establishes_trust: bool = field(default=False, init=False)
    establishes_authorization: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.request) is not InboundHttpRequest:
            raise ValueError("request has the wrong type")
        if self.request.request_authenticated is not False or self.request.peer_identity_proven is not False:
            raise ValueError("request authority facts MUST remain false")
        authority = _canonical_authority(self.host_authority)
        if type(self.route_kind) is not str or not self.route_kind:
            raise ValueError("route_kind MUST be non-empty exact text")
        if type(self.route_operation) is not str or not self.route_operation:
            raise ValueError("route_operation MUST be non-empty exact text")
        if type(self.status_code) is not int or self.status_code != 200:
            raise ValueError("M35 success status MUST be exact integer 200")
        if type(self.response_body_bytes) is not int or self.response_body_bytes < 1:
            raise ValueError("response_body_bytes MUST be a positive exact integer")
        if type(self.response_bytes) is not bytes:
            raise ValueError("response_bytes MUST be exact immutable bytes")
        if type(self.olp_message_type) is not str or not self.olp_message_type:
            raise ValueError("olp_message_type MUST be non-empty exact text")
        for name, expected in (
            ("host_authority_validated", True),
            ("tls_sni_bound", False),
            ("transmitted", False),
            ("request_authenticated", False),
            ("peer_identity_proven", False),
            ("establishes_marketplace_truth", False),
            ("establishes_trust", False),
            ("establishes_authorization", False),
            ("authorizes_protected_side_effects", False),
        ):
            if getattr(self, name, None) is not expected:
                raise ValueError("prepared M35 wire exchange promoted a forbidden authority fact")
        prefix = _response_prefix(self.response_body_bytes)
        if not self.response_bytes.startswith(prefix):
            raise ValueError("response_bytes do not use the exact M35 HTTP/1.1 success profile")
        if len(self.response_bytes) != len(prefix) + self.response_body_bytes:
            raise ValueError("response body length does not match the M35 frame")
        current = (
            "prepared-inbound-http-wire-exchange-v1",
            _request_snapshot(self.request),
            authority,
            self.route_kind,
            self.route_operation,
            self.status_code,
            self.response_body_bytes,
            self.response_bytes,
            self.olp_message_type,
            self.host_authority_validated,
            self.tls_sni_bound,
            self.transmitted,
            self.request_authenticated,
            self.peer_identity_proven,
            self.establishes_marketplace_truth,
            self.establishes_trust,
            self.establishes_authorization,
            self.authorizes_protected_side_effects,
        )
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("prepared M35 wire exchange integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)
        object.__setattr__(self, "host_authority", authority)


class BoundedInboundHttpWireAdapter:
    """Parse and frame one complete HTTP/1.1 exchange without network I/O."""

    def __init__(
        self,
        *,
        application_adapter: BoundedInboundHttpApplicationAdapter,
        authority: str,
        limits: InboundHttpWireLimits | None = None,
    ) -> None:
        if type(application_adapter) is not BoundedInboundHttpApplicationAdapter:
            raise TypeError("application_adapter MUST be exact BoundedInboundHttpApplicationAdapter")
        canonical_authority = _canonical_authority(authority)
        if limits is None:
            limits = InboundHttpWireLimits()
        if type(limits) is not InboundHttpWireLimits:
            raise TypeError("limits MUST be exact InboundHttpWireLimits")
        detached_limits = InboundHttpWireLimits(
            max_header_bytes=limits.max_header_bytes,
            max_body_bytes=limits.max_body_bytes,
            max_response_body_bytes=limits.max_response_body_bytes,
        )
        app_limits = application_adapter.limits
        if detached_limits.max_header_bytes > app_limits.max_header_bytes:
            raise ValueError("M35 header limit MUST NOT exceed the configured M34 header limit")
        if detached_limits.max_body_bytes > app_limits.max_request_body_bytes:
            raise ValueError("M35 body limit MUST NOT exceed the configured M34 request-body limit")
        if detached_limits.max_response_body_bytes > app_limits.max_response_body_bytes:
            raise ValueError("M35 response-body limit MUST NOT exceed the configured M34 response-body limit")
        self._application_adapter = application_adapter
        self._authority = canonical_authority
        self._limits = detached_limits

    @property
    def authority(self) -> str:
        return self._authority

    @property
    def limits(self) -> InboundHttpWireLimits:
        return self._limits

    def _parse_request(self, raw: bytes) -> InboundHttpRequest:
        if type(raw) is not bytes:
            _fail("INVALID_REQUEST_BYTES", "M35 request input MUST be exact immutable bytes")
        hard_total = self._limits.max_header_bytes + self._limits.max_body_bytes
        if not raw or len(raw) > hard_total:
            _fail("REQUEST_WIRE_LIMIT_EXCEEDED", "request bytes exceed the configured M35 total bound")

        marker_at = raw.find(_HEADER_TERMINATOR)
        if marker_at < 0:
            _fail("INCOMPLETE_HTTP_HEAD", "request does not contain one complete HTTP/1.1 head")
        head_end = marker_at + len(_HEADER_TERMINATOR)
        if head_end > self._limits.max_header_bytes:
            _fail("HTTP_HEADER_LIMIT_EXCEEDED", "request head exceeds the configured M35 header bound")
        body = raw[head_end:]
        if len(body) > self._limits.max_body_bytes:
            _fail("HTTP_BODY_LIMIT_EXCEEDED", "request body exceeds the configured M35 body bound")

        head = raw[:marker_at]
        scrubbed = head.replace(b"\r\n", b"")
        if b"\r" in scrubbed or b"\n" in scrubbed:
            _fail("NONCANONICAL_LINE_ENDING", "M35 requires exact CRLF request line endings")
        try:
            lines = head.decode("ascii").split("\r\n")
        except UnicodeDecodeError:
            _fail("NONASCII_HTTP_HEAD", "M35 request line and headers MUST be ASCII")
        if len(lines) < 2:
            _fail("MALFORMED_HTTP_HEAD", "request head is missing required fields")

        request_line = lines[0]
        if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in request_line):
            _fail("MALFORMED_REQUEST_LINE", "request line contains a control character")
        parts = request_line.split(" ")
        if len(parts) != 3 or any(not part for part in parts):
            _fail("MALFORMED_REQUEST_LINE", "request line MUST use exactly two single SP separators")
        method, path, version = parts
        if method not in {"GET", "POST"}:
            _fail("UNSUPPORTED_METHOD", "M35 supports exact GET or POST only")
        if version != "HTTP/1.1":
            _fail("UNSUPPORTED_HTTP_VERSION", "M35 accepts exact HTTP/1.1 only")
        if not path.startswith("/") or path.startswith("//"):
            _fail("UNSUPPORTED_REQUEST_TARGET", "M35 accepts origin-form request targets only")

        headers: dict[str, str] = {}
        for line in lines[1:]:
            if not line or line[0] in " \t":
                _fail("MALFORMED_HEADER", "empty or folded request header line is forbidden")
            if ": " not in line:
                _fail("MALFORMED_HEADER", "request headers MUST use exact 'Name: value' form")
            name, value = line.split(": ", 1)
            if not name or ":" in name:
                _fail("MALFORMED_HEADER", "request header name is malformed")
            lower = name.lower()
            if lower in headers:
                _fail("DUPLICATE_HEADER", "duplicate request headers are forbidden case-insensitively")
            canonical_name = _CANONICAL_WIRE_HEADER_NAMES.get(lower)
            if canonical_name is None:
                _fail("UNSUPPORTED_HEADER", "request header is outside the M35 wire profile")
            if name != canonical_name:
                _fail("NONCANONICAL_HEADER_NAME", "request header name is not in canonical M35 form")
            try:
                name_bytes = name.encode("ascii")
                value_bytes = value.encode("ascii")
            except UnicodeEncodeError:
                _fail("NONASCII_HEADER", "request headers MUST use exact ASCII")
            if len(name_bytes) > MAX_INBOUND_HTTP_WIRE_HEADER_NAME_BYTES:
                _fail("HEADER_NAME_LIMIT_EXCEEDED", "request header name exceeds the M35 bound")
            if len(value_bytes) > MAX_INBOUND_HTTP_WIRE_HEADER_VALUE_BYTES:
                _fail("HEADER_VALUE_LIMIT_EXCEEDED", "request header value exceeds the M35 bound")
            if not value or any(byte < 0x20 or byte == 0x7F for byte in value_bytes):
                _fail("UNSAFE_HEADER_VALUE", "request header value is empty or contains controls")
            headers[lower] = value
            if len(headers) > MAX_INBOUND_HTTP_WIRE_HEADERS:
                _fail("HEADER_COUNT_LIMIT_EXCEEDED", "request exceeds the M35 header-count bound")

        host = headers.get("host")
        if host is None:
            _fail("HOST_REQUIRED", "HTTP/1.1 request requires one exact Host header")
        if host != self._authority:
            _fail("HOST_AUTHORITY_MISMATCH", "request Host does not match the configured M35 authority")
        if headers.get("connection") != "close":
            _fail("CONNECTION_CLOSE_REQUIRED", "M35 requires exact Connection: close")

        declared = headers.get("content-length")
        if declared is None:
            if body:
                _fail("UNDECLARED_BODY_BYTES", "request contains body bytes without Content-Length")
        else:
            if (
                not declared.isascii()
                or not declared.isdecimal()
                or (len(declared) > 1 and declared.startswith("0"))
            ):
                _fail("NONCANONICAL_CONTENT_LENGTH", "Content-Length MUST use canonical decimal text")
            if declared != str(len(body)):
                _fail("CONTENT_LENGTH_MISMATCH", "Content-Length does not delimit exactly the supplied request body")

        app_headers = tuple(
            sorted(
                ((name, value) for name, value in headers.items() if name in _APPLICATION_HEADER_NAMES),
                key=lambda item: item[0].encode("ascii"),
            )
        )
        try:
            return InboundHttpRequest(
                method=method,
                path=path,
                headers=app_headers,
                body=body,
                max_header_bytes=self._limits.max_header_bytes,
            )
        except ValueError:
            _fail("APPLICATION_REQUEST_SHAPE_REJECTED", "parsed request is outside the canonical M34 request profile")

    def parse_request(self, raw: bytes) -> InboundHttpRequest:
        """Parse one complete request without invoking M34 or any disclosure helper."""
        return self._parse_request(raw)

    def _validated_application_response(
        self,
        result: PreparedInboundHttpResponse,
        *,
        request: InboundHttpRequest,
    ) -> PreparedInboundHttpResponse:
        if type(result) is not PreparedInboundHttpResponse:
            _fail("INVALID_APPLICATION_RESPONSE", "M34 returned an unexpected result type")
        for name in (
            "transmitted",
            "request_authenticated",
            "peer_identity_proven",
            "establishes_marketplace_truth",
            "establishes_trust",
            "establishes_authorization",
            "authorizes_protected_side_effects",
        ):
            if getattr(result, name, None) is not False:
                _fail("APPLICATION_AUTHORITY_ESCALATION", "M34 response promoted a forbidden authority fact")
        try:
            witnessed = replace(result)
        except (TypeError, ValueError):
            _fail("APPLICATION_RESPONSE_INTEGRITY_DRIFT", "M34 response no longer matches its integrity witness")
        if _request_snapshot(witnessed.request) != _request_snapshot(request):
            _fail("APPLICATION_REQUEST_BINDING_DRIFT", "M34 response is not bound to the parsed M35 request")
        if type(witnessed.body) is not bytes or not 1 <= len(witnessed.body) <= self._limits.max_response_body_bytes:
            _fail("RESPONSE_BODY_LIMIT_EXCEEDED", "M34 response body is outside the configured M35 bound")
        try:
            return PreparedInboundHttpResponse(
                request=request,
                route_kind=witnessed.route_kind,
                route_operation=witnessed.route_operation,
                status_code=witnessed.status_code,
                headers=witnessed.headers,
                body=witnessed.body,
                olp_message_type=witnessed.olp_message_type,
            )
        except ValueError:
            _fail("INVALID_APPLICATION_RESPONSE", "M34 response failed M35 integrity revalidation")

    def prepare(self, raw_request: bytes) -> PreparedInboundHttpWireExchange:
        """Prepare one response wire image and stop before transmission."""
        request = self._parse_request(raw_request)
        try:
            application_result = self._application_adapter.handle(request)
        except InboundHttpWireError:
            raise
        except InboundHttpError:
            _fail("APPLICATION_REQUEST_REJECTED", "M34 rejected the parsed inbound request")
        except Exception:
            _fail("APPLICATION_REQUEST_FAILED", "M34 could not prepare an inbound response")

        response = self._validated_application_response(application_result, request=request)
        prefix = _response_prefix(len(response.body))
        wire = prefix + response.body
        if len(wire) > self._limits.max_header_bytes + self._limits.max_response_body_bytes:
            _fail("RESPONSE_WIRE_LIMIT_EXCEEDED", "framed response exceeds the configured M35 bound")
        try:
            return PreparedInboundHttpWireExchange(
                request=request,
                host_authority=self._authority,
                route_kind=response.route_kind,
                route_operation=response.route_operation,
                status_code=response.status_code,
                response_body_bytes=len(response.body),
                response_bytes=wire,
                olp_message_type=response.olp_message_type,
            )
        except ValueError:
            _fail("INVALID_PREPARED_WIRE_RESPONSE", "could not construct immutable M35 wire response")
