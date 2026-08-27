"""Bounded transport-free read-result transition below M37.

M38 never invokes a reader. It accepts one already-returned immutable byte
chunk, validates that chunk against the construction-bound M37 read budget,
performs one bounded append, advances local read accounting exactly once, and
derives the next authoritative M37 plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
from typing import Any

from .inbound_http_read_plan import (
    READ_ACTION_COMPLETE,
    READ_ACTION_READ,
    BoundedInboundHttpReadPlanner,
    InboundHttpReadLimits,
    InboundHttpReadPlan,
    InboundHttpReadPlanError,
)
from .inbound_http_stream import InboundHttpStreamLimits
from .inbound_http_wire import InboundHttpWireLimits


class InboundHttpReadTransitionError(RuntimeError):
    """Fail-closed M38 error with preserved nested framing metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        plan_code: str | None = None,
        stream_code: str | None = None,
        wire_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.plan_code = plan_code
        self.stream_code = stream_code
        self.wire_code = wire_code


def _fail(
    code: str,
    message: str,
    *,
    plan_code: str | None = None,
    stream_code: str | None = None,
    wire_code: str | None = None,
) -> None:
    raise InboundHttpReadTransitionError(
        code,
        message,
        plan_code=plan_code,
        stream_code=stream_code,
        wire_code=wire_code,
    )


def _read_limits_snapshot(value: InboundHttpReadLimits) -> tuple[int, int]:
    if type(value) is not InboundHttpReadLimits:
        _fail("READ_CONFIGURATION_DRIFT", "M37 read limits changed type after M38 construction")
    return (value.max_read_calls, value.max_read_bytes)


def _stream_limits_snapshot(value: InboundHttpStreamLimits) -> tuple[int, int]:
    if type(value) is not InboundHttpStreamLimits:
        _fail("READ_CONFIGURATION_DRIFT", "M37 stream limits changed type after M38 construction")
    return (value.max_chunks, value.max_chunk_bytes)


def _wire_limits_snapshot(value: InboundHttpWireLimits) -> tuple[int, int, int]:
    if type(value) is not InboundHttpWireLimits:
        _fail("READ_CONFIGURATION_DRIFT", "M37 wire limits changed type after M38 construction")
    return (
        value.max_header_bytes,
        value.max_body_bytes,
        value.max_response_body_bytes,
    )


