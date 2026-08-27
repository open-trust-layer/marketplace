"""Finite orchestration above the one-step M48 inbound write invoker.

M49 owns no writer or transport capability. It repeatedly calls one construction-
bound M48 invoker only within an exact finite step ceiling and an injected
monotonic elapsed-time budget. Development and conformance tests use deterministic
in-memory writers and clocks only.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import isfinite
from typing import Any, Callable, Final

from .inbound_http_response_write_invoke import (
    WRITE_INVOCATION_COMPLETED,
    WRITE_INVOCATION_PROGRESS,
    BoundedInboundHttpResponseWriteInvoker,
    InboundHttpResponseWriteInvocationError,
    InboundHttpResponseWriteInvocationResult,
)
from .inbound_http_response_write_outcome import BoundedInboundHttpResponseWriteOutcomeHandler
from .inbound_http_response_write_plan import WRITE_ACTION_COMPLETE, WRITE_ACTION_WRITE
from .inbound_http_response_write_session import (
    BoundedInboundHttpResponseWriteSession,
    CompletedInboundHttpResponseWriteSession,
)

DEFAULT_MAX_INBOUND_HTTP_RESPONSE_WRITE_DRIVER_STEPS: Final = 65
MAX_INBOUND_HTTP_RESPONSE_WRITE_DRIVER_STEPS: Final = 1_025
DEFAULT_INBOUND_HTTP_RESPONSE_WRITE_DRIVER_TIMEOUT_SECONDS: Final = 30.0
MAX_INBOUND_HTTP_RESPONSE_WRITE_DRIVER_TIMEOUT_SECONDS: Final = 120.0

_BINDING_MARKER: Final = "inbound-http-write-driver-binding-v1"
_RESULT_MARKER: Final = "completed-inbound-http-write-driver-result-v1"
_AUTHORITY_NEGATIVE_FIELDS: Final = (
    "socket_access_proven",
    "tls_terminated",
    "transmitted",
    "request_authenticated",
    "peer_identity_proven",
    "establishes_marketplace_truth",
    "establishes_trust",
    "establishes_authorization",
    "authorizes_protected_side_effects",
)


class InboundHttpResponseWriteDriverError(RuntimeError):
    """Fail-closed M49 error with preserved M48-and-lower reason metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        invocation_code: str | None = None,
        outcome_code: str | None = None,
        session_code: str | None = None,
        transition_code: str | None = None,
        write_plan_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.invocation_code = invocation_code
        self.outcome_code = outcome_code
        self.session_code = session_code
        self.transition_code = transition_code
        self.write_plan_code = write_plan_code


def _fail(
    code: str,
    message: str,
    *,
    invocation_code: str | None = None,
    outcome_code: str | None = None,
    session_code: str | None = None,
    transition_code: str | None = None,
    write_plan_code: str | None = None,
) -> None:
    raise InboundHttpResponseWriteDriverError(
        code,
        message,
        invocation_code=invocation_code,
        outcome_code=outcome_code,
        session_code=session_code,
        transition_code=transition_code,
        write_plan_code=write_plan_code,
    )


def _fail_from_invocation(exc: InboundHttpResponseWriteInvocationError) -> None:
    _fail(
        "WRITE_DRIVER_INVOCATION_REJECTED",
        "M48 rejected the bounded driver step",
        invocation_code=exc.code,
        outcome_code=exc.outcome_code,
        session_code=exc.session_code,
        transition_code=exc.transition_code,
        write_plan_code=exc.write_plan_code,
    )


