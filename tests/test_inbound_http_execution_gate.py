from __future__ import annotations
import ast
import inspect
import pathlib
import unittest
from unittest.mock import patch
from olp.encoding.record_identity import record_identity_text
import marketplace.runtime.inbound_http_execution_gate as m62
from marketplace.runtime.inbound_http_connection import (
    CompletedInboundHttpSingleConnectionTransport,
)
from marketplace.runtime.inbound_http_execution_gate import (
    LOOPBACK_EXECUTION_OPT_IN,
    BoundedInboundHttpLoopbackExecutionGate,
    InboundHttpLoopbackExecutionGateError,
    InboundHttpLoopbackReadiness,
)
from marketplace.runtime.inbound_http_single_session import (
    BoundedInboundHttpSingleSessionOrchestrator,
)
from test_inbound_http_connection import _Connection
from test_inbound_http_end_to_end_composition import AUTHORITY, _root
from test_inbound_http_hardening import FakeSource, record, record_responder
from test_inbound_http_single_session import _Constructor, _Listener
ROOT = pathlib.Path(__file__).resolve().parents[1]
class _OptInSubclass(str):
    pass
SOURCE = ROOT / "src/marketplace/runtime/inbound_http_execution_gate.py"
def _execution_fixture():
    served = record()
    source = FakeSource(served)
    root = _root(records=record_responder(source))
    connection = _Connection()
    identity = record_identity_text(served)
    connection.input_bytes = (
        f"GET /v1/records/{identity} HTTP/1.1\r\n"
        f"Host: {AUTHORITY}\r\n"
        "Accept: application/json\r\n"
        "Connection: close\r\n\r\n"
    ).encode("ascii")
    listener = _Listener(connection)
    constructor = _Constructor(listener)
    return root, source, connection, listener, constructor