@dataclass(frozen=True)
class InboundHttpReadTransition:
    """One validated local buffer transition; not evidence of transport I/O."""

    prefix: bytes
    reads_completed: int
    accepted_chunk_bytes: int
    prior_plan: InboundHttpReadPlan
    next_plan: InboundHttpReadPlan
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    reader_invoked: bool = field(default=False, init=False)
    socket_accessed: bool = field(default=False, init=False)
    tls_terminated: bool = field(default=False, init=False)
    transmitted: bool = field(default=False, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    establishes_marketplace_truth: bool = field(default=False, init=False)
    establishes_trust: bool = field(default=False, init=False)
    establishes_authorization: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.prefix) is not bytes:
            raise ValueError("prefix MUST be exact immutable bytes")
        if type(self.reads_completed) is not int or self.reads_completed <= 0:
            raise ValueError("reads_completed MUST be a positive exact integer")
        if type(self.accepted_chunk_bytes) is not int or self.accepted_chunk_bytes <= 0:
            raise ValueError("accepted_chunk_bytes MUST be a positive exact integer")
        if type(self.prior_plan) is not InboundHttpReadPlan:
            raise ValueError("prior_plan MUST be exact InboundHttpReadPlan")
        if type(self.next_plan) is not InboundHttpReadPlan:
            raise ValueError("next_plan MUST be exact InboundHttpReadPlan")

        try:
            witnessed_prior = replace(self.prior_plan)
            witnessed_next = replace(self.next_plan)
        except ValueError as exc:
            raise ValueError("nested M37 read-plan integrity replay failed") from exc

        if witnessed_prior.action != READ_ACTION_READ:
            raise ValueError("M38 transition requires a prior READ plan")
        if witnessed_prior.reads_completed + 1 != self.reads_completed:
            raise ValueError("M38 read accounting did not advance exactly once")
        if witnessed_prior.buffered_bytes + self.accepted_chunk_bytes != len(self.prefix):
            raise ValueError("M38 prefix length is inconsistent with accepted chunk bytes")
        if self.accepted_chunk_bytes > witnessed_prior.next_read_bytes:
            raise ValueError("M38 accepted chunk exceeds prior M37 read budget")
        if witnessed_next.reads_completed != self.reads_completed:
            raise ValueError("next M37 plan is bound to different read accounting")
        if witnessed_next.buffered_bytes != len(self.prefix):
            raise ValueError("next M37 plan is bound to different buffered bytes")

        for name, expected in (
            ("reader_invoked", False),
            ("socket_accessed", False),
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
                raise ValueError("M38 transition promoted a forbidden authority fact")

        current = (
            "inbound-http-read-transition-v1",
            sha256(self.prefix).digest(),
            len(self.prefix),
            self.reads_completed,
            self.accepted_chunk_bytes,
            witnessed_prior.integrity_snapshot,
            witnessed_next.integrity_snapshot,
            self.reader_invoked,
            self.socket_accessed,
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
            raise ValueError("M38 read-transition integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpReadTransitioner:
    """Validate one supplied read result and derive the next M37 plan."""

    def __init__(self, *, read_planner: BoundedInboundHttpReadPlanner) -> None:
        if type(read_planner) is not BoundedInboundHttpReadPlanner:
            raise TypeError("read_planner MUST be exact BoundedInboundHttpReadPlanner")

        read_limits = read_planner.limits
        stream_limits = read_planner.stream_limits
        wire_limits = read_planner.wire_limits
        wire_authority = read_planner.wire_authority
        if type(wire_authority) is not str or not wire_authority:
            raise ValueError("M37 wire authority MUST be non-empty exact text")

        self._read_planner = read_planner
        self._plan = read_planner.plan
        self._max_read_calls, self._max_read_bytes = _read_limits_snapshot(read_limits)
        self._stream_max_chunks, self._stream_max_chunk_bytes = _stream_limits_snapshot(stream_limits)
        (
            self._wire_max_header_bytes,
            self._wire_max_body_bytes,
            self._wire_max_response_body_bytes,
        ) = _wire_limits_snapshot(wire_limits)
        self._wire_authority = wire_authority

    @property
    def read_limits(self) -> InboundHttpReadLimits:
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
    def wire_limits(self) -> InboundHttpWireLimits:
        return InboundHttpWireLimits(
            max_header_bytes=self._wire_max_header_bytes,
            max_body_bytes=self._wire_max_body_bytes,
            max_response_body_bytes=self._wire_max_response_body_bytes,
        )

    @property
    def wire_authority(self) -> str:
        return self._wire_authority

    def _validate_read_configuration(self) -> None:
        if type(self._read_planner) is not BoundedInboundHttpReadPlanner:
            _fail("READ_CONFIGURATION_DRIFT", "M37 helper changed type after M38 construction")
        if _read_limits_snapshot(self._read_planner.limits) != (
            self._max_read_calls,
            self._max_read_bytes,
        ):
            _fail("READ_CONFIGURATION_DRIFT", "M37 read limits changed after M38 construction")
        if _stream_limits_snapshot(self._read_planner.stream_limits) != (
            self._stream_max_chunks,
            self._stream_max_chunk_bytes,
        ):
            _fail("READ_CONFIGURATION_DRIFT", "M37 stream limits changed after M38 construction")
        if self._read_planner.wire_authority != self._wire_authority:
            _fail("READ_CONFIGURATION_DRIFT", "M37 wire authority changed after M38 construction")
        if _wire_limits_snapshot(self._read_planner.wire_limits) != (
            self._wire_max_header_bytes,
            self._wire_max_body_bytes,
            self._wire_max_response_body_bytes,
        ):
            _fail("READ_CONFIGURATION_DRIFT", "M37 wire limits changed after M38 construction")

    def _authoritative_plan(self, prefix: bytes, *, reads_completed: int) -> InboundHttpReadPlan:
        self._validate_read_configuration()
        try:
            plan = self._plan(prefix, reads_completed=reads_completed)
        except InboundHttpReadPlanError as exc:
            self._validate_read_configuration()
            _fail(
                "READ_PLAN_REJECTED",
                "M37 rejected the supplied transition state",
                plan_code=exc.code,
                stream_code=exc.stream_code,
                wire_code=exc.wire_code,
            )
        self._validate_read_configuration()
        if type(plan) is not InboundHttpReadPlan:
            _fail("INVALID_READ_PLAN", "M37 returned an unexpected plan type")
        try:
            witnessed = replace(plan)
        except ValueError:
            _fail("READ_PLAN_DRIFT", "M37 plan failed integrity replay")
        self._validate_read_configuration()
        return witnessed

    def transition(
        self,
        prefix: bytes,
        *,
        reads_completed: int,
        chunk: bytes,
    ) -> InboundHttpReadTransition:
        """Validate one already-returned chunk and advance bounded local state."""
        if type(prefix) is not bytes:
            _fail("INVALID_READ_PREFIX", "M38 prefix MUST be exact immutable bytes")
        if type(reads_completed) is not int or reads_completed < 0:
            _fail("INVALID_READ_COUNT", "M38 reads_completed MUST be a non-negative exact integer")
        if type(chunk) is not bytes:
            _fail("INVALID_READ_CHUNK", "M38 chunk MUST be exact immutable bytes")
        if not chunk:
            _fail("EMPTY_READ_CHUNK", "M38 does not interpret EOF or zero-byte read results")

        prior_plan = self._authoritative_plan(prefix, reads_completed=reads_completed)
        if prior_plan.action == READ_ACTION_COMPLETE:
            _fail("READ_AFTER_COMPLETE", "a read result was supplied after M37 reported completion")
        if prior_plan.action != READ_ACTION_READ:
            _fail("INVALID_READ_PLAN", "M37 prior action is outside the M38 transition profile")
        if len(chunk) > prior_plan.next_read_bytes:
            _fail("READ_CHUNK_EXCEEDS_PLAN", "supplied chunk exceeds the exact M37 next-read budget")
        if len(chunk) > self._stream_max_chunk_bytes:
            _fail("READ_CHUNK_EXCEEDS_STREAM_LIMIT", "supplied chunk exceeds the M36 chunk-size bound")

        next_prefix = prefix + chunk
        if len(next_prefix) > self._wire_max_header_bytes + self._wire_max_body_bytes:
            _fail("READ_BUFFER_INVARIANT", "M38 buffered prefix exceeds the M35 request framing bound")
        next_reads_completed = reads_completed + 1
        next_plan = self._authoritative_plan(
            next_prefix,
            reads_completed=next_reads_completed,
        )

        return InboundHttpReadTransition(
            prefix=next_prefix,
            reads_completed=next_reads_completed,
            accepted_chunk_bytes=len(chunk),
            prior_plan=prior_plan,
            next_plan=next_plan,
        )
