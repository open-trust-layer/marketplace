"""Bounded transport-free read planning below the M36 stream assembler.

M37 never invokes a reader. It accepts one already-buffered immutable request
prefix, asks M36 for pure completion facts, and derives the maximum size of the
next read a future transport layer may request without exceeding the existing
M35/M36 framing bounds.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Final

from .inbound_http_stream import (
    PROGRESS_COMPLETE,
    PROGRESS_NEED_MORE,
    BoundedInboundHttpStreamAssembler,
    InboundHttpStreamError,
    InboundHttpStreamLimits,
    InboundHttpStreamProgress,
)
from .inbound_http_wire import InboundHttpWireLimits

READ_ACTION_READ: Final = "READ"
READ_ACTION_COMPLETE: Final = "COMPLETE"

DEFAULT_MAX_INBOUND_HTTP_READ_CALLS: Final = 64
DEFAULT_MAX_INBOUND_HTTP_READ_BYTES: Final = 16 * 1024
MAX_INBOUND_HTTP_READ_CALLS: Final = 1_024
MAX_INBOUND_HTTP_READ_BYTES: Final = 1 * 1024 * 1024


class InboundHttpReadPlanError(RuntimeError):
    """Fail-closed M37 error with stable local reason metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stream_code: str | None = None,
        wire_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.stream_code = stream_code
        self.wire_code = wire_code


def _fail(
    code: str,
    message: str,
    *,
    stream_code: str | None = None,
    wire_code: str | None = None,
) -> None:
    raise InboundHttpReadPlanError(
        code,
        message,
        stream_code=stream_code,
        wire_code=wire_code,
    )


def _stream_limits_snapshot(value: InboundHttpStreamLimits) -> tuple[int, int]:
    if type(value) is not InboundHttpStreamLimits:
        _fail("STREAM_CONFIGURATION_DRIFT", "M36 stream limits changed type after M37 construction")
    return (value.max_chunks, value.max_chunk_bytes)


def _wire_limits_snapshot(value: InboundHttpWireLimits) -> tuple[int, int, int]:
    if type(value) is not InboundHttpWireLimits:
        _fail("STREAM_CONFIGURATION_DRIFT", "M36 wire limits changed type after M37 construction")
    return (
        value.max_header_bytes,
        value.max_body_bytes,
        value.max_response_body_bytes,
    )


@dataclass(frozen=True)
class InboundHttpReadLimits:
    """Finite M37 read-call and per-read planning limits."""

    max_read_calls: int = DEFAULT_MAX_INBOUND_HTTP_READ_CALLS
    max_read_bytes: int = DEFAULT_MAX_INBOUND_HTTP_READ_BYTES

    def __post_init__(self) -> None:
        if (
            type(self.max_read_calls) is not int
            or not 1 <= self.max_read_calls <= MAX_INBOUND_HTTP_READ_CALLS
        ):
            raise ValueError(
                f"max_read_calls MUST be within 1..{MAX_INBOUND_HTTP_READ_CALLS}"
            )
        if (
            type(self.max_read_bytes) is not int
            or not 1 <= self.max_read_bytes <= MAX_INBOUND_HTTP_READ_BYTES
        ):
            raise ValueError(
                f"max_read_bytes MUST be within 1..{MAX_INBOUND_HTTP_READ_BYTES}"
            )


