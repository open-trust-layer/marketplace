"""Transport-free composition root joining exact M56 to exact M55.

M57 constructs one reviewed response-preparer factory and one reviewed
single-session orchestrator. Composition does not invoke the injected socket
constructor, clock, reader, listener, or any network operation.
"""
from __future__ import annotations

from typing import Callable

from .inbound_http import BoundedInboundHttpApplicationAdapter
from .inbound_http_response_preparer_factory import (
    BoundedInboundHttpResponsePreparerCompositionFactory,
    InboundHttpResponsePreparerCompositionError,
)
from .inbound_http_single_session import (
    BoundedInboundHttpSingleSessionOrchestrator,
    InboundHttpSingleSessionOrchestratorError,
)
from .inbound_http_wire import BoundedInboundHttpWireAdapter
from .inbound_tcp_socket_factory import PythonTcpSocketConstructor

__all__ = [
    "BoundedInboundHttpSingleSessionCompositionRoot",
    "InboundHttpSingleSessionCompositionError",
]

_MIN_PORT = 1024
_MAX_PORT = 65535
_BINDING_MARKER = "inbound-http-single-session-composition-root-binding-v1"
_GRAPH_MARKER = "m57-m56-m55-class-identity-graph-v1"


class InboundHttpSingleSessionCompositionError(RuntimeError):
    """Stable M57 composition failure with bounded lower-stage metadata."""

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


def _fail(
    code: str,
    message: str,
    *,
    lower_code: str | None = None,
) -> None:
    raise InboundHttpSingleSessionCompositionError(
        code,
        message,
        lower_code=lower_code,
    ) from None


def _class_identity_snapshot(value: type) -> tuple[tuple[str, int], ...]:
    return tuple(map(lambda item: (item[0], id(item[1])), value.__dict__.items()))


