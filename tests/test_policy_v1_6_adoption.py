from __future__ import annotations

from pathlib import Path
import unittest

from repository_audit import _REQUIRED_GOVERNANCE_FILES


ROOT = Path(__file__).resolve().parents[1]


class PolicyV16AdoptionTests(unittest.TestCase):
    def test_adoption_record_exists_with_exact_source_hashes(self):
        path = ROOT / "docs" / "POLICY_V1_6_ADOPTION.md"
        self.assertTrue(path.is_file(), "v1.6 adoption record is required")
        text = path.read_text(encoding="utf-8")
        expected = (
            "c76d3f9b921abdf750f338c73303b0cd1cb31fd998142f635a1a971925f12b5c",
            "0cba8b4f68c570f2830720b2c1285ea132ab563978fa3ad2c22e152ac76379ca",
            "ec221545c8a7a5e203bf081238faf8b8d0e151087a3c20011255b8bc74ee4859",
            "12314b7fc9a4cbb5e93d907ed5c613f29c4895f610356285cc88da52898bcb76",
        )
        for digest in expected:
            with self.subTest(digest=digest):
                self.assertIn(digest, text)
        self.assertIn("ai-automation-department", text)
        self.assertIn("not imported as Marketplace facts", text)

    def test_development_policy_points_to_v1_6_stack_and_execution_kernel(self):
        text = (ROOT / "DEVELOPMENT_POLICY.md").read_text(encoding="utf-8")
        required = (
            "Coding Agent Constitution v1.3",
            "Coding Agent Policy v1.3",
            "Repository Governance v1.2",
            "Development Principles v1.6",
            "docs/POLICY_V1_6_ADOPTION.md",
            "Work Unit Contract",
            "Evidence Ledger",
            "bounded authorization reuse",
            "preauthorized rollback",
            "merge authorization",
            "runtime activation",
        )
        for fragment in required:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_agents_instructions_adopt_v1_6_fast_execution_method(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        required = (
            "Constitution v1.3",
            "Coding Agent Policy v1.3",
            "Development Principles v1.6",
            "docs/POLICY_V1_6_ADOPTION.md",
            "work-unit contract",
            "evidence ledger",
            "delta-first",
            "bounded authorization reuse",
            "separate",
            "runtime activation",
        )
        for fragment in required:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_marketplace_governance_references_v1_6_adoption_without_foreign_check_names(self):
        text = (ROOT / "docs" / "REPOSITORY_GOVERNANCE.md").read_text(encoding="utf-8")
        self.assertIn("docs/POLICY_V1_6_ADOPTION.md", text)
        self.assertIn("bounded authorization reuse", text)
        self.assertIn("preauthorized rollback", text)
        self.assertIn("merge", text)
        self.assertIn("runtime activation", text)
        self.assertNotIn("required check `quality`", text)

    def test_codeowners_and_repository_audit_require_v1_6_adoption_record(self):
        path = Path("docs/POLICY_V1_6_ADOPTION.md")
        codeowners = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
        self.assertIn("/docs/POLICY_V1_6_ADOPTION.md @tehki", codeowners)
        self.assertIn(path, _REQUIRED_GOVERNANCE_FILES)


if __name__ == "__main__":
    unittest.main()
