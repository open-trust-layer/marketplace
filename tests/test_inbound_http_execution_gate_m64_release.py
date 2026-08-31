from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http_execution_gate import (
    LOOPBACK_EXECUTION_OPT_IN,
    BoundedInboundHttpLoopbackExecutionGate,
    InboundHttpLoopbackExecutionGateError,
)
from test_inbound_http_end_to_end_composition import _root
from test_inbound_http_execution_gate import _execution_fixture


_RELEASED_AUTHORITY_FIELDS = (
    "_error_type",
    "_bounded_lower_code_function",
    "_fail_function",
)


class InboundHttpExecutionGateM64ReleaseTests(unittest.TestCase):
    def assert_terminal_authority_released(self, gate) -> None:
        self.assertTrue(gate.used)
        self.assertTrue(gate.closed)
        for name in _RELEASED_AUTHORITY_FIELDS:
            with self.subTest(name=name):
                self.assertIsNone(getattr(gate, name))

    def test_dry_run_releases_residual_reviewed_authority(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        gate.dry_run()
        self.assert_terminal_authority_released(gate)

    def test_successful_execution_releases_residual_reviewed_authority(self):
        root, _, _, _, constructor = _execution_fixture()
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
        gate.execute_once(opt_in=LOOPBACK_EXECUTION_OPT_IN, constructor=constructor)
        self.assert_terminal_authority_released(gate)

    def test_failed_execution_releases_residual_reviewed_authority(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())

        def failing_constructor(*_args):
            raise RuntimeError("redacted")

        with self.assertRaises(InboundHttpLoopbackExecutionGateError):
            gate.execute_once(
                opt_in=LOOPBACK_EXECUTION_OPT_IN,
                constructor=failing_constructor,
            )
        self.assert_terminal_authority_released(gate)

    def test_unused_explicit_close_releases_residual_reviewed_authority(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        gate.close()
        self.assert_terminal_authority_released(gate)

    def test_post_release_second_call_still_fails_as_exhausted(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        gate.close()
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            gate.dry_run()
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_EXHAUSTED")
        self.assert_terminal_authority_released(gate)


if __name__ == "__main__":
    unittest.main()
