"""Explicit one-shot execution gate above the exact M59 -> M55 inbound graph.
M62 adds no concrete socket implementation.  Source/CI acceptance may compose the
reviewed graph with deterministic constructor doubles, while a live caller must
supply both an explicit opt-in token and a constructor capability at the final
execution boundary.
"""
from __future__ import annotations
from dataclasses import dataclass
from .inbound_http_connection import CompletedInboundHttpSingleConnectionTransport
from .inbound_http_end_to_end_composition import (
    BoundedInboundHttpEndToEndSourceCompositionRoot,
    InboundHttpEndToEndSourceCompositionError,
)
from .inbound_http_single_session import (
    BoundedInboundHttpSingleSessionOrchestrator,
    InboundHttpSingleSessionOrchestratorError,
)
__all__ = [
    "LOOPBACK_EXECUTION_OPT_IN",
    "BoundedInboundHttpLoopbackExecutionGate",
    "InboundHttpLoopbackExecutionGateError",
    "InboundHttpLoopbackReadiness",
]
LOOPBACK_EXECUTION_OPT_IN = "EXECUTE_ONE_LOOPBACK_NETWORK_SESSION"
_BINDING_MARKER = "inbound-http-loopback-execution-gate-binding-v1"
_GRAPH_MARKER = "m62-reviewed-execution-gate-class-graph-v1"
_MAX_LOWER_CODE_LENGTH = 128
@dataclass(frozen=True, slots=True)
class InboundHttpLoopbackReadiness:
    """Authority-negative result for a source-safe M62 dry run."""
    composed: bool
    network_invoked: bool
    run_invoked: bool
    external_authorization_established: bool
    deployment_authorized: bool
