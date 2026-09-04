# Marketplace Development Policy

**Status:** Project engineering policy
**Applies to:** repository development, coding agents, maintainers, CI, conformance tooling, runtime/application code, adapters, deployment work, and project governance
**Policy basis:** portable Marketplace projection of Coding Agent Constitution v1.3, Coding Agent Policy v1.3, Repository Governance v1.2 input, and Coding Agent Development Principles v1.6
**Source SHA-256 (Constitution v1.3):** `c76d3f9b921abdf750f338c73303b0cd1cb31fd998142f635a1a971925f12b5c`
**Source SHA-256 (Policy v1.3):** `0cba8b4f68c570f2830720b2c1285ea132ab563978fa3ad2c22e152ac76379ca`
**Source SHA-256 (Governance v1.2 input):** `ec221545c8a7a5e203bf081238faf8b8d0e151087a3c20011255b8bc74ee4859`
**Source SHA-256 (Development Principles v1.6):** `12314b7fc9a4cbb5e93d907ed5c613f29c4895f610356285cc88da52898bcb76`
**Adoption record:** `docs/POLICY_V1_6_ADOPTION.md`
**Semantic authority:** `PRINCIPLES.md` remains authoritative for Marketplace protocol/semantic constraints

This policy governs **how Marketplace is developed**. It does not redefine Marketplace protocol semantics and MUST NOT weaken `PRINCIPLES.md`, the numbered Marketplace specifications, or applicable Open Layer Protocol requirements.

Repository-specific controls from another project are not imported as facts. The supplied Repository Governance v1.2 profile is for `ai-automation-department`; its repository name, workflow/check names, package/source paths, and provider-admin state are source input only unless Marketplace explicitly adopts an equivalent local rule.

The Marketplace engineering-policy stack is:

```text
1. applicable law / contractual obligation / authorized incident hold
2. Coding Agent Constitution v1.3 as adopted by docs/POLICY_V1_6_ADOPTION.md
3. portable Coding Agent Policy v1.3 requirements projected here
4. docs/REPOSITORY_GOVERNANCE.md for Marketplace repository controls
5. this DEVELOPMENT_POLICY.md Marketplace projection of Development Principles v1.6
6. project-specific conventions and implementation details
```

A lower layer may be stricter but MUST NOT silently weaken a higher layer. Compression in v1.6 does not silently remove a previously adopted v1.5 safety/security/privacy/retention/isolation/authorization/provenance/cryptographic/governance obligation; where this projection is ambiguous, use the stricter higher-precedence or previously adopted interpretation until resolved.

## 1. SAFETY FIRST

**SAFETY FIRST is the highest-priority engineering rule.**

Use this precedence when goals conflict:

```text
safety / security / privacy / legal obligations
-> correctness and data integrity
-> reliability and recoverability
-> maintainability and testability
-> performance and convenience
```

A material control MUST NOT be weakened merely to make tests pass, silence errors, preserve unsafe compatibility, simplify implementation, reduce CI time, improve benchmarks, or ship faster.

Known material security, privacy, project-isolation, unauthorized-retention, governance, or required-cryptographic defects block completion unless an explicit authorized, scoped, owned, expiring exception applies.

## 2. Marketplace semantic and project boundaries

Marketplace preserves two independent boundary sets:

1. Marketplace semantic constraints in `PRINCIPLES.md` and numbered specifications; and
2. engineering safety/capability/retention/governance constraints in this policy stack.

Project-scoped files, credentials, messages, prompts/responses, logs, caches, memories/context, indexes, tool state, derived data, generated artifacts, benchmark/profile data, temporary staging, and runtime processes MUST NOT cross into another project by default.

An authorized cross-project flow must specify source, destination, purpose, minimum necessary data, capabilities, retention, access controls, and auditability; the stricter applicable policy wins.

OLP is a protocol dependency and evidence substrate, not permission to import unrelated OLP project data, credentials, agent context, or runtime authority.

## 3. Security invariants

These invariants apply during success, failure, retry, restart, merge, deployment, rollback, and recovery:

