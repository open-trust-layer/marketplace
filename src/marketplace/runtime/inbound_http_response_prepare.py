"""One-shot bridge from bounded request reading to unsent HTTP response preparation.

M43 owns no concrete reader, socket, listener, TLS stack, writer, deployment, or
credential capability. It composes one exact M42 driver with the exact M37/M36/M35
chain retained beneath that driver, independently revalidates the completed
request, invokes M35 response preparation once, and stops before transmission.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Final

from .inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
    InboundHttpRequest,
    PreparedInboundHttpResponse,
)
from .inbound_http_read_driver import (
    BoundedInboundHttpReadDriver,
    CompletedInboundHttpReadDriverResult,
    InboundHttpReadDriverError,
)
from .inbound_http_read_plan import (
    READ_ACTION_COMPLETE,
    BoundedInboundHttpReadPlanner,
    InboundHttpReadLimits,
    InboundHttpReadPlan,
    InboundHttpReadPlanError,
)
from .inbound_http_read_session import (
    BoundedInboundHttpReadSession,
    CompletedInboundHttpReadSession,
)
from .inbound_http_stream import (
    BoundedInboundHttpStreamAssembler,
    InboundHttpStreamLimits,
)
from .inbound_http_wire import (
    BoundedInboundHttpWireAdapter,
    InboundHttpWireError,
    InboundHttpWireLimits,
    PreparedInboundHttpWireExchange,
)

_RESULT_MARKER: Final = "prepared-inbound-http-read-response-v1"
_BINDING_MARKER: Final = "inbound-http-response-preparer-binding-v1"
_AUTHORITY_NEGATIVE_FIELDS: Final = (
    "transmitted",
    "request_authenticated",
    "peer_identity_proven",
    "establishes_marketplace_truth",
    "establishes_trust",
    "establishes_authorization",
    "authorizes_protected_side_effects",
)
_M42_AUTHORITY_NEGATIVE_FIELDS: Final = (
    "socket_access_proven",
    "network_origin_proven",
    "request_authenticated",
    "peer_identity_proven",
    "establishes_marketplace_truth",
    "establishes_trust",
    "establishes_authorization",
    "authorizes_protected_side_effects",
)
_M39_AUTHORITY_NEGATIVE_FIELDS: Final = (
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
)


class InboundHttpResponsePreparationError(RuntimeError):
    """Fail-closed M43 error with preserved lower-layer reason metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        driver_code: str | None = None,
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
        self.driver_code = driver_code
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
    driver_code: str | None = None,
    invocation_code: str | None = None,
    outcome_code: str | None = None,
    session_code: str | None = None,
    transition_code: str | None = None,
    plan_code: str | None = None,
    stream_code: str | None = None,
    wire_code: str | None = None,
) -> None:
    raise InboundHttpResponsePreparationError(
        code,
        message,
        driver_code=driver_code,
        invocation_code=invocation_code,
        outcome_code=outcome_code,
        session_code=session_code,
        transition_code=transition_code,
        plan_code=plan_code,
        stream_code=stream_code,
        wire_code=wire_code,
    )


def _fail_from_driver(exc: InboundHttpReadDriverError) -> None:
    _fail(
        "RESPONSE_PREPARATION_READ_REJECTED",
        "M42 rejected the bounded read-to-completion operation",
        driver_code=exc.code,
        invocation_code=exc.invocation_code,
        outcome_code=exc.outcome_code,
        session_code=exc.session_code,
        transition_code=exc.transition_code,
        plan_code=exc.plan_code,
        stream_code=exc.stream_code,
        wire_code=exc.wire_code,
    )


def _fail_from_plan(exc: InboundHttpReadPlanError) -> None:
    _fail(
        "RESPONSE_PREPARATION_PLAN_REJECTED",
        "M37 rejected the completed request during M43 replay",
        plan_code=exc.code,
        stream_code=exc.stream_code,
        wire_code=exc.wire_code,
    )


