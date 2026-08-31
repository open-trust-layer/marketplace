from __future__ import annotations

import unittest

import marketplace.runtime.inbound_http_execution_gate as m62
from marketplace.runtime.inbound_http_execution_gate import (
    LOOPBACK_EXECUTION_OPT_IN,
    BoundedInboundHttpLoopbackExecutionGate,
    InboundHttpLoopbackExecutionGateError,
)
from test_inbound_http_end_to_end_composition import _root
from test_inbound_http_execution_gate import _execution_fixture


class InboundHttpExecutionGateM66BeginBindingTests(unittest.TestCase):
    def assert_binding_drift(self, callback) -> None:
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            callback()
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_BINDING_DRIFT")

    def test_pre_call_begin_substitution_is_blocked_before_dry_run_composition(self):
        root = _root()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        gate_type = type(gate)
        original = gate_type.__dict__["_begin_once"]
        touched: list[str] = []

        def hostile_begin(_gate) -> None:
            touched.append("begin")
            raise AssertionError("substituted begin MUST NOT execute")

        setattr(gate_type, "_begin_once", hostile_begin)
        try:
            self.assert_binding_drift(gate.dry_run)
        finally:
            setattr(gate_type, "_begin_once", original)
        self.assertEqual(touched, [])
        self.assertFalse(getattr(root, "_used"))

    def test_pre_call_begin_substitution_is_blocked_before_constructor(self):
        root, _, _, _, constructor = _execution_fixture()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        gate_type = type(gate)
        original = gate_type.__dict__["_begin_once"]
        touched: list[str] = []

        def hostile_begin(_gate) -> None:
            touched.append("begin")
            raise AssertionError("substituted begin MUST NOT execute")

        setattr(gate_type, "_begin_once", hostile_begin)
        try:
            self.assert_binding_drift(
                lambda: gate.execute_once(
                    opt_in=LOOPBACK_EXECUTION_OPT_IN,
                    constructor=constructor,
                )
            )
        finally:
            setattr(gate_type, "_begin_once", original)
        self.assertEqual(touched, [])
        self.assertEqual(constructor.calls, [])
        self.assertFalse(getattr(root, "_used"))

    def test_begin_descriptor_substitution_never_executes_descriptor(self):
        root = _root()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        gate_type = type(gate)
        original = gate_type.__dict__["_begin_once"]
        touched: list[str] = []

        class DescriptorTrap:
            def __get__(self, instance: object, owner: object) -> object:
                touched.append("descriptor")
                raise AssertionError("substituted begin descriptor MUST NOT execute")

        setattr(gate_type, "_begin_once", DescriptorTrap())
        try:
            self.assert_binding_drift(gate.dry_run)
        finally:
            setattr(gate_type, "_begin_once", original)
        self.assertEqual(touched, [])
        self.assertFalse(getattr(root, "_used"))

    def test_private_retained_begin_rebinding_never_executes(self):
        root = _root()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        touched: list[str] = []

        def hostile_begin(_gate) -> None:
            touched.append("begin")
            raise AssertionError("poisoned retained begin MUST NOT execute")

        object.__setattr__(gate, "_begin_once_function", hostile_begin)
        self.assert_binding_drift(gate.dry_run)
        self.assertEqual(touched, [])
        self.assertFalse(getattr(root, "_used"))

    def test_terminal_second_call_never_constructs_rebound_module_error_type(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        gate.close()
        touched: list[str] = []
        original = m62.InboundHttpLoopbackExecutionGateError

        class HostileError(RuntimeError):
            def __init__(self, *args: object, **kwargs: object) -> None:
                touched.append("error")
                raise AssertionError("rebound terminal error constructor MUST NOT execute")

        m62.InboundHttpLoopbackExecutionGateError = HostileError  # type: ignore[assignment]
        try:
            with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
                gate.dry_run()
        finally:
            m62.InboundHttpLoopbackExecutionGateError = original
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_EXHAUSTED")
        self.assertEqual(touched, [])


if __name__ == "__main__":
    unittest.main()
