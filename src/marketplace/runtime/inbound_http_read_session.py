"""Bounded transport-free read-session ownership above M37/M38.

M39 owns the in-memory request prefix and read-call accounting so normal callers
cannot reset reads_completed between M38 transitions. It invokes no reader and
performs no transport I/O.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
from typing import Any

from .inbound_http_read_plan import (
    READ_ACTION_COMPLETE,
    BoundedInboundHttpReadPlanner,
    InboundHttpReadLimits,
    InboundHttpReadPlan,
    InboundHttpReadPlanError,
)
from .inbound_http_read_transition import (
    BoundedInboundHttpReadTransitioner,
    InboundHttpReadTransition,
    InboundHttpReadTransitionError,
)
from .inbound_http_stream import InboundHttpStreamLimits
from .inbound_http_wire import InboundHttpWireLimits


class InboundHttpReadSessionError(RuntimeError):
    """Fail-closed M39 error with preserved nested framing metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        transition_code: str | None = None,
        plan_code: str | None = None,
        stream_code: str | None = None,
        wire_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.transition_code = transition_code
        self.plan_code = plan_code
        self.stream_code = stream_code
        self.wire_code = wire_code


def _fail(
    code: str,
    message: str,
    *,
    transition_code: str | None = None,
    plan_code: str | None = None,
    stream_code: str | None = None,
    wire_code: str | None = None,
) -> None:
    raise InboundHttpReadSessionError(
        code,
        message,
        transition_code=transition_code,
        plan_code=plan_code,
        stream_code=stream_code,
        wire_code=wire_code,
    )


def _read_limits_snapshot(value: InboundHttpReadLimits) -> tuple[int, int]:
    if type(value) is not InboundHttpReadLimits:
        _fail("READ_CONFIGURATION_DRIFT", "M39 observed an invalid M37 read-limit type")
    return (value.max_read_calls, value.max_read_bytes)


def _stream_limits_snapshot(value: InboundHttpStreamLimits) -> tuple[int, int]:
    if type(value) is not InboundHttpStreamLimits:
        _fail("READ_CONFIGURATION_DRIFT", "M39 observed an invalid M36 stream-limit type")
    return (value.max_chunks, value.max_chunk_bytes)


def _wire_limits_snapshot(value: InboundHttpWireLimits) -> tuple[int, int, int]:
    if type(value) is not InboundHttpWireLimits:
        _fail("READ_CONFIGURATION_DRIFT", "M39 observed an invalid M35 wire-limit type")
    return (
        value.max_header_bytes,
        value.max_body_bytes,
        value.max_response_body_bytes,
    )


