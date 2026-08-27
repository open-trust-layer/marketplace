"""Bounded transport-free inbound HTTP application adapter.

M34 accepts one already-received canonical HTTP-shaped request value, routes it
into the existing M32 or M33 disclosure responder, serializes one strict OLP JSON
response, and stops before transmission. It contains no socket, listener, TLS
termination, HTTP byte-stream parser, retry loop, background worker, persistence,
or network write primitive.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Final, Protocol

from .inbound_federation import (
    BoundedInboundFederationResponder,
    PreparedInboundFederationResponse,
)
from .inbound_record import (
    BoundedInboundRecordResponder,
    PreparedInboundRecordResponse,
    _canonical_record_identity as canonical_record_identity_transport_text,
)
from .prepared_integrity import (
    MAX_PREPARED_SNAPSHOT_DEPTH,
    MAX_PREPARED_SNAPSHOT_ITEMS,
    PreparedExchangeIntegrityError,
    detach_host_value,
    host_value_integrity_snapshot,
)

DEFAULT_MAX_INBOUND_HTTP_REQUEST_BYTES: Final = 1 * 1024 * 1024
DEFAULT_MAX_INBOUND_HTTP_RESPONSE_BYTES: Final = 1 * 1024 * 1024
DEFAULT_MAX_INBOUND_HTTP_HEADER_BYTES: Final = 32 * 1024
MAX_INBOUND_HTTP_BODY_BYTES: Final = 16 * 1024 * 1024
MAX_INBOUND_HTTP_HEADER_BYTES: Final = 128 * 1024
MAX_INBOUND_HTTP_PATH_BYTES: Final = 2_048
MAX_INBOUND_HTTP_HEADERS: Final = 16
MAX_INBOUND_HTTP_CONTROL_ROUTES: Final = 64
MAX_INBOUND_HTTP_OPERATION_BYTES: Final = 512
MAX_INBOUND_HTTP_HEADER_NAME_BYTES: Final = 64
MAX_INBOUND_HTTP_HEADER_VALUE_BYTES: Final = 4_096

RECORD_ROUTE_PREFIX: Final = "/v1/records/"
ROUTE_FEDERATION_CONTROL: Final = "FEDERATION_CONTROL"
ROUTE_IMMUTABLE_RECORD: Final = "IMMUTABLE_RECORD"

_PATH_RE = re.compile(r"^/[A-Za-z0-9._~/-]*$")
_HEADER_NAME_RE = re.compile(r"^[a-z0-9-]+$")
_ALLOWED_REQUEST_HEADERS = frozenset(
    {"accept", "connection", "content-length", "content-type"}
)


class InboundHttpError(RuntimeError):
    """Fail-closed M34 error with a stable local reason code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise InboundHttpError(code, message)


class TransportEnvelopeJsonDecoder(Protocol):
    def __call__(self, body: bytes) -> Any: ...


class TransportEnvelopeJsonEncoder(Protocol):
    def __call__(self, envelope: Any) -> bytes: ...


def _bounded_ascii(value: object, *, label: str, maximum: int) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{label} MUST be non-empty exact text")
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{label} MUST use exact ASCII text") from exc
    if len(encoded) > maximum:
        raise ValueError(f"{label} exceeds its M34 byte bound")
    if any(byte < 0x21 or byte == 0x7F for byte in encoded):
        raise ValueError(f"{label} MUST NOT contain whitespace/control bytes")
    return value


def _canonical_path(value: object) -> str:
    path = _bounded_ascii(value, label="path", maximum=MAX_INBOUND_HTTP_PATH_BYTES)
    if "\\" in path or "%" in path:
        raise ValueError("path MUST NOT contain backslashes or percent-encoding")
    if not _PATH_RE.fullmatch(path):
        raise ValueError("path contains characters outside the M34 safe subset")
    if path != "/" and "//" in path:
        raise ValueError("path MUST NOT contain repeated slashes")
    if any(segment in {".", ".."} for segment in path.split("/")):
        raise ValueError("path MUST NOT contain dot segments")
    return path


def _canonical_operation(value: object) -> str:
    return _bounded_ascii(
        value,
        label="operation",
        maximum=MAX_INBOUND_HTTP_OPERATION_BYTES,
    )


