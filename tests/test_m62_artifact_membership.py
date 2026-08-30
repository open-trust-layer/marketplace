from __future__ import annotations

import pathlib
import unittest

from marketplace.runtime import (
    LOOPBACK_EXECUTION_OPT_IN,
    BoundedInboundHttpLoopbackExecutionGate,
    InboundHttpLoopbackExecutionGateError,
    InboundHttpLoopbackReadiness,
)
from package_artifact_gate import _REQUIRED_PACKAGE_MEMBERS

ROOT = pathlib.Path(__file__).resolve().parents[1]


class M62ArtifactMembershipTests(unittest.TestCase):
    def test_m62_required_source_tests_docs_and_manual_tool_are_present(self):
        for relative in (
            "src/marketplace/runtime/inbound_http_execution_gate.py",
            "tests/test_inbound_http_execution_gate.py",
            "tests/test_inbound_http_loopback_acceptance_tool.py",
            "tools/inbound_http_loopback_acceptance.py",
            "docs/M62_LOOPBACK_ACCEPTANCE.md",
        ):
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_runtime_gate_is_in_wheel_but_manual_tool_is_repository_only(self):
        self.assertIn(
            "marketplace/runtime/inbound_http_execution_gate.py",
            _REQUIRED_PACKAGE_MEMBERS,
        )
        self.assertNotIn(
            "tools/inbound_http_loopback_acceptance.py",
            _REQUIRED_PACKAGE_MEMBERS,
        )

    def test_runtime_public_exports_are_exact_m62_symbols(self):
        self.assertEqual(
            LOOPBACK_EXECUTION_OPT_IN,
            "EXECUTE_ONE_LOOPBACK_NETWORK_SESSION",
        )
        self.assertEqual(BoundedInboundHttpLoopbackExecutionGate.__module__, "marketplace.runtime.inbound_http_execution_gate")
        self.assertEqual(InboundHttpLoopbackExecutionGateError.__module__, "marketplace.runtime.inbound_http_execution_gate")
        self.assertEqual(InboundHttpLoopbackReadiness.__module__, "marketplace.runtime.inbound_http_execution_gate")


if __name__ == "__main__":
    unittest.main()