1. Unauthorized input cannot trigger a protected side effect.
2. Secrets do not enter source, logs, messages, telemetry, crash output, screenshots, diagnostics, vectors, fixtures, benchmarks, caches, or ordinary provenance records.
3. Transient project content does not outlive its retention deadline without an explicit authorized exception/hold.
4. Untrusted input cannot directly become executable code, shell commands, queries, paths, templates, network destinations, or privileged targets without safe construction and validation.
5. TLS certificate and hostname verification are not disabled for convenience.
6. Privileged/destructive targets are re-verified immediately before execution.
7. Security failures do not silently fail open.
8. Dependencies do not gain trust merely because they are convenient.
9. Green tests do not override a known material security defect.
10. Deletion, encryption, isolation, authorization, CI, branch-protection, provenance, reproducible-build, or performance guarantees are never claimed without evidence appropriate to the claim.
11. Content-bearing logs do not silently inherit metadata-only long retention.
12. Repository policy files do not prove provider-side branch/ruleset enforcement.
13. Fast paths, caching, batching, concurrency, evidence reuse, or CI acceleration do not bypass required authorization, validation, isolation, retention, provenance, or security controls.
14. Required quality/security/integration/governance/conformance gates are not renamed, removed, skipped, bypassed, weakened, or silently narrowed merely for speed.
15. A reproducible-build claim requires an independently repeated build with matching declared inputs and artifact integrity; source pinning/provenance alone is not reproducibility proof.

Encode these invariants as tests, guards, types, validators, architecture constraints, or review controls where practical.

## 4. Capability model and least privilege

Standard capabilities are:

```text
READ_PROJECT
WRITE_PROJECT
EXECUTE_LOCAL
NETWORK_EXTERNAL
INSTALL_DEPENDENCY
DEPLOY
DELETE
MANAGE_SECRETS
ADMIN
```

Default is deny-by-default. For each work unit, identify the minimum capabilities and scope them to the exact repository/environment/branch/path/resource/account.

Read, write, execute, external network, dependency install, deploy, delete, secret management, and administration are separate authorities. `ADMIN` MUST NOT be inferred from ordinary repository write access.

## 5. Risk classification

Meaningful mutations are classified honestly:

- **LOW** — read-only inspection or narrow docs/test work without security effect.
- **MODERATE** — dependencies, external reads, broad refactors, non-production config, performance-sensitive implementation, or security/governance documentation changes.
- **HIGH** — deployment, deletion, schema migration, credentials, or privileged external side effects.
- **CRITICAL** — destructive production operations, protected/main force-push, disabling material controls, irreversible infrastructure changes, broad credential revocation/rotation, or high-risk retention exceptions.

Mixed-risk work uses the highest included risk. Risk MUST NOT be classified downward to avoid safeguards.

HIGH requires explicit authorization, immediate exact-target verification, blast-radius assessment, rollback/recovery consideration, and relevant security validation. CRITICAL adds dry-run/reversible-alternative review, independent human review where supported, and explicit post-action verification.

## 6. Destructive and protected side effects

Before destructive, irreversible, privileged, or difficult-to-recover action:

```text
resolve exact target
-> re-read/re-resolve immediately before action
-> verify exact authorization
-> assess blast radius
-> prefer reversible/dry-run alternative
-> define rollback/recovery
-> minimize scope
-> execute only while preconditions remain true
-> verify result
-> report precisely what changed
```

Authorization/capability checks occur before protected side effects. Object-level authorization verifies the exact target resource.

M11 remains authoritative for Marketplace protected-operation authorization semantics. Proposal/planning records, merged source, or a green CI result are not execution authority.

## 7. Retention, privacy, isolation, and observability

Every project-scoped file, log, message, prompt/response, tool payload/result, cache, trace, telemetry item, temporary row, queue payload, extracted text, benchmark/profile sample, and intermediary artifact has a retention class defined by `docs/RETENTION_POLICY.md`.

### EPHEMERAL

Default maximum post-use retention: **10 seconds**. Active legitimate use may refresh the post-use window. Automatic expiry/deletion is preferred over operator memory.

### OPERATIONAL_METADATA

Default project profile: 30 days only when intentionally classified and genuinely content-free. Message/file/prompt/response bodies, secrets, raw media, equivalent payload content, and content-bearing diagnostics are prohibited from this class.

