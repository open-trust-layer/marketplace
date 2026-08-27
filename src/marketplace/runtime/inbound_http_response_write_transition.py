"""Transport-free transition for one already-returned response-write count.

M45 never invokes a writer. It validates one positive local write count against
the exact construction-bound M44 budget, advances local accounting exactly once,
and independently derives the next M44 plan. Local accounting is not proof that
response bytes reached any peer.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from .inbound_http_response_prepare import PreparedInboundHttpReadResponse
from .inbound_http_response_write_plan import (
    WRITE_ACTION_COMPLETE,
    WRITE_ACTION_WRITE,
    BoundedInboundHttpResponseWritePlanner,
    InboundHttpResponseWriteLimits,
    InboundHttpResponseWritePlan,
    InboundHttpResponseWritePlanError,
)


class InboundHttpResponseWriteTransitionError(RuntimeError):
    """Fail-closed M45 error with preserved M44 reason metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        write_plan_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.write_plan_code = write_plan_code


def _fail(
    code: str,
    message: str,
    *,
    write_plan_code: str | None = None,
) -> None:
    raise InboundHttpResponseWriteTransitionError(
        code,
        message,
        write_plan_code=write_plan_code,
    )


def _limits_snapshot(value: InboundHttpResponseWriteLimits) -> tuple[int, int]:
    if type(value) is not InboundHttpResponseWriteLimits:
        _fail("WRITE_CONFIGURATION_DRIFT", "M44 write limits changed type after M45 construction")
    return (value.max_write_calls, value.max_write_bytes)


