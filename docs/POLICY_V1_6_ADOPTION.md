# Marketplace Policy v1.6 Adoption

**Status:** Project adoption record
**Adopted:** 2026-09-04
**Project:** `open-trust-layer/marketplace`
**Supersedes for active engineering method:** `docs/POLICY_V1_5_ADOPTION.md`
**Exact adoption baseline:** `b1921cb6c744e68f9d2ee8d9c83f5c44bbede4c2`

## Source inputs

The owner supplied four coordinated policy artifacts on 2026-09-04:

1. `CODING_AGENT_CONSTITUTION_v1.3.md`
   - SHA-256: `c76d3f9b921abdf750f338c73303b0cd1cb31fd998142f635a1a971925f12b5c`
2. `CODING_AGENT_POLICY_v1.3.yaml`
   - SHA-256: `0cba8b4f68c570f2830720b2c1285ea132ab563978fa3ad2c22e152ac76379ca`
3. `REPOSITORY_GOVERNANCE_v1.2.yaml`
   - SHA-256: `ec221545c8a7a5e203bf081238faf8b8d0e151087a3c20011255b8bc74ee4859`
4. `CODING_AGENT_DEVELOPMENT_PRINCIPLES_SYSTEM_PROMPT_v1.6.md`
   - SHA-256: `12314b7fc9a4cbb5e93d907ed5c613f29c4895f610356285cc88da52898bcb76`

The source artifacts are treated as project input until this record maps them into Marketplace authority. They do not import credentials, memory, data, permissions, runtime authority, repository administration, or cross-project access.

## Marketplace precedence

Marketplace adopts the portable policy stack as follows:

```text
1. applicable law / contractual obligation / authorized incident hold
2. Coding Agent Constitution v1.3 requirements adopted by this record
3. portable Coding Agent Policy v1.3 requirements projected into DEVELOPMENT_POLICY.md
4. docs/REPOSITORY_GOVERNANCE.md for Marketplace repository controls
5. DEVELOPMENT_POLICY.md as the Marketplace projection of Development Principles v1.6
6. project-specific conventions and implementation details
```

`PRINCIPLES.md` and the numbered Marketplace specifications remain authoritative for Marketplace protocol and semantic constraints. Engineering policy governs how those semantics are implemented, tested, reviewed, retained, secured, merged, activated, and deployed; it does not redefine them.

Compression in v1.6 does not silently remove a safety, security, privacy, retention, project-isolation, authorization, provenance, cryptographic, or repository-governance obligation already adopted under v1.5. Where this Marketplace projection is ambiguous, apply the stricter higher-precedence rule or the stricter previously adopted v1.5 interpretation until the ambiguity is resolved.

## Repository-specific adaptation

The supplied `REPOSITORY_GOVERNANCE_v1.2.yaml` is explicitly an `ai-automation-department` repository-specific profile and itself states that cross-repository copying requires path and control review.

Accordingly, its repository name, package paths, security-sensitive source paths, workflow path `.github/workflows/ci.yml`, required job/check name `quality`, validator filenames, runner assumptions, and project-specific runtime paths are **not imported as Marketplace facts**.

Marketplace keeps its actual repository controls:

- provider workflow: `.github/workflows/conformance.yml`;
- provider job: `acceptance`;
- unified acceptance command: `tools/conformance_gate.py`;
- Marketplace CODEOWNERS and sensitive paths;
- `docs/REPOSITORY_GOVERNANCE.md` as repository-specific governance authority;
- `PRINCIPLES.md` and Marketplace specifications as semantic authority.

The source governance profile's `require_linear_history` setting is not imported. Marketplace currently uses reviewed GitHub merge commits and verifies exact merge parentage; changing merge strategy is a separate repository-governance decision.

## Development-method changes adopted

Marketplace adopts the v1.6 FAST EXECUTION KERNEL and aligned Policy v1.3 delivery controls:

1. establish one compact **Work Unit Contract** at the start of meaningful work;
2. maintain an internal **Evidence Ledger** of verified facts and invalidate evidence only when its relevant inputs change;
3. inspect the minimum authoritative implementation/test/config/policy surface rather than recursively rediscovering the repository;
4. batch or parallelize independent read-only work and deterministic validation when safe;
5. plan once, then execute the authorized coherent work unit without repeatedly asking for unchanged authorization;
6. prefer one coherent patch/review surface and small reversible commits over repeated micro-PR boundaries;
7. validate the delta first, then run FULL once on the final review head when required;
8. reuse validation only when exact source/tree, dependency/toolchain, policy/governance, test/build definition, environment class where material, and artifact identity remain integrity-bound;
9. continue independent safe work while CI runs without mutating the head whose result is being treated as evidence;
10. stop and reassess on target drift, higher-than-authorized risk, material gate failure, security uncertainty, project-boundary ambiguity, suspected secret exposure, invalid rollback assumptions, inability to re-verify a destructive target, missing required provider controls without an exception, or material runtime/resource degradation;
11. use concise status reporting around meaningful progress, authorization boundaries, blockers, material failures, and completion rather than narrating every low-value tool call.