### DURABLE_PROJECT_ARTIFACT

Reviewed source, specifications, principles, tests, accepted conformance vectors, approved documentation/configuration, ADRs, and reviewed release/build evidence may be durable by explicit intent. Persistence by accident is not classification.

### SECURITY_INCIDENT_HOLD

Narrow, owned, access-controlled, justified, and expiring/removable. Preserve only minimum required evidence.

Deletion failure is a security/privacy event. Encryption does not extend retention authority.

Logs SHOULD use static event names and metadata-only fields. Content-bearing logs/traces remain EPHEMERAL. Correlation IDs are traceability, not authorization.

## 8. Dependencies, transport security, cryptography, and keys

A dependency, benchmark/profiling tool, native extension, or build accelerator is executable trust. Admission requires concrete need and review of maintenance, provenance/publisher trust, transitive footprint, known vulnerabilities, permissions/install behavior, license/policy fit, portability, and safer alternatives.

Prefer official registries and reproducible resolution where supported. Do not pipe unreviewed remote installation scripts directly to shell. Remove unused dependencies.

Custom cryptographic algorithms, signatures, password hashing, key exchange, or protocol designs are prohibited. Use maintained standard implementations and current project-approved profiles.

Cross-trust-boundary traffic carrying non-public project data uses authenticated encrypted transport; TLS certificate and hostname verification remain enabled. Sensitive durable data receives authenticated encryption when the threat model requires confidentiality beyond access control.

Keys are generated with secure randomness, purpose-separated, versioned where applicable, separated from ciphertext, least-privilege scoped, and stored in an appropriate managed key store/HSM/vault/OS secure store where available. Production private/master key material does not enter ordinary PR jobs or repository artifacts.

Passwords are normally hashed using an approved password-hashing construction rather than reversibly encrypted.

Transport/crypto claims must match verified implementation and deployment state. Encryption never expands authorization, retention, or project boundaries.

## 9. Architecture and input/resource safety

Prefer dependency direction:

```text
External Adapter
-> Application Boundary
-> Application / Domain Logic
-> Ports / Interfaces
-> Infrastructure Implementations
```

Framework, transport, storage, cloud, observability, identity-provider, and secret-store details belong at replaceable edges.

Validate security-sensitive input for type, syntax, length/range, identifiers, allowlists, paths/roots, URLs/hosts, encoding, ownership, content type, project identity, retention overrides, and network destinations as applicable.

Use parameterized queries/safe builders, subprocess argument arrays rather than shell interpolation, path traversal defenses, SSRF defenses for user-controlled destinations, safe deserialization, bounded parsing, explicit timeouts, resource quotas, queue limits, bounded concurrency, backpressure, and admission control.

Never let user input create unbounded tasks, subprocesses, retries, queues, file processing, requests, memory use, or output.

## 10. Testing, conformance, and CI lanes

Unit tests should be fast, deterministic, offline, isolated, and repeatable. Use contract/integration/security/retention/governance/end-to-end/live/performance tiers deliberately.

Every reproducible bug fix gets a regression test where practical. Security defects get negative/security regression tests where safely reproducible.

Marketplace semantic acceptance remains:

```text
python tools/conformance_gate.py --olp-root <path-to-pinned-olp-checkout>
```

Marketplace recognizes three validation lanes:

- **FAST** — intermediate deterministic feedback only when a tested impact map proves a smaller lane is sufficient; unknown relevance falls back to FULL.
- **FULL** — final ready-for-review head; security/policy/governance-sensitive paths; dependency/lockfile changes; HIGH/CRITICAL risk; ambiguous impact.
- **RELEASE** — FULL plus applicable packaging/distribution/provenance/release/live acceptance.

The current `.github/workflows/conformance.yml` is deliberately conservative and runs the full acceptance path on pull requests and `main`. This remains compliant; v1.6 adoption does not require immediate lane refactoring.

Run the cheapest high-signal checks first, then broader impacted checks, then FULL once on the final review head when required. Independent deterministic checks may run concurrently when resource-safe.