class InboundHttpLoopbackExecutionGateTests(unittest.TestCase):
    def test_public_surface_is_exact_and_minimal(self):
        constructor = inspect.signature(BoundedInboundHttpLoopbackExecutionGate.__init__)
        self.assertEqual(tuple(constructor.parameters), ("self", "source_composition_root"))
        dry_run = inspect.signature(BoundedInboundHttpLoopbackExecutionGate.dry_run)
        self.assertEqual(tuple(dry_run.parameters), ("self",))
        execute = inspect.signature(BoundedInboundHttpLoopbackExecutionGate.execute_once)
        self.assertEqual(tuple(execute.parameters), ("self", "opt_in", "constructor"))
        self.assertEqual(
            LOOPBACK_EXECUTION_OPT_IN,
            "EXECUTE_ONE_LOOPBACK_NETWORK_SESSION",
        )
    def test_dry_run_composes_exact_graph_without_network_or_run_once(self):
        root = _root()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        readiness = gate.dry_run()
        self.assertIs(type(readiness), InboundHttpLoopbackReadiness)
        self.assertTrue(readiness.composed)
        self.assertFalse(readiness.network_invoked)
        self.assertFalse(readiness.run_invoked)
        self.assertFalse(readiness.external_authorization_established)
        self.assertFalse(readiness.deployment_authorized)
        self.assertTrue(gate.used)
        self.assertTrue(gate.closed)
        self.assertTrue(getattr(root, "_used"))
    def test_missing_or_malformed_opt_in_fails_before_composition(self):
        for value in (None, "", "execute", _OptInSubclass(LOOPBACK_EXECUTION_OPT_IN)):
            with self.subTest(value=value):
                root = _root()
                gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
                with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
                    gate.execute_once(opt_in=value, constructor=lambda *_: None)  # type: ignore[arg-type]
                self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_OPT_IN_REQUIRED")
                self.assertFalse(getattr(root, "_used"))
    def test_noncallable_constructor_fails_before_composition(self):
        root = _root()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            gate.execute_once(opt_in=LOOPBACK_EXECUTION_OPT_IN, constructor=object())
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_CONSTRUCTOR_INVALID")
        self.assertFalse(getattr(root, "_used"))
    def test_execute_once_runs_exact_m59_m55_chain_once_with_injected_double(self):
        root, source, connection, listener, constructor = _execution_fixture()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        result = gate.execute_once(
            opt_in=LOOPBACK_EXECUTION_OPT_IN,
            constructor=constructor,
        )
        self.assertIs(type(result), CompletedInboundHttpSingleConnectionTransport)
        self.assertEqual(len(constructor.calls), 1)
        self.assertEqual(listener.bind_calls, [("127.0.0.1", 18080)])
        self.assertEqual(listener.listen_calls, [1])
        self.assertEqual(listener.accept_calls, 1)
        self.assertEqual(listener.close_calls, 1)
        self.assertEqual(connection.close_calls, 1)
        self.assertEqual(len(source.calls), 1)
        self.assertFalse(result.network_origin_proven)
        self.assertFalse(result.tls_terminated)
        self.assertFalse(result.request_authenticated)
        self.assertFalse(result.peer_identity_proven)
        self.assertFalse(result.establishes_authorization)
        self.assertTrue(gate.used)
        self.assertTrue(gate.closed)
    def test_second_terminal_call_never_reinvokes_constructor(self):
        root, _, _, _, constructor = _execution_fixture()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        gate.execute_once(opt_in=LOOPBACK_EXECUTION_OPT_IN, constructor=constructor)
        calls = list(constructor.calls)
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            gate.execute_once(opt_in=LOOPBACK_EXECUTION_OPT_IN, constructor=constructor)
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_EXHAUSTED")
        self.assertEqual(constructor.calls, calls)
    def test_constructor_failure_is_redacted_and_never_retried(self):
        root = _root()
        calls = []
        def hostile_constructor(*args):
            calls.append(args)
            raise RuntimeError("SECRET-CONSTRUCTOR-TEXT")
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            gate.execute_once(
                opt_in=LOOPBACK_EXECUTION_OPT_IN,
                constructor=hostile_constructor,
            )
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_FAILED")
        self.assertNotIn("SECRET-CONSTRUCTOR-TEXT", str(caught.exception))
        self.assertEqual(len(calls), 1)
    def test_private_root_rebinding_is_blocked_before_hostile_execution(self):
        root = _root()
        hostile_root = _root()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        object.__setattr__(gate, "_source_root", hostile_root)
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            gate.dry_run()
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_BINDING_DRIFT")
        self.assertFalse(getattr(root, "_used"))
        self.assertFalse(getattr(hostile_root, "_used"))
    def test_private_run_binding_poisoning_is_blocked_before_constructor(self):
        root, _, _, _, constructor = _execution_fixture()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        hostile_calls = []
        def hostile_run(_orchestrator):
            hostile_calls.append(True)
            raise AssertionError("hostile run MUST NOT execute")
        object.__setattr__(gate, "_run_once_function", hostile_run)
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            gate.execute_once(opt_in=LOOPBACK_EXECUTION_OPT_IN, constructor=constructor)
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])
        self.assertEqual(constructor.calls, [])
        self.assertFalse(getattr(root, "_used"))
    def test_m55_public_run_substitution_is_blocked_before_constructor(self):
        root, _, _, _, constructor = _execution_fixture()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        hostile_calls = []
        def hostile_run(_orchestrator):
            hostile_calls.append(True)
            raise AssertionError("substituted M55 run MUST NOT execute")
        with patch.object(BoundedInboundHttpSingleSessionOrchestrator, "run_once", hostile_run):
            with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
                gate.execute_once(opt_in=LOOPBACK_EXECUTION_OPT_IN, constructor=constructor)
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])
        self.assertEqual(constructor.calls, [])
    def test_close_is_idempotent_and_never_composes_or_executes(self):
        root = _root()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        gate.close()
        gate.close()
        self.assertTrue(gate.closed)
        self.assertFalse(getattr(root, "_used"))
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            gate.dry_run()
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_EXHAUSTED")
class InboundHttpLoopbackExecutionGateSourceTests(unittest.TestCase):
    def test_source_has_no_direct_network_background_retry_or_loop_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        blocked_imports = {
            "socket", "ssl", "asyncio", "threading", "multiprocessing",
            "subprocess", "selectors", "select", "concurrent", "logging",
            "pathlib", "os", "sys", "time",
        }
        direct_calls = {
            "bind", "listen", "accept", "recv", "send", "sendall", "connect",
            "getaddrinfo", "create_connection",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(
                    all(alias.name.split(".")[0] not in blocked_imports for alias in node.names)
                )
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], blocked_imports)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertNotIn(node.func.attr, direct_calls)
            self.assertNotIsInstance(node, (ast.For, ast.While, ast.AsyncFor))
    def test_module_import_does_not_select_real_socket_constructor(self):
        self.assertFalse(hasattr(m62, "socket"))
        self.assertFalse(hasattr(m62, "ssl"))
if __name__ == "__main__":
    unittest.main()
