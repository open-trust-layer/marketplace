# Marketplace Development Policy

**Status:** Project engineering policy
**Applies to:** repository development, coding agents, maintainers, CI, conformance tooling, future runtime code, adapters, deployment work, and project governance
**Policy basis:** portable Marketplace projection of Coding Agent Constitution v1.2, Coding Agent Policy v1.2, Repository Governance v1.1, and Coding Agent Development Principles v1.5
**Source SHA-256 (Constitution v1.2):** `50f6c00a195fd7cc2d02878d9dd2e9640299db71c42d097ffd60a309ac96cd94`
**Source SHA-256 (Policy v1.2):** `b25dbc67897240e2a20a43982578ad253a547dc7050a2c00b637bcbbd19c41a5`
**Source SHA-256 (Governance v1.1 input):** `97c5826e24a70de5c47ff8cf469c0c936bc1b8976d77f05bd3080fd580c3c9ba`
**Source SHA-256 (Handbook v1.5):** `97ba608c1c29a1c630469b5f877efcdf8c47d403ff332abc0a6236410e0996d9`
**Adoption record:** `docs/POLICY_V1_5_ADOPTION.md`
**Semantic authority:** `PRINCIPLES.md` remains authoritative for Marketplace protocol/semantic constraints

This policy governs **how Marketplace is developed**. It does not redefine Marketplace protocol semantics and MUST NOT weaken `PRINCIPLES.md`, the numbered Marketplace specifications, or applicable Open Layer Protocol requirements.

Repository-specific controls from another project are not imported as facts. Source-handbook statements specific to `ai-automation-department` are treated as source examples/history unless Marketplace explicitly adopts an equivalent rule here.

The Marketplace engineering-policy stack is:

```text
1. applicable law / contractual obligation / authorized incident hold
2. Coding Agent Constitution v1.2 as adopted by docs/POLICY_V1_5_ADOPTION.md
3. portable Coding Agent Policy v1.2 requirements adopted into this Marketplace policy
4. docs/REPOSITORY_GOVERNANCE.md for Marketplace repository controls
5. this DEVELOPMENT_POLICY.md Marketplace projection of the v1.5 handbook
6. project-specific conventions and implementation details
```

A lower layer may be stricter but MUST NOT silently weaken a higher layer. `PRINCIPLES.md` and the numbered Marketplace specifications remain authoritative for Marketplace semantic constraints; the engineering-policy stack governs how those semantics are implemented and changed.

## 1. SAFETY FIRST

**SAFETY FIRST is the highest-priority engineering rule.**

Use this precedence when engineering goals conflict:

```text
safety / security / privacy / legal obligations
-> correctness and data integrity
-> reliability and recoverability
-> maintainability and testability
-> performance and convenience
```

A material security control MUST NOT be weakened merely to make a test pass, silence an error, preserve unsafe compatibility, simplify implementation, ship faster, or make a benchmark/CI result look better.

Known material security, privacy, project-isolation, unauthorized-retention, or governance defects prevent a change from being declared complete unless an explicit authorized, scoped, owned, expiring exception exists.

## 2. Project and semantic boundaries

Marketplace development MUST preserve two independent boundary sets:

1. **Marketplace semantic boundaries** in `PRINCIPLES.md` and the specifications; and
2. **engineering safety boundaries** in this policy.

Project-scoped files, credentials, messages, prompts/responses, logs, caches, tool state, indexes, benchmark/profile data, derived data, generated artifacts, and retained context MUST NOT cross into another project by default.

An authorized cross-project flow MUST identify source, destination, purpose, minimum necessary data, required capabilities, retention, and access controls.

## 3. Security invariants

The following invariants apply to current tooling and future runtime code:

