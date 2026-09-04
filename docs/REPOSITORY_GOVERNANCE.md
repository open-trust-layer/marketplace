# Marketplace Repository Governance

**Status:** Desired and repository-enforced governance policy where technically available
**Provider:** GitHub is the current repository host but is not part of Marketplace semantic authority
**Current policy adoption:** `docs/POLICY_V1_6_ADOPTION.md`

Repository governance is a security control. Repository files define desired policy and review workflow, but they do not by themselves prove provider-side branch protection or rulesets are active.

The supplied Repository Governance v1.2 source is an `ai-automation-department` repository-specific profile. Marketplace adopts its portable governance intent only after path/control review; foreign repository names, workflow/check names, package paths, validator names, and runtime paths are not Marketplace facts.

## 1. `main` policy

The desired remote policy for `main` is:

- changes enter through pull requests by default;
- direct pushes are disabled except an explicitly authorized, scoped emergency procedure;
- normal changes require at least one approval;
- security/policy-sensitive paths require code-owner review where provider capabilities support it;
- stale approvals are dismissed after material changes where supported;
- review conversations are resolved before merge where supported;
- the Marketplace conformance/acceptance CI result is required;
- the branch is up to date before merge where supported;
- force push is disabled;
- branch deletion is disabled;
- CRITICAL changes target two independent approvals where technically and practically supported.

The exact provider check/ruleset identifiers MUST be discovered from GitHub before configuration. Do not substitute a foreign or assumed check name.

Marketplace currently uses reviewed GitHub merge commits plus exact parent/provenance verification. The foreign governance profile's linear-history setting is not imported; changing Marketplace merge strategy is a separate governance decision.

Performance or CI pressure never authorizes reducing these controls or renaming/skipping required checks to evade them.

## 2. Governance as code

The repository contains:

- `.github/CODEOWNERS` for sensitive paths;
- `.github/pull_request_template.md` for work-unit/risk/capability/retention/security/activation/performance evidence;
- `.github/workflows/conformance.yml` for provider-neutral acceptance invocation;
- `tools/repository_audit.py` and `tools/conformance_gate.py` for local/CI acceptance;
- `DEVELOPMENT_POLICY.md`, `docs/POLICY_V1_6_ADOPTION.md`, historical adoption records, and `docs/RETENTION_POLICY.md` for engineering policy/provenance/retention.

These controls are reviewable source artifacts. They do **not** equal GitHub branch protection.

## 3. Current provider verification boundary

Provider-side branch protection/ruleset state MUST be independently read and verified through an authorized GitHub administrative control plane.

At exact v1.6 adoption baseline `b1921cb6c744e68f9d2ee8d9c83f5c44bbede4c2`, GitHub reported:

```text
main protected: false
branch protection enabled: false
```

Therefore Marketplace MUST NOT claim `main` is remotely protected at this point. The desired protection remains required policy, but enabling/changing it is a separate ADMIN capability and must be separately authorized and verified.

Current exact-head PR discipline, CI, CODEOWNERS, review records, merge-parent verification, and merged-main push verification are compensating/review controls; they are not a substitute for provider-side protection.

## 4. Security-sensitive paths

The following paths are policy/security-sensitive and SHOULD receive explicit owner review:

```text
PRINCIPLES.md
DEVELOPMENT_POLICY.md
docs/POLICY_V1_6_ADOPTION.md
docs/POLICY_V1_5_ADOPTION.md
docs/POLICY_V1_4_ADOPTION.md
docs/RETENTION_POLICY.md
docs/REPOSITORY_GOVERNANCE.md
.github/**
pyproject.toml
src/marketplace/application/**
src/marketplace/runtime/**
src/marketplace/reference/**
tools/conformance_gate.py
tools/conformance_manifest.py
tools/repository_audit.py
tools/package_artifact_gate.py
conformance/olp-source-pin.txt
specification/**
```

Authorization, secret-management, retention, deployment, network, persistence, package/dependency admission, optimization fast paths/caches, and protected-side-effect execution paths are security-sensitive even when not named individually above.

## 5. Pull-request evidence and validation

Each meaningful PR SHOULD record:

