from __future__ import annotations

import unittest

import marketplace.runtime.inbound_http_execution_gate as m62
from marketplace.runtime.inbound_http_execution_gate import (
    LOOPBACK_EXECUTION_OPT_IN,
    BoundedInboundHttpLoopbackExecutionGate,
    InboundHttpLoopbackExecutionGateError,
)
from test_inbound_http_end_to_end_composition import _root


class _EqualityTrap:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __eq__(self, other: object) -> bool:
        self.calls.append("eq")
        raise AssertionError("hostile equality MUST NOT execute")

    def __ne__(self, other: object) -> bool:
        self.calls.append("ne")
        raise AssertionError("hostile inequality MUST NOT execute")


class InboundHttpExecutionGateM63HardeningTests(unittest.TestCase):
    def assert_binding_drift(self, callback) -> None:
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            callback()
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_BINDING_DRIFT")

    def test_module_opt_in_rebinding_cannot_change_accepted_token(self):
        root = _root()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        constructor_calls: list[tuple[object, ...]] = []

        def hostile_constructor(*args: object) -> object:
            constructor_calls.append(args)
            raise AssertionError("constructor MUST NOT execute")

        original = m62.LOOPBACK_EXECUTION_OPT_IN
        m62.LOOPBACK_EXECUTION_OPT_IN = "ATTACKER_TOKEN"
        try:
            self.assert_binding_drift(
                lambda: gate.execute_once(opt_in="ATTACKER_TOKEN", constructor=hostile_constructor)
            )
        finally:
            m62.LOOPBACK_EXECUTION_OPT_IN = original
        self.assertEqual(constructor_calls, [])

    def test_module_binding_marker_poisoning_never_executes_equality(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        trap = _EqualityTrap()
        original = m62._BINDING_MARKER
        m62._BINDING_MARKER = trap
        try:
            self.assert_binding_drift(gate.dry_run)
        finally:
            m62._BINDING_MARKER = original
        self.assertEqual(trap.calls, [])

    def test_module_graph_marker_poisoning_never_executes_equality(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        trap = _EqualityTrap()
        original = m62._GRAPH_MARKER
        m62._GRAPH_MARKER = trap
        try:
            self.assert_binding_drift(gate.dry_run)
        finally:
            m62._GRAPH_MARKER = original
        self.assertEqual(trap.calls, [])

    def test_module_gate_class_poisoning_fails_before_attribute_execution(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        touched: list[str] = []
        class PoisonedGateBinding:
            def __getattr__(self, name: str) -> object:
                touched.append(name)
                raise AssertionError("poisoned gate class binding MUST NOT execute")

        original = m62.BoundedInboundHttpLoopbackExecutionGate
        m62.BoundedInboundHttpLoopbackExecutionGate = PoisonedGateBinding()  # type: ignore[assignment]
        try:
            self.assert_binding_drift(gate.dry_run)
        finally:
            m62.BoundedInboundHttpLoopbackExecutionGate = original
        self.assertEqual(touched, [])

    def test_module_fail_helper_poisoning_never_executes(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        touched: list[str] = []
        original_fail = m62._fail
        original_marker = m62._BINDING_MARKER

        def hostile_fail(*args: object, **kwargs: object) -> None:
            touched.append("fail")
            raise AssertionError("poisoned fail helper MUST NOT execute")

        m62._fail = hostile_fail
        m62._BINDING_MARKER = "poisoned-marker"
        try:
            self.assert_binding_drift(gate.dry_run)
        finally:
            m62._fail = original_fail
            m62._BINDING_MARKER = original_marker
        self.assertEqual(touched, [])

    def test_module_readiness_type_poisoning_is_blocked_before_execution(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        touched: list[str] = []
        original = m62.InboundHttpLoopbackReadiness

        class PoisonedReadiness:
            def __init__(self, *args: object, **kwargs: object) -> None:
                touched.append("readiness")
                raise AssertionError("poisoned readiness type MUST NOT execute")

        m62.InboundHttpLoopbackReadiness = PoisonedReadiness  # type: ignore[assignment]
        try:
            self.assert_binding_drift(gate.dry_run)
        finally:
            m62.InboundHttpLoopbackReadiness = original
        self.assertEqual(touched, [])


    def test_gate_validator_descriptor_poisoning_never_executes(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        touched: list[str] = []

        class DescriptorTrap:
            def __get__(self, instance: object, owner: object) -> object:
                touched.append("descriptor")
                raise AssertionError("poisoned descriptor MUST NOT execute")

        gate_type = type(gate)
        original = gate_type.__dict__["_validate_bindings"]
        setattr(gate_type, "_validate_bindings", DescriptorTrap())
        try:
            self.assert_binding_drift(gate.dry_run)
        finally:
            setattr(gate_type, "_validate_bindings", original)
        self.assertEqual(touched, [])

    def test_downstream_class_descriptor_poisoning_never_executes(self):
        targets = (
            (m62.BoundedInboundHttpEndToEndSourceCompositionRoot, "__call__"),
            (m62.BoundedInboundHttpSingleSessionOrchestrator, "run_once"),
            (m62.BoundedInboundHttpSingleSessionOrchestrator, "close"),
        )
        for target_type, name in targets:
            with self.subTest(target=target_type.__name__, name=name):
                gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
                touched: list[str] = []

                class DescriptorTrap:
                    def __get__(self, instance: object, owner: object) -> object:
                        touched.append("descriptor")
                        raise AssertionError("poisoned downstream descriptor MUST NOT execute")

                original = target_type.__dict__[name]
                setattr(target_type, name, DescriptorTrap())
                try:
                    self.assert_binding_drift(gate.dry_run)
                finally:
                    setattr(target_type, name, original)
                self.assertEqual(touched, [])

if __name__ == "__main__":
    unittest.main()
