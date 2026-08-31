import unittest

from marketplace.runtime.inbound_http_execution_gate import (
    BoundedInboundHttpLoopbackExecutionGate,
    InboundHttpLoopbackExecutionGateError,
)
from test_inbound_http_end_to_end_composition import _root


class InboundHttpExecutionGateM67TerminalArtifactTests(unittest.TestCase):
    def assert_stable_terminal_error(self, callback) -> None:
        with self.assertRaises(InboundHttpLoopbackExecutionGateError) as caught:
            callback()
        self.assertEqual(caught.exception.code, "LOOPBACK_EXECUTION_EXHAUSTED")
        self.assertIsNone(caught.exception.lower_code)

    def terminal_gate(self):
        gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=_root())
        gate.close()
        return gate

    def test_post_release_template_rebinding_cannot_change_dry_run_error_type(self):
        gate = self.terminal_gate()
        object.__setattr__(gate, "_terminal_error_template", ValueError("poisoned"))
        self.assert_stable_terminal_error(gate.dry_run)

    def test_post_release_template_rebinding_cannot_change_execute_error_type(self):
        gate = self.terminal_gate()
        object.__setattr__(gate, "_terminal_error_template", ValueError("poisoned"))
        self.assert_stable_terminal_error(
            lambda: gate.execute_once(opt_in=None, constructor=None)
        )

    def test_post_release_terminal_witness_rebinding_cannot_change_error_type(self):
        gate = self.terminal_gate()
        object.__setattr__(
            gate,
            "_terminal_error_witness",
            ("m67-terminal-error-artifact-v1", ValueError("poisoned")),
        )
        self.assert_stable_terminal_error(gate.dry_run)

    def test_post_release_terminal_type_identity_rebinding_cannot_change_error_type(self):
        gate = self.terminal_gate()
        object.__setattr__(gate, "_terminal_error_type_identity", id(ValueError))
        self.assert_stable_terminal_error(gate.dry_run)


if __name__ == "__main__":
    unittest.main()
