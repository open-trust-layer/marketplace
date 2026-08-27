"""Finite orchestration above the one-step M41 inbound read invoker.

M42 owns no reader or transport capability. It repeatedly calls one construction-
bound M41 invoker only within an exact finite step ceiling and an injected
monotonic elapsed-time budget. Development and conformance tests use deterministic
in-memory readers and clocks only.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import isfinite
from typing import Any, Callable, Final

from .inbound_http_read_invoke import (
    READ_INVOCATION_COMPLETED,
    READ_INVOCATION_PROGRESS,
    BoundedInboundHttpReadInvoker,
    InboundHttpReadInvocationError,
    InboundHttpReadInvocationResult,
)
from .inbound_http_read_outcome import BoundedInboundHttpReadOutcomeHandler
from .inbound_http_read_plan import READ_ACTION_COMPLETE, READ_ACTION_READ
from .inbound_http_read_session import (
    BoundedInboundHttpReadSession,
    CompletedInboundHttpReadSession,
)

DEFAULT_MAX_INBOUND_HTTP_READ_DRIVER_STEPS: Final = 64
MAX_INBOUND_HTTP_READ_DRIVER_STEPS: Final = 1_024
DEFAULT_INBOUND_HTTP_READ_DRIVER_TIMEOUT_SECONDS: Final = 30.0
MAX_INBOUND_HTTP_READ_DRIVER_TIMEOUT_SECONDS: Final = 120.0

_BINDING_MARKER: Final = "inbound-http-read-driver-binding-v1"
_RESULT_MARKER: Final = "completed-inbound-http-read-driver-result-v1"
_AUTHORITY_NEGATIVE_FIELDS: Final = (
    "socket_access_proven",
    "network_origin_proven",
    "request_authenticated",
    "peer_identity_proven",
    "establishes_marketplace_truth",
    "establishes_trust",
    "establishes_authorization",
    "authorizes_protected_side_effects",
)


class InboundHttpReadDriverError(RuntimeError):
    """Fail-closed M42 error with preserved M41-and-lower reason metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        invocation_code: str | None = None,
        outcome_code: str | None = None,
        session_code: str | None = None,
        transition_code: str | None = None,
        plan_code: str | None = None,
        stream_code: str | None = None,
        wire_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.invocation_code = invocation_code
        self.outcome_code = outcome_code
        self.session_code = session_code
        self.transition_code = transition_code
        self.plan_code = plan_code
        self.stream_code = stream_code
        self.wire_code = wire_code


def _fail(
    code: str,
    message: str,
    *,
    invocation_code: str | None = None,
    outcome_code: str | None = None,
    session_code: str | None = None,
    transition_code: str | None = None,
    plan_code: str | None = None,
    stream_code: str | None = None,
    wire_code: str | None = None,
) -> None:
    raise InboundHttpReadDriverError(
        code,
        message,
        invocation_code=invocation_code,
        outcome_code=outcome_code,
        session_code=session_code,
        transition_code=transition_code,
        plan_code=plan_code,
        stream_code=stream_code,
        wire_code=wire_code,
    )


def _fail_from_invocation(exc: InboundHttpReadInvocationError) -> None:
    _fail(
        "READ_DRIVER_INVOCATION_REJECTED",
        "M41 rejected the bounded driver step",
        invocation_code=exc.code,
        outcome_code=exc.outcome_code,
        session_code=exc.session_code,
        transition_code=exc.transition_code,
        plan_code=exc.plan_code,
        stream_code=exc.stream_code,
        wire_code=exc.wire_code,
    )


