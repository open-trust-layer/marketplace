"""Transport-free ownership of bounded response-write progress."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Final

from .inbound_http_response_prepare import PreparedInboundHttpReadResponse
from .inbound_http_response_write_plan import (
    WRITE_ACTION_COMPLETE,
    BoundedInboundHttpResponseWritePlanner,
    InboundHttpResponseWritePlan,
    InboundHttpResponseWritePlanError,
)
from .inbound_http_response_write_transition import (
    BoundedInboundHttpResponseWriteTransitioner,
    InboundHttpResponseWriteTransition,
    InboundHttpResponseWriteTransitionError,
)

_NEGATIVE_FIELDS: Final = (
    "writer_invoked", "socket_accessed", "tls_terminated", "transmitted",
    "request_authenticated", "peer_identity_proven", "establishes_marketplace_truth",
    "establishes_trust", "establishes_authorization", "authorizes_protected_side_effects",
)


class InboundHttpResponseWriteSessionError(RuntimeError):
    def __init__(self, code: str, message: str, *, transition_code: str | None = None, write_plan_code: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.transition_code = transition_code
        self.write_plan_code = write_plan_code


def _fail(code: str, message: str, *, transition_code: str | None = None, write_plan_code: str | None = None) -> None:
    raise InboundHttpResponseWriteSessionError(code, message, transition_code=transition_code, write_plan_code=write_plan_code)


def _negative(value: object, fields: tuple[str, ...] = _NEGATIVE_FIELDS) -> None:
    for name in fields:
        if getattr(value, name, None) is not False:
            _fail("WRITE_SESSION_AUTHORITY_ESCALATION", "write-session input promoted authority")


def _replay_plan(value: InboundHttpResponseWritePlan) -> InboundHttpResponseWritePlan:
    if type(value) is not InboundHttpResponseWritePlan:
        _fail("WRITE_SESSION_PLAN_TYPE", "M44 plan changed type")
    _negative(value)
    try:
        replayed = replace(value)
    except ValueError as exc:
        raise InboundHttpResponseWriteSessionError("WRITE_SESSION_PLAN_DRIFT", "M44 plan failed integrity replay") from exc
    _negative(replayed)
    return replayed


def _replay_prepared(value: PreparedInboundHttpReadResponse) -> PreparedInboundHttpReadResponse:
    if type(value) is not PreparedInboundHttpReadResponse:
        _fail("WRITE_SESSION_RESPONSE_TYPE", "prepared_response MUST be exact M43 result")
    if value.response_prepared is not True or value.transmitted is not False:
        _fail("WRITE_SESSION_RESPONSE_DRIFT", "M43 prepared response authority changed")
    _negative(value, (
        "socket_access_proven", "network_origin_proven", "request_authenticated",
        "peer_identity_proven", "establishes_marketplace_truth", "establishes_trust",
        "establishes_authorization", "authorizes_protected_side_effects",
    ))
    try:
        replayed = replace(value)
    except ValueError as exc:
        raise InboundHttpResponseWriteSessionError("WRITE_SESSION_RESPONSE_DRIFT", "M43 response failed integrity replay") from exc
    return replayed


def _replay_transition(value: InboundHttpResponseWriteTransition) -> InboundHttpResponseWriteTransition:
    if type(value) is not InboundHttpResponseWriteTransition:
        _fail("WRITE_SESSION_TRANSITION_DRIFT", "M45 returned unexpected transition type")
    _negative(value)
    try:
        replayed = replace(value)
    except ValueError as exc:
        raise InboundHttpResponseWriteSessionError("WRITE_SESSION_TRANSITION_DRIFT", "M45 transition failed integrity replay") from exc
    _negative(replayed)
    return replayed


@dataclass(frozen=True)
class InboundHttpResponseWriteSessionProgress:
    response_bytes: int
    bytes_written: int
    write_calls_completed: int
    last_accepted_write_bytes: int
    plan: InboundHttpResponseWritePlan
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    writer_invoked: bool = field(default=False, init=False)
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
        plan = _replay_plan(self.plan)
        for name in ("response_bytes", "bytes_written", "write_calls_completed", "last_accepted_write_bytes"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} MUST be a non-negative exact integer")
        if self.response_bytes <= 0 or self.bytes_written > self.response_bytes:
            raise ValueError("invalid M46 response accounting")
        if (plan.response_bytes, plan.bytes_written, plan.write_calls_completed) != (self.response_bytes, self.bytes_written, self.write_calls_completed):
            raise ValueError("M46 progress does not match M44 plan")
        if self.last_accepted_write_bytes > self.bytes_written:
            raise ValueError("last accepted write exceeds cumulative bytes")
        for name in _NEGATIVE_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError("M46 progress promoted forbidden authority")
        current = ("inbound-http-response-write-session-progress-v1", self.response_bytes, self.bytes_written, self.write_calls_completed, self.last_accepted_write_bytes, plan.integrity_snapshot, *(getattr(self, n) for n in _NEGATIVE_FIELDS))
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("M46 progress integrity mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


@dataclass(frozen=True)
class CompletedInboundHttpResponseWriteSession:
    response_bytes: int
    bytes_written: int
    write_calls_completed: int
    plan: InboundHttpResponseWritePlan
    prepared_response_integrity: tuple[Any, ...]
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    session_closed: bool = field(default=True, init=False)
    writer_invoked: bool = field(default=False, init=False)
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
        plan = _replay_plan(self.plan)
        if plan.action != WRITE_ACTION_COMPLETE:
            raise ValueError("M46 completion requires M44 COMPLETE")
        if self.response_bytes != plan.response_bytes or self.bytes_written != self.response_bytes or self.write_calls_completed != plan.write_calls_completed:
            raise ValueError("M46 completion accounting mismatch")
        if type(self.prepared_response_integrity) is not tuple or self.prepared_response_integrity != plan.prepared_response_integrity:
            raise ValueError("M46 completion response binding mismatch")
        for name in _NEGATIVE_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError("M46 completion promoted forbidden authority")
        current = ("completed-inbound-http-response-write-session-v1", self.response_bytes, self.bytes_written, self.write_calls_completed, plan.integrity_snapshot, self.prepared_response_integrity, self.session_closed, *(getattr(self, n) for n in _NEGATIVE_FIELDS))
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("M46 completion integrity mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpResponseWriteSession:
    __slots__ = (
        "_transitioner", "_planner", "_prepared_response", "_response_identity", "_response_integrity",
        "_transition", "_transition_function", "_plan", "_plan_function", "_max_write_calls", "_max_write_bytes",
        "_write_calls_completed", "_bytes_written", "_current_plan", "_closed", "_state_witness",
    )

    def __init__(self, *, write_transitioner: BoundedInboundHttpResponseWriteTransitioner, prepared_response: PreparedInboundHttpReadResponse) -> None:
        if type(write_transitioner) is not BoundedInboundHttpResponseWriteTransitioner:
            raise TypeError("write_transitioner MUST be exact BoundedInboundHttpResponseWriteTransitioner")
        prepared = _replay_prepared(prepared_response)
        planner = getattr(write_transitioner, "_write_planner", None)
        if type(planner) is not BoundedInboundHttpResponseWritePlanner:
            raise ValueError("M45 MUST retain one exact M44 planner")
        self._transitioner, self._planner = write_transitioner, planner
        self._prepared_response = prepared_response
        self._response_identity, self._response_integrity = id(prepared_response), prepared.integrity_snapshot
        self._transition_function, self._plan_function = BoundedInboundHttpResponseWriteTransitioner.transition, BoundedInboundHttpResponseWritePlanner.plan
        self._transition = self._transition_function.__get__(write_transitioner, BoundedInboundHttpResponseWriteTransitioner)
        self._plan = self._plan_function.__get__(planner, BoundedInboundHttpResponseWritePlanner)
        limits = write_transitioner.write_limits
        self._max_write_calls, self._max_write_bytes = limits.max_write_calls, limits.max_write_bytes
        self._write_calls_completed, self._bytes_written, self._closed = 0, 0, False
        self._validate_configuration()
        self._current_plan = self._authoritative_plan(0, 0)
        self._state_witness = self._open_witness()

    @property
    def closed(self) -> bool:
        self._validate_state()
        return self._closed

    def _validate_configuration(self) -> None:
        if type(self._transitioner) is not BoundedInboundHttpResponseWriteTransitioner or type(self._planner) is not BoundedInboundHttpResponseWritePlanner:
            _fail("WRITE_SESSION_CONFIGURATION_DRIFT", "M45/M44 helper type changed")
        if getattr(self._transitioner, "_write_planner", None) is not self._planner:
            _fail("WRITE_SESSION_CONFIGURATION_DRIFT", "M45 changed retained M44 planner")
        if getattr(self._transition, "__self__", None) is not self._transitioner or getattr(self._transition, "__func__", None) is not self._transition_function:
            _fail("WRITE_SESSION_CONFIGURATION_DRIFT", "captured M45 transition binding changed")
        if getattr(self._plan, "__self__", None) is not self._planner or getattr(self._plan, "__func__", None) is not self._plan_function:
            _fail("WRITE_SESSION_CONFIGURATION_DRIFT", "captured M44 plan binding changed")
        limits, planner_limits = self._transitioner.write_limits, self._planner.limits
        expected = (self._max_write_calls, self._max_write_bytes)
        if (limits.max_write_calls, limits.max_write_bytes) != expected or (planner_limits.max_write_calls, planner_limits.max_write_bytes) != expected:
            _fail("WRITE_SESSION_CONFIGURATION_DRIFT", "M44/M45 write limits changed")

    def _authoritative_plan(self, calls: int, written: int) -> InboundHttpResponseWritePlan:
        self._validate_configuration()
        if self._prepared_response is None:
            _fail("WRITE_SESSION_CLOSED", "M46 no longer retains prepared response")
        replayed = _replay_prepared(self._prepared_response)
        if id(self._prepared_response) != self._response_identity or replayed.integrity_snapshot != self._response_integrity:
            _fail("WRITE_SESSION_STATE_DRIFT", "M46 prepared response binding changed")
        try:
            return _replay_plan(self._plan(self._prepared_response, write_calls_completed=calls, bytes_written=written))
        except InboundHttpResponseWritePlanError as exc:
            _fail("WRITE_SESSION_PLAN_REJECTED", "M44 rejected M46 state", write_plan_code=exc.code)

    def _open_witness(self) -> tuple[Any, ...]:
        return ("inbound-http-response-write-session-state-v1", False, self._response_identity, self._response_integrity, self._write_calls_completed, self._bytes_written, self._current_plan.integrity_snapshot)

    def _validate_state(self) -> None:
        if self._closed:
            if self._prepared_response is not None:
                _fail("WRITE_SESSION_STATE_DRIFT", "closed M46 retained prepared response")
            return
        self._validate_configuration()
        if self._prepared_response is None or id(self._prepared_response) != self._response_identity or self._state_witness != self._open_witness():
            _fail("WRITE_SESSION_STATE_DRIFT", "M46 owned state changed outside transition")
        replayed = self._authoritative_plan(self._write_calls_completed, self._bytes_written)
        if replayed.integrity_snapshot != self._current_plan.integrity_snapshot:
            _fail("WRITE_SESSION_STATE_DRIFT", "M46 current plan differs from authoritative M44 plan")

    def progress(self) -> InboundHttpResponseWriteSessionProgress:
        self._validate_state()
        if self._closed:
            _fail("WRITE_SESSION_CLOSED", "M46 session is closed")
        return InboundHttpResponseWriteSessionProgress(response_bytes=self._current_plan.response_bytes, bytes_written=self._bytes_written, write_calls_completed=self._write_calls_completed, last_accepted_write_bytes=0, plan=self._current_plan)

    def accept_write_count(self, accepted_write_bytes: int) -> InboundHttpResponseWriteSessionProgress:
        self._validate_state()
        if self._closed:
            _fail("WRITE_SESSION_CLOSED", "M46 session is closed")
        before_plan, before_calls, before_bytes = self._current_plan, self._write_calls_completed, self._bytes_written
        try:
            result = self._transition(self._prepared_response, write_calls_completed=before_calls, bytes_written=before_bytes, accepted_write_bytes=accepted_write_bytes)
        except InboundHttpResponseWriteTransitionError as exc:
            self._validate_state()
            _fail("WRITE_SESSION_TRANSITION_REJECTED", "M45 rejected write count", transition_code=exc.code, write_plan_code=exc.write_plan_code)
        self._validate_configuration()
        witnessed = _replay_transition(result)
        if witnessed.prior_plan.integrity_snapshot != before_plan.integrity_snapshot:
            _fail("WRITE_SESSION_PRIOR_PLAN_DRIFT", "M45 prior plan differs from M46 current plan")
        if witnessed.accepted_write_bytes != accepted_write_bytes or witnessed.write_calls_completed != before_calls + 1 or witnessed.bytes_written != before_bytes + accepted_write_bytes:
            _fail("WRITE_SESSION_TRANSITION_DRIFT", "M45 transition accounting differs from supplied write count")
        independent = self._authoritative_plan(witnessed.write_calls_completed, witnessed.bytes_written)
        if independent.integrity_snapshot != witnessed.next_plan.integrity_snapshot:
            _fail("WRITE_SESSION_NEXT_PLAN_DRIFT", "M45 next plan differs from independent M44 replay")
        self._write_calls_completed, self._bytes_written, self._current_plan = witnessed.write_calls_completed, witnessed.bytes_written, independent
        self._state_witness = self._open_witness()
        return InboundHttpResponseWriteSessionProgress(response_bytes=independent.response_bytes, bytes_written=self._bytes_written, write_calls_completed=self._write_calls_completed, last_accepted_write_bytes=accepted_write_bytes, plan=independent)

    def take_completed(self) -> CompletedInboundHttpResponseWriteSession:
        self._validate_state()
        if self._closed:
            _fail("WRITE_SESSION_CLOSED", "M46 session is closed")
        if self._current_plan.action != WRITE_ACTION_COMPLETE:
            _fail("WRITE_SESSION_INCOMPLETE", "M46 cannot complete while M44 still requires writes")
        completed = CompletedInboundHttpResponseWriteSession(response_bytes=self._current_plan.response_bytes, bytes_written=self._bytes_written, write_calls_completed=self._write_calls_completed, plan=self._current_plan, prepared_response_integrity=self._response_integrity)
        self.close()
        return completed

    def close(self) -> None:
        self._prepared_response = None
        self._closed = True
        self._state_witness = ("inbound-http-response-write-session-state-v1", True)