@dataclass(frozen=True)
class InboundHttpReadSessionProgress:
    """Detached public session progress with no raw request bytes."""

    buffered_bytes: int
    reads_completed: int
    last_accepted_chunk_bytes: int
    plan: InboundHttpReadPlan
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
        if type(self.buffered_bytes) is not int or self.buffered_bytes < 0:
            raise ValueError("buffered_bytes MUST be a non-negative exact integer")
        if type(self.reads_completed) is not int or self.reads_completed < 0:
            raise ValueError("reads_completed MUST be a non-negative exact integer")
        if (
            type(self.last_accepted_chunk_bytes) is not int
            or self.last_accepted_chunk_bytes < 0
        ):
            raise ValueError("last_accepted_chunk_bytes MUST be a non-negative exact integer")
        if type(self.plan) is not InboundHttpReadPlan:
            raise ValueError("plan MUST be exact InboundHttpReadPlan")

        try:
            witnessed_plan = replace(self.plan)
        except ValueError as exc:
            raise ValueError("nested M37 read-plan integrity replay failed") from exc

        if witnessed_plan.buffered_bytes != self.buffered_bytes:
            raise ValueError("M39 progress buffered byte count does not match M37 plan")
        if witnessed_plan.reads_completed != self.reads_completed:
            raise ValueError("M39 progress read count does not match M37 plan")
        if self.last_accepted_chunk_bytes > self.buffered_bytes:
            raise ValueError("M39 progress accepted chunk exceeds buffered bytes")

        for name in (
            "reader_invoked",
            "socket_accessed",
            "tls_terminated",
            "transmitted",
            "request_authenticated",
            "peer_identity_proven",
            "establishes_marketplace_truth",
            "establishes_trust",
            "establishes_authorization",
            "authorizes_protected_side_effects",
        ):
            if getattr(self, name, None) is not False:
                raise ValueError("M39 progress promoted a forbidden authority fact")

        current = (
            "inbound-http-read-session-progress-v1",
            self.buffered_bytes,
            self.reads_completed,
            self.last_accepted_chunk_bytes,
            witnessed_plan.integrity_snapshot,
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
            raise ValueError("M39 read-session progress integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


@dataclass(frozen=True)
class CompletedInboundHttpReadSession:
    """One-shot completed-buffer handoff after the owning session closes."""

    prefix: bytes
    reads_completed: int
    plan: InboundHttpReadPlan
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    session_closed: bool = field(default=True, init=False)
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
        if type(self.reads_completed) is not int or self.reads_completed < 0:
            raise ValueError("reads_completed MUST be a non-negative exact integer")
        if type(self.plan) is not InboundHttpReadPlan:
            raise ValueError("plan MUST be exact InboundHttpReadPlan")

        try:
            witnessed_plan = replace(self.plan)
        except ValueError as exc:
            raise ValueError("nested M37 read-plan integrity replay failed") from exc

        if witnessed_plan.action != READ_ACTION_COMPLETE:
            raise ValueError("completed M39 handoff requires an M37 COMPLETE plan")
        if witnessed_plan.buffered_bytes != len(self.prefix):
            raise ValueError("completed M39 prefix length does not match M37 plan")
        if witnessed_plan.reads_completed != self.reads_completed:
            raise ValueError("completed M39 read count does not match M37 plan")
        if self.session_closed is not True:
            raise ValueError("completed M39 handoff MUST record a closed source session")

        for name in (
            "reader_invoked",
            "socket_accessed",
            "tls_terminated",
            "transmitted",
            "request_authenticated",
            "peer_identity_proven",
            "establishes_marketplace_truth",
            "establishes_trust",
            "establishes_authorization",
            "authorizes_protected_side_effects",
        ):
            if getattr(self, name, None) is not False:
                raise ValueError("completed M39 handoff promoted a forbidden authority fact")

        current = (
            "completed-inbound-http-read-session-v1",
            sha256(self.prefix).digest(),
            len(self.prefix),
            self.reads_completed,
            witnessed_plan.integrity_snapshot,
            self.session_closed,
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
            raise ValueError("completed M39 read-session integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpReadSession:
    """Own bounded read state without invoking a reader or transport."""

    __slots__ = (
        "_transitioner",
        "_read_planner",
        "_transition_function",
        "_plan_function",
        "_transition",
        "_plan",
        "_max_read_calls",
        "_max_read_bytes",
        "_stream_max_chunks",
        "_stream_max_chunk_bytes",
        "_wire_max_header_bytes",
        "_wire_max_body_bytes",
        "_wire_max_response_body_bytes",
        "_wire_authority",
        "_prefix",
        "_reads_completed",
        "_current_plan",
        "_closed",
        "_state_witness",
    )

    def __init__(self, *, read_transitioner: BoundedInboundHttpReadTransitioner) -> None:
        if type(read_transitioner) is not BoundedInboundHttpReadTransitioner:
            raise TypeError("read_transitioner MUST be exact BoundedInboundHttpReadTransitioner")

        read_planner = getattr(read_transitioner, "_read_planner", None)
        if type(read_planner) is not BoundedInboundHttpReadPlanner:
            raise ValueError("M38 MUST retain one exact M37 read planner")

        self._transitioner = read_transitioner
        self._read_planner = read_planner
        self._transition_function = BoundedInboundHttpReadTransitioner.transition
        self._plan_function = BoundedInboundHttpReadPlanner.plan
        self._transition = self._transition_function.__get__(
            read_transitioner,
            BoundedInboundHttpReadTransitioner,
        )
        self._plan = self._plan_function.__get__(
            read_planner,
            BoundedInboundHttpReadPlanner,
        )

        self._max_read_calls, self._max_read_bytes = _read_limits_snapshot(
            read_transitioner.read_limits
        )
        self._stream_max_chunks, self._stream_max_chunk_bytes = _stream_limits_snapshot(
            read_transitioner.stream_limits
        )
        (
            self._wire_max_header_bytes,
            self._wire_max_body_bytes,
            self._wire_max_response_body_bytes,
        ) = _wire_limits_snapshot(read_transitioner.wire_limits)
        self._wire_authority = read_transitioner.wire_authority
        if type(self._wire_authority) is not str or not self._wire_authority:
            raise ValueError("M38 wire authority MUST be non-empty exact text")

        self._validate_configuration()

        self._prefix = b""
        self._reads_completed = 0
        self._closed = False
        self._current_plan = self._authoritative_plan(self._prefix, reads_completed=0)
        self._state_witness = self._open_state_witness()

    @property
    def closed(self) -> bool:
        self._validate_state()
        return self._closed

    def _validate_configuration(self) -> None:
        if type(self._transitioner) is not BoundedInboundHttpReadTransitioner:
            _fail("READ_CONFIGURATION_DRIFT", "M38 helper changed type after M39 construction")
        if type(self._read_planner) is not BoundedInboundHttpReadPlanner:
            _fail("READ_CONFIGURATION_DRIFT", "M37 helper changed type after M39 construction")
        if getattr(self._transitioner, "_read_planner", None) is not self._read_planner:
            _fail("READ_CONFIGURATION_DRIFT", "M38 changed its bound M37 planner")
        if (
            getattr(self._transition, "__self__", None) is not self._transitioner
            or getattr(self._transition, "__func__", None) is not self._transition_function
        ):
            _fail("READ_CONFIGURATION_DRIFT", "M39 captured M38 transition binding changed")
        if (
            getattr(self._plan, "__self__", None) is not self._read_planner
            or getattr(self._plan, "__func__", None) is not self._plan_function
        ):
            _fail("READ_CONFIGURATION_DRIFT", "M39 captured M37 plan binding changed")
        if _read_limits_snapshot(self._transitioner.read_limits) != (
            self._max_read_calls,
            self._max_read_bytes,
        ):
            _fail("READ_CONFIGURATION_DRIFT", "M38 read limits changed after M39 construction")
        if _read_limits_snapshot(self._read_planner.limits) != (
            self._max_read_calls,
            self._max_read_bytes,
        ):
            _fail("READ_CONFIGURATION_DRIFT", "M37 read limits changed after M39 construction")
        if _stream_limits_snapshot(self._transitioner.stream_limits) != (
            self._stream_max_chunks,
            self._stream_max_chunk_bytes,
        ):
            _fail("READ_CONFIGURATION_DRIFT", "M38 stream limits changed after M39 construction")
        if _stream_limits_snapshot(self._read_planner.stream_limits) != (
            self._stream_max_chunks,
            self._stream_max_chunk_bytes,
        ):
            _fail("READ_CONFIGURATION_DRIFT", "M37 stream limits changed after M39 construction")
        if self._transitioner.wire_authority != self._wire_authority:
            _fail("READ_CONFIGURATION_DRIFT", "M38 wire authority changed after M39 construction")
        if self._read_planner.wire_authority != self._wire_authority:
            _fail("READ_CONFIGURATION_DRIFT", "M37 wire authority changed after M39 construction")
        expected_wire = (
            self._wire_max_header_bytes,
            self._wire_max_body_bytes,
            self._wire_max_response_body_bytes,
        )
        if _wire_limits_snapshot(self._transitioner.wire_limits) != expected_wire:
            _fail("READ_CONFIGURATION_DRIFT", "M38 wire limits changed after M39 construction")
        if _wire_limits_snapshot(self._read_planner.wire_limits) != expected_wire:
            _fail("READ_CONFIGURATION_DRIFT", "M37 wire limits changed after M39 construction")

    def _authoritative_plan(self, prefix: bytes, *, reads_completed: int) -> InboundHttpReadPlan:
        self._validate_configuration()
        try:
            plan = self._plan(prefix, reads_completed=reads_completed)
        except InboundHttpReadPlanError as exc:
            self._validate_configuration()
            _fail(
                "READ_PLAN_REJECTED",
                "M37 rejected the M39 session state",
                plan_code=exc.code,
                stream_code=exc.stream_code,
                wire_code=exc.wire_code,
            )
        self._validate_configuration()
        if type(plan) is not InboundHttpReadPlan:
            _fail("INVALID_READ_PLAN", "M37 returned an unexpected plan type")
        try:
            witnessed = replace(plan)
        except ValueError:
            _fail("READ_PLAN_DRIFT", "M37 plan failed integrity replay")
        self._validate_configuration()
        return witnessed

    def _replay_plan(self, plan: InboundHttpReadPlan) -> InboundHttpReadPlan:
        if type(plan) is not InboundHttpReadPlan:
            _fail("READ_SESSION_STATE_DRIFT", "M39 current plan changed type")
        try:
            return replace(plan)
        except ValueError:
            _fail("READ_SESSION_STATE_DRIFT", "M39 current plan failed integrity replay")

    def _open_state_witness(self) -> tuple[Any, ...]:
        plan = self._replay_plan(self._current_plan)
        return (
            "inbound-http-read-session-state-v1",
            sha256(self._prefix).digest(),
            len(self._prefix),
            self._reads_completed,
            plan.integrity_snapshot,
            self._transition_function,
            self._plan_function,
            False,
        )

    def _validate_state(self) -> None:
        if type(self._closed) is not bool:
            _fail("READ_SESSION_STATE_DRIFT", "M39 closed flag changed type")
        if self._closed:
            if self._prefix != b"":
                _fail("READ_SESSION_STATE_DRIFT", "closed M39 session retained raw prefix")
            if self._state_witness != ("inbound-http-read-session-state-v1", "closed"):
                _fail("READ_SESSION_STATE_DRIFT", "closed M39 state witness changed")
            return

        if type(self._prefix) is not bytes:
            _fail("READ_SESSION_STATE_DRIFT", "M39 prefix changed type")
        if type(self._reads_completed) is not int or self._reads_completed < 0:
            _fail("READ_SESSION_STATE_DRIFT", "M39 read count changed shape")
        plan = self._replay_plan(self._current_plan)
        if plan.buffered_bytes != len(self._prefix):
            _fail("READ_SESSION_STATE_DRIFT", "M39 prefix length drifted from current plan")
        if plan.reads_completed != self._reads_completed:
            _fail("READ_SESSION_STATE_DRIFT", "M39 read count drifted from current plan")
        if self._state_witness != self._open_state_witness():
            _fail("READ_SESSION_STATE_DRIFT", "M39 state integrity witness mismatch")

    def _ensure_open(self) -> None:
        self._validate_state()
        if self._closed:
            _fail("READ_SESSION_CLOSED", "M39 read session is closed")

    def progress(self) -> InboundHttpReadSessionProgress:
        """Return detached non-raw progress for the current open session."""
        self._ensure_open()
        self._validate_configuration()
        plan = self._replay_plan(self._current_plan)
        return InboundHttpReadSessionProgress(
            buffered_bytes=len(self._prefix),
            reads_completed=self._reads_completed,
            last_accepted_chunk_bytes=0,
            plan=plan,
        )

    def accept_chunk(self, chunk: bytes) -> InboundHttpReadSessionProgress:
        """Accept one already-returned chunk and advance owned state exactly once."""
        self._ensure_open()
        if type(chunk) is not bytes:
            _fail("INVALID_READ_CHUNK", "M39 chunk MUST be exact immutable bytes")
        if not chunk:
            _fail("EMPTY_READ_CHUNK", "M39 does not interpret EOF or zero-byte read results")

        self._validate_configuration()
        prior_plan = self._replay_plan(self._current_plan)
        if prior_plan.action == READ_ACTION_COMPLETE:
            _fail("READ_AFTER_COMPLETE", "M39 session is already complete")

        prefix = self._prefix
        reads_completed = self._reads_completed
        try:
            transition = self._transition(
                prefix,
                reads_completed=reads_completed,
                chunk=chunk,
            )
        except InboundHttpReadTransitionError as exc:
            self._validate_configuration()
            self._validate_state()
            _fail(
                "READ_TRANSITION_REJECTED",
                "M38 rejected the supplied M39 read result",
                transition_code=exc.code,
                plan_code=exc.plan_code,
                stream_code=exc.stream_code,
                wire_code=exc.wire_code,
            )

        self._validate_configuration()
        self._validate_state()
        if type(transition) is not InboundHttpReadTransition:
            _fail("INVALID_READ_TRANSITION", "M38 returned an unexpected transition type")
        try:
            witnessed = replace(transition)
        except ValueError:
            _fail("READ_TRANSITION_DRIFT", "M38 transition failed integrity replay")
        self._validate_configuration()
        self._validate_state()

        if witnessed.prior_plan.integrity_snapshot != prior_plan.integrity_snapshot:
            _fail("READ_PRIOR_PLAN_DRIFT", "M38 transition is not bound to M39 current plan")
        if witnessed.accepted_chunk_bytes != len(chunk):
            _fail("READ_TRANSITION_DRIFT", "M38 changed the accepted M39 chunk byte count")
        if witnessed.reads_completed != reads_completed + 1:
            _fail("READ_TRANSITION_DRIFT", "M38 did not advance M39 read accounting exactly once")
        if witnessed.next_plan.reads_completed != witnessed.reads_completed:
            _fail("READ_TRANSITION_DRIFT", "M38 next plan changed read accounting")
        if witnessed.next_plan.buffered_bytes != len(witnessed.prefix):
            _fail("READ_TRANSITION_DRIFT", "M38 next plan changed buffered byte accounting")

        expected_prefix_digest = sha256()
        expected_prefix_digest.update(prefix)
        expected_prefix_digest.update(chunk)
        if expected_prefix_digest.digest() != sha256(witnessed.prefix).digest():
            _fail("READ_TRANSITION_DRIFT", "M38 returned bytes outside the M39 prefix/chunk transition")

        self._prefix = witnessed.prefix
        self._reads_completed = witnessed.reads_completed
        self._current_plan = replace(witnessed.next_plan)
        self._state_witness = self._open_state_witness()

        return InboundHttpReadSessionProgress(
            buffered_bytes=len(self._prefix),
            reads_completed=self._reads_completed,
            last_accepted_chunk_bytes=witnessed.accepted_chunk_bytes,
            plan=self._replay_plan(self._current_plan),
        )

    def take_completed(self) -> CompletedInboundHttpReadSession:
        """Transfer the completed raw prefix once and close/clear the owning session."""
        self._ensure_open()
        self._validate_configuration()
        plan = self._replay_plan(self._current_plan)
        if plan.action != READ_ACTION_COMPLETE:
            _fail("READ_SESSION_INCOMPLETE", "M39 session has not reached an M37 COMPLETE plan")

        completed = CompletedInboundHttpReadSession(
            prefix=self._prefix,
            reads_completed=self._reads_completed,
            plan=plan,
        )
        self._prefix = b""
        self._closed = True
        self._state_witness = ("inbound-http-read-session-state-v1", "closed")
        return completed

    def close(self) -> None:
        """Idempotently clear the raw prefix and close this local session."""
        self._prefix = b""
        self._closed = True
        self._state_witness = ("inbound-http-read-session-state-v1", "closed")
