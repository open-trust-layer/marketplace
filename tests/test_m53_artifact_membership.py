from __future__ import annotations

import pathlib
import unittest
import zipfile

import marketplace.runtime as runtime

ROOT = pathlib.Path(__file__).resolve().parents[1]


class M53ArtifactMembershipTests(unittest.TestCase):
    def test_m53_runtime_document_and_exports_are_required_repository_artifacts(self):
        self.assertTrue((ROOT / "src/marketplace/runtime/inbound_tcp_listener.py").is_file())
        self.assertTrue((ROOT / "docs/bounded-inbound-tcp-listener-construction.md").is_file())
        for name in (
            "BoundedInboundTcpListenerConstruction",
            "InboundTcpListenerCapability",
            "InboundTcpListenerConstructionError",
            "InboundTcpListenerFactory",
        ):
            self.assertIn(name, runtime.__all__)
            self.assertIsNotNone(getattr(runtime, name))


    def test_built_distribution_contains_m53_runtime(self):
        wheels = sorted((ROOT / "dist").glob("*.whl"))
        if not wheels:
            self.skipTest("wheel is built by the artifact gate")
        with zipfile.ZipFile(wheels[-1]) as archive:
            self.assertIn("marketplace/runtime/inbound_tcp_listener.py", archive.namelist())


if __name__ == "__main__":
    unittest.main()
