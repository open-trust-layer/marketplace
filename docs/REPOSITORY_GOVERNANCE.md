# Marketplace Repository Governance

**Status:** Desired and repository-enforced governance policy where technically available
**Provider:** GitHub is the current repository host but is not part of Marketplace semantic authority

Repository governance is a security control. Repository files can define desired policy and review workflow, but they do not by themselves prove provider-side branch protection or rulesets are active.

## 1. `main` policy

The desired remote policy for `main` is:

- changes enter through pull requests by default;
- direct pushes are disabled except an explicitly authorized emergency procedure;
- normal changes require at least one approval;
- security/policy-sensitive paths require code-owner review where provider capabilities support it;
- stale approvals are dismissed after material changes where supported;
- review conversations must be resolved before merge where supported;
- the Marketplace conformance/acceptance CI check is required;
- the branch must be up to date before merge where supported;
- force push is disabled;
- branch deletion is disabled;
- CRITICAL changes target two independent approvals where technically/supportably possible.

The exact GitHub ruleset/check identifiers MUST be discovered from the provider before configuration. Do not substitute an assumed check name.

Performance or CI pressure never authorizes reducing these controls or renaming/skipping required checks to evade them.

## 2. Repository governance-as-code

The repository contains:

- `.github/CODEOWNERS` for sensitive paths;
- `.github/pull_request_template.md` for risk/capability/retention/security and performance-evidence review;
- `.github/workflows/conformance.yml` for provider-neutral acceptance invocation;
- `tools/repository_audit.py` and `tools/conformance_gate.py` for local/CI acceptance;
- `DEVELOPMENT_POLICY.md`, `docs/POLICY_V1_4_ADOPTION.md`, and `docs/RETENTION_POLICY.md` for engineering policy/provenance/retention.

These controls are reviewable source artifacts. They do **not** equal GitHub branch protection.

## 3. Current verification boundary

Provider-side branch protection/ruleset state MUST be independently read and verified through an authorized GitHub administrative control plane.

If the active connector cannot read or modify that setting, record the limitation. Never state that `main` is protected based solely on policy files, CODEOWNERS, CI configuration, or customary workflow.

## 4. Sensitive paths

The following paths are policy/security-sensitive and SHOULD receive explicit owner review:

```text
PRINCIPLES.md
DEVELOPMENT_POLICY.md
docs/POLICY_V1_4_ADOPTION.md
docs/RETENTION_POLICY.md
docs/REPOSITORY_GOVERNANCE.md
.github/**
pyproject.toml
src/marketplace/runtime/**
src/marketplace/reference/**
tools/conformance_gate.py
tools/conformance_manifest.py
tools/repository_audit.py
conformance/olp-source-pin.txt
specification/**
```

Authorization, secret-management, retention, deployment, network, persistence, optimization fast paths/caches, and protected-side-effect execution paths are security-sensitive even when not named individually above.

## 5. Pull-request evidence

Each meaningful PR SHOULD state:

- purpose/scope;
- risk classification;
- capabilities used or required;
- affected project/semantic boundaries;
- security/privacy impact;
- retention impact;
- destructive-action analysis when applicable;
- dependencies added/changed;
- tests and acceptance commands run;
- conformance/vector impact;
- unresolved provider/external controls;
- rollback/recovery notes for HIGH/CRITICAL changes.

For a material performance/resource claim or optimization-sensitive change, the PR SHOULD also state:

- user/business/operational problem and critical path;
- target metric and budget/success condition;
- representative baseline;
- profiling or bottleneck evidence;
- optimization hypothesis;
- candidate measurement under equivalent conditions or documented limitations;
- tail latency/saturation and CPU/memory/allocation/I/O/network/queue/external-service effects where relevant;
- cache/batching/concurrency/backpressure/invalidation/retention effects where relevant;
- variance/noise limitations;
- final `KEEP`, `REVISE`, or `REVERT` decision.

A material optimization claim MUST NOT be accepted solely because functional CI is green. Performance evidence and correctness/security evidence are distinct.

The PR template encodes these prompts.