1. Unauthorized input cannot trigger protected side effects.
2. Secrets do not enter source control, logs, messages, telemetry, crash output, screenshots, diagnostics, vectors, test fixtures, benchmark inputs, or profile output.
3. Ephemeral project content does not outlive its retention deadline without an authorized exception or hold.
4. Untrusted input cannot directly become executable code, shell commands, queries, paths, templates, or network destinations without safe construction and validation.
5. TLS certificate and hostname verification are not disabled for convenience or performance.
6. Privileged or destructive targets are re-verified immediately before execution.
7. Security failures fail closed where authorization or protected side effects are involved.
8. Dependencies do not gain trust merely because they are convenient or fast.
9. Green tests do not override a known material security defect.
10. Deletion, encryption, isolation, authorization, CI, branch-protection, reproducibility, or performance guarantees are never claimed without appropriate verification. A reproducible-build claim specifically requires an independently repeated build with matching declared inputs and artifact integrity; one successful or source-pinned build is only provenance/integrity evidence.
11. Content-bearing logs do not silently inherit metadata-only long retention.
12. Repository policy files do not prove provider-side branch/ruleset enforcement.
13. Optimization, caching, precomputation, batching, concurrency, or fast paths do not bypass authentication, authorization, capability checks, validation, project isolation, provenance, retention, or destructive-target re-verification.
14. Required quality/security/integration/governance/conformance gates are not renamed, removed, skipped, bypassed, weakened, or short-circuited merely to reduce CI duration.

Where practical, invariants SHOULD be encoded as tests, guards, types, validators, architecture constraints, or controlled regression checks.

## 4. Capability model and least privilege

Standard engineering capabilities are:

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

The default is deny-by-default. Each task MUST identify the minimum capabilities required and scope them to the correct repository, branch, path, environment, resource, and account.

`ADMIN` MUST NOT be inferred from ordinary repository write access. Read, write, execute, network, install, deploy, delete, secret-management, and administration are distinct authorities.

## 5. Risk classification

Meaningful mutations MUST be classified honestly:

- **LOW** — read-only inspection; documentation/test work with no security effect.
- **MODERATE** — dependency changes, external network reads, broad refactors, non-production configuration, performance-sensitive implementation, or security/governance documentation changes.
- **HIGH** — deployments, data deletion, schema migration, credential changes, or privileged external side effects.
- **CRITICAL** — destructive production operations, protected-branch force push, disabling material security controls, irreversible infrastructure changes, broad credential revocation/rotation, or high-risk retention exceptions.

HIGH and CRITICAL work requires exact-target verification, blast-radius analysis, recovery/rollback planning where possible, and explicit authorization. CRITICAL work additionally requires dry-run/reversible-alternative review and independent review where supported.

Risk MUST NOT be classified downward to bypass safeguards.

## 6. Destructive-action protocol

Before destructive, irreversible, or difficult-to-recover actions:

1. identify the exact target;
2. re-read or re-resolve it immediately before execution;
3. verify authority for that exact target;
4. assess blast radius;
5. prefer dry-run or reversible alternatives;
6. define rollback/recovery where possible;
7. minimize scope;
8. execute only while preconditions remain true;
9. verify the actual result; and
10. report precisely what changed.

Stale assumptions about branch, path, repository, account, environment, database, or resource identity are insufficient.

## 7. Architecture and side-effect boundaries

Marketplace code SHOULD preserve this dependency direction:

```text
External Adapter
      ↓
Application Boundary
      ↓
Application / Domain Logic
      ↓
Ports / Interfaces
      ↓
Infrastructure Implementations
```

Framework, transport, storage, cloud, queue, observability, identity-provider, and secret-store details belong at replaceable edges.

Protected side effects MUST follow this ordering wherever applicable:

```text
parse
-> identify/authenticate
-> authorize/capability-check
-> validate/canonicalize
-> classify risk
-> execute
-> verify/report
-> audit/provenance
-> retain/delete
```

M11 remains authoritative for Marketplace protected-operation authorization semantics. M14 deployment readiness and M16 workflow proposals MUST NOT be treated as execution authority.

## 8. Untrusted input and resource safety

External and repository-derived inputs MUST be treated as untrusted until validated at the appropriate boundary.

Use bounded collection sizes, explicit timeouts, concurrency limits, quotas, queue limits, safe path handling, parameterized queries/builders, subprocess argument arrays instead of shell interpolation, SSRF defenses for user-controlled URLs, and non-code-executing deserializers.

Do not add arbitrary shell, filesystem, network, package-installation, deployment, secret, administrative, or concurrency flexibility merely because it is easy to expose.

When producers can outrun consumers, use bounded queues, backpressure, admission control, or explicit shedding rather than unbounded buffering.

## 9. Secrets and dependencies

