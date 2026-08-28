from __future__ import annotations

import pathlib
import unittest
import zipfile

import marketplace.runtime as runtime

ROOT = pathlib.Path(__file__).resolve().parents[1]


class M51ArtifactMembershipTests(unittest.TestCase):
    def test_m51_runtime_document_and_exports_are_required_repository_artifacts(self):
        self.assertTrue((ROOT / "src/marketplace/runtime/inbound_http_connection.py").is_file())
        self.assertTrue((ROOT / "docs/bounded-inbound-http-single-connection-transport.md").is_file())
        for name in (
            "BoundedInboundHttpSingleConnectionIO",
            "BoundedInboundHttpSingleConnectionTransport",
            "CompletedInboundHttpSingleConnectionTransport",
            "InboundHttpSingleConnection",
            "InboundHttpSingleConnectionTransportError",
        ):
            self.assertIn(name, runtime.__all__)
            self.assertIsNotNone(getattr(runtime, name))

    def test_built_distribution_contains_m51_runtime(self):
        wheels = sorted((ROOT / "dist").glob("*.whl"))
        if not wheels:
            self.skipTest("wheel is built by the artifact gate")
        with zipfile.ZipFile(wheels[-1]) as archive:
            self.assertIn("marketplace/runtime/inbound_http_connection.py", archive.namelist())