def _wire_limits_snapshot(
    adapter: BoundedInboundHttpWireAdapter,
) -> tuple[int, int, int]:
    limits = adapter.limits
    if type(limits) is not InboundHttpWireLimits:
        _fail("RESPONSE_PREPARATION_CONFIGURATION_DRIFT", "M35 limits changed type")
    return (
        limits.max_header_bytes,
        limits.max_body_bytes,
        limits.max_response_body_bytes,
    )


def _stream_limits_snapshot(
    assembler: BoundedInboundHttpStreamAssembler,
) -> tuple[int, int]:
    limits = assembler.limits
    if type(limits) is not InboundHttpStreamLimits:
        _fail("RESPONSE_PREPARATION_CONFIGURATION_DRIFT", "M36 limits changed type")
    return (limits.max_chunks, limits.max_chunk_bytes)


def _read_limits_snapshot(
    planner: BoundedInboundHttpReadPlanner,
) -> tuple[int, int]:
    limits = planner.limits
    if type(limits) is not InboundHttpReadLimits:
        _fail("RESPONSE_PREPARATION_CONFIGURATION_DRIFT", "M37 limits changed type")
    return (limits.max_read_calls, limits.max_read_bytes)


def _application_limits_snapshot(
    adapter: BoundedInboundHttpApplicationAdapter,
) -> tuple[int, int, int]:
    limits = adapter.limits
    if type(limits) is not InboundHttpApplicationLimits:
        _fail("RESPONSE_PREPARATION_CONFIGURATION_DRIFT", "M34 limits changed type")
    return (
        limits.max_request_body_bytes,
        limits.max_response_body_bytes,
        limits.max_header_bytes,
    )


def _callable_binding(value: Any) -> tuple[Any, ...]:
    bound_self = getattr(value, "__self__", None)
    bound_function = getattr(value, "__func__", None)
    if bound_self is not None and bound_function is not None:
        return ("bound", bound_self, bound_function)
    return ("callable", value)


def _request_snapshot(request: InboundHttpRequest) -> tuple[Any, ...]:
    if type(request) is not InboundHttpRequest:
        _fail("RESPONSE_PREPARATION_REQUEST_DRIFT", "M35 request changed type")
    return (
        request.method,
        request.path,
        request.headers,
        request.body,
        request.request_authenticated,
        request.peer_identity_proven,
    )


def _response_snapshot(response: PreparedInboundHttpResponse) -> tuple[Any, ...]:
    if type(response) is not PreparedInboundHttpResponse:
        _fail("RESPONSE_PREPARATION_WIRE_DRIFT", "M35 application response changed type")
    return (
        _request_snapshot(response.request),
        response.route_kind,
        response.route_operation,
        response.status_code,
        response.headers,
        response.body,
        response.olp_message_type,
        response.transmitted,
        response.request_authenticated,
        response.peer_identity_proven,
        response.establishes_marketplace_truth,
        response.establishes_trust,
        response.establishes_authorization,
        response.authorizes_protected_side_effects,
    )


def _validate_m39_authority(value: CompletedInboundHttpReadSession) -> None:
    if type(value) is not CompletedInboundHttpReadSession:
        _fail(
            "RESPONSE_PREPARATION_COMPLETION_DRIFT",
            "M42 completion payload changed type",
        )
    for name in _M39_AUTHORITY_NEGATIVE_FIELDS:
        if getattr(value, name, None) is not False:
            _fail(
                "RESPONSE_PREPARATION_AUTHORITY_ESCALATION",
                "M39 completion promoted authority",
            )


def _validate_m42_authority(value: CompletedInboundHttpReadDriverResult) -> None:
    if type(value) is not CompletedInboundHttpReadDriverResult:
        _fail(
            "RESPONSE_PREPARATION_COMPLETION_DRIFT",
            "M42 returned unexpected completion type",
        )
    for name in _M42_AUTHORITY_NEGATIVE_FIELDS:
        if getattr(value, name, None) is not False:
            _fail(
                "RESPONSE_PREPARATION_AUTHORITY_ESCALATION",
                "M42 completion promoted authority",
            )
    _validate_m39_authority(value.completed)