def _canonical_headers(
    headers: object,
    *,
    max_header_bytes: int,
) -> tuple[tuple[str, str], ...]:
    if type(headers) is not tuple:
        raise ValueError("headers MUST be an exact tuple")
    if len(headers) > MAX_INBOUND_HTTP_HEADERS:
        raise ValueError("headers exceed the M34 header-count bound")
    normalized: list[tuple[str, str]] = []
    seen: set[str] = set()
    total = 0
    for pair in headers:
        if type(pair) is not tuple or len(pair) != 2:
            raise ValueError("each header MUST be an exact two-element tuple")
        name, value = pair
        if type(name) is not str or type(value) is not str:
            raise ValueError("header names and values MUST be exact text")
        try:
            name_bytes = name.encode("ascii")
            value_bytes = value.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError("headers MUST use unambiguous ASCII") from exc
        if (
            not name
            or len(name_bytes) > MAX_INBOUND_HTTP_HEADER_NAME_BYTES
            or not _HEADER_NAME_RE.fullmatch(name)
            or name.lower() != name
        ):
            raise ValueError("header name is not canonical lowercase HTTP token text")
        if name in seen:
            raise ValueError("duplicate request header is forbidden")
        if name not in _ALLOWED_REQUEST_HEADERS:
            raise ValueError("request header is outside the M34 application profile")
        if (
            len(value_bytes) > MAX_INBOUND_HTTP_HEADER_VALUE_BYTES
            or any(byte < 0x20 or byte == 0x7F for byte in value_bytes)
        ):
            raise ValueError("header value is outside the M34 bound")
        total += len(name_bytes) + 2 + len(value_bytes) + 2
        if total > max_header_bytes:
            raise ValueError("headers exceed the configured M34 byte bound")
        seen.add(name)
        normalized.append((name, value))
    canonical = tuple(sorted(normalized, key=lambda item: item[0].encode("ascii")))
    if tuple(headers) != canonical:
        raise ValueError("headers MUST already use canonical name ordering")
    return canonical