This is an optimization of engineering latency and cognitive load, not a reduction of controls.

## Bounded authorization reuse

Marketplace adopts bounded authorization reuse for an already authorized work unit while all relevant inputs remain unchanged:

```text
project
exact target/resource
exact head/version where the authorization specified one
scope
risk class
capability class
side-effect class
rollback/recovery assumptions
expiry/exception state
```

A safe read-only verification, deterministic test rerun, conversation continuation, or non-mutating diagnostic step does not by itself require a repeated approval.

This rule does **not** weaken Marketplace exact-head merge governance. If merge authorization names an exact head SHA, any head movement invalidates that authorization. Privileged or destructive targets still require immediate re-verification before execution.

Marketplace's local solo-maintainer and governance-exception procedures remain stricter where they impose extra evidence or exact-head requirements.

## Separate merge, activation, and deployment authority

Merge authorization, runtime activation authorization, configuration/service mutation authorization, and deployment authorization remain separate by default.

A merge does not authorize dependency installation, server start, socket bind/listen, browser launch, PostgreSQL activation/migration, environment/secret loading, service restart, Android build/install, public exposure, production deployment, or another runtime mutation unless the authorization explicitly combines that capability and exact target.

## Preauthorized rollback

When an authorized mutation includes an exact rollback condition and exact rollback method, that rollback may execute without a second approval if and only if the stated condition becomes true and the rollback stays within the original exact target/method. The restored state must be verified and the trigger/result reported. Silent infinite retry is prohibited.

## CI and evidence reuse

Marketplace recognizes FAST, FULL, and RELEASE lanes. The current provider workflow remains deliberately conservative and executes the full acceptance path on pull requests and `main`.

Policy/security/governance changes, dependency or lockfile changes, HIGH/CRITICAL risk, final ready-for-review heads, and ambiguous impact require FULL validation. A required gate is never renamed, skipped, bypassed, weakened, or narrowed merely for speed.

Superseded non-deployment runs may be cancelled where tooling supports it. Rerunning only failed jobs is preferred for plausibly transient failures with unchanged source; repeated identical failure requires root-cause investigation.

Exact-tree validation reuse is allowed only when every relevant validity input is unchanged and integrity-bound. If the merged tree differs from the FULL-validated tree, merged state is validated normally.

## Repository-control truthfulness

At adoption baseline `b1921cb6c744e68f9d2ee8d9c83f5c44bbede4c2`, GitHub reported `main` as `protected: false` and branch-protection enforcement disabled.

Therefore this adoption makes **no claim that `main` is remotely protected**. Desired provider-side protection remains required by Marketplace governance, but actual enforcement requires an authorized GitHub administrative control plane and independent verification.

Repository policy files, CODEOWNERS, PR templates, CI, exact-head merge discipline, and post-merge provenance checks are compensating/review controls; they are not branch protection.

## Retention, isolation, supply chain, and cryptography

The 10-second post-use `EPHEMERAL` default remains unchanged. Metadata-only longer retention must contain no project payload or secrets. Durable repository artifacts remain durable only by explicit intent. Deletion failure remains a security/privacy event.

Cross-project access remains denied by default. This adoption does not authorize copying `ai-automation-department` project data, credentials, runtime state, or repository configuration into Marketplace.

Dependencies remain executable trust relationships. New dependencies require concrete need and supply-chain review. Unreviewed remote scripts are not piped to shell.

Marketplace continues to prohibit custom cryptographic algorithms/protocols, requires maintained standard implementations, accurate transport-security claims, TLS certificate/hostname verification, authenticated encryption where required by the threat model, key-purpose separation, and production-key isolation from ordinary PR jobs/artifacts. Encryption does not extend retention or authorization.

The stricter v1.5 project-approved cryptographic profile is explicitly retained under v1.6 compression:

- Prefer TLS 1.3 for new trust boundaries; older compatibility requires an explicit reason.
- Privileged or non-idempotent operations MUST NOT use TLS 0-RTT.
- When durable sensitive project data requires confidentiality beyond access control, use maintained authenticated encryption such as AES-256-GCM or XChaCha20-Poly1305 as appropriate to the platform and threat model.
- Passwords are normally hashed, not reversibly encrypted; prefer Argon2id with a current reviewed parameter baseline, with another standard construction only under an explicitly approved compatibility profile.
- Signing, encryption, HMAC, token, and password purposes MUST NOT silently share one key.

These retained profile requirements are engineering constraints, not claims that Marketplace currently deploys or activates any such transport, storage, key, or password runtime.

## Historical record

`docs/POLICY_V1_5_ADOPTION.md` and `docs/POLICY_V1_4_ADOPTION.md` remain durable historical provenance. New engineering work should cite this v1.6 adoption record and `DEVELOPMENT_POLICY.md`.

This adoption intentionally takes the faster-safe-delivery method while refusing to import another repository's paths, check names, data, credentials, permissions, administrative state, or runtime authority.