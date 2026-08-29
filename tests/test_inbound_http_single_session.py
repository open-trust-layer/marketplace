from __future__ import annotations

import ast
import inspect
import pathlib
import unittest
from socket import AF_INET, IPPROTO_TCP, SOCK_STREAM

from marketplace.runtime.inbound_http_accept import BoundedInboundHttpSingleAccept
from marketplace.runtime.inbound_http_connection import (
    BoundedInboundHttpSingleConnectionIO,
    CompletedInboundHttpSingleConnectionTransport,
)
from marketplace.runtime.inbound_http_response_prepare import BoundedInboundHttpResponsePreparer
from marketplace.runtime.inbound_http_single_session import (
    BoundedInboundHttpSingleSessionOrchestrator,
    InboundHttpResponsePreparerFactory,
    InboundHttpSingleSessionOrchestratorError,
)
from test_inbound_http_connection import _Connection, _contains_raw_bytes
from test_inbound_http_response_prepare import _build

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/marketplace/runtime/inbound_http_single_session.py"
PORT = 18080


class _Listener:
    def __init__(self, connection: _Connection):
        self.connection = connection
        self.bind_calls = []
        self.listen_calls = []
        self.accept_calls = 0
        self.close_calls = 0
        self.bind_exception = None
        self.accept_exception = None
        self.mutate_on_bind = None

    def bind(self, address):
        self.bind_calls.append(address)
        if self.mutate_on_bind is not None:
            self.mutate_on_bind()
        if self.bind_exception is not None:
            raise self.bind_exception

    def listen(self, backlog):
        self.listen_calls.append(backlog)

    def accept(self):
        self.accept_calls += 1
        if self.accept_exception is not None:
            raise self.accept_exception
        return self.connection

    def close(self):
        self.close_calls += 1


class _Constructor:
    def __init__(self, listener: _Listener):
        self.listener = listener
        self.calls = []
        self.exception = None

    def __call__(self, family, kind, protocol):
        self.calls.append((family, kind, protocol))
        if self.exception is not None:
            raise self.exception
        return self.listener


class _PreparerFactory:
    def __init__(self, connection: _Connection):
        self.connection = connection
        self.calls = 0
        self.exception = None
        self.return_value = None
        self.use_wrong_reader = False
        self.harness = None
        self.session = None
        self.raw = None

    def __call__(self, reader):
        self.calls += 1
        if self.exception is not None:
            raise self.exception
        if self.return_value is not None:
            return self.return_value
        selected_reader = (lambda _max_bytes: None) if self.use_wrong_reader else reader
        harness, _, _, session, driver, raw = _build(selected_reader)
        self.connection.input_bytes = raw
        self.harness = harness
        self.session = session
        self.raw = raw
        return BoundedInboundHttpResponsePreparer(read_driver=driver)


def _build_orchestrator():
    connection = _Connection()
    listener = _Listener(connection)
    constructor = _Constructor(listener)
    preparer_factory = _PreparerFactory(connection)
    orchestrator = BoundedInboundHttpSingleSessionOrchestrator(
        constructor=constructor,
        response_preparer_factory=preparer_factory,
        clock=lambda: 0.0,
        port=PORT,
    )
    return orchestrator, constructor, listener, connection, preparer_factory