def _header_map(headers: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return dict(headers)


def _wire_value_snapshot(value: Any, *, depth: int = 0) -> tuple[Any, ...]:
    """Snapshot JSON/OLP wire meaning while ignoring list-vs-tuple host shape.

    M30's exact host snapshot remains authoritative for in-process mutation
    detection. JSON cannot preserve Python tuple/list distinction, so M34 uses
    this second bounded snapshot only when comparing a prepared envelope with
    its strict encode/decode round trip. Exact scalar types, map keys, sequence
    order, values, and resource limits remain bound.
    """
    if depth > MAX_PREPARED_SNAPSHOT_DEPTH:
        raise ValueError("wire value exceeds the M30 depth bound")
    if value is None:
        return ("none",)
    if type(value) is bool:
        return ("bool", value)
    if type(value) is int:
        return ("int", value)
    if type(value) is str:
        return ("str", value)
    if type(value) is bytes:
        return ("bytes", value)
    if isinstance(value, Mapping):
        if len(value) > MAX_PREPARED_SNAPSHOT_ITEMS:
            raise ValueError("wire map exceeds the M30 item bound")
        keys = tuple(value.keys())
        if any(type(key) is not str for key in keys):
            raise ValueError("wire maps require exact string keys")
        ordered = tuple(sorted(keys, key=lambda key: key.encode("utf-8")))
        return (
            "map",
            tuple(
                (key, _wire_value_snapshot(value[key], depth=depth + 1))
                for key in ordered
            ),
        )
    if isinstance(value, (tuple, list)):
        if len(value) > MAX_PREPARED_SNAPSHOT_ITEMS:
            raise ValueError("wire sequence exceeds the M30 item bound")
        return (
            "sequence",
            tuple(_wire_value_snapshot(item, depth=depth + 1) for item in value),
        )
    raise ValueError(f"unsupported wire host type: {type(value).__name__}")


@dataclass(frozen=True)
class InboundHttpApplicationLimits:
    max_request_body_bytes: int = DEFAULT_MAX_INBOUND_HTTP_REQUEST_BYTES
    max_response_body_bytes: int = DEFAULT_MAX_INBOUND_HTTP_RESPONSE_BYTES
    max_header_bytes: int = DEFAULT_MAX_INBOUND_HTTP_HEADER_BYTES

    def __post_init__(self) -> None:
        for name, value, maximum in (
            ("max_request_body_bytes", self.max_request_body_bytes, MAX_INBOUND_HTTP_BODY_BYTES),
            ("max_response_body_bytes", self.max_response_body_bytes, MAX_INBOUND_HTTP_BODY_BYTES),
            ("max_header_bytes", self.max_header_bytes, MAX_INBOUND_HTTP_HEADER_BYTES),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError(f"{name} MUST be within 1..{maximum}")


@dataclass(frozen=True)
class InboundFederationHttpRoute:
    """One exact local application path bound to one M32 operation."""

    path: str
    operation: str

    def __post_init__(self) -> None:
        path = _canonical_path(self.path)
        operation = _canonical_operation(self.operation)
        if path == "/" or path.endswith("/"):
            raise ValueError("control route path MUST be non-root and have no trailing slash")
        if path == "/v1/records" or path.startswith(RECORD_ROUTE_PREFIX):
            raise ValueError("control route MUST NOT overlap the immutable Record route namespace")
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "operation", operation)


@dataclass(frozen=True)
class InboundHttpRequest:
    """Canonical already-parsed application request; not a raw HTTP byte stream."""

    method: str
    path: str
    headers: tuple[tuple[str, str], ...]
    body: bytes
    max_header_bytes: int = field(
        default=DEFAULT_MAX_INBOUND_HTTP_HEADER_BYTES,
        repr=False,
        compare=False,
    )
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.method) is not str or self.method not in {"GET", "POST"}:
            raise ValueError("method MUST be exact GET or POST")
        path = _canonical_path(self.path)
        if type(self.max_header_bytes) is not int or not 1 <= self.max_header_bytes <= MAX_INBOUND_HTTP_HEADER_BYTES:
            raise ValueError("max_header_bytes is outside the M34 bound")
        headers = _canonical_headers(self.headers, max_header_bytes=self.max_header_bytes)
        if type(self.body) is not bytes:
            raise ValueError("body MUST be exact immutable bytes")
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "headers", headers)


def _request_snapshot(request: InboundHttpRequest) -> tuple[Any, ...]:
    return (
        "inbound-http-request-v1",
        request.method,
        request.path,
        request.headers,
        request.body,
    )