@dataclass(frozen=True)
class InboundHttpResponseWriteDriverLimits:
    """Finite M49 orchestration limits; never transport authority."""

    max_steps: int = DEFAULT_MAX_INBOUND_HTTP_RESPONSE_WRITE_DRIVER_STEPS
    max_elapsed_seconds: float = DEFAULT_INBOUND_HTTP_RESPONSE_WRITE_DRIVER_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if (
            type(self.max_steps) is not int
            or not 1 <= self.max_steps <= MAX_INBOUND_HTTP_RESPONSE_WRITE_DRIVER_STEPS
        ):
            raise ValueError(
                f"max_steps MUST be within 1..{MAX_INBOUND_HTTP_RESPONSE_WRITE_DRIVER_STEPS}"
            )
        value = self.max_elapsed_seconds
        if type(value) not in (int, float) or not isfinite(value):
            raise ValueError("max_elapsed_seconds MUST be one finite non-boolean number")
        normalized = float(value)
        if not 0.0 < normalized <= MAX_INBOUND_HTTP_RESPONSE_WRITE_DRIVER_TIMEOUT_SECONDS:
            raise ValueError(
                "max_elapsed_seconds MUST be positive and within the M49 hard maximum"
            )
        object.__setattr__(self, "max_elapsed_seconds", normalized)