Secrets MUST NOT be hard-coded or printed to prove they exist. Prefer scoped short-lived credentials and managed secret injection.

A new dependency, benchmark tool, profiler, native extension, or build accelerator is executable trust. Admission requires a concrete need and review of maintenance, provenance/publisher, transitive footprint, vulnerabilities, permissions/install scripts, license/policy fit, portability, and safer alternatives. Reproducible resolution and official registries are preferred.

Unreviewed remote scripts MUST NOT be piped directly to a shell.

### 9.1 Cryptography, transport, and key separation

Custom cryptographic algorithms, password hashing, signatures, key exchange, or encryption protocols are prohibited. Use maintained, reviewed implementations and current standards.

Cross-trust-boundary traffic carrying non-public project data MUST use authenticated encrypted transport. TLS certificate and hostname verification MUST remain enabled. Prefer TLS 1.3 for new boundaries; older compatibility requires an explicit reason. Privileged or non-idempotent operations MUST NOT use TLS 0-RTT.

When durable sensitive project data requires confidentiality beyond access control, use maintained authenticated encryption such as AES-256-GCM or XChaCha20-Poly1305 as appropriate to the platform and threat model. Keys MUST be generated with cryptographically secure randomness, kept separate from ciphertext, scoped to minimum use, versioned, and stored through an appropriate managed KMS/HSM/vault/OS secure store where available. Signing, encryption, HMAC, token, and password purposes MUST NOT silently share one key.

Passwords are normally hashed, not reversibly encrypted. Prefer Argon2id with a current reviewed parameter baseline; use an explicitly approved compatibility profile when platform/compliance constraints require another standard construction.

Encryption does not extend retention, authorization, or project boundaries. Encrypted EPHEMERAL content still expires under the normal post-use deadline, and production private keys MUST NOT enter PR jobs or ordinary repository artifacts.

## 10. Retention and data minimization

Every project-scoped file, message, prompt/response, tool payload/result, cache, trace, telemetry item, benchmark/profile sample, temporary artifact, and log MUST have a retention class defined by `docs/RETENTION_POLICY.md`.

The default maximum post-use retention for `EPHEMERAL` content is **10 seconds**.

Durable repository source, specifications, tests, approved documentation, reviewed configuration, accepted conformance artifacts, and approved aggregate benchmark evidence are `DURABLE_PROJECT_ARTIFACT` by intent. Persistence by accident does not make content durable.

Benchmark/profile evidence MUST NOT become a reason to retain sensitive project payloads longer than their authorized class. Prefer aggregate metadata over raw content.

Current Marketplace is primarily a specification/conformance/runtime-source repository and does not authorize production content persistence merely because runtime code exists. Future content-bearing runtime/deployment milestones MUST implement and verify applicable automatic retention/expiry behavior before durable operation is accepted.

## 11. Logging, diagnostics, provenance, and metrics

Logs SHOULD be structured and metadata-only by default. Message/file/prompt/response bodies, raw media, secrets, and equivalent project payloads MUST NOT be placed into long-lived operational logs.

Useful audit metadata includes correlation ID, operation, pseudonymous actor/target identity where appropriate, authorization result, high-level outcome, error type, duration, retention class, and deletion/expiry result.

Diagnostics MUST distinguish fact, inference, confidence, and unknown conditions and MUST NOT overclaim.

Security-sensitive build/release artifacts SHOULD use checksums, signatures, attestations, or equivalent provenance where supported.

Performance metrics SHOULD derive from an explicit component/service objective. Metric labels MUST remain low-cardinality and MUST NOT contain sensitive project content. Observability overhead on critical paths SHOULD be measured and bounded where material, but required safety/audit visibility MUST NOT be removed merely for speed.

## 12. Testing and acceptance

Unit tests SHOULD be deterministic, offline, isolated, and repeatable. External behavior belongs in deliberate integration/contract/end-to-end tiers.

Every bug fix requires a regression test where safely reproducible. Security defects require negative/security regressions where appropriate.

Marketplace retains its existing semantic acceptance authority:

```text
python tools/conformance_gate.py --olp-root <path-to-pinned-olp-checkout>
```

A semantic increment is not complete unless all applicable registered conformance vectors remain green and deterministic generator replay succeeds.

