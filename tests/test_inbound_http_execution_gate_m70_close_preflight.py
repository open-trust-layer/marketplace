from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http_execution_gate import (
    BoundedInboundHttpLoopbackExecutionGate,
)
from test_inbound_http_end_to_end_composition import _root


class InboundHttpExecutionGateM70ClosePreflightTests(unittest.TestCase):
    def test_close_never_dereferences_unvalidated_retained_gate_type(self):
        root = _root()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        touched: list[str] = []

        class HostileGateType:
            def __getattribute__(self, name: str) -> object:
                if name == "__dict__":
                    touched.append("__dict__")
                    raise AssertionError(
                        "unvalidated retained gate type MUST NOT be dereferenced"
                    )
                return object.__getattribute__(self, name)

        object.__setattr__(gate, "_gate_type", HostileGateType())
        gate.close()

        self.assertEqual(touched, [])
        self.assertFalse(getattr(root, "_used"))
        self.assertTrue(gate.used)
        self.assertTrue(gate.closed)


if __name__ == "__main__":
    unittest.main()
