from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http_execution_gate import (
    BoundedInboundHttpLoopbackExecutionGate,
    InboundHttpLoopbackExecutionGateError,
)
from test_inbound_http_end_to_end_composition import _root


_LIFECYCLE_FIELDS = (
    "_source_root",
    "_source_root_type",
    "_opt_in_token",
    "_binding_witness",
)


class InboundHttpExecutionGateM65LifecycleTests(unittest.TestCase):
    def assert_terminal_state(self, gate) -> None:
        self.assertTrue(gate.used)
        self.assertTrue(gate.closed)
        for field in _LIFECYCLE_FIELDS:
            with self.subTest(field=field):
                self.assertIsNone(getattr(gate, field))

    def test_terminal_release_does_not_restore_capability_state(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        gate.close()

        self.assert_terminal_state(gate)

        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            gate.close()

        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_EXHAUSTED")
        self.assert_terminal_state(gate)

    def test_terminal_state_is_stable_after_repeated_invalid_use(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        gate.close()

        for _ in range(2):
            with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
                gate.dry_run()
            self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_EXHAUSTED")
            self.assert_terminal_state(gate)


if __name__ == "__main__":
    unittest.main()
