# Coding Agent Development Principles v1.4 — Marketplace Adoption Record

**Status:** Project policy provenance and adaptation record  
**Adopted source:** `CODING_AGENT_DEVELOPMENT_PRINCIPLES_SYSTEM_PROMPT_v1.4.md`  
**Source revision:** 2026-08-30 — evidence-driven performance and optimization engineering  
**Source SHA-256:** `ab39374e010a931d5122c28bc3a97612cbeb41f1079c67f0f90863d01641e1cc`  
**Marketplace adoption issue:** #131  
**Base at adoption:** `1880b75c073aa7524036ed7d7fe4951734fc7686`

This document records how Coding Agent Development Principles v1.4 is adopted by Open Layer Marketplace. It is intentionally an **adaptation record**, not a verbatim replacement for Marketplace policy.

Marketplace engineering authority remains:

1. `PRINCIPLES.md` for Marketplace semantic constraints;
2. `DEVELOPMENT_POLICY.md` for project engineering policy;
3. `docs/RETENTION_POLICY.md` for retention classes and enforcement expectations;
4. `docs/REPOSITORY_GOVERNANCE.md` for repository workflow and review controls;
5. specifications, conformance material, tests, and implementation within their defined scopes.

A source handbook statement that is specific to another repository or companion file does not become Marketplace authority merely because the handbook is used as an engineering source.

## 1. Portable v1.4 additions adopted

Marketplace adopts the v1.4 optimization discipline as a safety-preserving extension of the existing v1.3 method.

Material performance work follows:

```text
measure
-> identify
-> hypothesize
-> change
-> measure again
-> verify invariants
-> KEEP | REVISE | REVERT
```

The project adopts these requirements:

- material optimization claims require evidence rather than intuition;
- a representative baseline, target metric, and success condition are defined before material optimization when safe and practical;
- demonstrated bottlenecks and critical paths are optimized before presumed bottlenecks;
- baseline and candidate measurements use equivalent workloads/environments or clearly document limitations;
- latency-sensitive work considers distribution/tail behavior and saturation, not averages alone;
- CPU, memory/allocation, filesystem/database/network I/O, connections, subprocesses, queue depth, external-service usage, and retained data are performance resources where relevant;
- optimization never weakens security, privacy, legal, correctness, integrity, recoverability, authorization, capability, project-isolation, provenance, or retention invariants;
- fast paths preserve all required authentication, authorization, capability, validation, retention, and security controls;
- caches and precomputed state never silently become trust, authorization, revocation, policy, retention, or project-boundary bypasses;
- concurrency, parallelism, retries, queues, pools, batching, and fan-out remain explicitly bounded and use backpressure/admission control where producers can outrun consumers;
- performance budgets may be introduced for important paths when the workload, environment, metric, owner, measurement method, and review trigger are explicit;
- benchmark/profile/load evidence follows normal privacy, retention, provenance, licensing, project-isolation, and authorization rules;
- performance-regression gates are used only where measurement noise is controlled enough to make them meaningful;
- CI/build/test acceleration preserves the exact required gate semantics and never renames, removes, skips, bypasses, weakens, or short-circuits a required quality/security/integration/governance/conformance check;
- optimization complexity is retained only when measured benefit justifies it.

## 2. Marketplace optimization priority

Prefer the least complex improvement that reduces demonstrated cost:

```text
1. remove unnecessary work
2. remove duplicate work
3. improve algorithm/data structure/data access
4. reduce copying/parsing/serialization/data movement
5. reduce unnecessary external round trips
6. batch/coalesce compatible work with explicit bounds
7. cache safe reusable results with explicit invalidation and retention
8. reuse expensive initialized resources safely
9. precompute stable immutable work
10. add bounded concurrency/parallelism with backpressure
11. reduce allocation/object churn and memory pressure
12. use runtime-specific optimization
13. use native/specialized acceleration only when evidence justifies its extra risk and maintenance cost
```

The absence of a measurable or operationally justified problem is normally a reason to keep simpler code.

## 3. Cache and reusable-state minimum contract

A material cache or reusable/precomputed state should define, as applicable:

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

Cache misses remain a correct supported path. Security-sensitive decisions require explicit freshness/revalidation. Cache keys and metrics do not expose secrets or sensitive raw content.

## 4. Benchmark and optimization evidence

Significant performance-sensitive changes should preserve a compact evidence record in the PR, issue, ADR, benchmark artifact, or equivalent review surface:

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

A benchmark record should identify enough context to understand the claim: commit/artifact, runner/environment, runtime/compiler/interpreter, dependency/build configuration, workload/input size, warmup, iterations/sample count, concurrency, measurement method, timeouts, latency distribution or percentiles where relevant, throughput where relevant, CPU/resource and memory data where relevant, baseline, candidate, delta, and variance/noise notes.

A single favorable run is not sufficient evidence for a durable material optimization claim.

## 5. Source-specific statements not imported as Marketplace authority

The supplied v1.4 handbook contains inherited references specific to `ai-automation-department`, including a repository-governance example and historical v1.3 runtime/governance implementation sections. Those statements are treated as source examples/history, not Marketplace facts.

The source policy-stack text also contains the inherited phrase `this v1.3 handbook` even though the document identifies itself as Version 1.4. Marketplace interprets the intended portable reference as **the v1.4 handbook**; the typo is not imported into project policy.

References in the source to `CODING_AGENT_CONSTITUTION_v1.1.md`, `CODING_AGENT_POLICY_v1.1.yaml`, and `REPOSITORY_GOVERNANCE_v1.0.yaml` do not create those files or their authority in Marketplace. Equivalent Marketplace controls apply only where explicitly adopted in this repository.

## 6. Unchanged boundaries

This adoption does not change Marketplace protocol semantics, OLP semantics, authorization meanings, retention classes, the 10-second EPHEMERAL default, or protected-side-effect authority.

It grants no `NETWORK_EXTERNAL`, `DEPLOY`, `DELETE`, `MANAGE_SECRETS`, or `ADMIN` capability. It does not configure or claim provider-side branch protection/ruleset enforcement.

Optimization remains subordinate to the existing SAFETY FIRST precedence:

```text
safety / security / privacy / legal obligations
-> correctness and data integrity
-> reliability and recoverability
-> maintainability and testability
-> performance and convenience
```