## 6. Emergency exception

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

After emergency use:

1. verify the exact resulting repository state;
2. restore normal protection immediately;
3. open follow-up review/audit work;
4. document why ordinary PR controls were insufficient; and
5. remove the exception when its condition ends.

Performance targets or CI duration are not, by themselves, sufficient reasons for an emergency governance bypass.

## 7. Solo-maintainer review procedure

This section defines a **standing compensating-control procedure for periods when no eligible independent reviewer is practically available**. It is not an independent approval and does not erase the preference for independent human review.

This procedure is available only while this section is present on `main`, only in a real solo-maintainer state for the affected change, and only when every applicable condition below is satisfied and recorded.

### 7.1 Review provenance

A PR using this procedure MUST record all of the following:

- the PR author is also the only practically available maintainer/CODEOWNER for the affected change, or no eligible independent reviewer is available;
- submitted independent approval count for the accepted head;
- unresolved review-thread count;
- that maintainer/security self-review and automated CI are **not independent human review**;
- the exact accepted head SHA and exact base SHA or exact tested synthetic merge relation;
- the applicable owner authorization path from section 7.2;
- all risk-specific compensating controls from sections 7.3 and 7.4.

### 7.2 Owner authorization paths

A solo-maintainer PR may proceed through either of two explicit owner-authorization forms.

#### A. Exact-head authorization

The project owner explicitly authorizes the exact PR number and exact accepted head SHA after that SHA exists. Any head movement invalidates this authorization.

#### B. Bounded standing owner mandate

The project owner may explicitly issue a **time-bounded standing mandate** for repository source-control work when uninterrupted execution is desired. The mandate MUST be recorded in a durable repository discussion (for example the governance issue or each affected PR) and MUST state or be conservatively interpreted with all of these fields:

```text
owner
repository scope
authorized source-control actions
risk ceiling
issued_at
expires_at
excluded capabilities/actions
removal condition
```

A standing mandate may authorize routine branch commits, file replacement/removal, PR creation/update, and SHA-guarded PR merges without requiring a fresh chat/message for each accepted head, **but only after that exact head independently satisfies the acceptance controls below**.

A standing mandate MUST NOT authorize any of the following merely by being broad or by saying “all further actions”:

- CRITICAL changes;
- live external network execution against a real peer or public endpoint;
- production deployment or service activation;
- credential, secret, token, key, or certificate issuance/mutation;
- provider/repository administration such as changing branch protection/rulesets or force-pushing `main`;
- destructive user/content/database/infrastructure operations outside bounded source-branch cleanup;
- irreversible infrastructure mutation;
- settlement, payment, fulfillment, or other protected external side-effect execution;
- bypass of an explicit safety stop in `DEVELOPMENT_POLICY.md`.

Those actions require their own separately applicable authorization immediately before execution, and CRITICAL changes require independent human review.

A standing mandate MUST have an explicit expiry no later than 24 hours after issuance unless renewed by a later explicit owner action. If the source authorization did not name an expiry, the implementation MUST conservatively apply a maximum 24-hour expiry. Owner withdrawal, repository-scope drift, or the availability of an eligible independent reviewer ends the mandate earlier where applicable.

Head movement does **not** by itself require a new owner message while an in-scope standing mandate remains valid, but it always invalidates prior acceptance evidence. The new exact head MUST pass the full applicable acceptance gate and be recorded before merge.

### 7.3 Eligible and ineligible risk

LOW and MODERATE source changes may use this procedure when the conditions above hold.

HIGH source changes may use it only when all of these additional conditions hold:

- the PR itself does not perform a production deployment, destructive external data action, credential/secret mutation, provider-administration action, protected-branch force push, or irreversible infrastructure mutation;
- any capability that could perform external I/O is implemented/tested only through deterministic doubles or explicitly non-live fixtures unless separately authorized immediately before real execution;
- the PR includes an explicit security/threat-boundary review;
- deterministic adversarial/security regression coverage exists for the newly introduced or expanded attack surface;
- rollback/recovery is documented and does not depend on a false transactional guarantee;
- exact-head acceptance is green after the final substantive or documentation change.