class InboundHttpLoopbackExecutionGateError(RuntimeError):
    """Stable M62 failure with at most one bounded stable lower code."""
    def __init__(
        self,
        code: str,
        message: str,
        *,
        lower_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.lower_code = lower_code
def _bounded_lower_code(
    value: object,
    *,
    _max_length: int = _MAX_LOWER_CODE_LENGTH,
) -> str | None:
    if type(value) is str and 0 < len(value) <= _max_length:
        return value
    return None
def _fail(
    code: str,
    message: str,
    *,
    lower_code: object = None,
    _error_type: type[InboundHttpLoopbackExecutionGateError] = InboundHttpLoopbackExecutionGateError,
    _bounded_lower_code_function=_bounded_lower_code,
) -> None:
    raise _error_type(
        code,
        message,
        lower_code=_bounded_lower_code_function(lower_code),
    ) from None
def _class_identity_snapshot(value: type) -> tuple[tuple[str, int], ...]:
    return tuple(map(lambda item: (item[0], id(item[1])), value.__dict__.items()))
class _OfflineSocketConstructor:
    """Callable capability that proves composition never invokes its constructor."""
    __slots__ = ("calls",)
    def __init__(self) -> None:
        self.calls = 0
    def __call__(self, _family: object, _kind: object, _protocol: object) -> object:
        self.calls += 1
        raise AssertionError("M62 dry-run constructor MUST NOT execute")
class BoundedInboundHttpLoopbackExecutionGate:
    """Dry-run or execute exactly one already-configured M59 source graph."""
    __slots__ = (
        "_source_root",
        "_source_root_type",
        "_compose_function",
        "_gate_type",
        "_opt_in_token",
        "_binding_marker",
        "_graph_marker",
        "_max_lower_code_length",
        "_error_type",
        "_readiness_type",
        "_offline_constructor_type",
        "_bounded_lower_code_function",
        "_fail_function",
        "_composition_error_type",
        "_m55_error_type",
        "_m55_class",
        "_run_once_function",
        "_orchestrator_close_function",
        "_completed_class",
        "_class_snapshot_function",
        "_construction_graph",
        "_validate_bindings_function",
        "_dry_run_function",
        "_execute_once_function",
        "_close_function",
        "_binding_witness",
        "_used",
        "_closed",
    )
    def __init__(
        self,
        *,
        source_composition_root: BoundedInboundHttpEndToEndSourceCompositionRoot,
    ) -> None:
        if type(source_composition_root) is not BoundedInboundHttpEndToEndSourceCompositionRoot:
            raise TypeError(
                "source_composition_root MUST be exact "
                "BoundedInboundHttpEndToEndSourceCompositionRoot"
            )
        snapshot = _class_identity_snapshot
        self._gate_type = type(self)
        self._opt_in_token = "EXECUTE_ONE_LOOPBACK_NETWORK_SESSION"
        self._binding_marker = "inbound-http-loopback-execution-gate-binding-v1"
        self._graph_marker = "m62-reviewed-execution-gate-class-graph-v1"
        self._max_lower_code_length = 128
        self._error_type = InboundHttpLoopbackExecutionGateError
        self._readiness_type = InboundHttpLoopbackReadiness
        self._offline_constructor_type = _OfflineSocketConstructor
        self._bounded_lower_code_function = _bounded_lower_code
        self._fail_function = _fail
        self._composition_error_type = InboundHttpEndToEndSourceCompositionError
        self._m55_error_type = InboundHttpSingleSessionOrchestratorError
        self._source_root = source_composition_root
        self._source_root_type = BoundedInboundHttpEndToEndSourceCompositionRoot
        self._compose_function = BoundedInboundHttpEndToEndSourceCompositionRoot.__call__
        self._m55_class = BoundedInboundHttpSingleSessionOrchestrator
        self._run_once_function = BoundedInboundHttpSingleSessionOrchestrator.run_once
        self._orchestrator_close_function = BoundedInboundHttpSingleSessionOrchestrator.close
        self._completed_class = CompletedInboundHttpSingleConnectionTransport
        self._class_snapshot_function = snapshot
        self._construction_graph = (
            self._graph_marker,
            self._source_root_type,
            snapshot(self._source_root_type),
            self._m55_class,
            snapshot(self._m55_class),
            self._completed_class,
            snapshot(self._completed_class),
        )
        self._validate_bindings_function = BoundedInboundHttpLoopbackExecutionGate._validate_bindings
        self._dry_run_function = BoundedInboundHttpLoopbackExecutionGate.dry_run
        self._execute_once_function = BoundedInboundHttpLoopbackExecutionGate.execute_once
        self._close_function = BoundedInboundHttpLoopbackExecutionGate.close
        self._used = False
        self._closed = False
        self._binding_witness = (
            self._binding_marker,
            self._source_root,
            self._source_root_type,
            self._compose_function,
            self._m55_class,
            self._run_once_function,
            self._orchestrator_close_function,
            self._completed_class,
            self._class_snapshot_function,
            self._construction_graph,
            self._validate_bindings_function,
            self._dry_run_function,
            self._execute_once_function,
            self._close_function,
            self._gate_type,
            self._opt_in_token,
            self._binding_marker,
            self._graph_marker,
            self._max_lower_code_length,
            self._error_type,
            self._readiness_type,
            self._offline_constructor_type,
            self._bounded_lower_code_function,
            self._fail_function,
            self._composition_error_type,
            self._m55_error_type,
        )
        self._validate_bindings_function(self)
    @property
    def used(self) -> bool:
        return self._used
    @property
    def closed(self) -> bool:
        return self._closed
    def _validate_bindings(self, _reviewed_fail=_fail) -> None:
        fail = _reviewed_fail
        if BoundedInboundHttpLoopbackExecutionGate is not self._gate_type:
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 execution-gate class binding changed")
        if type(LOOPBACK_EXECUTION_OPT_IN) is not str or type(self._opt_in_token) is not str:
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 execution opt-in binding changed")
        if LOOPBACK_EXECUTION_OPT_IN != self._opt_in_token:
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 execution opt-in binding changed")
        if type(_BINDING_MARKER) is not str or type(self._binding_marker) is not str:
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 binding marker changed")
        if _BINDING_MARKER != self._binding_marker:
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 binding marker changed")
        if type(_GRAPH_MARKER) is not str or type(self._graph_marker) is not str:
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 graph marker changed")
        if _GRAPH_MARKER != self._graph_marker:
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 graph marker changed")
        if type(_MAX_LOWER_CODE_LENGTH) is not int or type(self._max_lower_code_length) is not int:
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 lower-code bound changed")
        if _MAX_LOWER_CODE_LENGTH != self._max_lower_code_length:
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 lower-code bound changed")
        if (
            InboundHttpLoopbackExecutionGateError is not self._error_type
            or InboundHttpLoopbackReadiness is not self._readiness_type
            or _OfflineSocketConstructor is not self._offline_constructor_type
            or _bounded_lower_code is not self._bounded_lower_code_function
            or _fail is not self._fail_function
            or _class_identity_snapshot is not self._class_snapshot_function
            or InboundHttpEndToEndSourceCompositionError is not self._composition_error_type
            or InboundHttpSingleSessionOrchestratorError is not self._m55_error_type
        ):
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 reviewed module authority changed")
        if (
            BoundedInboundHttpEndToEndSourceCompositionRoot is not self._source_root_type
            or BoundedInboundHttpSingleSessionOrchestrator is not self._m55_class
            or CompletedInboundHttpSingleConnectionTransport is not self._completed_class
        ):
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 reviewed dependency binding changed")
        witness = self._binding_witness
        if type(witness) is not tuple or len(witness) != 26:
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 execution-gate binding witness changed")
        if type(witness[0]) is not str or witness[0] != self._binding_marker:
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 execution-gate binding witness changed")
        if (
            witness[1] is not self._source_root
            or witness[2] is not self._source_root_type
            or witness[3] is not self._compose_function
            or witness[4] is not self._m55_class
            or witness[5] is not self._run_once_function
            or witness[6] is not self._orchestrator_close_function
            or witness[7] is not self._completed_class
            or witness[8] is not self._class_snapshot_function
            or witness[9] is not self._construction_graph
            or witness[10] is not self._validate_bindings_function
            or witness[11] is not self._dry_run_function
            or witness[12] is not self._execute_once_function
            or witness[13] is not self._close_function
            or witness[14] is not self._gate_type
        ):
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 execution-gate binding witness changed")
        if (
            type(witness[15]) is not str
            or witness[15] != self._opt_in_token
            or type(witness[16]) is not str
            or witness[16] != self._binding_marker
            or type(witness[17]) is not str
            or witness[17] != self._graph_marker
            or type(witness[18]) is not int
            or witness[18] != self._max_lower_code_length
            or witness[19] is not self._error_type
            or witness[20] is not self._readiness_type
            or witness[21] is not self._offline_constructor_type
            or witness[22] is not self._bounded_lower_code_function
            or witness[23] is not self._fail_function
            or witness[24] is not self._composition_error_type
            or witness[25] is not self._m55_error_type
        ):
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 execution-gate policy witness changed")
        if (
            type(self) is not self._gate_type
            or self._compose_function is not self._source_root_type.__call__
            or self._run_once_function is not self._m55_class.run_once
            or self._orchestrator_close_function is not self._m55_class.close
            or self._validate_bindings_function is not self._gate_type._validate_bindings
            or self._dry_run_function is not self._gate_type.dry_run
            or self._execute_once_function is not self._gate_type.execute_once
            or self._close_function is not self._gate_type.close
        ):
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 execution-gate helper graph changed")
        graph = self._construction_graph
        snapshot = self._class_snapshot_function
        if (
            type(graph) is not tuple
            or len(graph) != 7
            or type(graph[0]) is not str
            or graph[0] != self._graph_marker
            or graph[1] is not self._source_root_type
            or graph[3] is not self._m55_class
            or graph[5] is not self._completed_class
        ):
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 reviewed class graph changed")
        if (
            graph[2] != snapshot(self._source_root_type)
            or graph[4] != snapshot(self._m55_class)
            or graph[6] != snapshot(self._completed_class)
        ):
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 reviewed class implementation changed")
        if type(self._source_root) is not self._source_root_type:
            fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 retained M59 source root changed")

    def _release(self) -> None:
        self._source_root = None
        self._source_root_type = None
        self._compose_function = None
        self._gate_type = None
        self._opt_in_token = None
        self._binding_marker = None
        self._graph_marker = None
        self._max_lower_code_length = None
        self._readiness_type = None
        self._offline_constructor_type = None
        self._composition_error_type = None
        self._m55_error_type = None
        self._m55_class = None
        self._run_once_function = None
        self._orchestrator_close_function = None
        self._completed_class = None
        self._class_snapshot_function = None
        self._construction_graph = None
        self._validate_bindings_function = None
        self._dry_run_function = None
        self._execute_once_function = None
        self._close_function = None
        self._binding_witness = None
        self._closed = True

    def _begin_once(self, _reviewed_fail=_fail) -> None:
        if self._used or self._closed:
            _reviewed_fail("LOOPBACK_EXECUTION_EXHAUSTED", "M62 execution gate is already terminal")
        validate = self._validate_bindings_function
        gate_type = self._gate_type
        if gate_type is None or validate is not gate_type._validate_bindings:
            _reviewed_fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 validation authority changed")
        validate(self)
        self._used = True

    def dry_run(self) -> InboundHttpLoopbackReadiness:
        self._begin_once()
        root = self._source_root
        compose = self._compose_function
        close_orchestrator = self._orchestrator_close_function
        validate = self._validate_bindings_function
        offline_type = self._offline_constructor_type
        readiness_type = self._readiness_type
        composition_error_type = self._composition_error_type
        fail = self._fail_function
        offline = offline_type()
        orchestrator = None
        try:
            try:
                orchestrator = compose(root, offline)
            except composition_error_type as exc:
                fail(
                    "LOOPBACK_DRY_RUN_COMPOSITION_REJECTED",
                    "M59 rejected the M62 dry-run composition",
                    lower_code=exc.code,
                )
            except Exception:
                fail("LOOPBACK_DRY_RUN_FAILED", "M62 dry-run composition failed")
            validate(self)
            if type(orchestrator) is not self._m55_class:
                fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 dry run received an unexpected orchestrator")
            if offline.calls != 0:
                fail("LOOPBACK_DRY_RUN_NETWORK_VIOLATION", "M62 dry run invoked its offline constructor")
            try:
                close_orchestrator(orchestrator)
            except Exception:
                fail("LOOPBACK_DRY_RUN_CLEANUP_UNCERTAIN", "M62 dry-run orchestrator cleanup is uncertain")
            validate(self)
            return readiness_type(
                composed=True,
                network_invoked=False,
                run_invoked=False,
                external_authorization_established=False,
                deployment_authorized=False,
            )
        finally:
            self._release()

    def execute_once(
        self,
        *,
        opt_in: object,
        constructor: object,
    ) -> CompletedInboundHttpSingleConnectionTransport:
        self._begin_once()
        root = self._source_root
        compose = self._compose_function
        run_once = self._run_once_function
        close_orchestrator = self._orchestrator_close_function
        validate = self._validate_bindings_function
        expected_m55 = self._m55_class
        expected_result = self._completed_class
        expected_opt_in = self._opt_in_token
        composition_error_type = self._composition_error_type
        m55_error_type = self._m55_error_type
        error_type = self._error_type
        bounded_lower_code = self._bounded_lower_code_function
        fail = self._fail_function
        orchestrator = None
        failure = None
        try:
            if type(opt_in) is not str or opt_in != expected_opt_in:
                fail(
                    "LOOPBACK_EXECUTION_OPT_IN_REQUIRED",
                    "M62 live execution requires the exact explicit opt-in token",
                )
            if not callable(constructor):
                fail(
                    "LOOPBACK_EXECUTION_CONSTRUCTOR_INVALID",
                    "M62 constructor capability MUST be callable",
                )
            validate(self)
            try:
                orchestrator = compose(root, constructor)
            except composition_error_type as exc:
                fail(
                    "LOOPBACK_EXECUTION_COMPOSITION_REJECTED",
                    "M59 rejected M62 execution composition",
                    lower_code=exc.code,
                )
            except Exception:
                fail("LOOPBACK_EXECUTION_COMPOSITION_FAILED", "M62 execution composition failed")
            validate(self)
            if type(orchestrator) is not expected_m55:
                fail("LOOPBACK_EXECUTION_BINDING_DRIFT", "M62 execution received an unexpected orchestrator")
            try:
                result = run_once(orchestrator)
            except m55_error_type as exc:
                failure = error_type(
                    "LOOPBACK_EXECUTION_FAILED",
                    "M55 rejected the one-shot M62 execution",
                    lower_code=bounded_lower_code(exc.code),
                )
                raise failure from None
            except Exception:
                failure = error_type(
                    "LOOPBACK_EXECUTION_FAILED",
                    "M62 one-shot execution failed",
                )
                raise failure from None
            validate(self)
            if type(result) is not expected_result:
                fail("LOOPBACK_EXECUTION_RESULT_INVALID", "M62 execution returned an unexpected result")
            return result
        finally:
            try:
                if orchestrator is not None:
                    try:
                        close_orchestrator(orchestrator)
                    except Exception:
                        if failure is None:
                            fail(
                                "LOOPBACK_EXECUTION_CLEANUP_UNCERTAIN",
                                "M62 execution cleanup is uncertain",
                            )
                    if failure is None:
                        validate(self)
            finally:
                self._release()

    def close(self) -> None:
        if self._closed:
            return
        if not self._used:
            validate = self._validate_bindings_function
            gate_type = self._gate_type
            error_type = self._error_type
            if gate_type is not None and validate is gate_type._validate_bindings:
                try:
                    validate(self)
                except error_type:
                    pass
        self._used = True
        self._release()