class InboundHttpSingleSessionTests(unittest.TestCase):
    def test_public_constructor_surface_is_exact_and_bounded(self):
        params = inspect.signature(BoundedInboundHttpSingleSessionOrchestrator).parameters
        self.assertEqual(
            tuple(params),
            ("constructor", "response_preparer_factory", "clock", "port"),
        )
        self.assertTrue(inspect.isclass(InboundHttpResponsePreparerFactory))

    def test_one_session_composes_exact_chain_and_returns_exact_m51_result(self):
        orchestrator, constructor, listener, connection, factory = _build_orchestrator()

        result = orchestrator.run_once()

        self.assertIs(type(result), CompletedInboundHttpSingleConnectionTransport)
        self.assertEqual(constructor.calls, [(AF_INET, SOCK_STREAM, IPPROTO_TCP)])
        self.assertEqual(listener.bind_calls, [("127.0.0.1", PORT)])
        self.assertEqual(listener.listen_calls, [1])
        self.assertEqual(listener.accept_calls, 1)
        self.assertEqual(listener.close_calls, 1)
        self.assertEqual(connection.close_calls, 1)
        self.assertEqual(factory.calls, 1)
        self.assertEqual(len(factory.harness.calls), 1)
        self.assertEqual(result.request_bytes, len(factory.raw))
        self.assertEqual(sum(map(len, connection.sent_chunks)), result.response_bytes)
        self.assertTrue(result.connection_closed)
        self.assertFalse(_contains_raw_bytes(result))
        for name in (
            "network_origin_proven",
            "tls_terminated",
            "transmitted",
            "request_authenticated",
            "peer_identity_proven",
            "establishes_marketplace_truth",
            "establishes_trust",
            "establishes_authorization",
            "authorizes_protected_side_effects",
        ):
            self.assertIs(getattr(result, name), False)
        self.assertTrue(orchestrator.used)
        self.assertTrue(orchestrator.closed)

    def test_second_run_is_terminal_and_never_reinvokes_lower_chain(self):
        orchestrator, constructor, listener, connection, factory = _build_orchestrator()
        orchestrator.run_once()

        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            orchestrator.run_once()
        self.assertEqual(caught.exception.code, "SESSION_ORCHESTRATOR_USED")
        self.assertEqual(len(constructor.calls), 1)
        self.assertEqual(listener.accept_calls, 1)
        self.assertEqual(connection.close_calls, 1)
        self.assertEqual(factory.calls, 1)

    def test_invalid_port_fails_before_constructor_invocation(self):
        connection = _Connection()
        listener = _Listener(connection)
        constructor = _Constructor(listener)
        factory = _PreparerFactory(connection)
        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            BoundedInboundHttpSingleSessionOrchestrator(
                constructor=constructor,
                response_preparer_factory=factory,
                clock=lambda: 0.0,
                port=80,
            )
        self.assertEqual(caught.exception.code, "SESSION_CONFIGURATION_REJECTED")
        self.assertEqual(caught.exception.lower_code, "LISTENER_PORT_INVALID")
        self.assertEqual(constructor.calls, [])

    def test_noncallable_preparer_factory_is_rejected_without_constructor_use(self):
        connection = _Connection()
        listener = _Listener(connection)
        constructor = _Constructor(listener)
        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            BoundedInboundHttpSingleSessionOrchestrator(
                constructor=constructor,
                response_preparer_factory=object(),
                clock=lambda: 0.0,
                port=PORT,
            )
        self.assertEqual(caught.exception.code, "SESSION_PREPARER_FACTORY_INVALID")
        self.assertEqual(constructor.calls, [])

    def test_preparer_factory_exception_is_redacted_and_connection_is_closed(self):
        orchestrator, _, listener, connection, factory = _build_orchestrator()
        factory.exception = RuntimeError("SECRET-PREPARER-TEXT")

        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            orchestrator.run_once()
        self.assertEqual(caught.exception.code, "SESSION_PREPARER_FACTORY_FAILED")
        self.assertNotIn("SECRET-PREPARER-TEXT", str(caught.exception))
        self.assertEqual(factory.calls, 1)
        self.assertEqual(listener.close_calls, 1)
        self.assertEqual(connection.close_calls, 1)

    def test_non_exact_preparer_result_is_rejected_and_connection_is_closed(self):
        orchestrator, _, listener, connection, factory = _build_orchestrator()
        factory.return_value = object()

        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            orchestrator.run_once()
        self.assertEqual(caught.exception.code, "SESSION_PREPARER_INVALID")
        self.assertEqual(listener.close_calls, 1)
        self.assertEqual(connection.close_calls, 1)

    def test_wrong_reader_preparer_is_rejected_and_all_owned_state_is_closed(self):
        orchestrator, _, listener, connection, factory = _build_orchestrator()
        factory.use_wrong_reader = True

        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            orchestrator.run_once()
        self.assertEqual(caught.exception.code, "SESSION_TRANSPORT_CONSTRUCTION_FAILED")
        self.assertEqual(listener.close_calls, 1)
        self.assertEqual(connection.close_calls, 1)
        self.assertTrue(factory.session.closed)

    def test_constructor_failure_preserves_only_stable_lower_code(self):
        orchestrator, constructor, listener, connection, factory = _build_orchestrator()
        constructor.exception = RuntimeError("SECRET-CONSTRUCTOR-TEXT")

        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            orchestrator.run_once()
        self.assertEqual(caught.exception.code, "SESSION_LISTENER_REJECTED")
        self.assertEqual(caught.exception.lower_code, "LISTENER_FACTORY_FAILED")
        self.assertNotIn("SECRET-CONSTRUCTOR-TEXT", str(caught.exception))
        self.assertEqual(listener.bind_calls, [])
        self.assertEqual(listener.listen_calls, [])
        self.assertEqual(listener.accept_calls, 0)
        self.assertEqual(connection.close_calls, 0)
        self.assertEqual(factory.calls, 0)

    def test_bind_failure_is_redacted_and_listener_is_closed_once(self):
        orchestrator, _, listener, connection, factory = _build_orchestrator()
        listener.bind_exception = RuntimeError("SECRET-BIND-TEXT")

        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            orchestrator.run_once()
        self.assertEqual(caught.exception.code, "SESSION_LISTENER_REJECTED")
        self.assertEqual(caught.exception.lower_code, "LISTENER_BIND_FAILED")
        self.assertNotIn("SECRET-BIND-TEXT", str(caught.exception))
        self.assertEqual(listener.close_calls, 1)
        self.assertEqual(listener.listen_calls, [])
        self.assertEqual(listener.accept_calls, 0)
        self.assertEqual(connection.close_calls, 0)
        self.assertEqual(factory.calls, 0)

    def test_accept_failure_is_redacted_and_listener_is_closed_once(self):
        orchestrator, _, listener, connection, factory = _build_orchestrator()
        listener.accept_exception = RuntimeError("SECRET-ACCEPT-TEXT")

        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            orchestrator.run_once()
        self.assertEqual(caught.exception.code, "SESSION_ACCEPT_REJECTED")
        self.assertEqual(caught.exception.lower_code, "ACCEPT_FAILED")
        self.assertNotIn("SECRET-ACCEPT-TEXT", str(caught.exception))
        self.assertEqual(listener.close_calls, 1)
        self.assertEqual(listener.accept_calls, 1)
        self.assertEqual(connection.close_calls, 0)
        self.assertEqual(factory.calls, 0)

    def test_close_before_run_releases_authority_without_constructor_invocation(self):
        orchestrator, constructor, listener, connection, factory = _build_orchestrator()

        orchestrator.close()
        orchestrator.close()

        self.assertTrue(orchestrator.closed)
        self.assertTrue(orchestrator.used)
        self.assertEqual(constructor.calls, [])
        self.assertEqual(listener.bind_calls, [])
        self.assertEqual(listener.accept_calls, 0)
        self.assertEqual(connection.close_calls, 0)
        self.assertEqual(factory.calls, 0)
        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            orchestrator.run_once()
        self.assertEqual(caught.exception.code, "SESSION_ORCHESTRATOR_USED")

    def test_transaction_rejection_is_stable_and_connection_remains_closed(self):
        orchestrator, _, listener, connection, factory = _build_orchestrator()
        connection.recv_override = b""

        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            orchestrator.run_once()
        self.assertEqual(caught.exception.code, "SESSION_TRANSACTION_REJECTED")
        self.assertEqual(caught.exception.lower_code, "CONNECTION_TRANSACTION_REJECTED")
        self.assertEqual(listener.close_calls, 1)
        self.assertEqual(connection.close_calls, 1)
        self.assertEqual(factory.calls, 1)

    def test_m52_method_graph_mutation_during_bind_closes_without_accept(self):
        orchestrator, constructor, listener, connection, factory = _build_orchestrator()
        original = BoundedInboundHttpSingleAccept.accept_once
        hostile_calls = []

        def hostile(_self):
            hostile_calls.append(True)
            raise AssertionError("substituted M52 accept MUST NOT run")

        listener.mutate_on_bind = lambda: setattr(
            BoundedInboundHttpSingleAccept,
            "accept_once",
            hostile,
        )
        try:
            with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
                orchestrator.run_once()
        finally:
            BoundedInboundHttpSingleAccept.accept_once = original

        self.assertEqual(caught.exception.code, "SESSION_LISTENER_REJECTED")
        self.assertEqual(caught.exception.lower_code, "LISTENER_CONSTRUCTION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])
        self.assertEqual(len(constructor.calls), 1)
        self.assertEqual(listener.accept_calls, 0)
        self.assertEqual(listener.close_calls, 1)
        self.assertEqual(connection.close_calls, 0)
        self.assertEqual(factory.calls, 0)

    def test_m51_io_graph_mutation_during_bind_closes_before_accept(self):
        orchestrator, _, listener, connection, factory = _build_orchestrator()
        original = BoundedInboundHttpSingleConnectionIO._read_once

        def hostile(_self, _max_bytes):
            raise AssertionError("substituted M51 read MUST NOT run")

        listener.mutate_on_bind = lambda: setattr(
            BoundedInboundHttpSingleConnectionIO,
            "_read_once",
            hostile,
        )
        try:
            with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
                orchestrator.run_once()
        finally:
            BoundedInboundHttpSingleConnectionIO._read_once = original

        self.assertEqual(caught.exception.code, "SESSION_LOWER_BINDING_DRIFT")
        self.assertEqual(listener.accept_calls, 0)
        self.assertEqual(listener.close_calls, 1)
        self.assertEqual(connection.close_calls, 0)
        self.assertEqual(factory.calls, 0)

    def test_private_preparer_call_rebinding_during_accept_never_executes(self):
        orchestrator, _, listener, connection, factory = _build_orchestrator()
        original_accept = listener.accept
        hostile_calls = []

        def hostile(*_args):
            hostile_calls.append(True)
            raise AssertionError("private preparer substitution MUST NOT run")

        def mutating_accept():
            orchestrator._preparer_factory_call = hostile
            return original_accept()

        listener.accept = mutating_accept
        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            orchestrator.run_once()

        self.assertEqual(caught.exception.code, "SESSION_ORCHESTRATOR_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])
        self.assertEqual(listener.accept_calls, 1)
        self.assertEqual(listener.close_calls, 1)
        self.assertEqual(connection.close_calls, 1)
        self.assertEqual(factory.calls, 0)

    def test_transport_graph_mutation_during_preparer_factory_is_cleaned(self):
        from marketplace.runtime.inbound_http_connection import (
            BoundedInboundHttpSingleConnectionTransport,
        )

        orchestrator, _, listener, connection, factory = _build_orchestrator()
        original_call = factory.__class__.__call__
        original_run = BoundedInboundHttpSingleConnectionTransport.run
        hostile_calls = []
        original_build = globals()["_build"]

        def hostile_run(_self):
            hostile_calls.append(True)
            raise AssertionError("substituted M51 run MUST NOT execute")

        def mutating_build(*args, **kwargs):
            built = original_build(*args, **kwargs)
            BoundedInboundHttpSingleConnectionTransport.run = hostile_run
            return built

        globals()["_build"] = mutating_build
        try:
            with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
                orchestrator.run_once()
        finally:
            globals()["_build"] = original_build
            BoundedInboundHttpSingleConnectionTransport.run = original_run

        self.assertEqual(caught.exception.code, "SESSION_LOWER_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])
        self.assertEqual(listener.close_calls, 1)
        self.assertEqual(connection.close_calls, 1)
        self.assertTrue(factory.session.closed)


class InboundHttpSingleSessionSourceTests(unittest.TestCase):
    def test_source_has_no_direct_network_background_or_loop_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        blocked_imports = {
            "socket", "ssl", "asyncio", "threading", "multiprocessing",
            "subprocess", "selectors", "select", "concurrent", "logging",
        }
        direct_calls = {"bind", "listen", "accept", "recv", "send", "connect"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(
                    all(alias.name.split(".")[0] not in blocked_imports for alias in node.names)
                )
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], blocked_imports)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertNotIn(node.func.attr, direct_calls)

        run_node = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "run_once"
        )
        self.assertFalse(
            any(isinstance(node, (ast.For, ast.AsyncFor, ast.While)) for node in ast.walk(run_node))
        )

    def test_public_run_and_result_do_not_add_transport_or_authority_surface(self):
        signature = inspect.signature(BoundedInboundHttpSingleSessionOrchestrator.run_once)
        self.assertEqual(tuple(signature.parameters), ("self",))
        self.assertEqual(
            signature.return_annotation,
            "CompletedInboundHttpSingleConnectionTransport",
        )


class InboundHttpSingleSessionBindingWitnessTests(unittest.TestCase):
    def test_private_factory_rebinding_never_invokes_caller_equality(self):
        class ExplosiveFactory(_PreparerFactory):
            def __eq__(self, _other):
                raise RuntimeError("TOP-SECRET-M55-EQUALITY")

        connection = _Connection()
        listener = _Listener(connection)
        constructor = _Constructor(listener)
        factory = ExplosiveFactory(connection)
        orchestrator = BoundedInboundHttpSingleSessionOrchestrator(
            constructor=constructor,
            response_preparer_factory=factory,
            clock=lambda: 0.0,
            port=PORT,
        )
        orchestrator._preparer_factory = ExplosiveFactory(connection)

        with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
            orchestrator.run_once()

        self.assertEqual(caught.exception.code, "SESSION_ORCHESTRATOR_BINDING_DRIFT")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(constructor.calls, [])
        self.assertEqual(listener.bind_calls, [])


class InboundHttpSingleSessionNoLoopTests(unittest.TestCase):
    def test_m55_source_contains_no_loop_or_comprehension(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        loop_nodes = (
            ast.For,
            ast.AsyncFor,
            ast.While,
            ast.ListComp,
            ast.SetComp,
            ast.DictComp,
            ast.GeneratorExp,
        )
        self.assertFalse(any(isinstance(node, loop_nodes) for node in ast.walk(tree)))


class InboundHttpSingleSessionTransportConstructionGraphTests(unittest.TestCase):
    def test_transport_new_mutation_during_preparer_factory_never_executes(self):
        from marketplace.runtime.inbound_http_connection import (
            BoundedInboundHttpSingleConnectionTransport,
        )

        orchestrator, _, _, connection, _ = _build_orchestrator()
        original_new = BoundedInboundHttpSingleConnectionTransport.__new__
        original_build = globals()["_build"]
        hostile_calls = []

        def hostile_new(cls, *args, **kwargs):
            hostile_calls.append(True)
            raise AssertionError("substituted M51 transport __new__ MUST NOT run")

        def mutating_build(*args, **kwargs):
            built = original_build(*args, **kwargs)
            BoundedInboundHttpSingleConnectionTransport.__new__ = staticmethod(hostile_new)
            return built
        globals()["_build"] = mutating_build
        try:
            with self.assertRaises(InboundHttpSingleSessionOrchestratorError) as caught:
                orchestrator.run_once()
        finally:
            globals()["_build"] = original_build
            BoundedInboundHttpSingleConnectionTransport.__new__ = original_new

        self.assertEqual(caught.exception.code, "SESSION_LOWER_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])
        self.assertEqual(connection.close_calls, 1)
