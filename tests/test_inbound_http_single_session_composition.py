from __future__ import annotations

import ast
import inspect
import pathlib
import unittest
from unittest.mock import patch

import marketplace.runtime.inbound_http_single_session_composition as m57
from marketplace.runtime.inbound_http import BoundedInboundHttpApplicationAdapter
from marketplace.runtime.inbound_http_response_preparer_factory import (
    BoundedInboundHttpResponsePreparerCompositionFactory,
)
from marketplace.runtime.inbound_http_single_session import (
    BoundedInboundHttpSingleSessionOrchestrator,
)
from marketplace.runtime.inbound_http_single_session_composition import (
    BoundedInboundHttpSingleSessionCompositionRoot,
    InboundHttpSingleSessionCompositionError,
)
from test_inbound_http_response_preparer_factory import _Clock, _wire_adapter

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/marketplace/runtime/inbound_http_single_session_composition.py"
PORT = 18080


class _Constructor:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, object]] = []

    def __call__(self, family, kind, protocol):
        self.calls.append((family, kind, protocol))
        raise AssertionError("M57 composition MUST NOT invoke constructor")


class InboundHttpSingleSessionCompositionTests(unittest.TestCase):
    def test_public_surface_is_exact_and_minimal(self):
        constructor = inspect.signature(
            BoundedInboundHttpSingleSessionCompositionRoot.__init__
        )
        self.assertEqual(
            tuple(constructor.parameters),
            ("self", "wire_adapter", "clock", "port"),
        )
        call = inspect.signature(BoundedInboundHttpSingleSessionCompositionRoot.__call__)
        self.assertEqual(tuple(call.parameters), ("self", "constructor"))

    def test_one_call_builds_exact_m55_without_invoking_constructor_or_clock(self):
        wire = _wire_adapter()
        clock = _Clock()
        constructor = _Constructor()
        root = BoundedInboundHttpSingleSessionCompositionRoot(
            wire_adapter=wire,
            clock=clock,
            port=PORT,
        )

        orchestrator = root(constructor)

        self.assertIs(type(orchestrator), BoundedInboundHttpSingleSessionOrchestrator)
        preparer_factory = getattr(orchestrator, "_preparer_factory")
        self.assertIs(
            type(preparer_factory),
            BoundedInboundHttpResponsePreparerCompositionFactory,
        )
        self.assertIs(getattr(preparer_factory, "_wire_adapter"), wire)
        self.assertIs(getattr(preparer_factory, "_clock"), clock)
        self.assertIs(getattr(orchestrator, "_preparer_factory"), preparer_factory)
        self.assertIs(getattr(orchestrator, "_clock"), clock)
        listener = getattr(orchestrator, "_listener_construction")
        socket_factory = getattr(listener, "_factory")
        self.assertIs(getattr(socket_factory, "_constructor"), constructor)
        self.assertEqual(getattr(listener, "_port"), PORT)
        self.assertEqual(constructor.calls, [])
        self.assertEqual(clock.calls, 0)
        self.assertTrue(getattr(root, "_used"))
        for name in ("_wire_adapter", "_clock", "_binding_witness"):
            self.assertIsNone(getattr(root, name))

    def test_second_call_is_terminal(self):
        constructor = _Constructor()
        root = BoundedInboundHttpSingleSessionCompositionRoot(
            wire_adapter=_wire_adapter(),
            clock=_Clock(),
            port=PORT,
        )
        root(constructor)

        with self.assertRaises(InboundHttpSingleSessionCompositionError) as caught:
            root(constructor)

        self.assertEqual(caught.exception.code, "SESSION_COMPOSITION_EXHAUSTED")
        self.assertEqual(constructor.calls, [])

    def test_invalid_configuration_fails_before_lower_construction(self):
        with self.assertRaises(TypeError):
            BoundedInboundHttpSingleSessionCompositionRoot(
                wire_adapter=object(),  # type: ignore[arg-type]
                clock=_Clock(),
                port=PORT,
            )
        with self.assertRaises(InboundHttpSingleSessionCompositionError) as caught:
            BoundedInboundHttpSingleSessionCompositionRoot(
                wire_adapter=_wire_adapter(),
                clock=None,  # type: ignore[arg-type]
                port=PORT,
            )
        self.assertEqual(caught.exception.code, "SESSION_COMPOSITION_CLOCK_INVALID")

        for port in (True, 0, 80, 65536):
            with self.subTest(port=port):
                with self.assertRaises(InboundHttpSingleSessionCompositionError) as caught:
                    BoundedInboundHttpSingleSessionCompositionRoot(
                        wire_adapter=_wire_adapter(),
                        clock=_Clock(),
                        port=port,  # type: ignore[arg-type]
                    )
                self.assertEqual(caught.exception.code, "SESSION_COMPOSITION_PORT_INVALID")

    def test_noncallable_constructor_is_terminal_and_builds_nothing(self):
        root = BoundedInboundHttpSingleSessionCompositionRoot(
            wire_adapter=_wire_adapter(),
            clock=_Clock(),
            port=PORT,
        )
        with self.assertRaises(InboundHttpSingleSessionCompositionError) as caught:
            root(object())  # type: ignore[arg-type]
        self.assertEqual(caught.exception.code, "SESSION_COMPOSITION_CONSTRUCTOR_INVALID")
        self.assertTrue(getattr(root, "_used"))
        self.assertIsNone(getattr(root, "_wire_adapter"))
        self.assertIsNone(getattr(root, "_clock"))

    def test_m56_class_substitution_is_blocked_before_execution(self):
        root = BoundedInboundHttpSingleSessionCompositionRoot(
            wire_adapter=_wire_adapter(),
            clock=_Clock(),
            port=PORT,
        )
        hostile_calls = []

        class HostileM56:
            def __init__(self, *args, **kwargs):
                hostile_calls.append((args, kwargs))
                raise AssertionError("hostile M56 MUST NOT execute")

        with patch.object(m57, "BoundedInboundHttpResponsePreparerCompositionFactory", HostileM56):
            with self.assertRaises(InboundHttpSingleSessionCompositionError) as caught:
                root(_Constructor())

        self.assertEqual(caught.exception.code, "SESSION_COMPOSITION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])

    def test_private_validator_poisoning_never_executes(self):
        root = BoundedInboundHttpSingleSessionCompositionRoot(
            wire_adapter=_wire_adapter(), clock=_Clock(), port=PORT
        )
        hostile_calls = []

        def hostile_validate(_self):
            hostile_calls.append(True)
            raise AssertionError("hostile M57 validator MUST NOT execute")

        object.__setattr__(root, "_validate_bindings_function", hostile_validate)
        with self.assertRaises(InboundHttpSingleSessionCompositionError) as caught:
            root(_Constructor())

        self.assertEqual(caught.exception.code, "SESSION_COMPOSITION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])

    def test_m34_handle_substitution_is_blocked_before_m56_construction(self):
        root = BoundedInboundHttpSingleSessionCompositionRoot(
            wire_adapter=_wire_adapter(), clock=_Clock(), port=PORT
        )
        hostile_calls = []

        def hostile_handle(_self):
            hostile_calls.append(True)
            raise AssertionError("hostile M34 handle MUST NOT execute")

        with patch.object(BoundedInboundHttpApplicationAdapter, "handle", property(hostile_handle)):
            with self.assertRaises(InboundHttpSingleSessionCompositionError) as caught:
                root(_Constructor())

        self.assertEqual(caught.exception.code, "SESSION_COMPOSITION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])

    def test_m55_class_substitution_is_blocked_before_execution(self):
        root = BoundedInboundHttpSingleSessionCompositionRoot(
            wire_adapter=_wire_adapter(),
            clock=_Clock(),
            port=PORT,
        )
        hostile_calls = []

        class HostileM55:
            def __init__(self, *args, **kwargs):
                hostile_calls.append((args, kwargs))
                raise AssertionError("hostile M55 MUST NOT execute")

        with patch.object(m57, "BoundedInboundHttpSingleSessionOrchestrator", HostileM55):
            with self.assertRaises(InboundHttpSingleSessionCompositionError) as caught:
                root(_Constructor())

        self.assertEqual(caught.exception.code, "SESSION_COMPOSITION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])


class InboundHttpSingleSessionCompositionSourceTests(unittest.TestCase):
    def test_source_has_no_external_io_background_retry_or_loop_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
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
        for node in ast.walk(tree):
            self.assertNotIsInstance(
                node,
                (ast.For, ast.AsyncFor, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp),
            )