class BoundedInboundHttpSingleSessionCompositionRoot:
    """Construct exactly one M56 -> M55 source-level composition graph."""

    __slots__ = (
        "_wire_adapter",
        "_application_adapter",
        "_clock",
        "_port",
        "_m56_class",
        "_m55_class",
        "_construction_graph",
        "_class_snapshot_function",
        "_validate_graph_function",
        "_validate_bindings_function",
        "_call_function",
        "_binding_witness",
        "_used",
    )

    def __init__(
        self,
        *,
        wire_adapter: BoundedInboundHttpWireAdapter,
        clock: Callable[[], float],
        port: int,
    ) -> None:
        if type(wire_adapter) is not BoundedInboundHttpWireAdapter:
            raise TypeError("wire_adapter MUST be exact BoundedInboundHttpWireAdapter")
        if not callable(clock):
            _fail("SESSION_COMPOSITION_CLOCK_INVALID", "M57 clock MUST be callable")
        if type(port) is not int or not _MIN_PORT <= port <= _MAX_PORT:
            _fail(
                "SESSION_COMPOSITION_PORT_INVALID",
                "M57 port MUST be exact integer within 1024..65535",
            )
        application_adapter = getattr(wire_adapter, "_application_adapter", None)
        if type(application_adapter) is not BoundedInboundHttpApplicationAdapter:
            _fail("SESSION_COMPOSITION_BINDING_DRIFT", "M57 retained M34 adapter is invalid")
        snapshot = _class_identity_snapshot
        self._wire_adapter = wire_adapter
        self._application_adapter = application_adapter
        self._clock = clock
        self._port = port
        self._m56_class = BoundedInboundHttpResponsePreparerCompositionFactory
        self._m55_class = BoundedInboundHttpSingleSessionOrchestrator
        self._class_snapshot_function = snapshot
        self._construction_graph = (
            _GRAPH_MARKER,
            BoundedInboundHttpApplicationAdapter,
            snapshot(BoundedInboundHttpApplicationAdapter),
            BoundedInboundHttpWireAdapter,
            snapshot(BoundedInboundHttpWireAdapter),
            self._m56_class,
            snapshot(self._m56_class),
            self._m55_class,
            snapshot(self._m55_class),
        )
        self._validate_graph_function = (
            BoundedInboundHttpSingleSessionCompositionRoot._validate_construction_graph
        )
        self._validate_bindings_function = (
            BoundedInboundHttpSingleSessionCompositionRoot._validate_bindings
        )
        self._call_function = BoundedInboundHttpSingleSessionCompositionRoot.__call__
        self._used = False
        self._binding_witness = (
            _BINDING_MARKER,
            self._wire_adapter,
            self._application_adapter,
            self._clock,
            self._port,
            self._m56_class,
            self._m55_class,
            self._construction_graph,
            self._class_snapshot_function,
            self._validate_graph_function,
            self._validate_bindings_function,
            self._call_function,
        )
        self._validate_bindings_function(self)

    def _validate_construction_graph(self) -> None:
        graph = self._construction_graph
        snapshot = self._class_snapshot_function
        if snapshot is not _class_identity_snapshot:
            _fail("SESSION_COMPOSITION_BINDING_DRIFT", "M57 class-snapshot authority changed")
        if type(graph) is not tuple or len(graph) != 9 or graph[0] != _GRAPH_MARKER:
            _fail("SESSION_COMPOSITION_BINDING_DRIFT", "M57 construction graph witness changed")
        if (
            graph[1] is not BoundedInboundHttpApplicationAdapter
            or graph[3] is not BoundedInboundHttpWireAdapter
            or graph[5] is not self._m56_class
            or graph[7] is not self._m55_class
            or self._m56_class is not BoundedInboundHttpResponsePreparerCompositionFactory
            or self._m55_class is not BoundedInboundHttpSingleSessionOrchestrator
        ):
            _fail("SESSION_COMPOSITION_BINDING_DRIFT", "M57 retained lower class graph changed")
        if (
            graph[2] != snapshot(BoundedInboundHttpApplicationAdapter)
            or graph[4] != snapshot(BoundedInboundHttpWireAdapter)
            or graph[6] != snapshot(self._m56_class)
            or graph[8] != snapshot(self._m55_class)
        ):
            _fail("SESSION_COMPOSITION_BINDING_DRIFT", "M57 reviewed lower class graph changed")

    def _validate_bindings(self) -> None:
        witness = self._binding_witness
        if (
            type(self) is not BoundedInboundHttpSingleSessionCompositionRoot
            or type(witness) is not tuple
            or len(witness) != 12
            or witness[0] != _BINDING_MARKER
            or witness[1] is not self._wire_adapter
            or witness[2] is not self._application_adapter
            or witness[3] is not self._clock
            or witness[4] != self._port
            or witness[5] is not self._m56_class
            or witness[6] is not self._m55_class
            or witness[7] is not self._construction_graph
            or witness[8] is not self._class_snapshot_function
            or witness[9] is not self._validate_graph_function
            or witness[10] is not self._validate_bindings_function
            or witness[11] is not self._call_function
        ):
            _fail("SESSION_COMPOSITION_BINDING_DRIFT", "M57 composition binding witness changed")
        if (
            self._validate_graph_function is not BoundedInboundHttpSingleSessionCompositionRoot._validate_construction_graph
            or self._validate_bindings_function is not BoundedInboundHttpSingleSessionCompositionRoot._validate_bindings
            or self._call_function is not BoundedInboundHttpSingleSessionCompositionRoot.__call__
        ):
            _fail("SESSION_COMPOSITION_BINDING_DRIFT", "M57 helper graph changed")
        self._validate_graph_function(self)
        if type(self._wire_adapter) is not BoundedInboundHttpWireAdapter:
            _fail("SESSION_COMPOSITION_BINDING_DRIFT", "M57 retained M35 adapter changed")
        if type(self._application_adapter) is not BoundedInboundHttpApplicationAdapter:
            _fail("SESSION_COMPOSITION_BINDING_DRIFT", "M57 retained M34 adapter changed")
        if getattr(self._wire_adapter, "_application_adapter", None) is not self._application_adapter:
            _fail("SESSION_COMPOSITION_BINDING_DRIFT", "M57 M35 to M34 binding changed")

    def __call__(
        self,
        constructor: PythonTcpSocketConstructor,
    ) -> BoundedInboundHttpSingleSessionOrchestrator:
        if self._used:
            _fail(
                "SESSION_COMPOSITION_EXHAUSTED",
                "M57 single-session composition root is one-shot",
            )
        object.__setattr__(self, "_used", True)

        wire_adapter = self._wire_adapter
        clock = self._clock
        port = self._port
        m56_class = self._m56_class
        m55_class = self._m55_class
        validate_bindings = self._validate_bindings_function
        validate_graph = self._validate_graph_function

        try:
            if (
                validate_bindings
                is not BoundedInboundHttpSingleSessionCompositionRoot._validate_bindings
                or validate_graph
                is not BoundedInboundHttpSingleSessionCompositionRoot._validate_construction_graph
                or self._call_function
                is not BoundedInboundHttpSingleSessionCompositionRoot.__call__
            ):
                _fail("SESSION_COMPOSITION_BINDING_DRIFT", "M57 executable helper graph changed")
            validate_bindings(self)
            if not callable(constructor):
                _fail(
                    "SESSION_COMPOSITION_CONSTRUCTOR_INVALID",
                    "M57 socket constructor capability MUST be callable",
                )
            validate_graph(self)
            try:
                preparer_factory = m56_class(
                    wire_adapter=wire_adapter,
                    clock=clock,
                )
            except InboundHttpResponsePreparerCompositionError as exc:
                _fail(
                    "SESSION_COMPOSITION_M56_REJECTED",
                    "M56 rejected M57 response-preparer composition",
                    lower_code=exc.code,
                )
            except Exception:
                _fail(
                    "SESSION_COMPOSITION_M56_FAILED",
                    "M57 could not construct the M56 response-preparer factory",
                )
            validate_graph(self)
            if type(preparer_factory) is not m56_class:
                _fail(
                    "SESSION_COMPOSITION_M56_INVALID",
                    "M57 M56 construction returned an unexpected type",
                )

            try:
                orchestrator = m55_class(
                    constructor=constructor,
                    response_preparer_factory=preparer_factory,
                    clock=clock,
                    port=port,
                )
            except InboundHttpSingleSessionOrchestratorError as exc:
                _fail(
                    "SESSION_COMPOSITION_M55_REJECTED",
                    "M55 rejected M57 single-session composition",
                    lower_code=exc.code,
                )
            except Exception:
                _fail(
                    "SESSION_COMPOSITION_M55_FAILED",
                    "M57 could not construct the M55 orchestrator",
                )

            validate_graph(self)
            if type(orchestrator) is not m55_class:
                _fail(
                    "SESSION_COMPOSITION_M55_INVALID",
                    "M57 M55 construction returned an unexpected type",
                )
            if (
                getattr(orchestrator, "_preparer_factory", None) is not preparer_factory
                or getattr(orchestrator, "_clock", None) is not clock
            ):
                _fail(
                    "SESSION_COMPOSITION_BINDING_DRIFT",
                    "M57 M56 to M55 retained binding changed",
                )
            listener = getattr(orchestrator, "_listener_construction", None)
            if getattr(listener, "_port", None) != port:
                _fail(
                    "SESSION_COMPOSITION_BINDING_DRIFT",
                    "M57 retained M55 listener port changed",
                )
            socket_factory = getattr(listener, "_factory", None)
            if getattr(socket_factory, "_constructor", None) is not constructor:
                _fail(
                    "SESSION_COMPOSITION_BINDING_DRIFT",
                    "M57 retained socket constructor binding changed",
                )
            return orchestrator
        except InboundHttpSingleSessionCompositionError:
            raise
        except Exception:
            _fail(
                "SESSION_COMPOSITION_FAILED",
                "M57 composition failed without exposing lower exception text",
            )
        finally:
            object.__setattr__(self, "_wire_adapter", None)
            object.__setattr__(self, "_application_adapter", None)
            object.__setattr__(self, "_clock", None)
            object.__setattr__(self, "_port", None)
            object.__setattr__(self, "_m56_class", None)
            object.__setattr__(self, "_m55_class", None)
            object.__setattr__(self, "_construction_graph", None)
            object.__setattr__(self, "_class_snapshot_function", None)
            object.__setattr__(self, "_validate_graph_function", None)
            object.__setattr__(self, "_validate_bindings_function", None)
            object.__setattr__(self, "_call_function", None)
            object.__setattr__(self, "_binding_witness", None)
