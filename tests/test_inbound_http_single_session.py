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