CRITICAL changes are **never eligible** for the solo-maintainer procedure. They require independent human review and any additional controls required by `DEVELOPMENT_POLICY.md`.

Risk MUST NOT be classified downward to make a change eligible.

### 7.4 Mandatory compensating controls

Before merge under this procedure:

1. the PR MUST be open, review-ready, and mergeable;
2. the exact accepted head SHA MUST be recorded;
3. the complete applicable Marketplace acceptance/conformance gate MUST be green for that exact candidate, or for the exact GitHub synthetic merge candidate formed from that head and unchanged base with the relation recorded;
4. all applicable deterministic unit, adversarial/security, repository-audit, reproducible-artifact, package-smoke, vector, generator-replay, whitespace, and stable performance-regression checks MUST be green;
5. there MUST be no unresolved review threads;
6. the PR MUST explicitly state that automated acceptance and maintainer self-review are not independent human review;
7. known material security, privacy, retention, project-isolation, or governance defects MUST be absent or separately tracked with a fail-closed scope that does not invalidate the change;
8. HIGH changes MUST include exact rollback/recovery notes and blast-radius/side-effect analysis;
9. material performance/resource claims MUST include evidence adequate to the claim and MUST NOT rely on weakened or non-equivalent acceptance conditions;
10. merge MUST use an exact-head guard (`expected_head_sha` or provider-equivalent) so a moving head cannot be substituted;
11. the resulting merged `main` commit MUST independently pass the applicable push acceptance workflow before the milestone/change is declared complete;
12. provider-side branch/ruleset enforcement claims MUST remain separate and independently verified.

A green CI result does not convert this procedure into independent review, and a faster CI result does not authorize gate reduction.

### 7.5 No self-approval fiction

The PR author MUST NOT create or describe a self-review as an independent approval. If the provider allows the author to submit an `APPROVE` review, that action does not satisfy an independent-review requirement and SHOULD NOT be used to manufacture one.

Statements such as “approved by review” or “code-owner approved” require an actually independent eligible reviewer when independence is claimed.

### 7.6 Procedure lifecycle

Standing procedure metadata:

```text
owner: tehki
scope: open-trust-layer/marketplace solo-maintainer pull-request review procedure
risk ceiling: HIGH subject to sections 7.2-7.4; CRITICAL excluded
issued_at: 2026-08-27
next_review: 2026-11-25
expires_at: 2026-11-25 unless renewed by a later governance change
removal_condition: an eligible independent reviewer path becomes available for the affected changes, or the project owner withdraws the procedure
```

Once an eligible independent reviewer becomes available, normal independent review is preferred and this procedure MUST NOT be used merely for convenience.

This procedure does not retroactively convert earlier solo-maintainer merges into independently reviewed changes.

## 8. Branch and milestone method

The preferred Marketplace milestone/change flow remains:

```text
issue/scope
-> dedicated branch
-> smallest coherent implementation
-> focused tests
-> performance baseline/evidence when applicable
-> repository audit
-> full conformance gate when applicable
-> PR with objective evidence
-> independent review or eligible solo-maintainer procedure
-> exact-head guarded merge
-> verify merged-main CI
```

For performance-sensitive work, measurement should occur before and after the smallest safe candidate under equivalent conditions. Do not make the first implementation more complex merely to produce an impressive benchmark.

Policy/security changes SHOULD use the same workflow even when they are documentation-heavy because they can alter future authority and operational behavior.

## 9. No false enforcement claims

The following statements require provider-side verification before use:

- `main` requires PRs;
- `main` requires N approvals;
- code-owner review is enforced;
- stale approvals are dismissed;
- conversations must be resolved;
- a named status check is required;
- force pushes are disabled;
- branch deletion is disabled.

Desired configuration and verified active configuration are separate facts.

Performance, reproducibility, cache integrity, benchmark equivalence, and CI-acceleration claims likewise require evidence appropriate to those claims; desired behavior and verified behavior are separate facts.