@dataclass(frozen=True)
class InboundHttpResponseWriteTransition:
    """One validated local write-count transition; never transport evidence."""

    write_calls_completed: int
    bytes_written: int
    accepted_write_bytes: int
    prior_plan: InboundHttpResponseWritePlan
    next_plan: InboundHttpResponseWritePlan
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
        if type(self.write_calls_completed) is not int or self.write_calls_completed <= 0:
            raise ValueError("write_calls_completed MUST be a positive exact integer")
        if type(self.bytes_written) is not int or self.bytes_written <= 0:
            raise ValueError("bytes_written MUST be a positive exact integer")
        if type(self.accepted_write_bytes) is not int or self.accepted_write_bytes <= 0:
            raise ValueError("accepted_write_bytes MUST be a positive exact integer")
        if type(self.prior_plan) is not InboundHttpResponseWritePlan:
            raise ValueError("prior_plan MUST be exact InboundHttpResponseWritePlan")
        if type(self.next_plan) is not InboundHttpResponseWritePlan:
            raise ValueError("next_plan MUST be exact InboundHttpResponseWritePlan")
        try:
            prior = replace(self.prior_plan)
            next_plan = replace(self.next_plan)
        except ValueError as exc:
            raise ValueError("nested M44 write-plan integrity replay failed") from exc
        if prior.action != WRITE_ACTION_WRITE:
            raise ValueError("M45 transition requires a prior WRITE plan")
        if prior.write_calls_completed + 1 != self.write_calls_completed:
            raise ValueError("M45 write-call accounting did not advance exactly once")
        if prior.bytes_written + self.accepted_write_bytes != self.bytes_written:
            raise ValueError("M45 byte accounting did not advance by accepted count")
        if self.accepted_write_bytes > prior.next_write_bytes:
            raise ValueError("M45 accepted write count exceeds prior M44 budget")
        if next_plan.write_calls_completed != self.write_calls_completed:
            raise ValueError("next M44 plan has different write-call accounting")
        if next_plan.bytes_written != self.bytes_written:
            raise ValueError("next M44 plan has different byte accounting")
        if next_plan.response_bytes != prior.response_bytes:
            raise ValueError("M45 transition changed prepared response length")
        if next_plan.prepared_response_integrity != prior.prepared_response_integrity:
            raise ValueError("M45 transition changed M43 response binding")
        for name in (
            "writer_invoked",
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
                raise ValueError("M45 transition promoted a forbidden authority fact")
        current = (
            "inbound-http-response-write-transition-v1",
            self.write_calls_completed,
            self.bytes_written,
            self.accepted_write_bytes,
            prior.integrity_snapshot,
            next_plan.integrity_snapshot,
            self.writer_invoked,
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
            raise ValueError("M45 write-transition integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpResponseWriteTransitioner:
    """Validate one already-returned write count against construction-bound M44."""

    def __init__(self, *, write_planner: BoundedInboundHttpResponseWritePlanner) -> None:
        if type(write_planner) is not BoundedInboundHttpResponseWritePlanner:
            raise TypeError("write_planner MUST be exact BoundedInboundHttpResponseWritePlanner")
        self._write_planner = write_planner
        self._plan = write_planner.plan
        self._plan_function = self._plan.__func__
        self._max_write_calls, self._max_write_bytes = _limits_snapshot(write_planner.limits)

    @property
    def write_limits(self) -> InboundHttpResponseWriteLimits:
        return InboundHttpResponseWriteLimits(
            max_write_calls=self._max_write_calls,
            max_write_bytes=self._max_write_bytes,
        )

    def _validate_configuration(self) -> None:
        if type(self._write_planner) is not BoundedInboundHttpResponseWritePlanner:
            _fail("WRITE_CONFIGURATION_DRIFT", "M44 planner changed type after M45 construction")
        if _limits_snapshot(self._write_planner.limits) != (
            self._max_write_calls,
            self._max_write_bytes,
        ):
            _fail("WRITE_CONFIGURATION_DRIFT", "M44 write limits changed after M45 construction")
        if (
            getattr(self._plan, "__self__", None) is not self._write_planner
            or getattr(self._plan, "__func__", None) is not self._plan_function
        ):
            _fail("WRITE_CONFIGURATION_DRIFT", "captured M44 plan binding changed after M45 construction")

    def _authoritative_plan(
        self,
        prepared_response: PreparedInboundHttpReadResponse,
        *,
        write_calls_completed: int,
        bytes_written: int,
    ) -> InboundHttpResponseWritePlan:
        self._validate_configuration()
        try:
            plan = self._plan(
                prepared_response,
                write_calls_completed=write_calls_completed,
                bytes_written=bytes_written,
            )
        except InboundHttpResponseWritePlanError as exc:
            self._validate_configuration()
            _fail(
                "WRITE_PLAN_REJECTED",
                "M44 rejected supplied write-transition state",
                write_plan_code=exc.code,
            )
        self._validate_configuration()
        if type(plan) is not InboundHttpResponseWritePlan:
            _fail("INVALID_WRITE_PLAN", "M44 returned an unexpected plan type")
        try:
            witnessed = replace(plan)
        except ValueError:
            _fail("WRITE_PLAN_DRIFT", "M44 plan failed integrity replay")
        self._validate_configuration()
        return witnessed

    def transition(
        self,
        prepared_response: PreparedInboundHttpReadResponse,
        *,
        write_calls_completed: int,
        bytes_written: int,
        accepted_write_bytes: int,
    ) -> InboundHttpResponseWriteTransition:
        """Advance local accounting for one already-returned positive write count."""
        if type(write_calls_completed) is not int or write_calls_completed < 0:
            _fail("INVALID_WRITE_CALL_COUNT", "write_calls_completed MUST be non-negative exact int")
        if type(bytes_written) is not int or bytes_written < 0:
            _fail("INVALID_WRITE_BYTE_COUNT", "bytes_written MUST be non-negative exact int")
        if type(accepted_write_bytes) is not int or accepted_write_bytes <= 0:
            _fail("INVALID_ACCEPTED_WRITE_COUNT", "accepted_write_bytes MUST be positive exact int")

        prior = self._authoritative_plan(
            prepared_response,
            write_calls_completed=write_calls_completed,
            bytes_written=bytes_written,
        )
        if prior.action == WRITE_ACTION_COMPLETE:
            _fail("WRITE_AFTER_COMPLETE", "a write result was supplied after M44 reported completion")
        if prior.action != WRITE_ACTION_WRITE:
            _fail("INVALID_WRITE_PLAN", "M44 prior action is outside M45 transition profile")
        if accepted_write_bytes > prior.next_write_bytes:
            _fail("WRITE_COUNT_EXCEEDS_PLAN", "accepted write count exceeds exact M44 next-write budget")
        if accepted_write_bytes > prior.remaining_bytes:
            _fail("WRITE_COUNT_EXCEEDS_REMAINING", "accepted write count exceeds remaining response")

        next_calls = write_calls_completed + 1
        next_bytes = bytes_written + accepted_write_bytes
        next_plan = self._authoritative_plan(
            prepared_response,
            write_calls_completed=next_calls,
            bytes_written=next_bytes,
        )
        return InboundHttpResponseWriteTransition(
            write_calls_completed=next_calls,
            bytes_written=next_bytes,
            accepted_write_bytes=accepted_write_bytes,
            prior_plan=prior,
            next_plan=next_plan,
        )
