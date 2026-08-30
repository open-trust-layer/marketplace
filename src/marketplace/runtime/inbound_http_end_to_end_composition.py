"""Transport-free source composition from exact M32/M33 through exact M57.

M59 constructs one reviewed M34 -> M35 -> M57 -> M55 graph and stops. It does
not invoke the supplied socket constructor, clock, reader, listener, or any
network operation, and it never calls the returned M55 orchestrator.
"""
from __future__ import annotations

from typing import Callable

from .inbound_federation import BoundedInboundFederationResponder
from .inbound_record import BoundedInboundRecordResponder
from .inbound_http import (
    MAX_INBOUND_HTTP_CONTROL_ROUTES,
    BoundedInboundHttpApplicationAdapter,
    InboundFederationHttpRoute,
)
from .inbound_http_wire import BoundedInboundHttpWireAdapter
from .inbound_http_response_preparer_factory import (
    BoundedInboundHttpResponsePreparerCompositionFactory,
)
from .inbound_http_single_session import BoundedInboundHttpSingleSessionOrchestrator
from .inbound_http_single_session_composition import (
    BoundedInboundHttpSingleSessionCompositionRoot,
    InboundHttpSingleSessionCompositionError,
)
from .inbound_tcp_socket_factory import PythonTcpSocketConstructor

__all__ = [
    "BoundedInboundHttpEndToEndSourceCompositionRoot",
    "InboundHttpEndToEndSourceCompositionError",
]

_BINDING_MARKER = "inbound-http-end-to-end-source-composition-binding-v1"
_GRAPH_MARKER = "m59-reviewed-inbound-source-class-graph-v1"


class InboundHttpEndToEndSourceCompositionError(RuntimeError):
    """Stable M59 source-composition failure with bounded lower metadata."""

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


def _fail(code: str, message: str, *, lower_code: str | None = None) -> None:
    raise InboundHttpEndToEndSourceCompositionError(
        code,
        message,
        lower_code=lower_code,
    ) from None


def _class_identity_snapshot(value: type) -> tuple[tuple[str, int], ...]:
    return tuple(map(lambda item: (item[0], id(item[1])), value.__dict__.items()))


def _callable_binding_snapshot(value: object) -> tuple[object, ...]:
    owner = getattr(value, "__self__", None)
    function = getattr(value, "__func__", None)
    if owner is not None and function is not None:
        return ("bound", owner, function)
    return ("direct", value)


