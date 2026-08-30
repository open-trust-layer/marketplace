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
def _bounded_lower_code(value: object) -> str | None:
    if type(value) is str and 0 < len(value) <= _MAX_LOWER_CODE_LENGTH:
        return value
    return None
def _fail(code: str, message: str, *, lower_code: object = None) -> None:
    raise InboundHttpLoopbackExecutionGateError(
        code,
        message,
        lower_code=_bounded_lower_code(lower_code),
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
        self._source_root = source_composition_root
        self._source_root_type = BoundedInboundHttpEndToEndSourceCompositionRoot
        self._compose_function = BoundedInboundHttpEndToEndSourceCompositionRoot.__call__
        self._m55_class = BoundedInboundHttpSingleSessionOrchestrator
        self._run_once_function = BoundedInboundHttpSingleSessionOrchestrator.run_once
        self._orchestrator_close_function = BoundedInboundHttpSingleSessionOrchestrator.close
        self._completed_class = CompletedInboundHttpSingleConnectionTransport
        self._class_snapshot_function = snapshot
        self._construction_graph = (
            _GRAPH_MARKER,
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
            _BINDING_MARKER,
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
        )
        self._validate_bindings_function(self)
    @property
    def used(self) -> bool:
        return self._used
    @property
    def closed(self) -> bool:
        return self._closed
    def _validate_bindings(self) -> None:
        witness = self._binding_witness
        if (
            type(self) is not BoundedInboundHttpLoopbackExecutionGate
            or type(witness) is not tuple
            or len(witness) != 14
            or type(witness[0]) is not str
            or witness[0] != _BINDING_MARKER
            or witness[1] is not self._source_root
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
        ):
            _fail(
                "LOOPBACK_EXECUTION_BINDING_DRIFT",
                "M62 execution-gate binding witness changed",
            )
        if (
            self._source_root_type is not BoundedInboundHttpEndToEndSourceCompositionRoot
            or self._compose_function is not BoundedInboundHttpEndToEndSourceCompositionRoot.__call__
            or self._m55_class is not BoundedInboundHttpSingleSessionOrchestrator
            or self._run_once_function is not BoundedInboundHttpSingleSessionOrchestrator.run_once
            or self._orchestrator_close_function is not BoundedInboundHttpSingleSessionOrchestrator.close
            or self._completed_class is not CompletedInboundHttpSingleConnectionTransport
            or self._class_snapshot_function is not _class_identity_snapshot
            or self._validate_bindings_function
            is not BoundedInboundHttpLoopbackExecutionGate._validate_bindings
            or self._dry_run_function is not BoundedInboundHttpLoopbackExecutionGate.dry_run
            or self._execute_once_function is not BoundedInboundHttpLoopbackExecutionGate.execute_once
            or self._close_function is not BoundedInboundHttpLoopbackExecutionGate.close
        ):
            _fail(
                "LOOPBACK_EXECUTION_BINDING_DRIFT",
                "M62 execution-gate helper graph changed",
            )
        graph = self._construction_graph
        snapshot = self._class_snapshot_function
        if (
            type(graph) is not tuple
            or len(graph) != 7
            or type(graph[0]) is not str
            or graph[0] != _GRAPH_MARKER
            or graph[1] is not self._source_root_type
            or graph[3] is not self._m55_class
            or graph[5] is not self._completed_class
        ):
            _fail(
                "LOOPBACK_EXECUTION_BINDING_DRIFT",
                "M62 reviewed class graph changed",
            )
        if (
            graph[2] != snapshot(self._source_root_type)
            or graph[4] != snapshot(self._m55_class)
            or graph[6] != snapshot(self._completed_class)
        ):
            _fail(
                "LOOPBACK_EXECUTION_BINDING_DRIFT",
                "M62 reviewed class implementation changed",
            )
        if type(self._source_root) is not self._source_root_type:
            _fail(
                "LOOPBACK_EXECUTION_BINDING_DRIFT",
                "M62 retained M59 source root changed",
            )
    def _release(self) -> None:
        self._source_root = None
        self._source_root_type = None
        self._compose_function = None
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
    def _begin_once(self) -> None:
        if self._used or self._closed:
            _fail("LOOPBACK_EXECUTION_EXHAUSTED", "M62 execution gate is already terminal")
        validate = self._validate_bindings_function
        if validate is not BoundedInboundHttpLoopbackExecutionGate._validate_bindings:
            _fail(
                "LOOPBACK_EXECUTION_BINDING_DRIFT",
                "M62 validation authority changed",
            )
        validate(self)
        self._used = True
    def dry_run(self) -> InboundHttpLoopbackReadiness:
        self._begin_once()
        root = self._source_root
        compose = self._compose_function
        close_orchestrator = self._orchestrator_close_function
        offline = _OfflineSocketConstructor()
        orchestrator = None
        try:
            try:
                orchestrator = compose(root, offline)
            except InboundHttpEndToEndSourceCompositionError as exc:
                _fail(
                    "LOOPBACK_DRY_RUN_COMPOSITION_REJECTED",
                    "M59 rejected the M62 dry-run composition",
                    lower_code=exc.code,
                )
            except Exception:
                _fail(
                    "LOOPBACK_DRY_RUN_FAILED",
                    "M62 dry-run composition failed",
                )
            if type(orchestrator) is not self._m55_class:
                _fail(
                    "LOOPBACK_EXECUTION_BINDING_DRIFT",
                    "M62 dry run received an unexpected orchestrator",
                )
            if offline.calls != 0:
                _fail(
                    "LOOPBACK_DRY_RUN_NETWORK_VIOLATION",
                    "M62 dry run invoked its offline constructor",
                )
            try:
                close_orchestrator(orchestrator)
            except Exception:
                _fail(
                    "LOOPBACK_DRY_RUN_CLEANUP_UNCERTAIN",
                    "M62 dry-run orchestrator cleanup is uncertain",
                )
            return InboundHttpLoopbackReadiness(
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
        expected_m55 = self._m55_class
        expected_result = self._completed_class
        orchestrator = None
        failure = None
        try:
            if type(opt_in) is not str or opt_in != LOOPBACK_EXECUTION_OPT_IN:
                _fail(
                    "LOOPBACK_EXECUTION_OPT_IN_REQUIRED",
                    "M62 live execution requires the exact explicit opt-in token",
                )
            if not callable(constructor):
                _fail(
                    "LOOPBACK_EXECUTION_CONSTRUCTOR_INVALID",
                    "M62 constructor capability MUST be callable",
                )
            self._validate_bindings_function(self)
            try:
                orchestrator = compose(root, constructor)
            except InboundHttpEndToEndSourceCompositionError as exc:
                _fail(
                    "LOOPBACK_EXECUTION_COMPOSITION_REJECTED",
                    "M59 rejected M62 execution composition",
                    lower_code=exc.code,
                )
            except Exception:
                _fail(
                    "LOOPBACK_EXECUTION_COMPOSITION_FAILED",
                    "M62 execution composition failed",
                )
            if type(orchestrator) is not expected_m55:
                _fail(
                    "LOOPBACK_EXECUTION_BINDING_DRIFT",
                    "M62 execution received an unexpected orchestrator",
                )
            self._validate_bindings_function(self)
            try:
                result = run_once(orchestrator)
            except InboundHttpSingleSessionOrchestratorError as exc:
                failure = InboundHttpLoopbackExecutionGateError(
                    "LOOPBACK_EXECUTION_FAILED",
                    "M55 rejected the one-shot M62 execution",
                    lower_code=_bounded_lower_code(exc.code),
                )
                raise failure from None
            except Exception:
                failure = InboundHttpLoopbackExecutionGateError(
                    "LOOPBACK_EXECUTION_FAILED",
                    "M62 one-shot execution failed",
                )
                raise failure from None
            if type(result) is not expected_result:
                _fail(
                    "LOOPBACK_EXECUTION_RESULT_INVALID",
                    "M62 execution returned an unexpected result",
                )
            return result
        finally:
            if orchestrator is not None:
                try:
                    close_orchestrator(orchestrator)
                except Exception:
                    if failure is None:
                        self._release()
                        _fail(
                            "LOOPBACK_EXECUTION_CLEANUP_UNCERTAIN",
                            "M62 execution cleanup is uncertain",
                        )
            self._release()
    def close(self) -> None:
        if self._closed:
            return
        if not self._used:
            validate = self._validate_bindings_function
            if validate is BoundedInboundHttpLoopbackExecutionGate._validate_bindings:
                try:
                    validate(self)
                except InboundHttpLoopbackExecutionGateError:
                    pass
        self._used = True
        self._release()