@dataclass(frozen=True)
class InboundHttpReadPlan:
    """One local read-budget decision; never evidence that a read occurred."""

    action: str
    buffered_bytes: int
    reads_completed: int
    next_read_bytes: int
    expected_total_bytes: int | None
    missing_bytes: int | None
    head_complete: bool
    head_validated: bool
    request_complete: bool
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
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
        if self.action not in {READ_ACTION_READ, READ_ACTION_COMPLETE}:
            raise ValueError("action is outside the M37 read-plan profile")
        if type(self.buffered_bytes) is not int or self.buffered_bytes < 0:
            raise ValueError("buffered_bytes MUST be a non-negative exact integer")
        if type(self.reads_completed) is not int or self.reads_completed < 0:
            raise ValueError("reads_completed MUST be a non-negative exact integer")
        if type(self.next_read_bytes) is not int or self.next_read_bytes < 0:
            raise ValueError("next_read_bytes MUST be a non-negative exact integer")
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
        for name, expected in (
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
                raise ValueError("M37 read plan promoted a forbidden authority fact")

        if self.action == READ_ACTION_COMPLETE:
            if self.next_read_bytes != 0:
                raise ValueError("COMPLETE MUST plan zero additional read bytes")
            if not self.request_complete or not self.head_complete or not self.head_validated:
                raise ValueError("COMPLETE requires one validated complete request")
            if self.expected_total_bytes != self.buffered_bytes or self.missing_bytes != 0:
                raise ValueError("COMPLETE byte accounting is inconsistent")
        else:
            if self.next_read_bytes <= 0:
                raise ValueError("READ MUST plan a positive bounded read size")
            if self.request_complete:
                raise ValueError("READ cannot claim request completion")
            if self.expected_total_bytes is None:
                if self.missing_bytes is not None or self.head_complete or self.head_validated:
                    raise ValueError("head-incomplete READ plan is inconsistent")
            else:
                expected_missing = self.expected_total_bytes - self.buffered_bytes
                if expected_missing <= 0 or self.missing_bytes != expected_missing:
                    raise ValueError("body-incomplete READ accounting is inconsistent")
                if not self.head_complete or not self.head_validated:
                    raise ValueError("body-incomplete READ requires a validated head")
                if self.next_read_bytes > self.missing_bytes:
                    raise ValueError("READ exceeds the exact remaining request body")

        current = (
            "inbound-http-read-plan-v1",
            self.action,
            self.buffered_bytes,
            self.reads_completed,
            self.next_read_bytes,
            self.expected_total_bytes,
            self.missing_bytes,
            self.head_complete,
            self.head_validated,
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
            raise ValueError("M37 read-plan integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpReadPlanner:
    """Derive finite next-read budgets from M36 without performing any read."""

    def __init__(
        self,
        *,
        stream_assembler: BoundedInboundHttpStreamAssembler,
        limits: InboundHttpReadLimits | None = None,
    ) -> None:
        if type(stream_assembler) is not BoundedInboundHttpStreamAssembler:
            raise TypeError("stream_assembler MUST be exact BoundedInboundHttpStreamAssembler")
        if limits is None:
            limits = InboundHttpReadLimits()
        if type(limits) is not InboundHttpReadLimits:
            raise TypeError("limits MUST be exact InboundHttpReadLimits")

        detached_limits = InboundHttpReadLimits(
            max_read_calls=limits.max_read_calls,
            max_read_bytes=limits.max_read_bytes,
        )
        stream_limits = stream_assembler.limits
        wire_limits = stream_assembler.wire_limits
        if type(stream_limits) is not InboundHttpStreamLimits:
            raise TypeError("M36 stream limits MUST be exact InboundHttpStreamLimits")
        if type(wire_limits) is not InboundHttpWireLimits:
            raise TypeError("M36 wire limits MUST be exact InboundHttpWireLimits")
        wire_authority = stream_assembler.wire_authority
        if type(wire_authority) is not str or not wire_authority:
            raise ValueError("M36 wire authority MUST be non-empty exact text")
        if detached_limits.max_read_calls > stream_limits.max_chunks:
            raise ValueError("M37 max_read_calls MUST NOT exceed M36 max_chunks")
        if detached_limits.max_read_bytes > stream_limits.max_chunk_bytes:
            raise ValueError("M37 max_read_bytes MUST NOT exceed M36 max_chunk_bytes")

        self._stream_assembler = stream_assembler
        self._probe = stream_assembler.probe
        self._max_read_calls = detached_limits.max_read_calls
        self._max_read_bytes = detached_limits.max_read_bytes
        self._stream_max_chunks = stream_limits.max_chunks
        self._stream_max_chunk_bytes = stream_limits.max_chunk_bytes
        self._wire_authority = wire_authority
        self._wire_max_header_bytes = wire_limits.max_header_bytes
        self._wire_max_body_bytes = wire_limits.max_body_bytes
        self._wire_max_response_body_bytes = wire_limits.max_response_body_bytes

    @property
    def limits(self) -> InboundHttpReadLimits:
        return InboundHttpReadLimits(
            max_read_calls=self._max_read_calls,
            max_read_bytes=self._max_read_bytes,
        )

    @property
    def stream_limits(self) -> InboundHttpStreamLimits:
        return InboundHttpStreamLimits(
            max_chunks=self._stream_max_chunks,
            max_chunk_bytes=self._stream_max_chunk_bytes,
        )

    @property
    def wire_authority(self) -> str:
        return self._wire_authority

    @property
    def wire_limits(self) -> InboundHttpWireLimits:
        return InboundHttpWireLimits(
            max_header_bytes=self._wire_max_header_bytes,
            max_body_bytes=self._wire_max_body_bytes,
            max_response_body_bytes=self._wire_max_response_body_bytes,
        )

    def _validate_stream_configuration(self) -> None:
        if type(self._stream_assembler) is not BoundedInboundHttpStreamAssembler:
            _fail("STREAM_CONFIGURATION_DRIFT", "M36 helper changed type after M37 construction")
        if _stream_limits_snapshot(self._stream_assembler.limits) != (
            self._stream_max_chunks,
            self._stream_max_chunk_bytes,
        ):
            _fail("STREAM_CONFIGURATION_DRIFT", "M36 stream limits changed after M37 construction")
        if self._stream_assembler.wire_authority != self._wire_authority:
            _fail("STREAM_CONFIGURATION_DRIFT", "M36 wire authority changed after M37 construction")
        if _wire_limits_snapshot(self._stream_assembler.wire_limits) != (
            self._wire_max_header_bytes,
            self._wire_max_body_bytes,
            self._wire_max_response_body_bytes,
        ):
            _fail("STREAM_CONFIGURATION_DRIFT", "M36 wire limits changed after M37 construction")

    def _probe_with_configuration_guard(self, prefix: bytes) -> InboundHttpStreamProgress:
        self._validate_stream_configuration()
        try:
            progress = self._probe(prefix)
        except InboundHttpStreamError as exc:
            self._validate_stream_configuration()
            _fail(
                "STREAM_PROFILE_REJECTED",
                "M36 rejected the supplied request prefix during read planning",
                stream_code=exc.code,
                wire_code=exc.wire_code,
            )
        self._validate_stream_configuration()
        if type(progress) is not InboundHttpStreamProgress:
            _fail("INVALID_STREAM_PROGRESS", "M36 returned an unexpected progress type")
        try:
            witnessed = replace(progress)
        except ValueError:
            _fail("STREAM_PROGRESS_DRIFT", "M36 progress failed invariant replay")
        self._validate_stream_configuration()
        return witnessed

    def plan(self, prefix: bytes, *, reads_completed: int) -> InboundHttpReadPlan:
        """Return one pure finite next-read decision for the supplied M36 prefix."""
        if type(prefix) is not bytes:
            _fail("INVALID_READ_PREFIX", "read-planning prefix MUST be exact immutable bytes")
        if type(reads_completed) is not int or reads_completed < 0:
            _fail("INVALID_READ_COUNT", "reads_completed MUST be a non-negative exact integer")
        if reads_completed > self._max_read_calls:
            _fail("INVALID_READ_COUNT", "reads_completed exceeds the configured M37 call bound")

        progress = self._probe_with_configuration_guard(prefix)
        if progress.state == PROGRESS_COMPLETE:
            return InboundHttpReadPlan(
                action=READ_ACTION_COMPLETE,
                buffered_bytes=progress.buffered_bytes,
                reads_completed=reads_completed,
                next_read_bytes=0,
                expected_total_bytes=progress.expected_total_bytes,
                missing_bytes=progress.missing_bytes,
                head_complete=progress.head_complete,
                head_validated=progress.head_validated,
                request_complete=progress.request_complete,
            )
        if progress.state != PROGRESS_NEED_MORE:
            _fail("INVALID_STREAM_PROGRESS", "M36 progress state is outside the expected profile")
        if reads_completed >= self._max_read_calls:
            _fail("READ_CALL_LIMIT_EXHAUSTED", "request is incomplete after the configured M37 read-call bound")

        if progress.expected_total_bytes is None:
            remaining_header_bytes = self._wire_max_header_bytes - progress.buffered_bytes
            if remaining_header_bytes <= 0:
                _fail("READ_BUDGET_INVARIANT", "M36 requested more head bytes beyond the M35 header bound")
            next_read_bytes = min(self._max_read_bytes, remaining_header_bytes)
        else:
            if type(progress.missing_bytes) is not int or progress.missing_bytes <= 0:
                _fail("READ_BUDGET_INVARIANT", "M36 body-incomplete progress has no positive missing byte count")
            next_read_bytes = min(self._max_read_bytes, progress.missing_bytes)

        if next_read_bytes <= 0 or next_read_bytes > self._stream_max_chunk_bytes:
            _fail("READ_BUDGET_INVARIANT", "derived M37 read size is outside the M36 chunk bound")

        return InboundHttpReadPlan(
            action=READ_ACTION_READ,
            buffered_bytes=progress.buffered_bytes,
            reads_completed=reads_completed,
            next_read_bytes=next_read_bytes,
            expected_total_bytes=progress.expected_total_bytes,
            missing_bytes=progress.missing_bytes,
            head_complete=progress.head_complete,
            head_validated=progress.head_validated,
            request_complete=progress.request_complete,
        )