- purpose and smallest coherent scope;
- work-unit contract and exact base/head where material;
- risk classification and capabilities;
- affected semantic/project/security/retention boundaries;
- behavior changed and behavior explicitly preserved;
- dependency/provenance impact;
- validation lane and focused/FULL evidence;
- evidence reused and its exact validity inputs, if any;
- unresolved provider/external controls;
- rollback/recovery for HIGH/CRITICAL work;
- activation/deployment boundary if applicable.

Policy/security/governance/dependency changes, final ready-for-review heads, HIGH/CRITICAL work, and ambiguous impact require FULL validation.

The current `.github/workflows/conformance.yml` executes the full Marketplace acceptance path on pull requests and `main`. This conservative behavior remains valid; v1.6 adoption does not require weakening or immediately refactoring it.

A material performance/resource claim additionally records the operational problem, critical path, metric/budget, representative baseline, bottleneck evidence, hypothesis, candidate measurement under equivalent conditions, resource/tail/saturation effects, cache/concurrency/backpressure effects, limitations, and `KEEP | REVISE | REVERT` result.

A green functional suite does not by itself prove a performance or reproducible-build claim.

## 6. v1.6 delivery method

Marketplace adopts the v1.6 faster-safe-delivery method:

```text
work-unit contract
-> minimum authoritative reads
-> batch independent read-only work
-> one coherent patch with reversible checkpoints
-> delta-first focused validation
-> FULL once on final review head when required
-> exact-head review / applicable owner authority
-> exact-head guarded merge or verified merge queue
-> exact-tree evidence reuse only when integrity-bound
-> merged-main provenance/CI verification
-> separately authorized runtime activation or deployment
```

Maintain an internal evidence ledger of `VERIFIED / DECIDED / CHANGED / VALIDATED / WAITING / BLOCKED / NEXT`. Reuse a verified fact only until a relevant invalidation input changes.

Independent safe work may continue while CI runs, but the tested head MUST NOT be mutated while its in-progress result is being treated as evidence for that head.

Superseded non-deployment CI runs may be cancelled where tooling supports it. Re-running only failed jobs is preferred for plausibly transient failures with unchanged source; repeated identical failure requires root-cause investigation.

## 7. Bounded authorization reuse and activation separation

Marketplace permits **bounded authorization reuse** for an already authorized work unit while project, target/resource, exact head/version where specified, scope, risk, capability class, side-effect class, rollback/recovery assumptions, and expiry/exception state remain unchanged.

Safe read-only verification, deterministic test reruns, conversation continuation, and non-mutating diagnostics do not require repeated approval merely because time or conversational turns passed.

A material change to any authorization input requires renewed authority as applicable. If an authorization names an exact head SHA, head movement invalidates that authorization.

Privileged/destructive exact targets are still re-verified immediately before execution.

**Merge**, **runtime activation**, dependency installation, configuration/service mutation, database migration/activation, provider administration, and deployment are separate authorities by default. One MUST NOT be inferred from another unless explicitly combined by the approving authority.

## 8. Preauthorized rollback

When an authorized mutation includes an exact rollback condition and exact rollback method, that **preauthorized rollback** may execute without a second approval only when the stated condition becomes true and the rollback remains within the original exact target/method.

After rollback:

1. verify restored state;
2. report the trigger;
3. report resulting state; and
4. do not silently retry the failed mutation indefinitely.

## 9. Emergency governance exception

An emergency governance bypass, where provider policy permits one, MUST be narrow and explicit. The exception record MUST include:

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

It waives only what it explicitly names and MUST NOT silently expand into runtime/deployment/secret/admin authority.

After emergency use, verify exact resulting state, restore normal controls, document follow-up, and close/expire the exception when its condition ends.

Performance targets or CI duration are not sufficient reasons by themselves for an emergency bypass.

## 10. Solo-maintainer review procedure

This section preserves Marketplace's standing compensating-control procedure for periods when no eligible independent reviewer is practically available. It is **not independent human review** and does not erase the preference for independent review.

This procedure is available only while this section is present on `main`, only in a real solo-maintainer state for the affected change, and only when every applicable condition below is satisfied and recorded.

### 10.1 Review provenance

A PR using this procedure records:

- author/maintainer availability state;
- submitted independent approval count for the accepted head;
- unresolved review-thread count;
- that maintainer/security self-review and automated CI are not independent human review;
- exact accepted head SHA and exact base SHA or exact tested synthetic-merge relation;
- owner-authorization path;
- risk-specific compensating controls.

