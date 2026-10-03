# Marketplace Repository Governance

**Status:** Desired and repository-enforced governance policy where technically available
**Provider:** GitHub is the current repository host but is not part of Marketplace semantic authority
**Current policy adoption:** `docs/POLICY_V1_7_ADOPTION.md`

Repository governance is a security control. Repository files define desired policy and review workflow, but they do not by themselves prove provider-side branch protection or rulesets are active.

The supplied Repository Governance v1.3 source is an `ai-automation-department` repository-specific profile. Marketplace adopts its portable governance intent only after path/control review; foreign repository names, workflow/check names, package paths, validator names, and runtime paths are not Marketplace facts.

## 1. `main` policy

The desired remote policy for `main` is:

- changes enter through pull requests by default;
- direct pushes are disabled except an explicitly authorized, scoped emergency procedure;
- mandatory human PR approval count is **zero** at every PR risk level;
- CODEOWNERS routes optional feedback but is not a mandatory approval gate;
- review conversations are resolved before merge where supported;
- the exact Marketplace provider check `acceptance` is required;
- the branch is up to date before merge where supported;
- force push is disabled;
- branch deletion is disabled;
- agent diff review and applicable automated security/policy/governance validation are required;
- HIGH/CRITICAL operational authority remains separate when merge itself triggers such an operation.

The exact provider check/ruleset identifiers MUST be discovered from GitHub before configuration. Do not substitute a foreign or assumed check name.

Marketplace currently uses reviewed GitHub merge commits plus exact parent/provenance verification. The foreign governance profile's linear-history setting is not imported; changing Marketplace merge strategy is a separate governance decision.

Performance or CI pressure never authorizes reducing these controls or renaming/skipping required checks to evade them.

## 2. Governance as code

The repository contains:

- `.github/CODEOWNERS` for sensitive paths;
- `.github/pull_request_template.md` for work-unit/risk/capability/retention/security/activation/performance evidence;
- `.github/workflows/conformance.yml` for provider-neutral acceptance invocation;
- `tools/repository_audit.py` and `tools/conformance_gate.py` for local/CI acceptance;
- `DEVELOPMENT_POLICY.md`, `docs/POLICY_V1_7_ADOPTION.md`, historical adoption records, and `docs/RETENTION_POLICY.md` for engineering policy/provenance/retention.

These controls are reviewable source artifacts. They do **not** equal GitHub branch protection.

## 3. Current provider verification boundary

Provider-side branch protection/ruleset state MUST be independently read and verified through an authorized GitHub administrative control plane.

At the 2026-09-21 v1.7 adoption verification, current `main` was `9a090388143690b0a230433b0b828a3dcaf64fef` and GitHub reported:

```text
main protected: false
branch protection enabled: false
required status checks: enforcement off
repository rulesets: []
current Marketplace check-run identity: acceptance
```

The detailed branch-protection endpoint was inaccessible to the connected integration, but the branch endpoint directly reports that protection is disabled.

Therefore Marketplace MUST NOT claim `main` is remotely protected. Provider-side protection remains required policy; enabling/changing it is a separate ADMIN capability tracked by Issue #212 and must be separately authorized and independently verified.

Until that required provider control exists, source development and PR validation may continue, but routine merge to `main` is blocked unless an applicable explicit narrow exception authorizes that governance gap. Exact-head discipline, CI, CODEOWNERS, agent review, merge-parent verification, and merged-main push verification are compensating/review controls; they are not substitutes for branch protection.

## 4. Security-sensitive paths

The following paths are policy/security-sensitive and SHOULD receive explicit owner review:

