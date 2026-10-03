# Marketplace Policy v1.7 Adoption

**Status:** Project adoption record
**Adopted:** 2026-09-21
**Project:** `open-trust-layer/marketplace`
**Supersedes for active engineering method:** `docs/POLICY_V1_6_ADOPTION.md`
**Exact adoption baseline:** `9a090388143690b0a230433b0b828a3dcaf64fef`

## Source inputs

The owner supplied and explicitly adopted four coordinated policy artifacts on 2026-09-21:

1. `CODING_AGENT_CONSTITUTION_v1.4.md`
   - SHA-256: `fdc846fd266063aa1388d55ba0e21c4565b24d2ac8d667a5a553dd5ddcc14943`
2. `CODING_AGENT_POLICY_v1.4.yaml`
   - SHA-256: `f741c91014cbb1775716c31e45e3d181c732763b7fe14341f4d47d919bd998a3`
3. `REPOSITORY_GOVERNANCE_v1.3.yaml`
   - SHA-256: `e00083ead3e9bc48ced6cee3674c8449ab507f2269711b7c440d008c0ad2497c`
4. `CODING_AGENT_DEVELOPMENT_PRINCIPLES_SYSTEM_PROMPT_v1.7.md`
   - SHA-256: `78b579613b98b388db0cac2a5bf360089b2137e997b6a19a87da44a11acb183c`

The source artifacts are project-policy input only. They do not import credentials, cross-project data, runtime authority, deployment authority, repository administration, or provider settings.

## Marketplace precedence

Marketplace adopts the coordinated bundle as:

```text
1. applicable law / contractual obligation / authorized incident hold
2. Coding Agent Constitution v1.4 requirements adopted by this record
3. portable Coding Agent Policy v1.4 requirements projected into DEVELOPMENT_POLICY.md
4. docs/REPOSITORY_GOVERNANCE.md for Marketplace repository controls
5. DEVELOPMENT_POLICY.md as the Marketplace projection of Development Principles v1.7
6. project-specific conventions and implementation details
```

`PRINCIPLES.md` and numbered Marketplace specifications remain authoritative for Marketplace protocol/semantic constraints. Engineering policy controls how those semantics are implemented, tested, reviewed, retained, secured, merged, activated, and deployed.

This v1.7 bundle is self-contained with its named companions. Superseded policy/handbook revisions remain durable historical provenance, not hidden current requirements.

## Repository-specific adaptation

The supplied `REPOSITORY_GOVERNANCE_v1.3.yaml` is explicitly repository-specific to `ai-automation-department`.

Marketplace therefore does **not** import as facts:

- repository name or project paths;
- `.github/workflows/ci.yml`;
- required check name `quality`;
- linear-history assumptions;
- validator filenames;
- runner/runtime paths;
- provider administrative state.

Marketplace keeps its reviewed local equivalents:

- provider workflow: `.github/workflows/conformance.yml`;
- provider job/check identity: `acceptance`;
- local acceptance command: `python tools/conformance_gate.py --olp-root <path>`;
- Marketplace CODEOWNERS/sensitive paths;
- `docs/REPOSITORY_GOVERNANCE.md` as repository-specific governance authority;
- reviewed GitHub merge-commit provenance rather than importing the foreign linear-history setting.

## v1.7 development-method changes

Marketplace adopts the v1.7 proportional delivery kernel:

1. establish one work-unit contract and evidence ledger;
2. inspect the minimum authoritative implementation/test/config/policy surface;
3. batch independent read-only work;
4. plan once and implement one coherent patch;
5. use delta-first focused validation;
6. run FULL once on the final policy/security/governance-sensitive candidate;
7. reuse validation only when all relevant integrity-bound inputs are unchanged;
8. continue independent safe work while CI runs without mutating the tested head;
9. avoid micro-PR churn for one coherent objective;
10. keep concise progress/evidence reporting;
11. preserve explicit stop conditions.

## Task-scoped PR delivery and zero mandatory approvals

For an explicitly adopted Marketplace delivery task, source-delivery authority includes:

- implementation and tests;
- task-branch commits/pushes;
- PR creation/update;
- routine merge after required checks and merge preconditions pass.

Marketplace now requires **zero mandatory human PR approvals at every PR risk level**.

This does not remove review or validation:

- agent diff review remains required;
- applicable automated policy/security/governance checks remain required;
- required Marketplace conformance remains required;
- blocking review feedback must be resolved;
- exact head/base/mergeability must be verified;
- merge-triggered HIGH/CRITICAL operational actions require their own authority.

A same-scope head change refreshes affected validation/evidence and exact-head merge guarding; it does not require renewed task authorization unless the user explicitly pinned authority to the old head.

Historical solo-maintainer exceptions and exact-head approvals remain provenance for earlier actions, but they are not current routine PR gates.

## Separate operational authority

Routine source merge does **not** authorize:

- provider administration;
- dependency installation into a live environment;
- secret/credential/key mutation;
- database migration or live persistence activation;
- service/process/runtime activation;
- deployment/public exposure;
- destructive external action;
- payment/settlement/fulfillment side effects.

A merge that itself triggers one of those operations inherits that operational boundary and requires the applicable authority before merge.

## Provider-control truthfulness

Current provider state was re-read during this adoption.

At baseline `9a090388143690b0a230433b0b828a3dcaf64fef`, GitHub reported:

```text
main protected: false
branch protection enabled: false
required status checks: enforcement off
repository rulesets: []
Marketplace check-run identity on main: acceptance
```

The detailed branch-protection endpoint is inaccessible to the connected GitHub integration, but the branch endpoint directly reports protection disabled.

Therefore this adoption makes **no claim that `main` is remotely protected**.

The adopted policy requires provider-side protection where supported. Until that control is configured and independently verified, source development and PR validation may continue, but routine merge to `main` is blocked unless an explicit narrow governance exception applies.

Provider-side adoption is tracked by Issue #212 and is a separate HIGH/ADMIN control-plane action.

## Retention, isolation, crypto, and supply chain

The 10-second post-use `EPHEMERAL` default remains unchanged.

Metadata-only operational retention defaults to 30 days and must contain no project payload/secrets/raw media. Deliberate source/spec/test/docs remain `DURABLE_PROJECT_ARTIFACT`. Deletion failure remains a security/privacy event.

Cross-project access remains denied by default.

Dependencies remain executable trust relationships and require concrete need/review.

Marketplace continues to prohibit custom cryptography, requires maintained standard implementations, accurate transport/crypto claims, TLS certificate/hostname verification, authenticated encryption where required by the threat model, purpose-separated keys, and isolation of production private keys from ordinary PR jobs/artifacts.

Encryption does not extend retention or authorization.

## Transition validation rule

This policy transition must be validated against the previously adopted v1.6 state. The candidate policy does not grant itself provider ADMIN authority and does not waive the controls needed to validate its own adoption.

The transition requires FULL Marketplace conformance on the final exact source candidate.

## Historical records

The following remain durable historical provenance:

- `docs/POLICY_V1_6_ADOPTION.md`
- `docs/POLICY_V1_5_ADOPTION.md`
- `docs/POLICY_V1_4_ADOPTION.md`

New engineering work should cite this v1.7 adoption record and `DEVELOPMENT_POLICY.md`.
