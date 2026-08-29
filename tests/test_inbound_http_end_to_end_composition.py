from __future__ import annotations

import ast
import inspect
import pathlib
import unittest
from unittest.mock import patch

import marketplace.runtime.inbound_http_end_to_end_composition as m59
from marketplace.reference.inbound_http_v1 import (
    decode_inbound_control_envelope_json,
    encode_prepared_inbound_response_json,
)
from marketplace.runtime.inbound_http import InboundFederationHttpRoute
from marketplace.runtime.inbound_http_single_session import (
    BoundedInboundHttpSingleSessionOrchestrator,
)
from marketplace.runtime.inbound_http_end_to_end_composition import (
    BoundedInboundHttpEndToEndSourceCompositionRoot,
    InboundHttpEndToEndSourceCompositionError,
)
from test_inbound_http_hardening import (
    FakeSource,
    SNAPSHOT_PATH,
    SYNC_PATH,
    federation_responder,
    federation_v1,
    record,
    record_responder,
)
from test_inbound_http_response_preparer_factory import _Clock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/marketplace/runtime/inbound_http_end_to_end_composition.py"
PORT = 18080
AUTHORITY = "market.example"


class _Constructor:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, object]] = []

    def __call__(self, family, kind, protocol):
        self.calls.append((family, kind, protocol))
        raise AssertionError("M59 composition MUST NOT invoke constructor")


def _routes() -> tuple[InboundFederationHttpRoute, ...]:
    return (
        InboundFederationHttpRoute(SNAPSHOT_PATH, federation_v1.OP_SNAPSHOT),
        InboundFederationHttpRoute(SYNC_PATH, federation_v1.OP_SYNC),
    )


def _root(*, federation=None, records=None, routes=None, decoder=None, encoder=None, clock=None, authority=AUTHORITY, port=PORT):
    return BoundedInboundHttpEndToEndSourceCompositionRoot(
        federation_responder=federation if federation is not None else federation_responder(),
        record_responder=records if records is not None else record_responder(FakeSource(record())),
        control_routes=routes if routes is not None else _routes(),
        decode_transport_envelope_json=(
            decoder if decoder is not None else decode_inbound_control_envelope_json
        ),
        encode_transport_envelope_json=(
            encoder if encoder is not None else encode_prepared_inbound_response_json
        ),
        authority=authority,
        clock=clock if clock is not None else _Clock(),
        port=port,
    )