A successful validation result may be reused only when all relevant validity inputs remain unchanged and integrity-bound: source/tree, dependency lock/toolchain, relevant config, policy/governance version, test/build definition, environment class where material, and artifact digest where material. If validity cannot be proven, rerun.

Superseded non-deployment runs may be cancelled where supported. For a plausibly transient failure with unchanged source, rerun only failed jobs where practical and bounded; repeated identical failure requires root-cause investigation.

## 11. v1.6 FAST EXECUTION KERNEL

### 11.1 Work Unit Contract

At the start of meaningful work, establish once:

```text
project / repository
goal
exact current base/head/target where material
behavior_to_change
behavior_to_preserve
risk
minimum_capabilities
mutation_boundary
authorization_state
validation_lane
rollback_or_recovery
stop_conditions
```

Do not repeatedly rediscover unchanged contract facts. Re-resolve volatile facts or facts required immediately before a protected action.

### 11.2 Evidence Ledger

Maintain a compact internal ledger:

```text
VERIFIED
DECIDED
CHANGED
VALIDATED
WAITING
BLOCKED
NEXT
```

Reuse a verified fact until an invalidation input changes, such as source/tree, target/environment, dependency lock, toolchain, policy/governance, credential/session identity, relevant runtime state, time-sensitive remote state, or authorization scope.

### 11.3 Minimum authoritative reads and safe batching

Inspect the smallest authoritative surface sufficient for the work: target implementation, direct interfaces/callers, relevant tests, relevant config/composition, and relevant policy/security/retention boundary. Expand only when evidence shows broader impact.

Batch or parallelize independent read-only operations and deterministic validations when tools and resource limits permit.

### 11.4 Plan once and patch coherently

Before first mutation, define files/components, intended behavior, preserved behavior, risk, validation, and rollback. Then execute within the authorized scope without repeatedly requesting the same unchanged authorization.

Prefer:

```text
inspect
-> coherent patch
-> diff review
-> focused validation
-> fix
-> FULL once on final candidate when required
```

Use small reversible commits/checkpoints without multiplying PR/CI boundaries unnecessarily.

### 11.5 Delta-first validation and evidence reuse

Prefer syntax/compile, changed-file lint/type checks, focused unit/contract/security tests, broader impacted tests, then FULL. Do not rerun an unchanged expensive check merely for ceremony when exact-input validity is proven.

### 11.6 Keep moving while CI runs

While remote CI runs, continue independent safe work that does not mutate the tested head or invalidate its evidence: diff review, docs/release notes, governance/review checks, rollback/acceptance preparation, or analysis of a separate non-overlapping future unit.

### 11.7 Stop conditions

Stop mutation and reassess when:

- authorized exact head/target changed;
- a security invariant cannot be demonstrated;
- a required gate fails materially;
- risk is higher than authorized;
- project boundary becomes ambiguous;
- secret exposure is suspected;
- rollback/recovery assumptions are false;
- a destructive target cannot be re-verified;
- a required provider-side control is absent and no applicable exception/compensating procedure exists;
- runtime health materially degrades; or
- thermal/resource safety thresholds are exceeded.

A stop condition is a decision boundary, not a reason to loop indefinitely on the same failed action.

### 11.8 Concise status

Report meaningful progress, authorization needs, blockers, material failures, risk/scope changes, and completion. Do not narrate every low-value tool call. Preferred status keys are `DONE`, `EVIDENCE`, `BLOCKER`, `NEXT`, and `AUTH NEEDED` when relevant.

## 12. Bounded authorization reuse and preauthorized rollback

Marketplace adopts **bounded authorization reuse** inside one work unit while all relevant authorization inputs remain unchanged:

```text
project
target/resource
exact head/version where specified
scope
risk class
capability class
side-effect class
rollback/recovery assumptions
expiry/exception state
```

A safe read-only verification, deterministic test rerun, conversation continuation, or non-mutating diagnostic does not by itself require repeated approval.

A material target/head/resource change, scope expansion, risk increase, new privileged/destructive capability, changed rollback assumptions, or expired/closed exception requires renewed authority as applicable.

This does not weaken exact-head governance: if an authorization specifies an exact head SHA, head movement makes that authorization stale.