class BoundedInboundHttpEndToEndSourceCompositionRoot:
    """Construct exactly one M32/M33 -> M34 -> M35 -> M57 -> M55 graph."""

    __slots__ = (
        "_federation_responder",
        "_record_responder",
        "_control_routes",
        "_route_snapshot",
        "_decode_json",
        "_encode_json",
        "_authority",
        "_clock",
        "_port",
        "_federation_prepare_binding",
        "_record_prepare_binding",
        "_m34_class",
        "_m35_class",
        "_m57_class",
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
        federation_responder: BoundedInboundFederationResponder,
        record_responder: BoundedInboundRecordResponder,
        control_routes: tuple[InboundFederationHttpRoute, ...],
        decode_transport_envelope_json: object,
        encode_transport_envelope_json: object,
        authority: str,
        clock: Callable[[], float],
        port: int,
    ) -> None:
        if type(federation_responder) is not BoundedInboundFederationResponder:
            raise TypeError("federation_responder MUST be exact BoundedInboundFederationResponder")
        if type(record_responder) is not BoundedInboundRecordResponder:
            raise TypeError("record_responder MUST be exact BoundedInboundRecordResponder")
        if (
            type(control_routes) is not tuple
            or not 1 <= len(control_routes) <= MAX_INBOUND_HTTP_CONTROL_ROUTES
            or not all(map(lambda route: type(route) is InboundFederationHttpRoute, control_routes))
        ):
            raise TypeError("control_routes MUST be a bounded exact tuple of M34 routes")
        if not all(
            map(
                lambda route: type(route.path) is str and type(route.operation) is str,
                control_routes,
            )
        ):
            raise TypeError("control_routes MUST retain exact text route fields")
        if not callable(decode_transport_envelope_json) or not callable(
            encode_transport_envelope_json
        ):
            _fail("END_TO_END_COMPOSITION_CODEC_INVALID", "M59 codecs MUST be callable")
        if not callable(clock):
            _fail("END_TO_END_COMPOSITION_CLOCK_INVALID", "M59 clock MUST be callable")

        snapshot = _class_identity_snapshot
        self._federation_responder = federation_responder
        self._record_responder = record_responder
        self._control_routes = control_routes
        self._route_snapshot = tuple(map(lambda route: (route.path, route.operation), control_routes))
        self._decode_json = decode_transport_envelope_json
        self._encode_json = encode_transport_envelope_json
        self._authority = authority
        self._clock = clock
        self._port = port
        self._federation_prepare_binding = _callable_binding_snapshot(
            federation_responder.prepare_response
        )
        self._record_prepare_binding = _callable_binding_snapshot(record_responder.prepare)
        self._m34_class = BoundedInboundHttpApplicationAdapter
        self._m35_class = BoundedInboundHttpWireAdapter
        self._m57_class = BoundedInboundHttpSingleSessionCompositionRoot
        self._class_snapshot_function = snapshot
        self._construction_graph = (
            _GRAPH_MARKER,
            BoundedInboundFederationResponder,
            snapshot(BoundedInboundFederationResponder),
            BoundedInboundRecordResponder,
            snapshot(BoundedInboundRecordResponder),
            self._m34_class,
            snapshot(self._m34_class),
            self._m35_class,
            snapshot(self._m35_class),
            BoundedInboundHttpResponsePreparerCompositionFactory,
            snapshot(BoundedInboundHttpResponsePreparerCompositionFactory),
            BoundedInboundHttpSingleSessionOrchestrator,
            snapshot(BoundedInboundHttpSingleSessionOrchestrator),
            self._m57_class,
            snapshot(self._m57_class),
        )
        self._validate_graph_function = (
            BoundedInboundHttpEndToEndSourceCompositionRoot._validate_construction_graph
        )
        self._validate_bindings_function = (
            BoundedInboundHttpEndToEndSourceCompositionRoot._validate_bindings
        )
        self._call_function = BoundedInboundHttpEndToEndSourceCompositionRoot.__call__
        self._used = False
        self._binding_witness = (
            _BINDING_MARKER,
            self._federation_responder,
            self._record_responder,
            self._control_routes,
            self._route_snapshot,
            self._decode_json,
            self._encode_json,
            self._authority,
            self._clock,
            self._port,
            self._federation_prepare_binding,
            self._record_prepare_binding,
            self._m34_class,
            self._m35_class,
            self._m57_class,
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
            _fail(
                "END_TO_END_COMPOSITION_BINDING_DRIFT",
                "M59 class-snapshot authority changed",
            )
        if (
            type(graph) is not tuple
            or len(graph) != 15
            or type(graph[0]) is not str
            or graph[0] != _GRAPH_MARKER
        ):
            _fail(
                "END_TO_END_COMPOSITION_BINDING_DRIFT",
                "M59 construction graph witness changed",
            )
        if (
            graph[1] is not BoundedInboundFederationResponder
            or graph[3] is not BoundedInboundRecordResponder
            or graph[5] is not BoundedInboundHttpApplicationAdapter
            or graph[7] is not BoundedInboundHttpWireAdapter
            or graph[9] is not BoundedInboundHttpResponsePreparerCompositionFactory
            or graph[11] is not BoundedInboundHttpSingleSessionOrchestrator
            or graph[13] is not BoundedInboundHttpSingleSessionCompositionRoot
            or self._m34_class is not BoundedInboundHttpApplicationAdapter
            or self._m35_class is not BoundedInboundHttpWireAdapter
            or self._m57_class is not BoundedInboundHttpSingleSessionCompositionRoot
        ):
            _fail(
                "END_TO_END_COMPOSITION_BINDING_DRIFT",
                "M59 retained lower class graph changed",
            )
        if (
            graph[2] != snapshot(BoundedInboundFederationResponder)
            or graph[4] != snapshot(BoundedInboundRecordResponder)
            or graph[6] != snapshot(self._m34_class)
            or graph[8] != snapshot(self._m35_class)
            or graph[10] != snapshot(BoundedInboundHttpResponsePreparerCompositionFactory)
            or graph[12] != snapshot(BoundedInboundHttpSingleSessionOrchestrator)
            or graph[14] != snapshot(self._m57_class)
        ):
            _fail(
                "END_TO_END_COMPOSITION_BINDING_DRIFT",
                "M59 reviewed lower class graph changed",
            )

    def _validate_bindings(self) -> None:
        witness = self._binding_witness
        if (
            type(self) is not BoundedInboundHttpEndToEndSourceCompositionRoot
            or type(witness) is not tuple
            or len(witness) != 20
            or type(witness[0]) is not str
            or witness[0] != _BINDING_MARKER
            or witness[1] is not self._federation_responder
            or witness[2] is not self._record_responder
            or witness[3] is not self._control_routes
            or witness[4] is not self._route_snapshot
            or witness[5] is not self._decode_json
            or witness[6] is not self._encode_json
            or witness[7] is not self._authority
            or witness[8] is not self._clock
            or witness[9] is not self._port
            or witness[10] is not self._federation_prepare_binding
            or witness[11] is not self._record_prepare_binding
            or witness[12] is not self._m34_class
            or witness[13] is not self._m35_class
            or witness[14] is not self._m57_class
            or witness[15] is not self._construction_graph
            or witness[16] is not self._class_snapshot_function
            or witness[17] is not self._validate_graph_function
            or witness[18] is not self._validate_bindings_function
            or witness[19] is not self._call_function
        ):
            _fail(
                "END_TO_END_COMPOSITION_BINDING_DRIFT",
                "M59 composition binding witness changed",
            )
        if (
            self._validate_graph_function
            is not BoundedInboundHttpEndToEndSourceCompositionRoot._validate_construction_graph
            or self._validate_bindings_function
            is not BoundedInboundHttpEndToEndSourceCompositionRoot._validate_bindings
            or self._call_function
            is not BoundedInboundHttpEndToEndSourceCompositionRoot.__call__
        ):
            _fail(
                "END_TO_END_COMPOSITION_BINDING_DRIFT",
                "M59 helper graph changed",
            )
        self._validate_graph_function(self)
        if type(self._federation_responder) is not BoundedInboundFederationResponder:
            _fail("END_TO_END_COMPOSITION_BINDING_DRIFT", "M59 retained M32 responder changed")
        if type(self._record_responder) is not BoundedInboundRecordResponder:
            _fail("END_TO_END_COMPOSITION_BINDING_DRIFT", "M59 retained M33 responder changed")
        if (
            type(self._control_routes) is not tuple
            or not 1 <= len(self._control_routes) <= MAX_INBOUND_HTTP_CONTROL_ROUTES
            or not all(
                map(lambda route: type(route) is InboundFederationHttpRoute, self._control_routes)
            )
        ):
            _fail(
                "END_TO_END_COMPOSITION_BINDING_DRIFT",
                "M59 retained route collection changed",
            )
        if not all(
            map(
                lambda route: type(route.path) is str and type(route.operation) is str,
                self._control_routes,
            )
        ):
            _fail(
                "END_TO_END_COMPOSITION_CONFIGURATION_DRIFT",
                "M59 retained route field types changed",
            )
        current_routes = tuple(
            map(lambda route: (route.path, route.operation), self._control_routes)
        )
        if current_routes != self._route_snapshot:
            _fail(
                "END_TO_END_COMPOSITION_CONFIGURATION_DRIFT",
                "M59 retained route configuration changed",
            )
        federation_call = self._federation_responder.prepare_response
        record_call = self._record_responder.prepare
        federation_witness = self._federation_prepare_binding
        record_witness = self._record_prepare_binding
        if federation_witness[0] == "bound":
            federation_ok = (
                getattr(federation_call, "__self__", None) is federation_witness[1]
                and getattr(federation_call, "__func__", None) is federation_witness[2]
            )
        else:
            federation_ok = federation_call is federation_witness[1]
        if record_witness[0] == "bound":
            record_ok = (
                getattr(record_call, "__self__", None) is record_witness[1]
                and getattr(record_call, "__func__", None) is record_witness[2]
            )
        else:
            record_ok = record_call is record_witness[1]
        if not federation_ok or not record_ok:
            _fail(
                "END_TO_END_COMPOSITION_BINDING_DRIFT",
                "M59 retained responder call binding changed",
            )
        if not callable(self._decode_json) or not callable(self._encode_json):
            _fail("END_TO_END_COMPOSITION_BINDING_DRIFT", "M59 retained codec binding changed")
        if not callable(self._clock):
            _fail("END_TO_END_COMPOSITION_BINDING_DRIFT", "M59 retained clock binding changed")

    def __call__(
        self,
        constructor: PythonTcpSocketConstructor,
    ) -> BoundedInboundHttpSingleSessionOrchestrator:
        if self._used:
            _fail(
                "END_TO_END_COMPOSITION_EXHAUSTED",
                "M59 source composition root is one-shot",
            )
        object.__setattr__(self, "_used", True)

        validate_bindings = self._validate_bindings_function
        validate_graph = self._validate_graph_function
        try:
            if (
                validate_bindings
                is not BoundedInboundHttpEndToEndSourceCompositionRoot._validate_bindings
                or validate_graph
                is not BoundedInboundHttpEndToEndSourceCompositionRoot._validate_construction_graph
                or self._call_function
                is not BoundedInboundHttpEndToEndSourceCompositionRoot.__call__
            ):
                _fail(
                    "END_TO_END_COMPOSITION_BINDING_DRIFT",
                    "M59 executable helper graph changed",
                )
            validate_bindings(self)
            if not callable(constructor):
                _fail(
                    "END_TO_END_COMPOSITION_CONSTRUCTOR_INVALID",
                    "M59 socket constructor capability MUST be callable",
                )

            federation = self._federation_responder
            records = self._record_responder
            routes = self._control_routes
            decoder = self._decode_json
            encoder = self._encode_json
            authority = self._authority
            clock = self._clock
            port = self._port
            m34_class = self._m34_class
            m35_class = self._m35_class
            m57_class = self._m57_class

            validate_graph(self)
            try:
                application = m34_class(
                    federation_responder=federation,
                    record_responder=records,
                    control_routes=routes,
                    decode_transport_envelope_json=decoder,
                    encode_transport_envelope_json=encoder,
                )
            except Exception:
                _fail(
                    "END_TO_END_COMPOSITION_M34_FAILED",
                    "M59 could not construct the M34 application adapter",
                )
            validate_graph(self)
            if type(application) is not m34_class:
                _fail(
                    "END_TO_END_COMPOSITION_M34_INVALID",
                    "M59 M34 construction returned an unexpected type",
                )
            if (
                getattr(application, "_federation_responder", None) is not federation
                or getattr(application, "_record_responder", None) is not records
                or getattr(application, "_decode_json", None) is not decoder
                or getattr(application, "_encode_json", None) is not encoder
                or tuple(getattr(application, "_routes", {}).items()) != self._route_snapshot
            ):
                _fail(
                    "END_TO_END_COMPOSITION_BINDING_DRIFT",
                    "M59 M32/M33 to M34 binding changed",
                )

            try:
                wire = m35_class(
                    application_adapter=application,
                    authority=authority,
                )
            except Exception:
                _fail(
                    "END_TO_END_COMPOSITION_M35_FAILED",
                    "M59 could not construct the M35 wire adapter",
                )
            validate_graph(self)
            if type(wire) is not m35_class:
                _fail(
                    "END_TO_END_COMPOSITION_M35_INVALID",
                    "M59 M35 construction returned an unexpected type",
                )
            if (
                getattr(wire, "_application_adapter", None) is not application
                or getattr(wire, "_authority", None) != authority
            ):
                _fail(
                    "END_TO_END_COMPOSITION_BINDING_DRIFT",
                    "M59 M34 to M35 binding changed",
                )

            try:
                session_root = m57_class(
                    wire_adapter=wire,
                    clock=clock,
                    port=port,
                )
            except InboundHttpSingleSessionCompositionError as exc:
                _fail(
                    "END_TO_END_COMPOSITION_M57_REJECTED",
                    "M57 rejected M59 source composition",
                    lower_code=exc.code,
                )
            except Exception:
                _fail(
                    "END_TO_END_COMPOSITION_M57_FAILED",
                    "M59 could not construct the M57 source-composition root",
                )

            validate_graph(self)
            if type(session_root) is not m57_class:
                _fail(
                    "END_TO_END_COMPOSITION_M57_INVALID",
                    "M59 M57 construction returned an unexpected type",
                )
            if (
                getattr(session_root, "_wire_adapter", None) is not wire
                or getattr(session_root, "_application_adapter", None) is not application
                or getattr(session_root, "_clock", None) is not clock
                or getattr(session_root, "_port", None) != port
            ):
                _fail(
                    "END_TO_END_COMPOSITION_BINDING_DRIFT",
                    "M59 M35 to M57 binding changed",
                )

            validate_graph(self)
            try:
                orchestrator = session_root(constructor)
            except InboundHttpSingleSessionCompositionError as exc:
                _fail(
                    "END_TO_END_COMPOSITION_M57_REJECTED",
                    "M57 rejected M59 final source handoff",
                    lower_code=exc.code,
                )
            except Exception:
                _fail(
                    "END_TO_END_COMPOSITION_M57_FAILED",
                    "M59 final M57 source handoff failed",
                )

            validate_graph(self)
            if type(orchestrator) is not BoundedInboundHttpSingleSessionOrchestrator:
                _fail(
                    "END_TO_END_COMPOSITION_RESULT_INVALID",
                    "M59 source composition returned an unexpected final type",
                )
            preparer_factory = getattr(orchestrator, "_preparer_factory", None)
            if (
                type(preparer_factory)
                is not BoundedInboundHttpResponsePreparerCompositionFactory
                or getattr(preparer_factory, "_wire_adapter", None) is not wire
                or getattr(preparer_factory, "_clock", None) is not clock
                or getattr(orchestrator, "_clock", None) is not clock
            ):
                _fail(
                    "END_TO_END_COMPOSITION_BINDING_DRIFT",
                    "M59 returned M55 retained preparer graph changed",
                )
            listener = getattr(orchestrator, "_listener_construction", None)
            factory = getattr(listener, "_factory", None)
            if (
                getattr(listener, "_port", None) != port
                or getattr(factory, "_constructor", None) is not constructor
            ):
                _fail(
                    "END_TO_END_COMPOSITION_BINDING_DRIFT",
                    "M59 returned M55 listener/constructor binding changed",
                )
            return orchestrator
        except InboundHttpEndToEndSourceCompositionError:
            raise
        except Exception:
            _fail(
                "END_TO_END_COMPOSITION_FAILED",
                "M59 source composition failed without exposing lower exception text",
            )
        finally:
            object.__setattr__(self, "_federation_responder", None)
            object.__setattr__(self, "_record_responder", None)
            object.__setattr__(self, "_control_routes", None)
            object.__setattr__(self, "_route_snapshot", None)
            object.__setattr__(self, "_decode_json", None)
            object.__setattr__(self, "_encode_json", None)
            object.__setattr__(self, "_authority", None)
            object.__setattr__(self, "_clock", None)
            object.__setattr__(self, "_port", None)
            object.__setattr__(self, "_federation_prepare_binding", None)
            object.__setattr__(self, "_record_prepare_binding", None)
            object.__setattr__(self, "_m34_class", None)
            object.__setattr__(self, "_m35_class", None)
            object.__setattr__(self, "_m57_class", None)
            object.__setattr__(self, "_construction_graph", None)
            object.__setattr__(self, "_class_snapshot_function", None)
            object.__setattr__(self, "_validate_graph_function", None)
            object.__setattr__(self, "_validate_bindings_function", None)
            object.__setattr__(self, "_call_function", None)
            object.__setattr__(self, "_binding_witness", None)