Green functional tests are necessary but not sufficient: they do not override known material security defects and they do not, by themselves, prove an optimization claim.

## 13. Evidence-driven optimization

Optimization is governed by the same safety, correctness, privacy, retention, project-isolation, provenance, authorization, and recoverability requirements as any other change.

For a material performance-sensitive change, when safe and practical:

1. identify the user/business/operational problem and the relevant critical path;
2. define the target metric and explicit success condition or budget;
3. establish a representative baseline;
4. profile or otherwise identify the demonstrated bottleneck;
5. state a concrete optimization hypothesis;
6. make the smallest safe change;
7. repeat equivalent measurements;
8. inspect correctness, security, tail latency, throughput/saturation, CPU, memory/allocation, I/O, queueing, external-service usage, and failure behavior where relevant;
9. verify all required invariants and gates; and
10. record `KEEP`, `REVISE`, or `REVERT` based on evidence.

Use this governing sequence:

```text
measure -> identify -> hypothesize -> change -> measure again -> verify invariants -> KEEP | REVISE | REVERT
```

Do not claim `faster`, `lighter`, `more efficient`, `higher throughput`, or equivalent material improvements from intuition alone when measurement is practical.

Baseline and candidate measurements MUST represent equivalent workloads/environments for the claim being made, or the limitation MUST be stated explicitly. A single favorable run is not sufficient evidence for a durable material claim.

Latency-sensitive paths SHOULD consider distribution/percentiles and saturation rather than averages alone.

## 14. Optimization priority and resource design

Prefer optimization in roughly this order:

```text
1. remove unnecessary work
2. remove duplicate work
3. improve algorithm/data structure/data access
4. reduce copying/parsing/serialization/data movement
5. reduce unnecessary filesystem/database/network round trips
6. batch/coalesce compatible work with explicit bounds
7. cache safe reusable results with explicit invalidation and retention
8. reuse expensive initialized resources safely
9. precompute stable immutable work
10. add bounded concurrency/parallelism with backpressure
11. reduce allocation/object churn and memory pressure
12. apply runtime/interpreter/compiler-specific optimization
13. add native/specialized acceleration only when evidence justifies its extra risk and maintenance cost
```

The absence of a measurable or operationally justified problem is normally a reason to preserve simpler code.

### 14.1 Caching and reusable state

Caching is a performance mechanism, not a trust mechanism. A material cache/reusable-state design SHOULD define, as applicable:

```text
purpose
key semantics
owner
source of truth
maximum size
entry lifetime
retention class
invalidation/revalidation rule
eviction behavior
integrity/provenance assumptions
project/tenant isolation
concurrency behavior
failure behavior
observability
```

Security-sensitive cached decisions require explicit freshness/invalidation. Cache misses remain a correct supported path. Cache poisoning and cross-project cache collisions are security defects. Secrets and sensitive raw content MUST NOT appear in ordinary cache keys, logs, or metric labels.

Restored CI/build caches and generated artifacts are untrusted inputs unless integrity/provenance is independently established to the degree required by their use.

### 14.2 Batching, coalescing, and duplicate suppression

Batching/coalescing MUST bound maximum batch size, maximum wait time, memory use, queue depth, retry/cancellation behavior, and partial-failure semantics. Do not batch operations whose authorization, project boundary, confidentiality, transactionality, or failure semantics require separation.

### 14.3 Concurrency and backpressure

Concurrency MUST have a demonstrated reason. Bound active tasks, workers, queues, connections, subprocesses, requests, open files, memory, retries, and per-user/project work where relevant.

Higher concurrency that reduces one latency metric while increasing saturation, instability, attack surface, unfairness, or resource exhaustion is not automatically an improvement.

### 14.4 Memory, allocation, and I/O efficiency

Look for accidental retention, duplicate materialization, whole-file/whole-response buffering where bounded streaming is appropriate, repeated serialization/parsing, object churn, oversized caches, queue accumulation, and resource leaks.

Prefer bounded buffers, streaming/iterators, compact structures, and explicit lifecycle when they preserve clarity and correctness. Sensitive content MUST NOT be retained longer merely to avoid recomputation without explicit retention authority.

Fewer milliseconds never justify weaker TLS, SSRF/egress restrictions, destination validation, authorization, timeouts, size limits, retry bounds, or retention/deletion controls.