class InboundHttpEndToEndSourceCompositionTests(unittest.TestCase):
    def test_public_surface_is_exact_and_minimal(self):
        constructor = inspect.signature(
            BoundedInboundHttpEndToEndSourceCompositionRoot.__init__
        )
        self.assertEqual(
            tuple(constructor.parameters),
            (
                "self",
                "federation_responder",
                "record_responder",
                "control_routes",
                "decode_transport_envelope_json",
                "encode_transport_envelope_json",
                "authority",
                "clock",
                "port",
            ),
        )
        call = inspect.signature(BoundedInboundHttpEndToEndSourceCompositionRoot.__call__)
        self.assertEqual(tuple(call.parameters), ("self", "constructor"))

    def test_one_call_builds_exact_graph_without_invoking_constructor_or_clock(self):
        federation = federation_responder()
        records = record_responder(FakeSource(record()))
        routes = _routes()
        clock = _Clock()
        constructor = _Constructor()
        root = BoundedInboundHttpEndToEndSourceCompositionRoot(
            federation_responder=federation,
            record_responder=records,
            control_routes=routes,
            decode_transport_envelope_json=decode_inbound_control_envelope_json,
            encode_transport_envelope_json=encode_prepared_inbound_response_json,
            authority=AUTHORITY,
            clock=clock,
            port=PORT,
        )

        orchestrator = root(constructor)

        self.assertIs(type(orchestrator), BoundedInboundHttpSingleSessionOrchestrator)
        preparer_factory = getattr(orchestrator, "_preparer_factory")
        wire = getattr(preparer_factory, "_wire_adapter")
        application = getattr(wire, "_application_adapter")
        self.assertIs(getattr(application, "_federation_responder"), federation)
        self.assertIs(getattr(application, "_record_responder"), records)
        self.assertEqual(
            tuple(getattr(application, "_routes").items()),
            tuple((route.path, route.operation) for route in routes),
        )
        self.assertEqual(getattr(wire, "_authority"), AUTHORITY)
        self.assertIs(getattr(preparer_factory, "_clock"), clock)
        self.assertIs(getattr(orchestrator, "_clock"), clock)
        listener = getattr(orchestrator, "_listener_construction")
        self.assertEqual(getattr(listener, "_port"), PORT)
        self.assertIs(getattr(getattr(listener, "_factory"), "_constructor"), constructor)
        self.assertEqual(constructor.calls, [])
        self.assertEqual(clock.calls, 0)
        self.assertTrue(getattr(root, "_used"))
        self.assertIsNone(getattr(root, "_federation_responder"))
        self.assertIsNone(getattr(root, "_binding_witness"))

    def test_second_call_is_terminal(self):
        root = _root()
        constructor = _Constructor()
        root(constructor)

        with self.assertRaises(InboundHttpEndToEndSourceCompositionError) as caught:
            root(constructor)

        self.assertEqual(caught.exception.code, "END_TO_END_COMPOSITION_EXHAUSTED")
        self.assertEqual(constructor.calls, [])

    def test_invalid_input_shapes_fail_closed(self):
        with self.assertRaises(TypeError):
            BoundedInboundHttpEndToEndSourceCompositionRoot(
                federation_responder=object(),  # type: ignore[arg-type]
                record_responder=record_responder(FakeSource(record())),
                control_routes=_routes(),
                decode_transport_envelope_json=decode_inbound_control_envelope_json,
                encode_transport_envelope_json=encode_prepared_inbound_response_json,
                authority=AUTHORITY,
                clock=_Clock(),
                port=PORT,
            )
        with self.assertRaises(TypeError):
            _root(records=object())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            _root(routes=list(_routes()))  # type: ignore[arg-type]
        with self.assertRaises(InboundHttpEndToEndSourceCompositionError) as caught:
            _root(clock=object())  # type: ignore[arg-type]
        self.assertEqual(caught.exception.code, "END_TO_END_COMPOSITION_CLOCK_INVALID")
        with self.assertRaises(InboundHttpEndToEndSourceCompositionError) as caught:
            _root(decoder=object())  # type: ignore[arg-type]
        self.assertEqual(caught.exception.code, "END_TO_END_COMPOSITION_CODEC_INVALID")

    def test_route_mutation_after_construction_is_blocked(self):
        routes = _routes()
        root = _root(routes=routes)
        object.__setattr__(routes[0], "path", "/v1/federation/changed")

        with self.assertRaises(InboundHttpEndToEndSourceCompositionError) as caught:
            root(_Constructor())

        self.assertEqual(
            caught.exception.code,
            "END_TO_END_COMPOSITION_CONFIGURATION_DRIFT",
        )
    def test_private_codec_rebinding_is_blocked_before_execution(self):
        root = _root()
        hostile_calls = []

        def hostile_decoder(_body):
            hostile_calls.append(True)
            raise AssertionError("hostile M59 codec MUST NOT execute")

        object.__setattr__(root, "_decode_json", hostile_decoder)
        with self.assertRaises(InboundHttpEndToEndSourceCompositionError) as caught:
            root(_Constructor())

        self.assertEqual(caught.exception.code, "END_TO_END_COMPOSITION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])

    def test_m34_class_substitution_is_blocked_before_execution(self):
        root = _root()
        hostile_calls = []

        class HostileM34:
            def __init__(self, *args, **kwargs):
                hostile_calls.append((args, kwargs))
                raise AssertionError("hostile M34 MUST NOT execute")

        with patch.object(m59, "BoundedInboundHttpApplicationAdapter", HostileM34):
            with self.assertRaises(InboundHttpEndToEndSourceCompositionError) as caught:
                root(_Constructor())

        self.assertEqual(caught.exception.code, "END_TO_END_COMPOSITION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])

    def test_m35_and_m57_class_substitution_are_blocked_before_execution(self):
        for name in (
            "BoundedInboundHttpWireAdapter",
            "BoundedInboundHttpSingleSessionCompositionRoot",
        ):
            with self.subTest(name=name):
                root = _root()
                hostile_calls = []

                class Hostile:
                    def __init__(self, *args, **kwargs):
                        hostile_calls.append((args, kwargs))
                        raise AssertionError("hostile lower constructor MUST NOT execute")

                with patch.object(m59, name, Hostile):
                    with self.assertRaises(
                        InboundHttpEndToEndSourceCompositionError
                    ) as caught:
                        root(_Constructor())
                self.assertEqual(
                    caught.exception.code,
                    "END_TO_END_COMPOSITION_BINDING_DRIFT",
                )
                self.assertEqual(hostile_calls, [])

    def test_private_validator_and_module_snapshot_poisoning_never_execute(self):
        for mode in ("private", "module"):
            with self.subTest(mode=mode):
                root = _root()
                hostile_calls = []

                def hostile(_value):
                    hostile_calls.append(True)
                    raise AssertionError("hostile M59 helper MUST NOT execute")

                if mode == "private":
                    object.__setattr__(root, "_validate_bindings_function", hostile)
                    context = patch.object(
                        m59,
                        "_class_identity_snapshot",
                        m59._class_identity_snapshot,
                    )
                else:
                    context = patch.object(m59, "_class_identity_snapshot", hostile)
                with context:
                    with self.assertRaises(
                        InboundHttpEndToEndSourceCompositionError
                    ) as caught:
                        root(_Constructor())

                self.assertEqual(
                    caught.exception.code,
                    "END_TO_END_COMPOSITION_BINDING_DRIFT",
                )
                self.assertEqual(hostile_calls, [])


class InboundHttpEndToEndSourceCompositionBoundaryTests(unittest.TestCase):
    def test_invalid_constructor_is_terminal_without_execution(self):
        root = _root()
        with self.assertRaises(InboundHttpEndToEndSourceCompositionError) as caught:
            root(object())  # type: ignore[arg-type]
        self.assertEqual(caught.exception.code, "END_TO_END_COMPOSITION_CONSTRUCTOR_INVALID")
        self.assertTrue(getattr(root, "_used"))

    def test_authority_and_port_rejections_are_redacted_and_bounded(self):
        with self.assertRaises(InboundHttpEndToEndSourceCompositionError) as caught:
            _root(authority="bad authority")(_Constructor())
        self.assertEqual(caught.exception.code, "END_TO_END_COMPOSITION_M35_FAILED")
        self.assertNotIn("bad authority", str(caught.exception))

        with self.assertRaises(InboundHttpEndToEndSourceCompositionError) as caught:
            _root(port=80)(_Constructor())
        self.assertEqual(caught.exception.code, "END_TO_END_COMPOSITION_M57_REJECTED")
        self.assertEqual(caught.exception.lower_code, "SESSION_COMPOSITION_PORT_INVALID")

    def test_m32_and_m33_method_substitution_are_blocked_before_execution(self):
        for target_name in ("_federation_responder", "_record_responder"):
            with self.subTest(target_name=target_name):
                root = _root()
                target = getattr(root, target_name)
                method_name = "prepare_response" if target_name == "_federation_responder" else "prepare"
                hostile_calls = []

                def hostile(*args, **kwargs):
                    hostile_calls.append((args, kwargs))
                    raise AssertionError("hostile responder method MUST NOT execute")

                with patch.object(type(target), method_name, hostile):
                    with self.assertRaises(InboundHttpEndToEndSourceCompositionError) as caught:
                        root(_Constructor())
                self.assertEqual(caught.exception.code, "END_TO_END_COMPOSITION_BINDING_DRIFT")
                self.assertEqual(hostile_calls, [])


class InboundHttpEndToEndSourceCompositionSourceTests(unittest.TestCase):
    def test_source_has_no_external_io_background_retry_or_loop_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(
                    alias.name.split(".", 1)[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        forbidden = {
            "asyncio",
            "concurrent",
            "logging",
            "multiprocessing",
            "os",
            "pathlib",
            "select",
            "selectors",
            "socket",
            "ssl",
            "subprocess",
            "threading",
            "time",
        }
        self.assertTrue(imported_roots.isdisjoint(forbidden))
        forbidden_nodes = (
            ast.For,
            ast.AsyncFor,
            ast.While,
            ast.ListComp,
            ast.SetComp,
            ast.DictComp,
            ast.GeneratorExp,
        )
        for node in ast.walk(tree):
            self.assertNotIsInstance(node, forbidden_nodes)


if __name__ == "__main__":
    unittest.main()
