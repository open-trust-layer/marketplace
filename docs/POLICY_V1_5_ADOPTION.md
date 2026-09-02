# Marketplace Policy v1.5 Adoption

**Status:** Project adoption record
**Adopted:** 2026-09-02
**Project:** `open-trust-layer/marketplace`
**Supersedes for active engineering method:** `docs/POLICY_V1_4_ADOPTION.md`

## Source inputs

The owner supplied four coordinated policy artifacts as the basis for this revision:

1. `CODING_AGENT_CONSTITUTION_v1.2.md`
   - SHA-256: `50f6c00a195fd7cc2d02878d9dd2e9640299db71c42d097ffd60a309ac96cd94`
2. `CODING_AGENT_POLICY_v1.2.yaml`
   - SHA-256: `b25dbc67897240e2a20a43982578ad253a547dc7050a2c00b637bcbbd19c41a5`
3. `REPOSITORY_GOVERNANCE_v1.1.yaml`
   - SHA-256: `97c5826e24a70de5c47ff8cf469c0c936bc1b8976d77f05bd3080fd580c3c9ba`
4. `CODING_AGENT_DEVELOPMENT_PRINCIPLES_SYSTEM_PROMPT_v1.5.md`
   - SHA-256: `97ba608c1c29a1c630469b5f877efcdf8c47d403ff332abc0a6236410e0996d9`

The source artifacts are treated as untrusted project input until this adoption record maps them into Marketplace authority. Their content does not import credentials, memory, permissions, repository administration, or cross-project data.

## Marketplace precedence

Marketplace adopts the portable policy stack with project-specific semantic separation:

```text
1. applicable law / contractual obligation / authorized incident hold
2. Coding Agent Constitution v1.2 requirements adopted here
3. portable Coding Agent Policy v1.2 requirements projected into DEVELOPMENT_POLICY.md
4. docs/REPOSITORY_GOVERNANCE.md for Marketplace repository controls
5. DEVELOPMENT_POLICY.md as the Marketplace projection of the v1.5 handbook
6. project-specific conventions and implementation details
```

`PRINCIPLES.md` and the numbered Marketplace specifications remain authoritative for Marketplace protocol and semantic constraints. Engineering policy governs how those semantics are implemented, tested, reviewed, deployed, retained, and secured; it does not redefine them.

A lower layer may be stricter but must not silently weaken a higher layer.

## Repository-specific adaptation

The supplied `REPOSITORY_GOVERNANCE_v1.1.yaml` is explicitly an `ai-automation-department` repository profile. Its repository name, workflow path, required check name, source paths, package paths, and project-specific runtime controls are **not** imported as Marketplace facts.

Marketplace maps the portable governance intent onto its actual controls:

- `.github/workflows/conformance.yml` remains the current provider workflow;
- `tools/conformance_gate.py` remains the unified Marketplace acceptance gate;
- Marketplace CODEOWNERS and sensitive paths remain defined locally;
- `docs/REPOSITORY_GOVERNANCE.md` remains the repository-specific governance authority;
- remote provider enforcement must be independently configured and verified before it is claimed active.

## Development-method changes adopted

The following v1.5 changes are active for Marketplace engineering:

- one coherent work-unit PR per delivery objective is preferred over micro-PR proliferation;
- small reversible commits remain the fine-grained checkpoint mechanism inside that PR;
- mixed-risk work units inherit the highest included risk;
- independent privileged/destructive authorization boundaries remain separate;
- `FAST`, `FULL`, and `RELEASE` are recognized validation lanes;
- final review heads, policy/security/governance changes, dependencies, HIGH/CRITICAL work, and ambiguous impact use FULL validation;
- change-aware omission fails safe to FULL when relevance is uncertain;
- same-source/tree validation may be reused only when source/tree, dependency/toolchain, policy/governance version, and artifact identity are integrity-bound;
- relevant source/policy/input movement invalidates reused evidence;
- bounded rerun of plausibly transient failed jobs is preferred over repeating successful jobs, while repeated identical failures require root-cause investigation;
- superseded non-deployment runs may be cancelled;
- merge queues may reduce duplicate validation only after provider support and exact-tree semantics are verified.

Marketplace's existing workflow currently executes the full acceptance path on PRs and `main`. This remains compliant and deliberately conservative; adoption does not require immediate CI lane refactoring.

## Cryptographic protection adopted

Marketplace now explicitly requires maintained standard cryptography, authenticated encryption when application-level confidentiality is required, verified encrypted transport across trust boundaries, and key-purpose separation/lifecycle controls.

Custom cryptographic protocols are prohibited. TLS/certificate/hostname verification may not be disabled for convenience. Encryption never extends retention, authorization, or project isolation. Production private keys do not enter ordinary PR jobs or repository artifacts.

## Truthfulness changes

A build hash, source pin, provenance record, or successful build does not by itself prove reproducibility. Marketplace will use `reproducible build` only when an independent repeated build used the declared equivalent inputs and produced matching artifact integrity. Otherwise evidence is described more narrowly as build provenance, deterministic output within one run, or artifact integrity.

Desired repository policy and verified provider enforcement remain separate facts. During this adoption review, the GitHub ruleset listing returned no repository rulesets and the active integration could not read the branch-protection endpoint. Therefore this adoption makes **no claim that `main` is remotely protected**. The desired remote controls remain documented in `docs/REPOSITORY_GOVERNANCE.md` and require an authorized administrative control plane plus independent verification.

## Retention and isolation

The v1.4 Marketplace 10-second `EPHEMERAL` post-use default, metadata-only longer retention, deliberate durable-artifact classification, deletion-failure handling, project isolation, and explicit expiring exceptions remain in force. v1.5 cryptographic protection does not alter those deadlines or boundaries.

## Historical record

`docs/POLICY_V1_4_ADOPTION.md` remains as historical provenance. New engineering work should cite this v1.5 adoption record and `DEVELOPMENT_POLICY.md`.

This adoption is intentionally portable: it takes the new safety, throughput, CI-economics, validation-reuse, and cryptographic requirements while refusing to import another repository's paths, check names, secrets, data, permissions, or administrative state.