### 10.2 Owner authorization paths

A solo-maintainer PR may proceed through either:

**A. Exact-head authorization** — the project owner explicitly authorizes the exact PR and exact accepted head SHA after that SHA exists. Any head movement invalidates it.

**B. Bounded standing owner mandate** — an explicit, time-bounded mandate may authorize routine repository source-control work when it states owner, repository scope, authorized source-control actions, risk ceiling, issue time, expiry, excluded capabilities/actions, and removal condition.

A standing mandate may cover routine branch commits, file replacement/removal, PR creation/update, and SHA-guarded source merges only after the exact candidate satisfies all required acceptance controls. It does not silently authorize CRITICAL changes, live external network execution, production deployment/service activation, credential/secret/key/certificate mutation, provider administration, force-push of `main`, destructive external data/infrastructure operations, protected settlement/payment/fulfillment, or bypass of an explicit safety stop.

Unless a stricter explicit expiry is stated, a standing mandate has a conservative maximum 24-hour authorization lifetime for source-control actions. Owner withdrawal, scope drift, or availability of an eligible independent reviewer ends it earlier where applicable.

A standing mandate does not preserve stale validation: every new exact head must pass the required acceptance gate before merge.

### 10.3 Eligible risk

LOW and MODERATE source changes may use the procedure when all conditions hold.

HIGH source changes may use it only when the PR itself does not perform production deployment, destructive external data action, credential/secret mutation, provider administration, protected-branch force push, or irreversible infrastructure mutation; external-I/O capability is tested only through deterministic doubles/non-live fixtures unless separately authorized; the PR includes explicit threat-boundary review and negative/security regression coverage; rollback/recovery is documented; and exact-head FULL acceptance is green.

CRITICAL changes are never eligible for the solo-maintainer procedure and require independent human review plus all other applicable controls.

Risk MUST NOT be classified downward to gain eligibility.

### 10.4 Mandatory compensating controls

Before merge under this procedure:

1. PR is open, review-ready, and mergeable;
2. exact accepted head SHA is recorded;
3. complete applicable Marketplace acceptance/conformance gate is green for that exact head/tree or a documented equivalent exact synthetic merge candidate;
4. applicable deterministic unit/security/repository-audit/artifact/package/vector/generator/whitespace/performance-regression checks are green;
5. unresolved review-thread count is zero;
6. PR explicitly states automated acceptance/self-review are not independent human review;
7. no known material security/privacy/retention/isolation/governance defect invalidates the change without a separately applicable explicit exception/compensating procedure;
8. HIGH changes include exact rollback/recovery and blast-radius/side-effect analysis;
9. material performance/reproducibility claims have evidence adequate to the claim;
10. merge uses an exact-head guard;
11. resulting merged `main` state receives required push acceptance/provenance verification before completion is declared;
12. provider-side protection claims remain separate and independently verified.

### 10.5 No self-approval fiction

The PR author MUST NOT describe self-review or automated acceptance as independent approval. Provider support for self-approval does not manufacture independence.

### 10.6 Procedure lifecycle

```text
owner: tehki
scope: open-trust-layer/marketplace solo-maintainer pull-request review procedure
risk ceiling: HIGH subject to this section; CRITICAL excluded
issued_at: 2026-08-27
next_review: 2026-11-25
expires_at: 2026-11-25 unless renewed by a later governance change
removal_condition: an eligible independent reviewer path becomes available for the affected changes, or the project owner withdraws the procedure
```

Once an eligible independent reviewer becomes available, normal independent review is preferred and the compensating procedure MUST NOT be used merely for convenience.

## 11. No false enforcement claims

The following require provider-side verification before being described as active enforcement:

- `main` requires pull requests;
- `main` requires a particular number of approvals;
- code-owner review is enforced;
- stale approvals are dismissed;
- review conversations must be resolved;
- a named status check is provider-required;
- force pushes are disabled;
- branch deletion is disabled.

Desired configuration and verified active configuration are separate facts. Performance, reproducibility, cache integrity, benchmark equivalence, exact-tree reuse, and CI-acceleration claims likewise require evidence appropriate to the claim.