@dataclass(frozen=True)
class PreparedInboundHttpResponse:
    """One canonical application response prepared in memory but never transmitted."""

    request: InboundHttpRequest
    route_kind: str
    route_operation: str
    status_code: int
    headers: tuple[tuple[str, str], ...]
    body: bytes
    olp_message_type: str
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
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
        if self.route_kind not in {ROUTE_FEDERATION_CONTROL, ROUTE_IMMUTABLE_RECORD}:
            raise ValueError("route_kind is invalid")
        _canonical_operation(self.route_operation)
        if type(self.status_code) is not int or self.status_code != 200:
            raise ValueError("successful prepared M34 response status MUST be exact integer 200")
        if type(self.body) is not bytes or not self.body:
            raise ValueError("prepared response body MUST be non-empty exact bytes")
        if type(self.olp_message_type) is not str or not self.olp_message_type:
            raise ValueError("olp_message_type MUST be non-empty exact text")
        expected_headers = (
            ("connection", "close"),
            ("content-length", str(len(self.body))),
            ("content-type", "application/json"),
        )
        if self.headers != expected_headers:
            raise ValueError("prepared response headers are not the exact M34 success profile")
        current = (
            "prepared-inbound-http-response-v1",
            _request_snapshot(self.request),
            self.route_kind,
            self.route_operation,
            self.status_code,
            self.headers,
            self.body,
            self.olp_message_type,
        )
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("prepared inbound HTTP response integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpApplicationAdapter:
    """Route and serialize one canonical request without any network I/O."""

    def __init__(
        self,
        *,
        federation_responder: BoundedInboundFederationResponder,
        record_responder: BoundedInboundRecordResponder,
        control_routes: tuple[InboundFederationHttpRoute, ...],
        decode_transport_envelope_json: TransportEnvelopeJsonDecoder,
        encode_transport_envelope_json: TransportEnvelopeJsonEncoder,
        limits: InboundHttpApplicationLimits | None = None,
    ) -> None:
        if type(federation_responder) is not BoundedInboundFederationResponder:
            raise TypeError("federation_responder MUST be exact BoundedInboundFederationResponder")
        if type(record_responder) is not BoundedInboundRecordResponder:
            raise TypeError("record_responder MUST be exact BoundedInboundRecordResponder")
        if type(control_routes) is not tuple or not 1 <= len(control_routes) <= MAX_INBOUND_HTTP_CONTROL_ROUTES:
            raise ValueError("control_routes MUST be a bounded non-empty exact tuple")
        if not callable(decode_transport_envelope_json) or not callable(encode_transport_envelope_json):
            raise TypeError("M34 JSON decoder/encoder MUST be callable")
        if limits is None:
            limits = InboundHttpApplicationLimits()
        if type(limits) is not InboundHttpApplicationLimits:
            raise TypeError("limits MUST be exact InboundHttpApplicationLimits")

        by_path: dict[str, InboundFederationHttpRoute] = {}
        operations: set[str] = set()
        for route in control_routes:
            if type(route) is not InboundFederationHttpRoute:
                raise ValueError("control_routes MUST contain exact InboundFederationHttpRoute values")
            if route.path in by_path:
                raise ValueError("control route paths MUST be unique")
            if route.operation in operations:
                raise ValueError("one M32 operation MUST NOT be exposed through multiple M34 route aliases")
            by_path[route.path] = route
            operations.add(route.operation)

        self._federation_responder = federation_responder
        self._record_responder = record_responder
        self._routes = by_path
        self._decode_json = decode_transport_envelope_json
        self._encode_json = encode_transport_envelope_json
        self._limits = limits

    @property
    def limits(self) -> InboundHttpApplicationLimits:
        return self._limits

    def _validate_common_headers(self, request: InboundHttpRequest) -> dict[str, str]:
        headers = _header_map(request.headers)
        accept = headers.get("accept")
        connection = headers.get("connection")
        if accept is not None and accept != "application/json":
            _fail("UNSUPPORTED_ACCEPT", "request Accept value is outside the M34 application profile")
        if connection is not None and connection != "close":
            _fail("UNSUPPORTED_CONNECTION_PROFILE", "M34 accepts only connection-close application requests")
        return headers

    def _decode_control_request(self, request: InboundHttpRequest) -> tuple[Any, ...]:
        headers = self._validate_common_headers(request)
        if headers.get("content-type") != "application/json":
            _fail("CONTENT_TYPE_REQUIRED", "control POST requires exact application/json content type")
        declared = headers.get("content-length")
        if (
            declared is None
            or not declared.isascii()
            or not declared.isdecimal()
            or (len(declared) > 1 and declared.startswith("0"))
        ):
            _fail("CANONICAL_CONTENT_LENGTH_REQUIRED", "control POST requires one canonical decimal content length")
        if not request.body:
            _fail("EMPTY_CONTROL_BODY", "control POST requires a non-empty body")
        if len(request.body) > self._limits.max_request_body_bytes:
            _fail("REQUEST_BODY_LIMIT_EXCEEDED", "control POST body exceeds the configured M34 bound")
        if declared != str(len(request.body)):
            _fail("CONTENT_LENGTH_MISMATCH", "declared content length does not equal the supplied body")
        try:
            decoded = self._decode_json(request.body)
        except Exception:
            _fail("CONTROL_BODY_REJECTED", "control request body is not a valid strict OLP JSON envelope")
        try:
            detached = detach_host_value(decoded)
        except PreparedExchangeIntegrityError:
            _fail("CONTROL_ENVELOPE_UNSAFE", "decoded control envelope is outside the bounded immutable host profile")
        if type(detached) is not tuple or len(detached) != 4:
            _fail("CONTROL_ENVELOPE_INVALID", "decoded control request is not one exact OLP envelope")
        return detached

    def _validate_get_request(self, request: InboundHttpRequest) -> str:
        headers = self._validate_common_headers(request)
        if request.body:
            _fail("RECORD_GET_BODY_FORBIDDEN", "immutable Record GET MUST NOT contain a request body")
        if "content-type" in headers or "content-length" in headers:
            _fail("RECORD_GET_ENTITY_HEADERS_FORBIDDEN", "immutable Record GET MUST NOT contain entity-body headers")
        if not request.path.startswith(RECORD_ROUTE_PREFIX):
            _fail("ROUTE_NOT_FOUND", "request path is not a configured M34 route")
        identity = request.path[len(RECORD_ROUTE_PREFIX) :]
        if not identity or "/" in identity:
            _fail("INVALID_RECORD_ROUTE", "immutable Record path has invalid shape")
        try:
            return canonical_record_identity_transport_text(identity)
        except Exception:
            _fail("INVALID_RECORD_ROUTE", "immutable Record path identity is not canonical")

    def _validate_federation_result(
        self,
        result: PreparedInboundFederationResponse,
        *,
        operation: str,
    ) -> tuple[Any, ...]:
        if type(result) is not PreparedInboundFederationResponse:
            _fail("INVALID_FEDERATION_RESPONDER_RESULT", "M32 responder returned an unexpected result type")
        if result.request_context.operation != operation:
            _fail("FEDERATION_ROUTE_BINDING_DRIFT", "M32 result operation differs from selected route")
        for name, expected in (
            ("transmitted", False),
            ("request_authenticated", False),
            ("peer_identity_proven", False),
            ("absence_is_deletion_evidence", False),
            ("creates_agreement", False),
            ("establishes_truth", False),
            ("establishes_trust", False),
            ("authorizes_protected_side_effects", False),
        ):
            if getattr(result, name, None) is not expected:
                _fail("FEDERATION_RESPONDER_AUTHORITY_ESCALATION", "M32 result promoted a forbidden authority fact")
        if result.global_completeness != "UNKNOWN":
            _fail("FEDERATION_RESPONDER_AUTHORITY_ESCALATION", "M32 result promoted global completeness")
        return result.envelope

    def _validate_record_result(
        self,
        result: PreparedInboundRecordResponse,
        *,
        expected_identity: str,
    ) -> tuple[Any, ...]:
        if type(result) is not PreparedInboundRecordResponse:
            _fail("INVALID_RECORD_RESPONDER_RESULT", "M33 responder returned an unexpected result type")
        if result.request_context.requested_record_identity != expected_identity:
            _fail("RECORD_ROUTE_BINDING_DRIFT", "M33 result identity differs from selected Record route")
        if result.identity_verified is not True or result.marketplace_semantics_verified is not True:
            _fail("RECORD_RESPONDER_VERIFICATION_DRIFT", "M33 result lost required identity/semantic verification")
        for name in (
            "transmitted",
            "proofs_verified",
            "request_authenticated",
            "peer_identity_proven",
            "absence_is_deletion_evidence",
            "creates_agreement",
            "establishes_truth",
            "establishes_ownership",
            "establishes_authority",
            "establishes_trust",
            "establishes_authorization",
            "authorizes_protected_side_effects",
        ):
            if getattr(result, name, None) is not False:
                _fail("RECORD_RESPONDER_AUTHORITY_ESCALATION", "M33 result promoted a forbidden authority fact")
        if result.global_existence != "UNKNOWN":
            _fail("RECORD_RESPONDER_AUTHORITY_ESCALATION", "M33 result promoted global existence")
        return result.envelope

    def _serialize_response(
        self,
        *,
        request: InboundHttpRequest,
        route_kind: str,
        route_operation: str,
        envelope: tuple[Any, ...],
    ) -> PreparedInboundHttpResponse:
        try:
            envelope_snapshot = host_value_integrity_snapshot(envelope)
            wire_snapshot = _wire_value_snapshot(envelope)
        except (PreparedExchangeIntegrityError, ValueError):
            _fail("RESPONSE_ENVELOPE_UNSAFE", "prepared responder envelope is outside the M34 integrity profile")
        try:
            body = self._encode_json(envelope)
        except Exception:
            _fail("RESPONSE_ENCODING_FAILED", "prepared OLP response could not be encoded")
        if type(body) is not bytes or not body:
            _fail("INVALID_RESPONSE_ENCODER_RESULT", "response encoder MUST return non-empty exact bytes")
        if len(body) > self._limits.max_response_body_bytes:
            _fail("RESPONSE_BODY_LIMIT_EXCEEDED", "encoded response exceeds the configured M34 bound")
        if host_value_integrity_snapshot(envelope) != envelope_snapshot:
            _fail("RESPONSE_ENCODER_MUTATED_ENVELOPE", "response encoder mutated the prepared responder envelope")
        try:
            round_trip = self._decode_json(body)
            detached_round_trip = detach_host_value(round_trip)
            round_trip_snapshot = _wire_value_snapshot(detached_round_trip)
        except Exception:
            _fail("RESPONSE_ROUND_TRIP_FAILED", "encoded response failed strict local round-trip verification")
        if round_trip_snapshot != wire_snapshot:
            _fail("RESPONSE_SERIALIZATION_DRIFT", "encoded response no longer represents the prepared responder envelope")
        headers = (
            ("connection", "close"),
            ("content-length", str(len(body))),
            ("content-type", "application/json"),
        )
        message_type = envelope[2]
        if type(message_type) is not str or not message_type:
            _fail("INVALID_RESPONSE_MESSAGE_TYPE", "prepared responder envelope message type is invalid")
        try:
            return PreparedInboundHttpResponse(
                request=request,
                route_kind=route_kind,
                route_operation=route_operation,
                status_code=200,
                headers=headers,
                body=body,
                olp_message_type=message_type,
            )
        except ValueError:
            _fail("INVALID_PREPARED_HTTP_RESPONSE", "could not construct immutable M34 response")

    def handle(self, request: InboundHttpRequest) -> PreparedInboundHttpResponse:
        """Handle exactly one canonical request and stop before transmission."""
        if type(request) is not InboundHttpRequest:
            _fail("INVALID_REQUEST_TYPE", "request MUST be exact InboundHttpRequest")
        if len(request.body) > self._limits.max_request_body_bytes:
            _fail("REQUEST_BODY_LIMIT_EXCEEDED", "request body exceeds the configured M34 bound")
        try:
            _canonical_headers(request.headers, max_header_bytes=self._limits.max_header_bytes)
        except ValueError:
            _fail("INVALID_REQUEST_HEADERS", "request headers are outside the configured M34 profile")

        route = self._routes.get(request.path)
        if route is not None:
            if request.method != "POST":
                _fail("METHOD_NOT_ALLOWED", "configured federation control route requires exact POST")
            envelope = self._decode_control_request(request)
            request_snapshot = host_value_integrity_snapshot(envelope)
            try:
                result = self._federation_responder.prepare_response(
                    envelope,
                    operation=route.operation,
                )
            except Exception:
                _fail("FEDERATION_REQUEST_REJECTED", "M32 rejected the inbound federation request")
            if host_value_integrity_snapshot(envelope) != request_snapshot:
                _fail("FEDERATION_RESPONDER_MUTATED_REQUEST", "M32 mutated the detached control request envelope")
            response_envelope = self._validate_federation_result(result, operation=route.operation)
            return self._serialize_response(
                request=request,
                route_kind=ROUTE_FEDERATION_CONTROL,
                route_operation=route.operation,
                envelope=response_envelope,
            )

        if request.path.startswith(RECORD_ROUTE_PREFIX):
            if request.method != "GET":
                _fail("METHOD_NOT_ALLOWED", "immutable Record route requires exact GET")
            identity = self._validate_get_request(request)
            try:
                result = self._record_responder.prepare(
                    requested_record_identity=identity,
                )
            except Exception:
                _fail("RECORD_REQUEST_REJECTED", "M33 rejected the immutable Record request")
            response_envelope = self._validate_record_result(result, expected_identity=identity)
            return self._serialize_response(
                request=request,
                route_kind=ROUTE_IMMUTABLE_RECORD,
                route_operation=result.request_context.operation,
                envelope=response_envelope,
            )

        _fail("ROUTE_NOT_FOUND", "request path is not a configured M34 route")
