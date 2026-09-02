from __future__ import annotations

import unittest
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONSTITUTION_SHA256 = "50f6c00a195fd7cc2d02878d9dd2e9640299db71c42d097ffd60a309ac96cd94"
_POLICY_SHA256 = "b25dbc67897240e2a20a43982578ad253a547dc7050a2c00b637bcbbd19c41a5"
_GOVERNANCE_INPUT_SHA256 = "97c5826e24a70de5c47ff8cf469c0c936bc1b8976d77f05bd3080fd580c3c9ba"
_HANDBOOK_SHA256 = "97ba608c1c29a1c630469b5f877efcdf8c47d403ff332abc0a6236410e0996d9"


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text(encoding="utf-8")


class PolicyV15AdoptionTests(unittest.TestCase):
    def test_agent_baseline_is_v15_and_bound_to_source_digest(self):
        agents = _read("AGENTS.md")
        self.assertIn("Constitution v1.2", agents)
        self.assertIn("Coding Agent Policy v1.2", agents)
        self.assertIn("Development Principles v1.5", agents)
        self.assertIn(_HANDBOOK_SHA256, agents)
        self.assertIn("docs/POLICY_V1_5_ADOPTION.md", agents)
        self.assertIn("one coherent work-unit PR", agents)
        self.assertIn("FAST validation", agents)
        self.assertIn("FULL validation", agents)
        self.assertIn("independent matching reproduction", agents)
        self.assertIn("Never invent cryptography", agents)
        self.assertIn("measure -> identify -> hypothesize -> change -> measure again", agents)

    def test_development_policy_preserves_optimization_and_gate_semantics_at_v15(self):
        policy = _read("DEVELOPMENT_POLICY.md")
        self.assertIn("Coding Agent Constitution v1.2", policy)
        self.assertIn("Coding Agent Policy v1.2", policy)
        self.assertIn("Coding Agent Development Principles v1.5", policy)
        self.assertIn(_CONSTITUTION_SHA256, policy)
        self.assertIn(_POLICY_SHA256, policy)
        self.assertIn(_GOVERNANCE_INPUT_SHA256, policy)
        self.assertIn(_HANDBOOK_SHA256, policy)
        self.assertIn("## 13. Evidence-driven optimization", policy)
        self.assertIn("## 16. CI, build, and test acceleration without gate reduction", policy)
        self.assertIn("KEEP | REVISE | REVERT", policy)
        self.assertIn("Caching is a performance mechanism, not a trust mechanism", policy)
        self.assertIn("`FAST`", policy)
        self.assertIn("`FULL`", policy)
        self.assertIn("`RELEASE`", policy)
        self.assertIn("final review head", policy)
        self.assertIn("immutably bound to the same relevant source/tree", policy)
        self.assertIn(
            "Required quality/security/integration/governance/conformance gates are not renamed, removed, skipped, bypassed, weakened, or short-circuited merely to reduce CI duration.",
            policy,
        )
        self.assertIn("CI optimization MUST NOT:", policy)

    def test_development_policy_requires_standard_crypto_and_truthful_reproducibility(self):
        policy = _read("DEVELOPMENT_POLICY.md")
        self.assertIn("### 9.1 Cryptography, transport, and key separation", policy)
        self.assertIn("Custom cryptographic algorithms", policy)
        self.assertIn("TLS certificate and hostname verification MUST remain enabled", policy)
        self.assertIn("AES-256-GCM", policy)
        self.assertIn("XChaCha20-Poly1305", policy)
        self.assertIn("Argon2id", policy)
        self.assertIn("independently repeated build", policy)
        self.assertIn("one successful or source-pinned build is only provenance/integrity evidence", policy)

    def test_pr_template_requires_optimization_crypto_and_validation_reuse_evidence(self):
        template = _read(".github/pull_request_template.md")
        self.assertIn("## Performance / optimization evidence", template)
        self.assertIn("Representative baseline:", template)
        self.assertIn("Optimization hypothesis:", template)
        self.assertIn("Result: `KEEP` / `REVISE` / `REVERT`", template)
        self.assertIn("## Dependencies, cryptography, and provenance", template)
        self.assertIn("no custom cryptography", template)
        self.assertIn("## Validation lane and evidence reuse", template)
        self.assertIn("Selected lane: `FAST` / `FULL` / `RELEASE`", template)
        self.assertIn("ambiguous relevance falls back to FULL", template)
        self.assertIn("independent matching reproduction", template)
        self.assertIn("required quality/security/integration/governance/conformance gates", template)

    def test_repository_governance_preserves_final_full_and_merged_main_verification(self):
        governance = _read("docs/REPOSITORY_GOVERNANCE.md")
        self.assertIn("docs/POLICY_V1_5_ADOPTION.md", governance)
        self.assertIn("material performance/resource claim", governance)
        self.assertIn("KEEP`, `REVISE`, or `REVERT", governance)
        self.assertIn("No self-approval fiction", governance)
        self.assertIn("FULL acceptance on the final review head", governance)
        self.assertIn("exact-head guarded merge", governance)
        self.assertIn(
            "the resulting merged `main` commit MUST independently pass the applicable push acceptance workflow",
            governance,
        )
        self.assertIn("any reproducible-build claim additionally requires an independent matching reproduction", governance)

    def test_adoption_record_maps_foreign_governance_without_importing_authority(self):
        record = _read("docs/POLICY_V1_5_ADOPTION.md")
        for digest in (
            _CONSTITUTION_SHA256,
            _POLICY_SHA256,
            _GOVERNANCE_INPUT_SHA256,
            _HANDBOOK_SHA256,
        ):
            self.assertIn(digest, record)
        self.assertIn("ai-automation-department", record)
        self.assertIn("are **not** imported as Marketplace facts", record)
        self.assertIn(".github/workflows/conformance.yml", record)
        self.assertIn("tools/conformance_gate.py", record)
        self.assertIn("makes **no claim that `main` is remotely protected**", record)
        self.assertIn("independent repeated build", record)

    def test_v15_adoption_record_is_codeowned_and_v14_history_is_retained(self):
        codeowners = _read(".github/CODEOWNERS")
        self.assertIn("/docs/POLICY_V1_5_ADOPTION.md @tehki", codeowners)
        self.assertIn("/docs/POLICY_V1_4_ADOPTION.md @tehki", codeowners)
        record = _read("docs/POLICY_V1_5_ADOPTION.md")
        self.assertIn("docs/POLICY_V1_4_ADOPTION.md", record)
        self.assertIn("historical provenance", record)


if __name__ == "__main__":
    unittest.main()