@dataclass(frozen=True)
class InboundHttpReadDriverLimits:
    """Finite M42 orchestration limits; never transport authority."""

    max_steps: int = DEFAULT_MAX_INBOUND_HTTP_READ_DRIVER_STEPS
    max_elapsed_seconds: float = DEFAULT_INBOUND_HTTP_READ_DRIVER_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if (
            type(self.max_steps) is not int
            or not 1 <= self.max_steps <= MAX_INBOUND_HTTP_READ_DRIVER_STEPS
        ):
            raise ValueError(
                f"max_steps MUST be within 1..{MAX_INBOUND_HTTP_READ_DRIVER_STEPS}"
            )
        value = self.max_elapsed_seconds
        if type(value) not in (int, float) or not isfinite(value):
            raise ValueError("max_elapsed_seconds MUST be one finite non-boolean number")
        normalized = float(value)
        if not 0.0 < normalized <= MAX_INBOUND_HTTP_READ_DRIVER_TIMEOUT_SECONDS:
            raise ValueError(
                "max_elapsed_seconds MUST be positive and within the M42 hard maximum"
            )
        object.__setattr__(self, "max_elapsed_seconds", normalized)


@dataclass(frozen=True)
class CompletedInboundHttpReadDriverResult:
    """Integrity-bound M42 completion without a second raw request copy."""

    completed: CompletedInboundHttpReadSession
    driver_steps: int
    reader_invocations: int
    elapsed_seconds: float
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    socket_access_proven: bool = field(default=False, init=False)
    network_origin_proven: bool = field(default=False, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    establishes_marketplace_truth: bool = field(default=False, init=False)
    establishes_trust: bool = field(default=False, init=False)
    establishes_authorization: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.completed) is not CompletedInboundHttpReadSession:
            raise ValueError("completed MUST be exact CompletedInboundHttpReadSession")
        try:
            witnessed_completed = replace(self.completed)
        except ValueError as exc:
            raise ValueError("M42 completion failed M39 integrity replay") from exc
        object.__setattr__(self, "completed", witnessed_completed)

        if type(self.driver_steps) is not int or self.driver_steps <= 0:
            raise ValueError("driver_steps MUST be one positive exact integer")
        if type(self.reader_invocations) is not int or self.reader_invocations < 0:
            raise ValueError("reader_invocations MUST be one non-negative exact integer")
        if self.reader_invocations != witnessed_completed.reads_completed:
            raise ValueError("reader_invocations MUST equal the M39 owned read count")
        if self.reader_invocations > self.driver_steps:
            raise ValueError("reader_invocations MUST NOT exceed M42 invocation steps")
        if type(self.elapsed_seconds) is not float or not isfinite(self.elapsed_seconds):
            raise ValueError("elapsed_seconds MUST be one finite float")
        if self.elapsed_seconds < 0.0:
            raise ValueError("elapsed_seconds MUST NOT be negative")

        for name in _AUTHORITY_NEGATIVE_FIELDS:
            if getattr(self, name, None) is not False:
                raise ValueError("M42 result promoted a forbidden authority fact")

        current = (
            _RESULT_MARKER,
            witnessed_completed.integrity_snapshot,
            self.driver_steps,
            self.reader_invocations,
            self.elapsed_seconds,
            self.socket_access_proven,
            self.network_origin_proven,
            self.request_authenticated,
            self.peer_identity_proven,
            self.establishes_marketplace_truth,
            self.establishes_trust,
            self.establishes_authorization,
            self.authorizes_protected_side_effects,
        )
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("M42 completion-result integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpReadDriver:
    """Drive one exact M41 invoker to completion under finite local ceilings."""

    __slots__ = (
        "_invoker",
        "_handler",
        "_session",
        "_clock",
        "_invoke_function",
        "_close_function",
        "_closed_function",
        "_invoke",
        "_close",
        "_closed_getter",
        "_m37_max_read_calls",
        "_max_steps",
        "_max_elapsed_seconds",
        "_binding_witness",
    )

    def __init__(
        self,
        *,
        read_invoker: BoundedInboundHttpReadInvoker,
        clock: Callable[[], float],
        limits: InboundHttpReadDriverLimits | None = None,
    ) -> None:
        if type(read_invoker) is not BoundedInboundHttpReadInvoker:
            raise TypeError("read_invoker MUST be exact BoundedInboundHttpReadInvoker")
        if not callable(clock):
            raise TypeError("clock MUST be callable")

        handler = getattr(read_invoker, "_handler", None)
        if type(handler) is not BoundedInboundHttpReadOutcomeHandler:
            raise ValueError("M41 MUST retain one exact M40 outcome handler")
        session = getattr(handler, "_session", None)
        if type(session) is not BoundedInboundHttpReadSession:
            raise ValueError("M40 MUST retain one exact M39 read session")
        m37_max_read_calls = getattr(session, "_max_read_calls", None)
        if (
            type(m37_max_read_calls) is not int
            or not 1 <= m37_max_read_calls <= MAX_INBOUND_HTTP_READ_DRIVER_STEPS
        ):
            raise ValueError("M39 retained M37 read-call ceiling is invalid")

        if limits is None:
            detached_limits = InboundHttpReadDriverLimits(
                max_steps=min(DEFAULT_MAX_INBOUND_HTTP_READ_DRIVER_STEPS, m37_max_read_calls),
                max_elapsed_seconds=DEFAULT_INBOUND_HTTP_READ_DRIVER_TIMEOUT_SECONDS,
            )
        else:
            if type(limits) is not InboundHttpReadDriverLimits:
                raise TypeError("limits MUST be exact InboundHttpReadDriverLimits")
            detached_limits = InboundHttpReadDriverLimits(
                max_steps=limits.max_steps,
                max_elapsed_seconds=limits.max_elapsed_seconds,
            )
        if detached_limits.max_steps > m37_max_read_calls:
            raise ValueError("M42 max_steps MUST NOT exceed the retained M37 read-call ceiling")

        closed_function = BoundedInboundHttpReadInvoker.closed.fget
        if closed_function is None:
            raise ValueError("M41 closed property MUST retain one exact getter")

        self._invoker = read_invoker
        self._handler = handler
        self._session = session
        self._clock = clock
        self._invoke_function = BoundedInboundHttpReadInvoker.invoke_once
        self._close_function = BoundedInboundHttpReadInvoker.close
        self._closed_function = closed_function
        self._invoke = self._invoke_function.__get__(
            read_invoker, BoundedInboundHttpReadInvoker
        )
        self._close = self._close_function.__get__(
            read_invoker, BoundedInboundHttpReadInvoker
        )
        self._closed_getter = self._closed_function.__get__(
            read_invoker, BoundedInboundHttpReadInvoker
        )
        self._m37_max_read_calls = m37_max_read_calls
        self._max_steps = detached_limits.max_steps
        self._max_elapsed_seconds = detached_limits.max_elapsed_seconds
        self._binding_witness = self._binding_snapshot()
        self._validate_bindings()
        self._closed_value()

    @property
    def limits(self) -> InboundHttpReadDriverLimits:
        return InboundHttpReadDriverLimits(
            max_steps=self._max_steps,
            max_elapsed_seconds=self._max_elapsed_seconds,
        )

    @property
    def m37_max_read_calls(self) -> int:
        self._validate_bindings()
        return self._m37_max_read_calls

    def _binding_snapshot(self) -> tuple[Any, ...]:
        return (
            _BINDING_MARKER,
            self._invoker,
            self._handler,
            self._session,
            self._clock,
            self._invoke_function,
            self._close_function,
            self._closed_function,
            self._m37_max_read_calls,
            self._max_steps,
            self._max_elapsed_seconds,
        )

    def _validate_bound_method(self, bound: Any, function: Any, label: str) -> None:
        if (
            getattr(bound, "__self__", None) is not self._invoker
            or getattr(bound, "__func__", None) is not function
        ):
            _fail("READ_DRIVER_BINDING_DRIFT", f"captured M41 {label} binding changed")

    def _validate_bindings(self) -> None:
        if type(self._invoker) is not BoundedInboundHttpReadInvoker:
            _fail("READ_DRIVER_BINDING_DRIFT", "M41 invoker changed type")
        if getattr(self._invoker, "_handler", None) is not self._handler:
            _fail("READ_DRIVER_BINDING_DRIFT", "M41 to M40 binding changed")
        if type(self._handler) is not BoundedInboundHttpReadOutcomeHandler:
            _fail("READ_DRIVER_BINDING_DRIFT", "M40 handler changed type")
        if getattr(self._handler, "_session", None) is not self._session:
            _fail("READ_DRIVER_BINDING_DRIFT", "M40 to M39 binding changed")
        if type(self._session) is not BoundedInboundHttpReadSession:
            _fail("READ_DRIVER_BINDING_DRIFT", "M39 session changed type")
        if getattr(self._session, "_max_read_calls", None) != self._m37_max_read_calls:
            _fail("READ_DRIVER_CONFIGURATION_DRIFT", "retained M37 read-call ceiling changed")
        if self._binding_witness != self._binding_snapshot():
            _fail("READ_DRIVER_BINDING_DRIFT", "M42 construction binding witness changed")
        if not callable(self._clock):
            _fail("READ_DRIVER_BINDING_DRIFT", "construction-bound clock is no longer callable")
        self._validate_bound_method(self._invoke, self._invoke_function, "invoke-once")
        self._validate_bound_method(self._close, self._close_function, "close")
        self._validate_bound_method(self._closed_getter, self._closed_function, "closed")

    def _best_effort_close(self) -> None:
        """Close only through the construction-captured exact M41 cleanup boundary."""
        witness = self._binding_witness
        if (
            type(witness) is not tuple
            or len(witness) != 11
            or witness[0] != _BINDING_MARKER
            or witness[1] is not self._invoker
            or type(self._invoker) is not BoundedInboundHttpReadInvoker
        ):
            _fail("READ_DRIVER_CLEANUP_UNCERTAIN", "M42 cleanup witness is unavailable")
        expected_close = witness[6]
        expected_closed = witness[7]
        if (
            getattr(self._close, "__self__", None) is not self._invoker
            or getattr(self._close, "__func__", None) is not expected_close
            or getattr(self._closed_getter, "__self__", None) is not self._invoker
            or getattr(self._closed_getter, "__func__", None) is not expected_closed
        ):
            _fail("READ_DRIVER_CLEANUP_UNCERTAIN", "captured M41 cleanup authority changed")
        try:
            self._close()
            closed = self._closed_getter()
        except Exception:
            _fail("READ_DRIVER_CLEANUP_UNCERTAIN", "M42 cleanup could not be verified")
        if closed is not True:
            _fail("READ_DRIVER_CLEANUP_UNCERTAIN", "M42 cleanup did not verify closed state")

    def _closed_value(self) -> bool:
        self._validate_bindings()
        try:
            value = self._closed_getter()
        except InboundHttpReadInvocationError as exc:
            _fail_from_invocation(exc)
        if type(value) is not bool:
            _fail("READ_DRIVER_BINDING_DRIFT", "M41 closed getter returned non-boolean")
        self._validate_bindings()
        return value

    def _clock_value(self) -> float:
        self._validate_bindings()
        try:
            value = self._clock()
        except Exception:
            _fail("READ_DRIVER_CLOCK_FAILURE", "construction-bound M42 clock failed")
        self._validate_bindings()
        if type(value) not in (int, float) or not isfinite(value):
            _fail("READ_DRIVER_CLOCK_DRIFT", "M42 clock MUST return one finite non-boolean number")
        return float(value)

    def _guarded_clock_value(self) -> float:
        try:
            return self._clock_value()
        except InboundHttpReadDriverError:
            self._best_effort_close()
            raise

    def _require_monotonic(self, *, prior: float, current: float) -> None:
        if current < prior:
            self._best_effort_close()
            _fail("READ_DRIVER_CLOCK_REGRESSION", "M42 monotonic clock moved backwards")

    def _require_within_time_budget(self, *, start: float, current: float) -> None:
        if current - start > self._max_elapsed_seconds:
            self._best_effort_close()
            _fail("READ_DRIVER_TIME_LIMIT_EXHAUSTED", "M42 aggregate elapsed-time budget exhausted")

    def _replay_result(
        self,
        result: InboundHttpReadInvocationResult,
    ) -> InboundHttpReadInvocationResult:
        if type(result) is not InboundHttpReadInvocationResult:
            self._best_effort_close()
            _fail("READ_DRIVER_RESULT_DRIFT", "M41 returned unexpected invocation-result type")
        for name in _AUTHORITY_NEGATIVE_FIELDS:
            if getattr(result, name, None) is not False:
                self._best_effort_close()
                _fail("READ_DRIVER_RESULT_DRIFT", "M41 result promoted a forbidden authority fact")
        try:
            witnessed = replace(result)
        except ValueError:
            self._best_effort_close()
            _fail("READ_DRIVER_RESULT_DRIFT", "M41 invocation result failed integrity replay")
        if witnessed.state not in (READ_INVOCATION_PROGRESS, READ_INVOCATION_COMPLETED):
            self._best_effort_close()
            _fail("READ_DRIVER_RESULT_DRIFT", "M41 returned unknown invocation state")
        return witnessed

    @property
    def closed(self) -> bool:
        return self._closed_value()

    def run_to_completion(self) -> CompletedInboundHttpReadDriverResult:
        """Drive M41 through one finite loop and return one M39 completion handoff."""
        try:
            self._validate_bindings()
            source_closed = self._closed_value()
        except InboundHttpReadDriverError:
            self._best_effort_close()
            raise
        if source_closed:
            _fail("READ_DRIVER_SESSION_CLOSED", "M42 source M41 session is already closed")

        start = self._guarded_clock_value()
        prior_clock = start
        completed_steps = 0

        for _ in range(self._max_steps):
            before = self._guarded_clock_value()
            self._require_monotonic(prior=prior_clock, current=before)
            self._require_within_time_budget(start=start, current=before)

            try:
                result = self._invoke()
            except InboundHttpReadInvocationError as exc:
                self._best_effort_close()
                _fail_from_invocation(exc)
            except Exception:
                self._best_effort_close()
                _fail("READ_DRIVER_INVOCATION_FAILURE", "M41 invocation failed unexpectedly")

            completed_steps += 1
            try:
                self._validate_bindings()
            except InboundHttpReadDriverError:
                self._best_effort_close()
                raise

            after = self._guarded_clock_value()
            self._require_monotonic(prior=before, current=after)
            self._require_within_time_budget(start=start, current=after)
            prior_clock = after

            witnessed = self._replay_result(result)
            if witnessed.state == READ_INVOCATION_COMPLETED:
                if type(witnessed.completed) is not CompletedInboundHttpReadSession:
                    self._best_effort_close()
                    _fail("READ_DRIVER_RESULT_DRIFT", "M41 completion payload changed type")
                if not self._closed_value():
                    self._best_effort_close()
                    _fail("READ_DRIVER_RESULT_DRIFT", "M41 completion did not close source session")
                elapsed = after - start
                return CompletedInboundHttpReadDriverResult(
                    completed=witnessed.completed,
                    driver_steps=completed_steps,
                    reader_invocations=witnessed.completed.reads_completed,
                    elapsed_seconds=float(elapsed),
                )

            if witnessed.state != READ_INVOCATION_PROGRESS:
                self._best_effort_close()
                _fail("READ_DRIVER_RESULT_DRIFT", "M41 progress state changed after replay")
            if witnessed.progress is None:
                self._best_effort_close()
                _fail("READ_DRIVER_RESULT_DRIFT", "M41 PROGRESS omitted M39 progress")
            if witnessed.progress.plan.action not in (READ_ACTION_READ, READ_ACTION_COMPLETE):
                self._best_effort_close()
                _fail("READ_DRIVER_RESULT_DRIFT", "M41 progress carried unknown M37 action")
            if self._closed_value():
                _fail("READ_DRIVER_RESULT_DRIFT", "M41 closed during non-terminal PROGRESS")

        self._best_effort_close()
        _fail("READ_DRIVER_STEP_LIMIT_EXHAUSTED", "M42 finite step ceiling exhausted before completion")

    def close(self) -> None:
        """Idempotently close/clear the construction-bound M41/M40/M39 session."""
        self._best_effort_close()
