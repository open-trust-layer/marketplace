from __future__ import annotations

import unittest
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_SHA256 = "ab39374e010a931d5122c28bc3a97612cbeb41f1079c67f0f90863d01641e1cc"


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text(encoding="utf-8")


class PolicyV14AdoptionTests(unittest.TestCase):
    def test_agent_baseline_is_v14_and_bound_to_source_digest(self):
        agents = _read("AGENTS.md")
        self.assertIn("Coding Agent Development Principles v1.4", agents)
        self.assertIn(_SOURCE_SHA256, agents)
        self.assertIn("docs/POLICY_V1_4_ADOPTION.md", agents)
        self.assertIn("measure -> identify -> hypothesize -> change -> measure again", agents)

    def test_development_policy_makes_optimization_evidence_mandatory_without_gate_reduction(self):
        policy = _read("DEVELOPMENT_POLICY.md")
        self.assertIn("Coding Agent Development Principles v1.4", policy)
        self.assertIn(_SOURCE_SHA256, policy)
        self.assertIn("## 13. Evidence-driven optimization", policy)
        self.assertIn("## 16. CI, build, and test acceleration without gate reduction", policy)
        self.assertIn("KEEP | REVISE | REVERT", policy)
        self.assertIn("Caching is a performance mechanism, not a trust mechanism", policy)
        self.assertIn("required quality/security/integration/governance/conformance gates", policy)
        self.assertIn("MUST NOT", policy)

    def test_pr_template_requires_material_optimization_evidence(self):
        template = _read(".github/pull_request_template.md")
        self.assertIn("## Performance / optimization evidence", template)
        self.assertIn("Representative baseline:", template)
        self.assertIn("Optimization hypothesis:", template)
        self.assertIn("Result: `KEEP` / `REVISE` / `REVERT`", template)
        self.assertIn("required quality/security/integration/governance/conformance gates", template)

    def test_repository_governance_requires_performance_evidence_without_self_approval_fiction(self):
        governance = _read("docs/REPOSITORY_GOVERNANCE.md")
        self.assertIn("docs/POLICY_V1_4_ADOPTION.md", governance)
        self.assertIn("material performance/resource claim", governance)
        self.assertIn("KEEP`, `REVISE`, or `REVERT", governance)
        self.assertIn("No self-approval fiction", governance)
        self.assertIn("exact-head guarded merge", governance)
        self.assertIn("verify merged-main CI", governance)

    def test_adoption_record_separates_source_examples_from_marketplace_authority(self):
        record = _read("docs/POLICY_V1_4_ADOPTION.md")
        self.assertIn(_SOURCE_SHA256, record)
        self.assertIn("ai-automation-department", record)
        self.assertIn("not Marketplace facts", record)
        self.assertIn("this v1.3 handbook", record)
        self.assertIn("the v1.4 handbook", record)
        self.assertIn("does not configure or claim provider-side branch protection", record)

    def test_policy_adoption_record_is_codeowned(self):
        codeowners = _read(".github/CODEOWNERS")
        self.assertIn("/docs/POLICY_V1_4_ADOPTION.md @tehki", codeowners)


if __name__ == "__main__":
    unittest.main()