## 15. Performance budgets, benchmarks, and regression control

Important components MAY define project-specific performance/resource budgets when useful. A budget SHOULD state workload/scope, environment assumptions, metric/percentile, target and hard limit where appropriate, measurement method, owner, and review trigger.

Illustrative values from external handbooks are not Marketplace defaults. Marketplace budgets become policy only when explicitly adopted for a specific path.

A significant optimization evidence record SHOULD include:

```text
problem
critical_path
baseline
metric
budget / success_condition
profiling_or_bottleneck_evidence
hypothesis
change
candidate_measurement
resource_effects
correctness/security/retention verification
variance / limitations
result: KEEP | REVISE | REVERT
```

A benchmark record SHOULD identify enough context to reproduce/understand the claim: commit/artifact, runner/environment, runtime/compiler/interpreter, dependency/build configuration, workload/input size, warmup, sample count, concurrency, measurement method, timeouts, latency distribution/percentiles where relevant, throughput where relevant, CPU/resource and memory data where relevant, baseline, candidate, delta, and variance/noise notes.

Do not cherry-pick favorable runs, compare warm candidates against undisclosed cold baselines, reduce representative workload merely to make a gate pass, or hide slow samples without a justified model change.

Automated performance-regression checks SHOULD be added only when the path is important and environment variance is sufficiently controlled. Prefer stable microbenchmarks for pure hot paths, controlled integration benchmarks for important boundaries, and load/capacity testing outside ordinary PR CI when expensive or disruptive.

Load/capacity testing against external or production systems requires separately applicable authorization and scope.

## 16. CI, build, and test acceleration without gate reduction

Optimize engineering feedback while preserving the same acceptance semantics.

Prefer, where safe and supported:

- dependency/build caching with lockfile- or artifact-aware keys and explicit integrity/retention rules;
- reusable deterministic environments and verified toolchains/images;
- parallel execution of genuinely independent jobs;
- deterministic test partitioning;
- incremental compilation/checking where omitted work is provably irrelevant and policy permits it;
- avoiding duplicate dependency installation/setup;
- cancellation of superseded non-deployment runs where appropriate;
- self-hosted runner tuning and resource sizing when authorized;
- local commands that mirror CI to reduce failed round trips.

CI optimization MUST NOT:

- rename a required check to evade repository controls;
- remove, skip, bypass, weaken, short-circuit, or silently narrow a required quality/security/integration/governance/conformance gate merely for speed;
- trust cache/generated output as source authority without provenance/invalidation;
- leak secrets into caches, artifacts, logs, or cache keys;
- suppress flaky failures instead of repairing their cause;
- run privileged reusable workers without required isolation/cleanup.

Measure queue time, setup time, execution time, cache effectiveness, critical path, failure/retry waste, PR count per milestone, full-CI runs per merged change, and branch-update retest waste separately where useful.

Marketplace MAY use three validation lanes while preserving one acceptance meaning:

- `FAST` — intermediate deterministic feedback when a versioned tested impact map proves a smaller lane is sufficient; ambiguous relevance falls back to FULL.
- `FULL` — required for the final review head, security/policy/governance-sensitive changes, dependency/lockfile changes, HIGH/CRITICAL risk, and ambiguous impact.
- `RELEASE` — FULL plus packaging/distribution/provenance/acceptance required at a release or deployment boundary.

A successful validation result MAY be reused only when it is immutably bound to the same relevant source/tree, dependency/toolchain inputs, policy/governance version, and reused artifact digest. A relevant source, dependency, toolchain, policy, governance, or artifact change invalidates that evidence. Cache misses and full revalidation remain correct supported paths.

For a plausibly transient failure with unchanged source, rerun only failed jobs when practical and bounded. Repeated identical failure requires root-cause investigation rather than indefinite retry. Superseded non-deployment runs may be cancelled.

A provider merge queue is preferred when supported and verified. Post-merge FULL duplication may be replaced by provenance verification plus bounded smoke only when the exact merged tree is proven identical to the already FULL-validated merge-group tree; otherwise merged state is revalidated normally.

## 17. Development method

For each meaningful increment:

1. resolve the exact repository/project/branch target;
2. inspect current implementation, tests, interfaces, callers, configuration, relevant specifications, security/retention policy, docs, and applicable operational/performance evidence;
3. define behavior to change and behavior to preserve;
4. classify risk;
5. identify minimum capabilities;
6. identify trust, privacy, retention, project-isolation, side-effect, and resource boundaries;
7. if performance-sensitive, define the operational problem, metric/objective, success condition, and representative baseline before optimizing when safe/practical;
8. if performance-sensitive, identify the demonstrated bottleneck/critical path and state an optimization hypothesis;
9. place responsibility in the correct architectural layer;
10. add/update deterministic, regression, negative-security, retention, and stable performance tests/benchmarks as applicable;
11. implement the smallest coherent safe work unit, using small reversible commits inside one pull request when they share one project boundary, delivery objective, authorization boundary, and rollback/recovery semantics; split unrelated objectives or independent privileged/destructive boundaries;
12. apply the destructive-action protocol when relevant;
13. run focused tests;
14. if performance-sensitive, repeat equivalent measurements and compare baseline vs candidate, including tail/resource/failure effects where relevant;
15. run repository audit and applicable quality/security/governance checks;
16. run the full Marketplace conformance gate when the change can affect acceptance behavior;
17. review security invariants, project isolation, provenance, retention, resource bounds, cache trust/invalidation, performance budgets, and provider-control claims;
18. keep performance complexity only when measured benefit justifies it and no required invariant regressed; otherwise simplify or revert;
19. open/update a reviewable pull request; and
20. report changed files, behavior, tests, benchmark evidence where relevant, risk, capabilities, security/retention impact, resource impact, and unresolved external controls.

The established milestone workflow remains preferred:

```text
issue/scope
-> one branch for one coherent milestone slice
-> small reversible commits with focused/local checks
-> draft PR while the work unit is still changing materially
-> FAST validation only when a proven impact map permits it
-> documentation and performance evidence when applicable
-> FULL acceptance on the final review head
-> exact-head review/authorization
-> exact-head guarded merge or verified merge queue
-> reuse exact-tree evidence only when integrity-bound; otherwise verify merged-main normally
```

## 18. Small coherent changes and read-before-edit

Inspect code and policy before editing unfamiliar areas. Do not claim files/functions/controls/tests/benchmarks exist or pass unless verified.

Prefer coherent work-unit pull requests with one delivery purpose, relevant tests, stable unrelated behavior, easy review/revert, and no silent privilege, retention, or resource expansion. A pull request is a review/merge boundary, not a one-commit boundary; avoid micro-PR churn that duplicates setup, review, merge, and CI without adding a real safety or authorization boundary. Mixed-risk work units use the highest included risk.

Existing architecture SHOULD be followed unless it is demonstrably unsafe or a measured critical bottleneck justifies a documented change.

## 19. Repository governance

Repository-governance requirements are defined in `docs/REPOSITORY_GOVERNANCE.md`.

`.github/CODEOWNERS`, pull-request templates, CI, and repository audits are governance-as-code. They do **not** prove remote GitHub branch protection or rulesets are active.

Provider-side enforcement MUST be independently configured and verified through an authorized administrative control plane before it is described as enforced.

Performance/CI pressure does not authorize bypass of repository review or merge controls.

## 20. Exceptions

Security, retention, project-isolation, capability, governance, and material performance-budget exceptions MUST record:

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

Exceptions are narrow, expiring, reviewable, and removable. They do not silently renew themselves.

A performance-budget exception does not authorize weakening security, correctness, retention, project isolation, or required CI/governance controls.

## 21. Completion standard

The preferred solution is the smallest safe solution that preserves Marketplace semantic constraints, minimizes privilege and retained data, validates trust boundaries, controls side effects, remains testable/recoverable, preserves provenance, bounds resources, measures performance where material, optimizes demonstrated critical paths with evidence, and makes unsafe states difficult to represent.

A change MUST NOT be declared complete while a known material security defect, privacy violation, project-isolation breach, unauthorized retention condition, expired exception, required failing quality gate, falsely claimed remote security control, or unsupported material performance claim remains unresolved without an explicit authorized exception applicable to that condition.

For a performance-sensitive change, completion additionally requires either adequate evidence for the claimed result or an explicit statement that no material optimization claim is being made.
