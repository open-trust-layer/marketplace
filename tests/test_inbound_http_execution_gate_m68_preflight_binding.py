from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http_execution_gate import (
    LOOPBACK_EXECUTION_OPT_IN,
    BoundedInboundHttpLoopbackExecutionGate,
    InboundHttpLoopbackExecutionGateError,
)
from test_inbound_http_end_to_end_composition import _root
from test_inbound_http_execution_gate import _execution_fixture


class InboundHttpExecutionGateM68PreflightBindingTests(unittest.TestCase):
    def assert_binding_drift(self, callback) -> None:
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            callback()
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_BINDING_DRIFT")
        self.assertIsNone(caught.exception.lower_code)

    def poison_validator_and_fail(self, gate, touched: list[str]) -> None:
        def hostile_validate(_gate) -> None:
            touched.append("validate")
            raise AssertionError("poisoned validator MUST NOT execute")

        def hostile_fail(*args: object, **kwargs: object) -> None:
            touched.append("fail")
            raise AssertionError("poisoned fail helper MUST NOT execute")

        object.__setattr__(gate, "_validate_bindings_function", hostile_validate)
        object.__setattr__(gate, "_fail_function", hostile_fail)

    def restore_validator_and_fail(self, gate, validate, fail) -> None:
        object.__setattr__(gate, "_validate_bindings_function", validate)
        object.__setattr__(gate, "_fail_function", fail)
        gate.close()

    def test_coherent_validator_and_fail_rebinding_never_executes_on_dry_run(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        original_validate = gate._validate_bindings_function
        original_fail = gate._fail_function
        touched: list[str] = []
        self.poison_validator_and_fail(gate, touched)
        try:
            self.assert_binding_drift(gate.dry_run)
        finally:
            self.restore_validator_and_fail(gate, original_validate, original_fail)
        self.assertEqual(touched, [])

    def test_coherent_validator_and_fail_rebinding_never_executes_on_execute_once(self):
        root, _, _, _, constructor = _execution_fixture()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        original_validate = gate._validate_bindings_function
        original_fail = gate._fail_function
        touched: list[str] = []
        self.poison_validator_and_fail(gate, touched)

        try:
            self.assert_binding_drift(
                lambda: gate.execute_once(
                    opt_in=LOOPBACK_EXECUTION_OPT_IN,
                    constructor=constructor,
                )
            )
        finally:
            self.restore_validator_and_fail(gate, original_validate, original_fail)
        self.assertEqual(touched, [])
        self.assertEqual(constructor.calls, [])
        self.assertFalse(getattr(root, "_used"))

    def assert_hostile_gate_type_is_not_dereferenced(self, callback, gate) -> None:
        touched: list[str] = []
        original_gate_type = gate._gate_type

        class HostileGateType:
            def __getattribute__(self, name: str) -> object:
                if name == "__dict__":
                    touched.append("__dict__")
                    raise AssertionError("unreviewed gate type MUST NOT be dereferenced")
                return object.__getattribute__(self, name)

        object.__setattr__(gate, "_gate_type", HostileGateType())
        try:
            self.assert_binding_drift(callback)

        finally:
            object.__setattr__(gate, "_gate_type", original_gate_type)
            gate.close()
        self.assertEqual(touched, [])

    def test_hostile_gate_type_is_not_dereferenced_on_dry_run(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        self.assert_hostile_gate_type_is_not_dereferenced(gate.dry_run, gate)

    def test_hostile_gate_type_is_not_dereferenced_on_execute_once(self):
        root, _, _, _, constructor = _execution_fixture()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        self.assert_hostile_gate_type_is_not_dereferenced(
            lambda: gate.execute_once(
                opt_in=LOOPBACK_EXECUTION_OPT_IN,
                constructor=constructor,
            ),
            gate,
        )
        self.assertEqual(constructor.calls, [])
        self.assertFalse(getattr(root, "_used"))


if __name__ == "__main__":
    unittest.main()
