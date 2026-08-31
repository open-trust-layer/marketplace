from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http_execution_gate import (
    LOOPBACK_EXECUTION_OPT_IN,
    BoundedInboundHttpLoopbackExecutionGate,
    InboundHttpLoopbackExecutionGateError,
)
from test_inbound_http_end_to_end_composition import _root
from test_inbound_http_execution_gate import _execution_fixture


class InboundHttpExecutionGateM65ReleaseBindingTests(unittest.TestCase):
    def assert_binding_drift(self, callback) -> None:
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            callback()
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_BINDING_DRIFT")

    def test_pre_call_release_substitution_is_blocked_before_dry_run_composition(self):
        root = _root()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        gate_type = type(gate)
        original = gate_type.__dict__["_release"]
        touched: list[str] = []

        def hostile_release(_gate) -> None:
            touched.append("release")
            raise AssertionError("substituted release MUST NOT execute")

        setattr(gate_type, "_release", hostile_release)
        try:
            self.assert_binding_drift(gate.dry_run)
        finally:
            setattr(gate_type, "_release", original)
        self.assertEqual(touched, [])
        self.assertFalse(getattr(root, "_used"))

    def test_pre_call_release_substitution_is_blocked_before_constructor(self):
        root, _, _, _, constructor = _execution_fixture()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        gate_type = type(gate)
        original = gate_type.__dict__["_release"]
        touched: list[str] = []

        def hostile_release(_gate) -> None:
            touched.append("release")
            raise AssertionError("substituted release MUST NOT execute")

        setattr(gate_type, "_release", hostile_release)
        try:
            self.assert_binding_drift(
                lambda: gate.execute_once(
                    opt_in=LOOPBACK_EXECUTION_OPT_IN,
                    constructor=constructor,
                )
            )
        finally:
            setattr(gate_type, "_release", original)
        self.assertEqual(touched, [])
        self.assertEqual(constructor.calls, [])
        self.assertFalse(getattr(root, "_used"))

    def test_constructor_release_substitution_is_detected_and_reviewed_cleanup_runs(self):
        root, _, _, _, constructor = _execution_fixture()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        gate_type = type(gate)
        original = gate_type.__dict__["_release"]
        touched: list[str] = []

        def hostile_release(_gate) -> None:
            touched.append("release")
            raise AssertionError("substituted release MUST NOT execute")

        def mutating_constructor(*args: object) -> object:
            setattr(gate_type, "_release", hostile_release)
            return constructor(*args)

        try:
            self.assert_binding_drift(
                lambda: gate.execute_once(
                    opt_in=LOOPBACK_EXECUTION_OPT_IN,
                    constructor=mutating_constructor,
                )
            )
        finally:
            setattr(gate_type, "_release", original)
        self.assertEqual(touched, [])
        self.assertTrue(gate.closed)

    def test_explicit_close_uses_reviewed_release_even_when_class_binding_drifted(self):
        root = _root()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        gate_type = type(gate)
        original = gate_type.__dict__["_release"]
        touched: list[str] = []

        def hostile_release(_gate) -> None:
            touched.append("release")
            raise AssertionError("substituted release MUST NOT execute")

        setattr(gate_type, "_release", hostile_release)
        try:
            gate.close()
        finally:
            setattr(gate_type, "_release", original)
        self.assertEqual(touched, [])
        self.assertFalse(getattr(root, "_used"))
        self.assertTrue(gate.used)
        self.assertTrue(gate.closed)


if __name__ == "__main__":
    unittest.main()
