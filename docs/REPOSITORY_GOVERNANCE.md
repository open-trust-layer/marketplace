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

## 2. Repository governance-as-code

The repository contains:

- `.github/CODEOWNERS` for sensitive paths;
- `.github/pull_request_template.md` for risk/capability/retention/security review;
- `.github/workflows/conformance.yml` for provider-neutral acceptance invocation;
- `tools/repository_audit.py` and `tools/conformance_gate.py` for local/CI acceptance;
- `DEVELOPMENT_POLICY.md` and `docs/RETENTION_POLICY.md` for engineering policy.

These controls are reviewable source artifacts. They do **not** equal GitHub branch protection.

## 3. Current verification boundary

Provider-side branch protection/ruleset state MUST be independently read and verified through an authorized GitHub administrative control plane.

If the active connector cannot read or modify that setting, record the limitation. Never state that `main` is protected based solely on policy files, CODEOWNERS, CI configuration, or customary workflow.

## 4. Sensitive paths

The following paths are policy/security-sensitive and SHOULD receive explicit owner review:

```text
PRINCIPLES.md
DEVELOPMENT_POLICY.md
docs/RETENTION_POLICY.md
docs/REPOSITORY_GOVERNANCE.md
.github/**
tools/conformance_gate.py
tools/conformance_manifest.py
tools/repository_audit.py
conformance/olp-source-pin.txt
specification/**
```

A future runtime should add authorization, secret-management, retention, deployment, and side-effect-execution paths to this list.

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

## 7. Branch and milestone method

The preferred Marketplace milestone/change flow remains:

```text
issue/scope
-> dedicated branch
-> smallest coherent implementation
-> focused tests
-> repository audit
-> full conformance gate when applicable
-> PR with objective evidence
-> review
-> merge
-> verify merged-main CI
```

Policy/security changes SHOULD use the same workflow even when they are documentation-heavy because they can alter future authority and operational behavior.

## 8. No false enforcement claims

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
