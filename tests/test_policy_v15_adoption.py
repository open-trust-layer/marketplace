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
    def test_v15_history_is_retained_while_agent_baseline_advances_to_v16(self):
        agents = _read("AGENTS.md")
        record = _read("docs/POLICY_V1_5_ADOPTION.md")
        self.assertIn("Constitution v1.3", agents)
        self.assertIn("Coding Agent Policy v1.3", agents)
        self.assertIn("Development Principles v1.6", agents)
        self.assertIn("docs/POLICY_V1_6_ADOPTION.md", agents)
        self.assertIn(_HANDBOOK_SHA256, record)
        self.assertIn("one coherent work-unit PR", agents)
        self.assertIn("delta-first validation", agents)
        self.assertIn("FULL once on final review head when required", agents)
        self.assertIn("Never invent cryptography", agents)
        self.assertIn(
            "measure -> identify bottleneck -> hypothesize -> smallest safe change",
            agents,
        )
        self.assertIn("without adequate evidence", agents)

    def test_v15_history_and_optimization_gate_semantics_survive_v16(self):
        policy = _read("DEVELOPMENT_POLICY.md")
        record = _read("docs/POLICY_V1_5_ADOPTION.md")
        self.assertIn("Coding Agent Constitution v1.3", policy)
        self.assertIn("Coding Agent Policy v1.3", policy)
        self.assertIn("Development Principles v1.6", policy)
        for digest in (
            _CONSTITUTION_SHA256,
            _POLICY_SHA256,
            _GOVERNANCE_INPUT_SHA256,
            _HANDBOOK_SHA256,
        ):
            self.assertIn(digest, record)
        self.assertIn("## 14. Optimization and performance discipline", policy)
        self.assertIn("## 10. Testing, conformance, and CI lanes", policy)
        self.assertIn("KEEP | REVISE | REVERT", policy)
        self.assertIn("A cache is not authorization", policy)
        self.assertIn("FAST", policy)
        self.assertIn("FULL", policy)
        self.assertIn("RELEASE", policy)
        self.assertIn("final review head", policy)
        self.assertIn("integrity-bound", policy)
        self.assertIn(
            "Required quality/security/integration/governance/conformance gates are not renamed, removed, skipped, bypassed, weakened",
            policy,
        )
        self.assertIn("CI/performance pressure does not authorize governance bypass", policy)

    def test_v15_crypto_and_reproducibility_guards_survive_v16_compression(self):
        policy = _read("DEVELOPMENT_POLICY.md")
        adoption = _read("docs/POLICY_V1_6_ADOPTION.md")
        self.assertIn("## 8. Dependencies, transport security, cryptography, and keys", policy)
        self.assertIn("Custom cryptographic algorithms", policy)
        self.assertIn("TLS certificate and hostname verification remain enabled", policy)
        for fragment in (
            "Prefer TLS 1.3 for new trust boundaries",
            "Privileged or non-idempotent operations MUST NOT use TLS 0-RTT",
            "AES-256-GCM",
            "XChaCha20-Poly1305",
            "Argon2id",
            "Signing, encryption, HMAC, token, and password purposes MUST NOT silently share one key",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, adoption)
        self.assertIn("independently repeated build", policy)
        self.assertIn("source pinning/provenance alone is not reproducibility proof", policy)

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
        self.assertIn("KEEP | REVISE | REVERT", governance)
        self.assertIn("No self-approval fiction", governance)
        self.assertIn("FULL once on final review head when required", governance)
        self.assertIn("exact-head guarded merge", governance)
        self.assertIn(
            "resulting merged `main` state receives required push acceptance/provenance verification",
            governance,
        )
        self.assertIn("reproducibility claims have evidence adequate to the claim", governance)

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