Privileged/destructive exact targets are still re-verified immediately before execution.

When the user authorizes a mutation together with an exact rollback condition and method, that **preauthorized rollback** may execute without a second approval if the condition becomes true, provided the rollback remains within the exact target/method. Verify restored state, report the trigger/result, and do not silently retry the failed mutation indefinitely.

## 13. Repository governance and truthfulness

Repository controls are defined in `docs/REPOSITORY_GOVERNANCE.md`.

`.github/CODEOWNERS`, PR templates, CI, repository audits, exact-head merge discipline, and source policy are governance-as-code. They do not prove remote GitHub branch protection/rulesets are active.

Desired provider configuration and verified provider state are separate facts. At the v1.6 adoption baseline, GitHub reported `main` unprotected; do not claim otherwise until an authorized admin control plane configures and independently verifies the required rule.

Policy/security/governance changes require FULL validation and security-sensitive review. CI/performance pressure does not authorize governance bypass.

## 14. Optimization and performance discipline

Material claims such as faster/lighter/higher-throughput require evidence. Default optimization order:

```text
do less work
-> remove duplicate work
-> improve algorithm/data access
-> reduce parsing/copying/serialization/data movement
-> reduce round trips
-> batch/coalesce safely
-> cache with explicit bounds/invalidation/retention
-> reuse initialized resources safely
-> precompute stable immutable work
-> add bounded concurrency/backpressure
-> reduce allocation/memory pressure
-> specialized/native acceleration only when justified
```

Optimization loop:

```text
measure -> identify bottleneck -> hypothesize -> smallest safe change
-> equivalent measurement -> verify invariants/resources -> KEEP | REVISE | REVERT
```

A material cache defines purpose, key semantics, owner/source of truth, maximum size, lifetime, retention class, invalidation/revalidation, eviction, trust/integrity assumptions, concurrency, failure behavior, and observability.

A cache is not authorization. A fast path must preserve authn/authz/capability/object checks, required validation, retention/deletion, project isolation, provenance, revocation/policy freshness, and destructive-target re-verification.

Do not cherry-pick favorable benchmark runs, compare non-equivalent workloads without disclosure, or call gate reduction an optimization.

## 15. Exceptions

Security, retention, isolation, capability, or repository-governance exceptions record:

```text
owner
reason
scope
risk
approved_by
compensating_controls
issued_at
expires_at
removal_condition
```

Exceptions are narrow, explicit, reviewable, removable, and expiring. They waive only what they explicitly name and cannot silently extend themselves. Close them immediately when the removal condition is satisfied and verify normal controls are restored.

## 16. Merge authorization, runtime activation, and deployment

**Merge authorization**, **runtime activation**, configuration/service mutation, dependency installation, and deployment are separate authorities by default.

Before merge:

```text
verify repository / PR / base
verify exact authorized head where applicable
verify required CI on that head/tree
verify approvals or active documented exception/procedure
verify mergeability and risk
merge with exact-head guard where supported
```

After merge, verify merged PR state, new `main` tip, parent/provenance relationship, signature/provenance where required, and merged-main CI or an explicitly allowed exact-tree reuse path. Close temporary governance exceptions.

Do not deploy or activate merely because merge succeeded.

Runtime activation is a separate work unit when it changes deployed code, environment, configuration, service state, hardware state, external authority, or user-visible production behavior. Before activation identify exact release/head, current known-good state, rollback, dependencies/health, and authorization. After activation verify service/process identity, health, bounded acceptance, rollback/fallback where relevant, and resource safety.

## 17. Completion standard

A change is complete only when applicable safety, semantic, policy/governance, tests, security/privacy, retention, capability, project-isolation, provenance, dependency, cryptographic, resource-bound, documentation, and merge/runtime-boundary requirements are satisfied.

Prefer the smallest **safe, clear, verifiable, recoverable, and fast-to-deliver** solution that expresses business intent, preserves architecture and project boundaries, minimizes privilege and retained data, controls side effects, validates trust boundaries, uses reviewed dependencies, keeps exceptions expiring, measures material performance, reuses valid evidence instead of repeating ceremony, and keeps merge/runtime/deployment authority explicit.