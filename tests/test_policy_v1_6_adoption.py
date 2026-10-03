from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PolicyV16HistoricalAdoptionTests(unittest.TestCase):
    def test_v1_6_adoption_record_remains_historical_provenance(self) -> None:
        path = ROOT / "docs" / "POLICY_V1_6_ADOPTION.md"
        self.assertTrue(path.is_file(), "historical v1.6 adoption record is required")
        text = path.read_text(encoding="utf-8")
        for digest in (
            "c76d3f9b921abdf750f338c73303b0cd1cb31fd998142f635a1a971925f12b5c",
            "0cba8b4f68c570f2830720b2c1285ea132ab563978fa3ad2c22e152ac76379ca",
            "ec221545c8a7a5e203bf081238faf8b8d0e151087a3c20011255b8bc74ee4859",
            "12314b7fc9a4cbb5e93d907ed5c613f29c4895f610356285cc88da52898bcb76",
        ):
            with self.subTest(digest=digest):
                self.assertIn(digest, text)
        self.assertIn("ai-automation-department", text)
        self.assertIn("not imported as Marketplace facts", text)

    def test_current_policy_does_not_point_back_to_v1_6(self) -> None:
        development = (ROOT / "DEVELOPMENT_POLICY.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        governance = (ROOT / "docs" / "REPOSITORY_GOVERNANCE.md").read_text(encoding="utf-8")
        for text in (development, agents, governance):
            self.assertIn("POLICY_V1_7_ADOPTION.md", text)
        self.assertNotIn("**Adoption record:** `docs/POLICY_V1_6_ADOPTION.md`", development)


if __name__ == "__main__":
    unittest.main()
