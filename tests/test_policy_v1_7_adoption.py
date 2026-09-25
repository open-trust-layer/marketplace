from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PolicyV17AdoptionTests(unittest.TestCase):
    def test_adoption_record_exists_with_exact_source_hashes(self) -> None:
        path = ROOT / "docs" / "POLICY_V1_7_ADOPTION.md"
        self.assertTrue(path.is_file(), "v1.7 adoption record is required")
        text = path.read_text(encoding="utf-8")
        for digest in (
            "fdc846fd266063aa1388d55ba0e21c4565b24d2ac8d667a5a553dd5ddcc14943",
            "f741c91014cbb1775716c31e45e3d181c732763b7fe14341f4d47d919bd998a3",
            "e00083ead3e9bc48ced6cee3674c8449ab507f2269711b7c440d008c0ad2497c",
            "78b579613b98b388db0cac2a5bf360089b2137e997b6a19a87da44a11acb183c",
        ):
            with self.subTest(digest=digest):
                self.assertIn(digest, text)
        self.assertIn("ai-automation-department", text)
        self.assertIn("acceptance", text)
        self.assertIn("main protected: false", text)

    def test_active_policy_points_to_v1_7_stack(self) -> None:
        text = (ROOT / "DEVELOPMENT_POLICY.md").read_text(encoding="utf-8")
        for fragment in (
            "Coding Agent Constitution v1.4",
            "Coding Agent Policy v1.4",
            "Repository Governance v1.3",
            "Development Principles v1.7",
            "docs/POLICY_V1_7_ADOPTION.md",
            "v1.7 FAST EXECUTION KERNEL",
            "zero mandatory human PR approvals",
            "task-branch commit/push",
            "routine merge after required checks",
            "provider-side protection of `main`",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_agents_adopt_task_scoped_delivery_without_operational_collapse(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for fragment in (
            "Constitution v1.4",
            "Coding Agent Policy v1.4",
            "Development Principles v1.7",
            "docs/POLICY_V1_7_ADOPTION.md",
            "zero mandatory human PR approvals",
            "task-branch commit/push",
            "Runtime activation is **separate** from merge",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_marketplace_governance_uses_zero_approval_profile_and_acceptance_check(self) -> None:
        text = (ROOT / "docs" / "REPOSITORY_GOVERNANCE.md").read_text(encoding="utf-8")
        self.assertIn("docs/POLICY_V1_7_ADOPTION.md", text)
        self.assertIn("mandatory human PR approval count is **zero**", text)
        self.assertIn("exact Marketplace provider check `acceptance` is required", text)
        self.assertIn("## 10. Zero-approval PR review profile", text)
        self.assertNotIn("normal changes require at least one approval", text)
        self.assertNotIn("## 10. Solo-maintainer review procedure", text)

    def test_codeowners_and_pr_template_point_to_current_profile(self) -> None:
        codeowners = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
        template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
        self.assertIn("/docs/POLICY_V1_7_ADOPTION.md @tehki", codeowners)
        self.assertIn("## v1.7 Evidence Ledger", template)
        self.assertIn("Mandatory human PR approvals required by current Marketplace policy: `0`", template)
        self.assertNotIn("Solo-maintainer procedure / governance exception", template)

    def test_remote_enforcement_truthfulness_stays_fail_closed(self) -> None:
        adoption = (ROOT / "docs" / "POLICY_V1_7_ADOPTION.md").read_text(encoding="utf-8")
        governance = (ROOT / "docs" / "REPOSITORY_GOVERNANCE.md").read_text(encoding="utf-8")
        for text in (adoption, governance):
            self.assertIn("main protected: false", text)
            self.assertIn("Issue #212", text)
        self.assertIn("routine merge to `main` is blocked", adoption)


if __name__ == "__main__":
    unittest.main()