```text
PRINCIPLES.md
DEVELOPMENT_POLICY.md
docs/POLICY_V1_7_ADOPTION.md
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

The current `.github/workflows/conformance.yml` executes the full Marketplace acceptance path on pull requests and `main`. This conservative behavior remains valid; v1.7 adoption does not require weakening or immediately refactoring it.

A material performance/resource claim additionally records the operational problem, critical path, metric/budget, representative baseline, bottleneck evidence, hypothesis, candidate measurement under equivalent conditions, resource/tail/saturation effects, cache/concurrency/backpressure effects, limitations, and `KEEP | REVISE | REVERT` result.

A green functional suite does not by itself prove a performance or reproducible-build claim.

material performance/reproducibility claims have evidence adequate to the claim before merge.

## 6. v1.7 delivery method

Marketplace adopts the v1.7 proportional faster-safe-delivery method:

```text
work-unit contract
-> minimum authoritative reads
-> batch independent read-only work
-> one coherent patch with reversible checkpoints
-> delta-first focused validation
-> FULL once on final review head when required
-> agent diff review + applicable automated security/policy checks
-> zero mandatory human PR approvals
-> exact-head guarded routine merge after provider preconditions and required checks
-> exact-tree evidence reuse only when integrity-bound
-> merged-main provenance/CI verification
-> separately authorized runtime activation or deployment
```

Maintain an internal evidence ledger of `VERIFIED / DECIDED / CHANGED / VALIDATED / WAITING / BLOCKED / NEXT`. Reuse a verified fact only until a relevant invalidation input changes.

Independent safe work may continue while CI runs, but the tested head MUST NOT be mutated while its in-progress result is being treated as evidence for that head.

Superseded non-deployment CI runs may be cancelled where tooling supports it. Re-running only failed jobs is preferred for plausibly transient failures with unchanged source; repeated identical failure requires root-cause investigation.

## 7. Bounded authorization reuse and activation separation

Marketplace permits **bounded authorization reuse** for an already authorized work unit while project, target/resource, exact head/version where explicitly specified, scope, risk, capability class, side-effect class, rollback/recovery assumptions, and expiry/exception state remain unchanged.

For an explicitly adopted Marketplace delivery task, task-branch commit/push, PR creation/update, and routine merge after required checks are included source-delivery actions. Safe read-only verification, deterministic test reruns, conversation continuation, and non-mutating diagnostics likewise do not require repeated approval merely because time or conversational turns passed.

Same-scope head movement requires affected validation and exact-head merge guards to refresh, not task reauthorization, unless the user explicitly pinned authority to the old head. A material target/resource change, scope expansion, risk increase, new privileged/destructive capability, changed rollback assumptions, or expired exception requires renewed authority.

Privileged/destructive exact targets are still re-verified immediately before execution.

**Runtime activation**, dependency installation, configuration/service mutation, database migration/activation, provider administration, destructive operations, and deployment are separate authorities by default. A merge that triggers one of those operations inherits that operational boundary and must not proceed without its applicable authority.

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

## 10. Zero-approval PR review profile

Marketplace requires **zero mandatory human PR approvals** for LOW, MODERATE, HIGH, and CRITICAL pull requests under the adopted v1.7 source-delivery profile.

This does not remove review obligations. Before merge, the agent/maintainer MUST:

1. inspect the complete candidate diff;
2. run the required focused and FULL/RELEASE validation for the actual risk/scope;
3. resolve blocking review feedback and verify unresolved review-thread state;
4. verify the exact head/base/mergeability and required provider checks;
5. verify no known material security/privacy/retention/isolation/governance defect remains unresolved;
6. verify any merge-triggered HIGH/CRITICAL operational side effect has its own explicit authority;
7. use an exact-head merge guard where supported;
8. verify merged-state provenance/CI after merge.

CODEOWNERS may route optional feedback, but provider code-owner approval is not a required gate under this profile.

Historical solo-maintainer exceptions and exact-head approval records remain durable provenance for actions performed under prior policy. They do not create a current approval requirement and they do not broaden runtime/deployment/admin authority.

The zero-approval profile cannot self-authorize provider administration, bypass a required CI check, waive the required `main` protection control, or convert source-delivery authority into deployment/destructive/secret/admin authority.

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