def _validate_wire_authority(value: PreparedInboundHttpWireExchange) -> None:
    if type(value) is not PreparedInboundHttpWireExchange:
        _fail(
            "RESPONSE_PREPARATION_WIRE_DRIFT",
            "M35 returned unexpected prepared type",
        )
    if getattr(value, "host_authority_validated", None) is not True:
        _fail(
            "RESPONSE_PREPARATION_WIRE_DRIFT",
            "M35 did not retain validated Host authority",
        )
    if getattr(value, "tls_sni_bound", None) is not False:
        _fail(
            "RESPONSE_PREPARATION_AUTHORITY_ESCALATION",
            "M35 promoted TLS binding",
        )
    for name in _AUTHORITY_NEGATIVE_FIELDS:
        if getattr(value, name, None) is not False:
            _fail(
                "RESPONSE_PREPARATION_AUTHORITY_ESCALATION",
                "M35 prepared response promoted authority",
            )


@dataclass(frozen=True)
class PreparedInboundHttpReadResponse:
    """Integrity-bound, unsent M35 response plus bounded M42 accounting."""

    wire_exchange: PreparedInboundHttpWireExchange
    completion_plan: InboundHttpReadPlan
    driver_steps: int
    reader_invocations: int
    reads_completed: int
    request_bytes: int
    response_bytes: int
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    response_prepared: bool = field(default=True, init=False)
    transmitted: bool = field(default=False, init=False)
    socket_access_proven: bool = field(default=False, init=False)
    network_origin_proven: bool = field(default=False, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    establishes_marketplace_truth: bool = field(default=False, init=False)
    establishes_trust: bool = field(default=False, init=False)
    establishes_authorization: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _validate_wire_authority(self.wire_exchange)
        try:
            witnessed_wire = replace(self.wire_exchange)
        except ValueError as exc:
            raise ValueError("M43 nested M35 integrity replay failed") from exc
        object.__setattr__(self, "wire_exchange", witnessed_wire)

        if type(self.completion_plan) is not InboundHttpReadPlan:
            raise ValueError("completion_plan MUST be exact InboundHttpReadPlan")
        try:
            witnessed_plan = replace(self.completion_plan)
        except ValueError as exc:
            raise ValueError("M43 completion plan failed M37 integrity replay") from exc
        if witnessed_plan.action != READ_ACTION_COMPLETE:
            raise ValueError("M43 completion plan MUST be COMPLETE")
        object.__setattr__(self, "completion_plan", witnessed_plan)

        for name in ("driver_steps", "reads_completed", "request_bytes", "response_bytes"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} MUST be a positive exact integer")
        if type(self.reader_invocations) is not int or self.reader_invocations < 0:
            raise ValueError(
                "reader_invocations MUST be a non-negative exact integer"
            )
        if self.reader_invocations > self.driver_steps:
            raise ValueError(
                "reader_invocations MUST NOT exceed M43-observed M42 steps"
            )
        if self.reader_invocations > self.reads_completed:
            raise ValueError(
                "reader_invocations MUST NOT exceed cumulative M39 reads"
            )
        if witnessed_plan.reads_completed != self.reads_completed:
            raise ValueError(
                "reads_completed MUST equal the exact replayed M37 completion plan"
            )
        if witnessed_plan.buffered_bytes != self.request_bytes:
            raise ValueError(
                "request_bytes MUST equal the exact replayed M37 completed prefix length"
            )
        if self.response_bytes != len(witnessed_wire.response_bytes):
            raise ValueError(
                "response_bytes MUST equal the exact M35 response wire length"
            )

        if self.response_prepared is not True or self.transmitted is not False:
            raise ValueError("M43 response preparation state is invalid")
        for name in (
            "socket_access_proven",
            "network_origin_proven",
            "request_authenticated",
            "peer_identity_proven",
            "establishes_marketplace_truth",
            "establishes_trust",
            "establishes_authorization",
            "authorizes_protected_side_effects",
        ):
            if getattr(self, name, None) is not False:
                raise ValueError(
                    "M43 prepared result promoted a forbidden authority fact"
                )

        current = (
            _RESULT_MARKER,
            witnessed_wire.integrity_snapshot,
            witnessed_plan.integrity_snapshot,
            self.driver_steps,
            self.reader_invocations,
            self.reads_completed,
            self.request_bytes,
            self.response_bytes,
            self.response_prepared,
            self.transmitted,
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
            raise ValueError("M43 prepared-response integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpResponsePreparer:
    """Drive one request to completion and prepare exactly one unsent M35 response."""

    __slots__ = (
        "_driver",
        "_session",
        "_planner",
        "_assembler",
        "_wire",
        "_application_adapter",
        "_run_function",
        "_close_function",
        "_session_close_function",
        "_plan_function",
        "_parse_function",
        "_prepare_function",
        "_response_validate_function",
        "_binding_snapshot_function",
        "_require_bound_function",
        "_validate_function",
        "_terminal_cleanup_function",
        "_independent_response_replay_function",
        "_run",
        "_close",
        "_session_close",
        "_plan",
        "_parse",
        "_prepare",
        "_response_validate",
        "_application_handle_witness",
        "_read_limits",
        "_stream_limits",
        "_wire_limits",
        "_application_limits",
        "_wire_authority",
        "_binding_witness",
        "_used",
    )

    def __init__(self, *, read_driver: BoundedInboundHttpReadDriver) -> None:
        if type(read_driver) is not BoundedInboundHttpReadDriver:
            raise TypeError("read_driver MUST be exact BoundedInboundHttpReadDriver")
        session = getattr(read_driver, "_session", None)
        if type(session) is not BoundedInboundHttpReadSession:
            raise ValueError("M42 MUST retain one exact M39 session")
        planner = getattr(session, "_read_planner", None)
        if type(planner) is not BoundedInboundHttpReadPlanner:
            raise ValueError("M39 MUST retain one exact M37 planner")
        assembler = getattr(planner, "_stream_assembler", None)
        if type(assembler) is not BoundedInboundHttpStreamAssembler:
            raise ValueError("M37 MUST retain one exact M36 assembler")
        wire = getattr(assembler, "_wire_adapter", None)
        if type(wire) is not BoundedInboundHttpWireAdapter:
            raise ValueError("M36 MUST retain one exact M35 wire adapter")
        application_adapter = getattr(wire, "_application_adapter", None)
        if type(application_adapter) is not BoundedInboundHttpApplicationAdapter:
            raise ValueError("M35 MUST retain one exact M34 application adapter")

        self._driver = read_driver
        self._session = session
        self._planner = planner
        self._assembler = assembler
        self._wire = wire
        self._application_adapter = application_adapter
        self._run_function = BoundedInboundHttpReadDriver.run_to_completion
        self._close_function = BoundedInboundHttpReadDriver.close
        self._session_close_function = BoundedInboundHttpReadSession.close
        self._plan_function = BoundedInboundHttpReadPlanner.plan
        self._parse_function = BoundedInboundHttpWireAdapter._parse_request
        self._prepare_function = BoundedInboundHttpWireAdapter.prepare
        self._response_validate_function = (
            BoundedInboundHttpWireAdapter._validated_application_response
        )
        self._binding_snapshot_function = BoundedInboundHttpResponsePreparer._binding_snapshot
        self._require_bound_function = BoundedInboundHttpResponsePreparer._require_bound
        self._validate_function = BoundedInboundHttpResponsePreparer._validate_bindings
        self._terminal_cleanup_function = BoundedInboundHttpResponsePreparer._terminal_cleanup
        self._independent_response_replay_function = BoundedInboundHttpResponsePreparer._independent_response_replay
        self._run = self._run_function.__get__(
            read_driver, BoundedInboundHttpReadDriver
        )
        self._close = self._close_function.__get__(
            read_driver, BoundedInboundHttpReadDriver
        )
        self._session_close = self._session_close_function.__get__(
            session, BoundedInboundHttpReadSession
        )
        self._plan = self._plan_function.__get__(
            planner, BoundedInboundHttpReadPlanner
        )
        self._parse = self._parse_function.__get__(
            wire, BoundedInboundHttpWireAdapter
        )
        self._prepare = self._prepare_function.__get__(
            wire, BoundedInboundHttpWireAdapter
        )
        self._response_validate = self._response_validate_function.__get__(
            wire, BoundedInboundHttpWireAdapter
        )
        self._application_handle_witness = _callable_binding(
            application_adapter.handle
        )
        self._read_limits = _read_limits_snapshot(planner)
        self._stream_limits = _stream_limits_snapshot(assembler)
        self._wire_limits = _wire_limits_snapshot(wire)
        self._application_limits = _application_limits_snapshot(
            application_adapter
        )
        self._wire_authority = wire.authority
        if type(self._wire_authority) is not str or not self._wire_authority:
            raise ValueError("M35 authority MUST remain non-empty exact text")
        self._used = False
        self._binding_witness = self._binding_snapshot_function(self)
        self._validate_function(self)

    def _binding_snapshot(self) -> tuple[Any, ...]:
        return (
            _BINDING_MARKER,
            self._driver,
            self._session,
            self._planner,
            self._assembler,
            self._wire,
            self._application_adapter,
            self._run_function,
            self._close_function,
            self._session_close_function,
            self._plan_function,
            self._parse_function,
            self._prepare_function,
            self._response_validate_function,
            self._read_limits,
            self._stream_limits,
            self._wire_limits,
            self._application_limits,
            self._wire_authority,
            self._application_handle_witness,
            self._binding_snapshot_function,
            self._require_bound_function,
            self._validate_function,
            self._terminal_cleanup_function,
            self._independent_response_replay_function,
        )

    def _require_bound(
        self,
        bound: Any,
        function: Any,
        owner: Any,
        label: str,
    ) -> None:
        if (
            getattr(bound, "__self__", None) is not owner
            or getattr(bound, "__func__", None) is not function
        ):
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                f"captured {label} binding changed",
            )

    def _validate_bindings(self) -> None:
        if (
            type(self._driver) is not BoundedInboundHttpReadDriver
            or getattr(self._driver, "_session", None) is not self._session
        ):
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                "M42 to M39 binding changed",
            )
        if (
            type(self._session) is not BoundedInboundHttpReadSession
            or getattr(self._session, "_read_planner", None) is not self._planner
        ):
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                "M39 to M37 binding changed",
            )
        if (
            type(self._planner) is not BoundedInboundHttpReadPlanner
            or getattr(self._planner, "_stream_assembler", None)
            is not self._assembler
        ):
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                "M37 to M36 binding changed",
            )
        if (
            type(self._assembler) is not BoundedInboundHttpStreamAssembler
            or getattr(self._assembler, "_wire_adapter", None) is not self._wire
        ):
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                "M36 to M35 binding changed",
            )
        if (
            type(self._wire) is not BoundedInboundHttpWireAdapter
            or getattr(self._wire, "_application_adapter", None)
            is not self._application_adapter
        ):
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                "M35 to M34 binding changed",
            )
        if _read_limits_snapshot(self._planner) != self._read_limits:
            _fail(
                "RESPONSE_PREPARATION_CONFIGURATION_DRIFT",
                "M37 limits changed",
            )
        if _stream_limits_snapshot(self._assembler) != self._stream_limits:
            _fail(
                "RESPONSE_PREPARATION_CONFIGURATION_DRIFT",
                "M36 limits changed",
            )
        if (
            _wire_limits_snapshot(self._wire) != self._wire_limits
            or self._wire.authority != self._wire_authority
        ):
            _fail(
                "RESPONSE_PREPARATION_CONFIGURATION_DRIFT",
                "M35 wire configuration changed",
            )
        if (
            _application_limits_snapshot(self._application_adapter)
            != self._application_limits
        ):
            _fail(
                "RESPONSE_PREPARATION_CONFIGURATION_DRIFT",
                "M34 application limits changed",
            )
        if (
            _callable_binding(self._application_adapter.handle)
            != self._application_handle_witness
        ):
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                "M34 application handle binding changed",
            )
        if BoundedInboundHttpWireAdapter._parse_request is not self._parse_function:
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                "M35 internal parser function changed",
            )
        if (
            BoundedInboundHttpWireAdapter._validated_application_response
            is not self._response_validate_function
        ):
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                "M35 response validator function changed",
            )
        snapshot = self._binding_snapshot_function
        require_bound = self._require_bound_function
        if (
            snapshot is not BoundedInboundHttpResponsePreparer._binding_snapshot
            or require_bound is not BoundedInboundHttpResponsePreparer._require_bound
            or self._validate_function
            is not BoundedInboundHttpResponsePreparer._validate_bindings
            or self._terminal_cleanup_function
            is not BoundedInboundHttpResponsePreparer._terminal_cleanup
            or self._independent_response_replay_function
            is not BoundedInboundHttpResponsePreparer._independent_response_replay
        ):
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                "M43 helper method graph changed",
            )
        witness = self._binding_witness
        current = snapshot(self)
        if (
            type(witness) is not tuple
            or len(witness) != 25
            or witness[0] != _BINDING_MARKER
            or any(witness[index] is not current[index] for index in range(1, 25))
        ):
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                "M43 construction witness changed",
            )
        require_bound(
            self, self._run, self._run_function, self._driver, "M42 run"
        )
        require_bound(
            self, self._close, self._close_function, self._driver, "M42 close"
        )
        require_bound(
            self,
            self._session_close,
            self._session_close_function,
            self._session,
            "M39 cleanup",
        )
        require_bound(
            self, self._plan, self._plan_function, self._planner, "M37 plan"
        )
        require_bound(
            self, self._parse, self._parse_function, self._wire, "M35 parser"
        )
        require_bound(
            self, self._prepare, self._prepare_function, self._wire, "M35 prepare"
        )
        require_bound(
            self,
            self._response_validate,
            self._response_validate_function,
            self._wire,
            "M35 response validator",
        )

    def _terminal_cleanup(self) -> None:
        """Clear M39 request bytes through construction-captured exact cleanup."""
        if (
            getattr(self._session_close, "__self__", None) is not self._session
            or getattr(self._session_close, "__func__", None)
            is not self._session_close_function
        ):
            _fail(
                "RESPONSE_PREPARATION_CLEANUP_UNCERTAIN",
                "captured M39 cleanup authority changed",
            )
        try:
            self._session_close()
        except Exception:
            _fail(
                "RESPONSE_PREPARATION_CLEANUP_UNCERTAIN",
                "captured M39 cleanup failed",
            )
        if (
            getattr(self._session, "_closed", None) is not True
            or getattr(self._session, "_prefix", None) != b""
        ):
            _fail(
                "RESPONSE_PREPARATION_CLEANUP_UNCERTAIN",
                "M39 cleanup did not verify cleared closed state",
            )

    @property
    def used(self) -> bool:
        return self._used

    def _independent_response_replay(
        self,
        value: PreparedInboundHttpWireExchange,
        *,
        request: InboundHttpRequest,
    ) -> None:
        validate = self._validate_function
        witness = self._binding_witness
        if (
            validate is not BoundedInboundHttpResponsePreparer._validate_bindings
            or type(witness) is not tuple
            or len(witness) != 25
            or witness[22] is not validate
        ):
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                "M43 trusted validator binding is unavailable",
            )
        body_bytes = value.response_body_bytes
        if (
            type(body_bytes) is not int
            or body_bytes <= 0
            or body_bytes > len(value.response_bytes)
        ):
            _fail(
                "RESPONSE_PREPARATION_WIRE_DRIFT",
                "M35 response body accounting is invalid",
            )
        body = value.response_bytes[-body_bytes:]
        headers = (
            ("connection", "close"),
            ("content-length", str(len(body))),
            ("content-type", "application/json"),
        )
        try:
            candidate = PreparedInboundHttpResponse(
                request=request,
                route_kind=value.route_kind,
                route_operation=value.route_operation,
                status_code=value.status_code,
                headers=headers,
                body=body,
                olp_message_type=value.olp_message_type,
            )
        except ValueError:
            _fail(
                "RESPONSE_PREPARATION_WIRE_DRIFT",
                "M35 wire result cannot reconstruct one canonical M34 response",
            )

        validate(self)
        try:
            replayed = self._response_validate(candidate, request=request)
        except InboundHttpWireError as exc:
            validate(self)
            _fail(
                "RESPONSE_PREPARATION_RESPONSE_REJECTED",
                "captured M35 response validator rejected the prepared response",
                wire_code=exc.code,
            )
        except Exception:
            validate(self)
            _fail(
                "RESPONSE_PREPARATION_RESPONSE_FAILED",
                "captured M35 response validation failed unexpectedly",
            )
        validate(self)
        if _response_snapshot(replayed) != _response_snapshot(candidate):
            _fail(
                "RESPONSE_PREPARATION_RESPONSE_DRIFT",
                "captured M35 response replay changed prepared semantics",
            )

    def prepare(self) -> PreparedInboundHttpReadResponse:
        """Perform one bounded read-to-unsent-response preparation transaction."""
        if self._used:
            _fail(
                "RESPONSE_PREPARER_USED",
                "M43 response preparer is one-shot",
            )
        validate = self._validate_function
        terminal_cleanup = self._terminal_cleanup_function
        independent_replay = self._independent_response_replay_function
        witness = self._binding_witness
        if (
            validate is not BoundedInboundHttpResponsePreparer._validate_bindings
            or terminal_cleanup is not BoundedInboundHttpResponsePreparer._terminal_cleanup
            or independent_replay
            is not BoundedInboundHttpResponsePreparer._independent_response_replay
            or type(witness) is not tuple
            or len(witness) != 25
            or witness[22] is not validate
            or witness[23] is not terminal_cleanup
            or witness[24] is not independent_replay
        ):
            _fail(
                "RESPONSE_PREPARATION_BINDING_DRIFT",
                "M43 trusted helper binding is unavailable",
            )
        try:
            validate(self)
        except InboundHttpResponsePreparationError:
            self._used = True
            terminal_cleanup(self)
            raise
        self._used = True

        try:
            completion = self._run()
        except InboundHttpReadDriverError as exc:
            _fail_from_driver(exc)
        except Exception:
            _fail(
                "RESPONSE_PREPARATION_READ_FAILED",
                "M42 read completion failed unexpectedly",
            )

        validate(self)
        _validate_m42_authority(completion)
        if completion.reads_completed != completion.completed.reads_completed:
            _fail(
                "RESPONSE_PREPARATION_COMPLETION_DRIFT",
                "M42 cumulative read accounting changed",
            )
        try:
            witnessed_completion = replace(completion)
        except ValueError:
            _fail(
                "RESPONSE_PREPARATION_COMPLETION_DRIFT",
                "M42 completion failed integrity replay",
            )

        completed = witnessed_completion.completed
        prefix = completed.prefix
        if type(prefix) is not bytes or not prefix:
            _fail(
                "RESPONSE_PREPARATION_COMPLETION_DRIFT",
                "M39 completion prefix is not exact non-empty bytes",
            )

        validate(self)
        try:
            replay_plan = self._plan(
                prefix,
                reads_completed=completed.reads_completed,
            )
        except InboundHttpReadPlanError as exc:
            validate(self)
            _fail_from_plan(exc)
        validate(self)
        if type(replay_plan) is not InboundHttpReadPlan:
            _fail(
                "RESPONSE_PREPARATION_PLAN_DRIFT",
                "M37 returned unexpected plan type",
            )
        try:
            witnessed_plan = replace(replay_plan)
        except ValueError:
            _fail(
                "RESPONSE_PREPARATION_PLAN_DRIFT",
                "M37 replay plan failed integrity replay",
            )
        if witnessed_plan.action != READ_ACTION_COMPLETE:
            _fail(
                "RESPONSE_PREPARATION_PLAN_DRIFT",
                "M37 no longer classifies M42 bytes as complete",
            )
        if witnessed_plan.integrity_snapshot != completed.plan.integrity_snapshot:
            _fail(
                "RESPONSE_PREPARATION_PLAN_DRIFT",
                "M37 completion witness drifted from M39 handoff",
            )
        if (
            witnessed_plan.buffered_bytes != len(prefix)
            or witnessed_plan.reads_completed != completed.reads_completed
        ):
            _fail(
                "RESPONSE_PREPARATION_PLAN_DRIFT",
                "M37 completed request accounting drifted",
            )

        validate(self)
        try:
            parsed = self._parse(prefix)
        except InboundHttpWireError as exc:
            validate(self)
            _fail(
                "RESPONSE_PREPARATION_PARSE_REJECTED",
                "M35 rejected the completed bytes during independent parse",
                wire_code=exc.code,
            )
        except Exception:
            validate(self)
            _fail(
                "RESPONSE_PREPARATION_PARSE_FAILED",
                "M35 independent parse failed unexpectedly",
            )
        validate(self)
        parsed_snapshot = _request_snapshot(parsed)

        try:
            wire_result = self._prepare(prefix)
        except InboundHttpWireError as exc:
            validate(self)
            _fail(
                "RESPONSE_PREPARATION_WIRE_REJECTED",
                "M35 rejected response preparation",
                wire_code=exc.code,
            )
        except Exception:
            validate(self)
            _fail(
                "RESPONSE_PREPARATION_WIRE_FAILED",
                "M35 response preparation failed unexpectedly",
            )
        validate(self)

        _validate_wire_authority(wire_result)
        if _request_snapshot(wire_result.request) != parsed_snapshot:
            _fail(
                "RESPONSE_PREPARATION_REQUEST_DRIFT",
                "M35 prepared response is not bound to the independently parsed request",
            )
        if wire_result.host_authority != self._wire_authority:
            _fail(
                "RESPONSE_PREPARATION_CONFIGURATION_DRIFT",
                "M35 prepared response changed Host authority",
            )
        try:
            witnessed_wire = replace(wire_result)
        except ValueError:
            _fail(
                "RESPONSE_PREPARATION_WIRE_DRIFT",
                "M35 prepared response failed integrity replay",
            )
        if _request_snapshot(witnessed_wire.request) != parsed_snapshot:
            _fail(
                "RESPONSE_PREPARATION_REQUEST_DRIFT",
                "M35 replay changed the prepared request",
            )

        independent_replay(self,
            witnessed_wire,
            request=parsed,
        )

        return PreparedInboundHttpReadResponse(
            wire_exchange=witnessed_wire,
            completion_plan=witnessed_plan,
            driver_steps=witnessed_completion.driver_steps,
            reader_invocations=witnessed_completion.reader_invocations,
            reads_completed=witnessed_completion.reads_completed,
            request_bytes=witnessed_plan.buffered_bytes,
            response_bytes=len(witnessed_wire.response_bytes),
        )

    def close(self) -> None:
        """Idempotently prevent use and clear the construction-bound M39 request state."""
        if not self._used:
            self._used = True
        terminal_cleanup = self._terminal_cleanup_function
        witness = self._binding_witness
        if (
            terminal_cleanup is not BoundedInboundHttpResponsePreparer._terminal_cleanup
            or type(witness) is not tuple
            or len(witness) != 25
            or witness[23] is not terminal_cleanup
        ):
            _fail(
                "RESPONSE_PREPARATION_CLEANUP_UNCERTAIN",
                "M43 trusted cleanup binding is unavailable",
            )
        terminal_cleanup(self)
