from __future__ import annotations

import pathlib
import unittest
import zipfile

import marketplace.runtime as runtime

ROOT = pathlib.Path(__file__).resolve().parents[1]


class M55ArtifactMembershipTests(unittest.TestCase):
    def test_m55_runtime_document_and_exports_are_required_repository_artifacts(self):
        self.assertTrue(
            (ROOT / "src/marketplace/runtime/inbound_http_single_session.py").is_file()
        )
        self.assertTrue(
            (ROOT / "docs/bounded-inbound-http-single-session-orchestrator.md").is_file()
        )
        for name in (
            "BoundedInboundHttpSingleSessionOrchestrator",
            "InboundHttpResponsePreparerFactory",
            "InboundHttpSingleSessionOrchestratorError",
        ):
            self.assertIn(name, runtime.__all__)
            self.assertIsNotNone(getattr(runtime, name))

    def test_built_distribution_contains_m55_runtime(self):
        wheels = sorted((ROOT / "dist").glob("*.whl"))
        if not wheels:
            self.skipTest("wheel is built by the artifact gate")
        with zipfile.ZipFile(wheels[-1]) as archive:
            self.assertIn(
                "marketplace/runtime/inbound_http_single_session.py",
                archive.namelist(),
            )


if __name__ == "__main__":
    unittest.main()
