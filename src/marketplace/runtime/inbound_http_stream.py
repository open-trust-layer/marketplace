"""Bounded transport-free stream assembly around the M35 HTTP/1.1 wire adapter.

M36 consumes already-received immutable byte chunks. It does not read from a
socket or any other external source. It uses M35's public parse boundary to
identify exactly one complete request, invokes M35 exactly once only after
completion, and returns an unsent integrity-bound prepared exchange.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Final

from .inbound_http import InboundHttpRequest
from .inbound_http_wire import (
    BoundedInboundHttpWireAdapter,
    InboundHttpWireError,
    InboundHttpWireLimits,
    PreparedInboundHttpWireExchange,
)

PROGRESS_NEED_MORE: Final = "NEED_MORE"
PROGRESS_COMPLETE: Final = "COMPLETE"

DEFAULT_MAX_INBOUND_HTTP_STREAM_CHUNKS: Final = 64
DEFAULT_MAX_INBOUND_HTTP_STREAM_CHUNK_BYTES: Final = 64 * 1024
MAX_INBOUND_HTTP_STREAM_CHUNKS: Final = 1_024
MAX_INBOUND_HTTP_STREAM_CHUNK_BYTES: Final = 1 * 1024 * 1024

_HEADER_TERMINATOR = b"\r\n\r\n"
_CANONICAL_CONTENT_LENGTH_PREFIX = "Content-Length: "


class InboundHttpStreamError(RuntimeError):
    """Fail-closed M36 error with stable local reason metadata."""

    def __init__(self, code: str, message: str, *, wire_code: str | None = None):
        super().__init__(message)
        self.code = code
        self.wire_code = wire_code


def _fail(code: str, message: str, *, wire_code: str | None = None) -> None:
    raise InboundHttpStreamError(code, message, wire_code=wire_code)


def _wire_rejected(exc: InboundHttpWireError) -> None:
    _fail(
        "WIRE_PROFILE_REJECTED",
        "M35 rejected the supplied stream prefix under its strict wire profile",
        wire_code=exc.code,
    )


def _decimal_exceeds_bound(value: str, bound: int) -> bool:
    """Compare canonical decimal text against a trusted integer without parsing it."""
    bound_text = str(bound)
    if len(value) != len(bound_text):
        return len(value) > len(bound_text)
    return value > bound_text


def _request_snapshot(request: InboundHttpRequest) -> tuple[Any, ...]:
    return (
        "m36-canonical-request-v1",
        request.method,
        request.path,
        request.headers,
        request.body,
        request.request_authenticated,
        request.peer_identity_proven,
    )


def _wire_snapshot(value: PreparedInboundHttpWireExchange) -> tuple[Any, ...]:
    return (
        "m36-m35-wire-snapshot-v1",
        _request_snapshot(value.request),
        value.host_authority,
        value.route_kind,
        value.route_operation,
        value.status_code,
        value.response_body_bytes,
        value.response_bytes,
        value.olp_message_type,
        value.integrity_snapshot,
        value.host_authority_validated,
        value.tls_sni_bound,
        value.transmitted,
        value.request_authenticated,
        value.peer_identity_proven,
        value.establishes_marketplace_truth,
        value.establishes_trust,
        value.establishes_authorization,
        value.authorizes_protected_side_effects,
    )


def _limits_snapshot(value: InboundHttpWireLimits) -> tuple[int, int, int]:
    if type(value) is not InboundHttpWireLimits:
        _fail("WIRE_CONFIGURATION_DRIFT", "M35 limits object changed type after M36 construction")
    return (
        value.max_header_bytes,
        value.max_body_bytes,
        value.max_response_body_bytes,
    )


@dataclass(frozen=True)
class InboundHttpStreamLimits:
    max_chunks: int = DEFAULT_MAX_INBOUND_HTTP_STREAM_CHUNKS
    max_chunk_bytes: int = DEFAULT_MAX_INBOUND_HTTP_STREAM_CHUNK_BYTES

    def __post_init__(self) -> None:
        if type(self.max_chunks) is not int or not 1 <= self.max_chunks <= MAX_INBOUND_HTTP_STREAM_CHUNKS:
            raise ValueError(f"max_chunks MUST be within 1..{MAX_INBOUND_HTTP_STREAM_CHUNKS}")
        if (
            type(self.max_chunk_bytes) is not int
            or not 1 <= self.max_chunk_bytes <= MAX_INBOUND_HTTP_STREAM_CHUNK_BYTES
        ):
            raise ValueError(
                f"max_chunk_bytes MUST be within 1..{MAX_INBOUND_HTTP_STREAM_CHUNK_BYTES}"
            )


@dataclass(frozen=True)
class InboundHttpStreamProgress:
    """Pure local completion facts for one currently buffered request prefix."""

    state: str
    buffered_bytes: int
    expected_total_bytes: int | None
    missing_bytes: int | None
    head_complete: bool
    head_validated: bool
    request_complete: bool

    def __post_init__(self) -> None:
        if self.state not in {PROGRESS_NEED_MORE, PROGRESS_COMPLETE}:
            raise ValueError("state is outside the M36 progress profile")
        if type(self.buffered_bytes) is not int or self.buffered_bytes < 0:
            raise ValueError("buffered_bytes MUST be a non-negative exact integer")
        if self.expected_total_bytes is not None and (
            type(self.expected_total_bytes) is not int
            or self.expected_total_bytes < self.buffered_bytes
        ):
            raise ValueError("expected_total_bytes is inconsistent with buffered bytes")
        if self.missing_bytes is not None and (
            type(self.missing_bytes) is not int or self.missing_bytes < 0
        ):
            raise ValueError("missing_bytes MUST be a non-negative exact integer")
        for name in ("head_complete", "head_validated", "request_complete"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} MUST be exact boolean")

        if self.state == PROGRESS_COMPLETE:
            if not self.head_complete or not self.head_validated or not self.request_complete:
                raise ValueError("COMPLETE requires a validated complete request")
            if self.expected_total_bytes != self.buffered_bytes or self.missing_bytes != 0:
                raise ValueError("COMPLETE byte accounting is inconsistent")
        else:
            if self.request_complete:
                raise ValueError("NEED_MORE cannot claim request completion")
            if self.expected_total_bytes is None:
                if self.missing_bytes is not None or self.head_complete or self.head_validated:
                    raise ValueError("head-incomplete NEED_MORE state is inconsistent")
            else:
                expected_missing = self.expected_total_bytes - self.buffered_bytes
                if expected_missing <= 0 or self.missing_bytes != expected_missing:
                    raise ValueError("body-incomplete NEED_MORE state is inconsistent")
                if not self.head_complete or not self.head_validated:
                    raise ValueError("body-incomplete NEED_MORE requires a validated head")


@dataclass(frozen=True)
class PreparedInboundHttpStreamExchange:
    """One M35 exchange prepared from bounded chunks and never transmitted by M36."""

    wire_exchange: PreparedInboundHttpWireExchange
    chunk_count: int
    request_bytes: int
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    request_complete: bool = field(default=True, init=False)
    network_read_performed: bool = field(default=False, init=False)
    socket_bound: bool = field(default=False, init=False)
    tls_terminated: bool = field(default=False, init=False)
    transmitted: bool = field(default=False, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    establishes_marketplace_truth: bool = field(default=False, init=False)
    establishes_trust: bool = field(default=False, init=False)
    establishes_authorization: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.wire_exchange) is not PreparedInboundHttpWireExchange:
            raise ValueError("wire_exchange has the wrong type")
        try:
            _validate_wire_authority(self.wire_exchange)
        except InboundHttpStreamError as exc:
            raise ValueError("wire_exchange promoted a forbidden M35 authority fact") from exc
        try:
            replace(self.wire_exchange)
        except ValueError as exc:
            raise ValueError("wire_exchange failed its original M35 integrity witness") from exc

        if type(self.chunk_count) is not int or not 1 <= self.chunk_count <= MAX_INBOUND_HTTP_STREAM_CHUNKS:
            raise ValueError("chunk_count is outside the M36 hard bound")
        if type(self.request_bytes) is not int or self.request_bytes <= 0:
            raise ValueError("request_bytes MUST be a positive exact integer")
        for name, expected in (
            ("request_complete", True),
            ("network_read_performed", False),
            ("socket_bound", False),
            ("tls_terminated", False),
            ("transmitted", False),
            ("request_authenticated", False),
            ("peer_identity_proven", False),
            ("establishes_marketplace_truth", False),
            ("establishes_trust", False),
            ("establishes_authorization", False),
            ("authorizes_protected_side_effects", False),
        ):
            if getattr(self, name, None) is not expected:
                raise ValueError("prepared M36 exchange promoted a forbidden authority fact")

        current = (
            "prepared-inbound-http-stream-exchange-v1",
            _wire_snapshot(self.wire_exchange),
            self.chunk_count,
            self.request_bytes,
            self.request_complete,
            self.network_read_performed,
            self.socket_bound,
            self.tls_terminated,
            self.transmitted,
            self.request_authenticated,
            self.peer_identity_proven,
            self.establishes_marketplace_truth,
            self.establishes_trust,
            self.establishes_authorization,
            self.authorizes_protected_side_effects,
        )
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("prepared M36 stream exchange integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


def _validate_wire_authority(value: PreparedInboundHttpWireExchange) -> None:
    if type(value) is not PreparedInboundHttpWireExchange:
        _fail("INVALID_WIRE_RESULT", "M35 returned an unexpected result type")
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
        if getattr(value, name, None) is not expected:
            _fail("WIRE_AUTHORITY_ESCALATION", "M35 result promoted a forbidden authority fact")


class BoundedInboundHttpStreamAssembler:
    """Assemble finite already-received chunks into one exact M35 request."""

    def __init__(
        self,
        *,
        wire_adapter: BoundedInboundHttpWireAdapter,
        limits: InboundHttpStreamLimits | None = None,
    ) -> None:
        if type(wire_adapter) is not BoundedInboundHttpWireAdapter:
            raise TypeError("wire_adapter MUST be exact BoundedInboundHttpWireAdapter")
        if limits is None:
            limits = InboundHttpStreamLimits()
        if type(limits) is not InboundHttpStreamLimits:
            raise TypeError("limits MUST be exact InboundHttpStreamLimits")
        detached_limits = InboundHttpStreamLimits(
            max_chunks=limits.max_chunks,
            max_chunk_bytes=limits.max_chunk_bytes,
        )
        wire_limits = wire_adapter.limits
        if type(wire_limits) is not InboundHttpWireLimits:
            raise TypeError("wire_adapter limits MUST be exact InboundHttpWireLimits")
        detached_wire_limits = InboundHttpWireLimits(
            max_header_bytes=wire_limits.max_header_bytes,
            max_body_bytes=wire_limits.max_body_bytes,
            max_response_body_bytes=wire_limits.max_response_body_bytes,
        )
        wire_authority = wire_adapter.authority
        if type(wire_authority) is not str or not wire_authority:
            raise ValueError("wire_adapter authority MUST be a non-empty canonical string")

        self._wire_adapter = wire_adapter
        self._limits = detached_limits
        self._wire_authority = wire_authority
        self._wire_limits = detached_wire_limits

    @property
    def limits(self) -> InboundHttpStreamLimits:
        return self._limits

    @property
    def wire_adapter(self) -> BoundedInboundHttpWireAdapter:
        return self._wire_adapter

    @property
    def wire_authority(self) -> str:
        return self._wire_authority

    @property
    def wire_limits(self) -> InboundHttpWireLimits:
        return self._wire_limits

    def _validate_wire_configuration(self) -> None:
        if self._wire_adapter.authority != self._wire_authority:
            _fail("WIRE_CONFIGURATION_DRIFT", "M35 authority changed after M36 construction")
        current_limits = _limits_snapshot(self._wire_adapter.limits)
        expected_limits = _limits_snapshot(self._wire_limits)
        if current_limits != expected_limits:
            _fail("WIRE_CONFIGURATION_DRIFT", "M35 limits changed after M36 construction")

    def _parse_with_configuration_guard(self, raw: bytes) -> InboundHttpRequest:
        self._validate_wire_configuration()
        try:
            parsed = self._wire_adapter.parse_request(raw)
        except InboundHttpWireError as exc:
            self._validate_wire_configuration()
            _wire_rejected(exc)
        self._validate_wire_configuration()
        return parsed

    def _validated_declared_body_bytes(self, head_only: bytes) -> int:
        try:
            text = head_only[:-len(_HEADER_TERMINATOR)].decode("ascii")
        except UnicodeDecodeError as exc:
            _fail("VALIDATED_HEAD_DRIFT", "M35-validated head is no longer exact ASCII")
            raise AssertionError from exc
        matches = [
            line[len(_CANONICAL_CONTENT_LENGTH_PREFIX):]
            for line in text.split("\r\n")[1:]
            if line.startswith(_CANONICAL_CONTENT_LENGTH_PREFIX)
        ]
        if len(matches) != 1:
            _fail(
                "CONTENT_LENGTH_BINDING_DRIFT",
                "M35 body-mismatch result did not bind exactly one canonical Content-Length",
            )
        declared = matches[0]
        if (
            not declared
            or not declared.isascii()
            or not declared.isdecimal()
            or (len(declared) > 1 and declared.startswith("0"))
        ):
            _fail("CONTENT_LENGTH_BINDING_DRIFT", "validated Content-Length is noncanonical")
        body_limit = self._wire_limits.max_body_bytes
        if _decimal_exceeds_bound(declared, body_limit):
            _fail(
                "DECLARED_BODY_LIMIT_EXCEEDED",
                "declared request body exceeds the configured M35 body limit",
            )
        # Conversion is safe only after the decimal text is proven <= the finite M35 body limit.
        return int(declared)

    def probe(self, prefix: bytes) -> InboundHttpStreamProgress:
        """Classify one in-memory prefix without invoking M35 prepare or disclosure logic."""
        if type(prefix) is not bytes:
            _fail("INVALID_STREAM_PREFIX", "stream prefix MUST be exact immutable bytes")
        self._validate_wire_configuration()

        wire_limits = self._wire_limits
        total_limit = wire_limits.max_header_bytes + wire_limits.max_body_bytes
        if len(prefix) > total_limit:
            _fail("STREAM_TOTAL_LIMIT_EXCEEDED", "stream prefix exceeds the configured M35 total limit")

        marker_at = prefix.find(_HEADER_TERMINATOR)
        if marker_at < 0:
            if len(prefix) >= wire_limits.max_header_bytes:
                _fail("STREAM_HEADER_LIMIT_EXCEEDED", "request head cannot complete within the M35 header limit")
            return InboundHttpStreamProgress(
                state=PROGRESS_NEED_MORE,
                buffered_bytes=len(prefix),
                expected_total_bytes=None,
                missing_bytes=None,
                head_complete=False,
                head_validated=False,
                request_complete=False,
            )

        head_end = marker_at + len(_HEADER_TERMINATOR)
        if head_end > wire_limits.max_header_bytes:
            _fail("STREAM_HEADER_LIMIT_EXCEEDED", "request head exceeds the configured M35 header limit")
        body_bytes = len(prefix) - head_end
        if body_bytes > wire_limits.max_body_bytes:
            _fail("STREAM_BODY_LIMIT_EXCEEDED", "request body exceeds the configured M35 body limit")

        head_only = prefix[:head_end]
        self._validate_wire_configuration()
        try:
            self._wire_adapter.parse_request(head_only)
        except InboundHttpWireError as exc:
            self._validate_wire_configuration()
            if exc.code != "CONTENT_LENGTH_MISMATCH":
                _wire_rejected(exc)
            declared_body_bytes = self._validated_declared_body_bytes(head_only)
            expected_total = head_end + declared_body_bytes
            if len(prefix) < expected_total:
                return InboundHttpStreamProgress(
                    state=PROGRESS_NEED_MORE,
                    buffered_bytes=len(prefix),
                    expected_total_bytes=expected_total,
                    missing_bytes=expected_total - len(prefix),
                    head_complete=True,
                    head_validated=True,
                    request_complete=False,
                )
            if len(prefix) > expected_total:
                _fail(
                    "TRAILING_OR_PIPELINED_BYTES",
                    "stream prefix contains bytes beyond one exact M35 request",
                )
            self._parse_with_configuration_guard(prefix)
            return InboundHttpStreamProgress(
                state=PROGRESS_COMPLETE,
                buffered_bytes=len(prefix),
                expected_total_bytes=expected_total,
                missing_bytes=0,
                head_complete=True,
                head_validated=True,
                request_complete=True,
            )
        self._validate_wire_configuration()

        if len(prefix) > head_end:
            _fail(
                "TRAILING_OR_PIPELINED_BYTES",
                "stream prefix contains undeclared bytes beyond one exact M35 request",
            )
        return InboundHttpStreamProgress(
            state=PROGRESS_COMPLETE,
            buffered_bytes=len(prefix),
            expected_total_bytes=head_end,
            missing_bytes=0,
            head_complete=True,
            head_validated=True,
            request_complete=True,
        )

    def prepare_chunks(self, chunks: tuple[bytes, ...]) -> PreparedInboundHttpStreamExchange:
        """Prepare one M35 exchange from a finite exact tuple of already-received chunks."""
        if type(chunks) is not tuple:
            _fail("INVALID_CHUNK_COLLECTION", "chunks MUST be an exact tuple")
        if not chunks:
            _fail("INCOMPLETE_REQUEST", "no request bytes were supplied")
        if len(chunks) > self._limits.max_chunks:
            _fail("CHUNK_COUNT_LIMIT_EXCEEDED", "chunk tuple exceeds the configured M36 count limit")
        self._validate_wire_configuration()

        total_limit = self._wire_limits.max_header_bytes + self._wire_limits.max_body_bytes
        aggregate_bytes = 0
        for chunk in chunks:
            if type(chunk) is not bytes or not chunk:
                _fail("INVALID_CHUNK", "every M36 chunk MUST be non-empty exact immutable bytes")
            if len(chunk) > self._limits.max_chunk_bytes:
                _fail("CHUNK_SIZE_LIMIT_EXCEEDED", "chunk exceeds the configured M36 size limit")
            if aggregate_bytes + len(chunk) > total_limit:
                _fail("STREAM_TOTAL_LIMIT_EXCEEDED", "assembled request would exceed the M35 total limit")
            aggregate_bytes += len(chunk)

        raw = b"".join(chunks)
        if len(raw) != aggregate_bytes:
            _fail("ASSEMBLY_LENGTH_DRIFT", "joined request byte count changed during M36 assembly")
        progress = self.probe(raw)
        if progress.state != PROGRESS_COMPLETE:
            _fail("INCOMPLETE_REQUEST", "supplied chunks do not contain one complete M35 request")

        parsed = self._parse_with_configuration_guard(raw)
        self._validate_wire_configuration()
        try:
            wire_result = self._wire_adapter.prepare(raw)
        except InboundHttpWireError as exc:
            self._validate_wire_configuration()
            _wire_rejected(exc)
        self._validate_wire_configuration()

        _validate_wire_authority(wire_result)
        try:
            witnessed = replace(wire_result)
        except ValueError:
            _fail("WIRE_INTEGRITY_DRIFT", "M35 result failed its original integrity witness")
        if witnessed.request != parsed:
            _fail("WIRE_REQUEST_BINDING_DRIFT", "M35 result is not bound to the assembled request")
        if witnessed.host_authority != self._wire_authority:
            _fail("WIRE_AUTHORITY_BINDING_DRIFT", "M35 result changed configured Host authority")

        return PreparedInboundHttpStreamExchange(
            wire_exchange=witnessed,
            chunk_count=len(chunks),
            request_bytes=aggregate_bytes,
        )