@dataclass(frozen=True)
class CompletedInboundHttpResponseWriteDriverResult:
    """Integrity-bound M49 completion without a second raw response copy."""

    completed: CompletedInboundHttpResponseWriteSession
    driver_steps: int
    writer_invocations: int
    elapsed_seconds: float
    write_calls_completed: int = field(default=0, init=False)
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    socket_access_proven: bool = field(default=False, init=False)
    tls_terminated: bool = field(default=False, init=False)
    transmitted: bool = field(default=False, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    establishes_marketplace_truth: bool = field(default=False, init=False)
    establishes_trust: bool = field(default=False, init=False)
    establishes_authorization: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.completed) is not CompletedInboundHttpResponseWriteSession:
            raise ValueError("completed MUST be exact CompletedInboundHttpResponseWriteSession")
        try:
            witnessed_completed = replace(self.completed)
        except ValueError as exc:
            raise ValueError("M49 completion failed M46 integrity replay") from exc
        object.__setattr__(self, "completed", witnessed_completed)
        object.__setattr__(self, "write_calls_completed", witnessed_completed.write_calls_completed)

        if type(self.driver_steps) is not int or self.driver_steps <= 0:
            raise ValueError("driver_steps MUST be one positive exact integer")
        if type(self.writer_invocations) is not int or self.writer_invocations < 0:
            raise ValueError("writer_invocations MUST be one non-negative exact integer")
        if self.writer_invocations > self.driver_steps:
            raise ValueError("writer_invocations MUST NOT exceed M49 invocation steps")
        if self.writer_invocations > self.write_calls_completed:
            raise ValueError("M49 writer invocations MUST NOT exceed cumulative M46 write accounting")
        if type(self.elapsed_seconds) is not float or not isfinite(self.elapsed_seconds):
            raise ValueError("elapsed_seconds MUST be one finite float")
        if self.elapsed_seconds < 0.0:
            raise ValueError("elapsed_seconds MUST NOT be negative")

        for name in _AUTHORITY_NEGATIVE_FIELDS:
            if getattr(self, name, None) is not False:
                raise ValueError("M49 result promoted a forbidden authority fact")

        current = (
            _RESULT_MARKER,
            witnessed_completed.integrity_snapshot,
            self.driver_steps,
            self.writer_invocations,
            self.write_calls_completed,
            self.elapsed_seconds,
            self.socket_access_proven,
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
            raise ValueError("M49 completion-result integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpResponseWriteDriver:
    """Drive one exact M48 invoker to completion under finite local ceilings."""

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
        "_m44_max_write_calls",
        "_max_steps",
        "_max_elapsed_seconds",
        "_binding_witness",
    )

    def __init__(
        self,
        *,
        write_invoker: BoundedInboundHttpResponseWriteInvoker,
        clock: Callable[[], float],
        limits: InboundHttpResponseWriteDriverLimits | None = None,
    ) -> None:
        if type(write_invoker) is not BoundedInboundHttpResponseWriteInvoker:
            raise TypeError("write_invoker MUST be exact BoundedInboundHttpResponseWriteInvoker")
        if not callable(clock):
            raise TypeError("clock MUST be callable")

        handler = getattr(write_invoker, "_handler", None)
        if type(handler) is not BoundedInboundHttpResponseWriteOutcomeHandler:
            raise ValueError("M48 MUST retain one exact M47 outcome handler")
        session = getattr(handler, "_session", None)
        if type(session) is not BoundedInboundHttpResponseWriteSession:
            raise ValueError("M47 MUST retain one exact M46 write session")
        m44_max_write_calls = getattr(session, "_max_write_calls", None)
        if (
            type(m44_max_write_calls) is not int
            or not 1 <= m44_max_write_calls <= MAX_INBOUND_HTTP_RESPONSE_WRITE_DRIVER_STEPS - 1
        ):
            raise ValueError("M46 retained M44 write-call ceiling is invalid")

        if limits is None:
            detached_limits = InboundHttpResponseWriteDriverLimits(
                max_steps=min(DEFAULT_MAX_INBOUND_HTTP_RESPONSE_WRITE_DRIVER_STEPS, m44_max_write_calls + 1),
                max_elapsed_seconds=DEFAULT_INBOUND_HTTP_RESPONSE_WRITE_DRIVER_TIMEOUT_SECONDS,
            )
        else:
            if type(limits) is not InboundHttpResponseWriteDriverLimits:
                raise TypeError("limits MUST be exact InboundHttpResponseWriteDriverLimits")
            detached_limits = InboundHttpResponseWriteDriverLimits(
                max_steps=limits.max_steps,
                max_elapsed_seconds=limits.max_elapsed_seconds,
            )
        if detached_limits.max_steps > m44_max_write_calls + 1:
            raise ValueError("M49 max_steps MUST NOT exceed retained M44 write-call ceiling plus one completion-transfer step")

        closed_function = BoundedInboundHttpResponseWriteInvoker.closed.fget
        if closed_function is None:
            raise ValueError("M48 closed property MUST retain one exact getter")

        self._invoker = write_invoker
        self._handler = handler
        self._session = session
        self._clock = clock
        self._invoke_function = BoundedInboundHttpResponseWriteInvoker.invoke_once
        self._close_function = BoundedInboundHttpResponseWriteInvoker.close
        self._closed_function = closed_function
        self._invoke = self._invoke_function.__get__(
            write_invoker, BoundedInboundHttpResponseWriteInvoker
        )
        self._close = self._close_function.__get__(
            write_invoker, BoundedInboundHttpResponseWriteInvoker
        )
        self._closed_getter = self._closed_function.__get__(
            write_invoker, BoundedInboundHttpResponseWriteInvoker
        )
        self._m44_max_write_calls = m44_max_write_calls
        self._max_steps = detached_limits.max_steps
        self._max_elapsed_seconds = detached_limits.max_elapsed_seconds
        self._binding_witness = self._binding_snapshot()
        self._validate_bindings()
        self._closed_value()

    @property
    def limits(self) -> InboundHttpResponseWriteDriverLimits:
        return InboundHttpResponseWriteDriverLimits(
            max_steps=self._max_steps,
            max_elapsed_seconds=self._max_elapsed_seconds,
        )

    @property
    def m44_max_write_calls(self) -> int:
        self._validate_bindings()
        return self._m44_max_write_calls

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
            self._m44_max_write_calls,
            self._max_steps,
            self._max_elapsed_seconds,
        )

    def _validate_bound_method(self, bound: Any, function: Any, label: str) -> None:
        if (
            getattr(bound, "__self__", None) is not self._invoker
            or getattr(bound, "__func__", None) is not function
        ):
            _fail("WRITE_DRIVER_BINDING_DRIFT", f"captured M48 {label} binding changed")

    def _validate_bindings(self) -> None:
        if type(self._invoker) is not BoundedInboundHttpResponseWriteInvoker:
            _fail("WRITE_DRIVER_BINDING_DRIFT", "M48 invoker changed type")
        if getattr(self._invoker, "_handler", None) is not self._handler:
            _fail("WRITE_DRIVER_BINDING_DRIFT", "M48 to M47 binding changed")
        if type(self._handler) is not BoundedInboundHttpResponseWriteOutcomeHandler:
            _fail("WRITE_DRIVER_BINDING_DRIFT", "M47 handler changed type")
        if getattr(self._handler, "_session", None) is not self._session:
            _fail("WRITE_DRIVER_BINDING_DRIFT", "M47 to M46 binding changed")
        if type(self._session) is not BoundedInboundHttpResponseWriteSession:
            _fail("WRITE_DRIVER_BINDING_DRIFT", "M46 session changed type")
        if getattr(self._session, "_max_write_calls", None) != self._m44_max_write_calls:
            _fail("WRITE_DRIVER_CONFIGURATION_DRIFT", "retained M44 write-call ceiling changed")
        if self._binding_witness != self._binding_snapshot():
            _fail("WRITE_DRIVER_BINDING_DRIFT", "M49 construction binding witness changed")
        if not callable(self._clock):
            _fail("WRITE_DRIVER_BINDING_DRIFT", "construction-bound clock is no longer callable")
        self._validate_bound_method(self._invoke, self._invoke_function, "invoke-once")
        self._validate_bound_method(self._close, self._close_function, "close")
        self._validate_bound_method(self._closed_getter, self._closed_function, "closed")

    def _best_effort_close(self) -> None:
        """Close only through the construction-captured exact M48 cleanup boundary."""
        witness = self._binding_witness
        if (
            type(witness) is not tuple
            or len(witness) != 11
            or witness[0] != _BINDING_MARKER
            or witness[1] is not self._invoker
            or type(self._invoker) is not BoundedInboundHttpResponseWriteInvoker
        ):
            _fail("WRITE_DRIVER_CLEANUP_UNCERTAIN", "M49 cleanup witness is unavailable")
        expected_close = witness[6]
        expected_closed = witness[7]
        if (
            getattr(self._close, "__self__", None) is not self._invoker
            or getattr(self._close, "__func__", None) is not expected_close
            or getattr(self._closed_getter, "__self__", None) is not self._invoker
            or getattr(self._closed_getter, "__func__", None) is not expected_closed
        ):
            _fail("WRITE_DRIVER_CLEANUP_UNCERTAIN", "captured M48 cleanup authority changed")
        try:
            self._close()
            closed = self._closed_getter()
        except Exception:
            _fail("WRITE_DRIVER_CLEANUP_UNCERTAIN", "M49 cleanup could not be verified")
        if closed is not True:
            _fail("WRITE_DRIVER_CLEANUP_UNCERTAIN", "M49 cleanup did not verify closed state")

    def _closed_value(self) -> bool:
        self._validate_bindings()
        try:
            value = self._closed_getter()
        except InboundHttpResponseWriteInvocationError as exc:
            _fail_from_invocation(exc)
        if type(value) is not bool:
            _fail("WRITE_DRIVER_BINDING_DRIFT", "M48 closed getter returned non-boolean")
        self._validate_bindings()
        return value

    def _clock_value(self) -> float:
        self._validate_bindings()
        try:
            value = self._clock()
        except Exception:
            _fail("WRITE_DRIVER_CLOCK_FAILURE", "construction-bound M49 clock failed")
        self._validate_bindings()
        if type(value) not in (int, float) or not isfinite(value):
            _fail("WRITE_DRIVER_CLOCK_DRIFT", "M49 clock MUST return one finite non-boolean number")
        return float(value)

    def _guarded_clock_value(self) -> float:
        try:
            return self._clock_value()
        except InboundHttpResponseWriteDriverError:
            self._best_effort_close()
            raise

    def _require_monotonic(self, *, prior: float, current: float) -> None:
        if current < prior:
            self._best_effort_close()
            _fail("WRITE_DRIVER_CLOCK_REGRESSION", "M49 monotonic clock moved backwards")

    def _require_within_time_budget(self, *, start: float, current: float) -> None:
        if current - start > self._max_elapsed_seconds:
            self._best_effort_close()
            _fail("WRITE_DRIVER_TIME_LIMIT_EXHAUSTED", "M49 aggregate elapsed-time budget exhausted")

    def _replay_result(
        self,
        result: InboundHttpResponseWriteInvocationResult,
    ) -> InboundHttpResponseWriteInvocationResult:
        if type(result) is not InboundHttpResponseWriteInvocationResult:
            self._best_effort_close()
            _fail("WRITE_DRIVER_RESULT_DRIFT", "M48 returned unexpected invocation-result type")
        for name in _AUTHORITY_NEGATIVE_FIELDS:
            if getattr(result, name, None) is not False:
                self._best_effort_close()
                _fail("WRITE_DRIVER_RESULT_DRIFT", "M48 result promoted a forbidden authority fact")
        try:
            witnessed = replace(result)
        except ValueError:
            self._best_effort_close()
            _fail("WRITE_DRIVER_RESULT_DRIFT", "M48 invocation result failed integrity replay")
        if witnessed.state not in (WRITE_INVOCATION_PROGRESS, WRITE_INVOCATION_COMPLETED):
            self._best_effort_close()
            _fail("WRITE_DRIVER_RESULT_DRIFT", "M48 returned unknown invocation state")
        return witnessed

    @property
    def closed(self) -> bool:
        return self._closed_value()

    def run_to_completion(self) -> CompletedInboundHttpResponseWriteDriverResult:
        """Drive M48 through one finite loop and return one M46 completion handoff."""
        try:
            self._validate_bindings()
            source_closed = self._closed_value()
        except InboundHttpResponseWriteDriverError:
            self._best_effort_close()
            raise
        if source_closed:
            _fail("WRITE_DRIVER_SESSION_CLOSED", "M49 source M48 session is already closed")

        start = self._guarded_clock_value()
        prior_clock = start
        completed_steps = 0
        writer_invocations = 0

        for _ in range(self._max_steps):
            before = self._guarded_clock_value()
            self._require_monotonic(prior=prior_clock, current=before)
            self._require_within_time_budget(start=start, current=before)

            try:
                result = self._invoke()
            except InboundHttpResponseWriteInvocationError as exc:
                self._best_effort_close()
                _fail_from_invocation(exc)
            except Exception:
                self._best_effort_close()
                _fail("WRITE_DRIVER_INVOCATION_FAILURE", "M48 invocation failed unexpectedly")

            completed_steps += 1
            try:
                self._validate_bindings()
            except InboundHttpResponseWriteDriverError:
                self._best_effort_close()
                raise

            after = self._guarded_clock_value()
            self._require_monotonic(prior=before, current=after)
            self._require_within_time_budget(start=start, current=after)
            prior_clock = after

            witnessed = self._replay_result(result)
            if witnessed.writer_invoked is True:
                writer_invocations += 1
            if witnessed.state == WRITE_INVOCATION_COMPLETED:
                if type(witnessed.completed) is not CompletedInboundHttpResponseWriteSession:
                    self._best_effort_close()
                    _fail("WRITE_DRIVER_RESULT_DRIFT", "M48 completion payload changed type")
                if not self._closed_value():
                    self._best_effort_close()
                    _fail("WRITE_DRIVER_RESULT_DRIFT", "M48 completion did not close source session")
                elapsed = after - start
                return CompletedInboundHttpResponseWriteDriverResult(
                    completed=witnessed.completed,
                    driver_steps=completed_steps,
                    writer_invocations=writer_invocations,
                    elapsed_seconds=float(elapsed),
                )

            if witnessed.state != WRITE_INVOCATION_PROGRESS:
                self._best_effort_close()
                _fail("WRITE_DRIVER_RESULT_DRIFT", "M48 progress state changed after replay")
            if witnessed.progress is None:
                self._best_effort_close()
                _fail("WRITE_DRIVER_RESULT_DRIFT", "M48 PROGRESS omitted M46 progress")
            if witnessed.progress.plan.action not in (WRITE_ACTION_WRITE, WRITE_ACTION_COMPLETE):
                self._best_effort_close()
                _fail("WRITE_DRIVER_RESULT_DRIFT", "M48 progress carried unknown M44 action")
            if self._closed_value():
                _fail("WRITE_DRIVER_RESULT_DRIFT", "M48 closed during non-terminal PROGRESS")

        self._best_effort_close()
        _fail("WRITE_DRIVER_STEP_LIMIT_EXHAUSTED", "M49 finite step ceiling exhausted before completion")

    def close(self) -> None:
        """Idempotently close/clear the construction-bound M48/M47/M46 session."""
        self._best_effort_close()
