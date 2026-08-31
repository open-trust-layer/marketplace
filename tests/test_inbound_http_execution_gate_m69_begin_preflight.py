from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http_execution_gate import (
    BoundedInboundHttpLoopbackExecutionGate,
    InboundHttpLoopbackExecutionGateError,
)


class InboundHttpExecutionGateM69BeginPreflightTests(unittest.TestCase):
    def test_reviewed_begin_never_dereferences_unvalidated_retained_gate_type(self):
        gate = object.__new__(BoundedInboundHttpLoopbackExecutionGate)
        object.__setattr__(gate, "_used", False)
        object.__setattr__(gate, "_closed", False)
        object.__setattr__(gate, "_validate_bindings_function", lambda _gate: None)
        touched: list[str] = []

        class HostileGateType:
            def __getattribute__(self, name: str) -> object:
                if name == "__dict__":
                    touched.append("__dict__")
                    raise AssertionError("unvalidated retained gate type MUST NOT be dereferenced")
                return object.__getattribute__(self, name)

        object.__setattr__(gate, "_gate_type", HostileGateType())
        reviewed_begin = BoundedInboundHttpLoopbackExecutionGate.__dict__["_begin_once"]
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            reviewed_begin(gate)

        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_BINDING_DRIFT")
        self.assertIsNone(caught.exception.lower_code)
        self.assertEqual(touched, [])
        self.assertFalse(gate._used)


if __name__ == "__main__":
    unittest.main()
