# Marketplace Development Policy

**Status:** Project engineering policy
**Applies to:** repository development, coding agents, maintainers, CI, conformance tooling, future runtime code, adapters, deployment work, and project governance
**Policy basis:** portable provisions adapted from Coding Agent Development Principles v1.3
**Semantic authority:** `PRINCIPLES.md` remains authoritative for Marketplace protocol/semantic constraints

This policy governs **how Marketplace is developed**. It does not redefine Marketplace protocol semantics and MUST NOT weaken `PRINCIPLES.md`, the numbered Marketplace specifications, or applicable Open Layer Protocol requirements.

Repository-specific controls from another project are not imported as facts. In particular, controls described specifically for `ai-automation-department` are treated as source examples unless Marketplace explicitly adopts an equivalent rule here.

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

A material security control MUST NOT be weakened merely to make a test pass, silence an error, preserve unsafe compatibility, simplify implementation, or ship faster.

Known material security, privacy, project-isolation, unauthorized-retention, or governance defects prevent a change from being declared complete unless an explicit authorized, scoped, owned, expiring exception exists.

## 2. Project and semantic boundaries

Marketplace development MUST preserve two independent boundary sets:

1. **Marketplace semantic boundaries** in `PRINCIPLES.md` and the specifications; and
2. **engineering safety boundaries** in this policy.

Project-scoped files, credentials, messages, prompts/responses, logs, caches, tool state, indexes, derived data, generated artifacts, and retained context MUST NOT cross into another project by default.

An authorized cross-project flow MUST identify source, destination, purpose, minimum necessary data, required capabilities, retention, and access controls.

## 3. Security invariants

The following invariants apply to current tooling and future runtime code:

1. Unauthorized input cannot trigger protected side effects.
2. Secrets do not enter source control, logs, messages, telemetry, crash output, screenshots, diagnostics, vectors, or test fixtures.
3. Ephemeral project content does not outlive its retention deadline without an authorized exception or hold.
4. Untrusted input cannot directly become executable code, shell commands, queries, paths, templates, or network destinations without safe construction and validation.
5. TLS certificate and hostname verification are not disabled for convenience.
6. Privileged or destructive targets are re-verified immediately before execution.
7. Security failures fail closed where authorization or protected side effects are involved.
8. Dependencies do not gain trust merely because they are convenient.
9. Green tests do not override a known material security defect.
10. Deletion, encryption, isolation, authorization, CI, or branch-protection guarantees are never claimed without verification.
11. Content-bearing logs do not silently inherit metadata-only long retention.
12. Repository policy files do not prove provider-side branch/ruleset enforcement.

Where practical, invariants SHOULD be encoded as tests, guards, types, validators, or architecture constraints.

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
- **MODERATE** — dependency changes, external network reads, broad refactors, non-production configuration, or security/governance documentation changes.
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

Use bounded collection sizes, explicit timeouts, concurrency limits, quotas, safe path handling, parameterized queries/builders, subprocess argument arrays instead of shell interpolation, SSRF defenses for user-controlled URLs, and non-code-executing deserializers.

Do not add arbitrary shell, filesystem, network, package-installation, deployment, secret, or administrative flexibility merely because it is easy to expose.

## 9. Secrets and dependencies

Secrets MUST NOT be hard-coded or printed to prove they exist. Prefer scoped short-lived credentials and managed secret injection.

A new dependency is executable trust. Admission requires a concrete need and review of maintenance, provenance/publisher, transitive footprint, vulnerabilities, permissions/install scripts, license/policy fit, and safer alternatives. Reproducible resolution and official registries are preferred.

Unreviewed remote scripts MUST NOT be piped directly to a shell.

## 10. Retention and data minimization

Every project-scoped file, message, prompt/response, tool payload/result, cache, trace, telemetry item, temporary artifact, and log MUST have a retention class defined by `docs/RETENTION_POLICY.md`.

The default maximum post-use retention for `EPHEMERAL` content is **10 seconds**.

Durable repository source, specifications, tests, approved documentation, reviewed configuration, and accepted conformance artifacts are `DURABLE_PROJECT_ARTIFACT` by intent. Persistence by accident does not make content durable.

Current Marketplace is a specification/conformance repository and does not yet provide a production conversation/message runtime. Future runtime/reference-node milestones MUST implement automatic retention/expiry behavior before content-bearing transient storage is accepted.

## 11. Logging, diagnostics, provenance, and metrics

Logs SHOULD be structured and metadata-only by default. Message/file/prompt/response bodies, raw media, secrets, and equivalent project payloads MUST NOT be placed into long-lived operational logs.

Useful audit metadata includes correlation ID, operation, pseudonymous actor/target identity where appropriate, authorization result, high-level outcome, error type, duration, retention class, and deletion/expiry result.

Diagnostics MUST distinguish fact, inference, confidence, and unknown conditions and MUST NOT overclaim.

Security-sensitive build/release artifacts SHOULD use checksums, signatures, attestations, or equivalent provenance where supported.

## 12. Testing and acceptance

Unit tests SHOULD be deterministic, offline, isolated, and repeatable. External behavior belongs in deliberate integration/contract/end-to-end tiers.

Every bug fix requires a regression test where safely reproducible. Security defects require negative/security regressions where appropriate.

Marketplace retains its existing semantic acceptance authority:

```text
python tools/conformance_gate.py --olp-root <path-to-pinned-olp-checkout>
```

A semantic increment is not complete unless all applicable registered conformance vectors remain green and deterministic generator replay succeeds.

Green tests are necessary but not sufficient: known material security defects still block completion.

## 13. Development method

For each meaningful increment:

1. resolve the exact repository/project/branch target;
2. inspect current implementation, tests, interfaces, callers, configuration, relevant specifications, security/retention policy, and docs;
3. define behavior to change and behavior to preserve;
4. classify risk;
5. identify minimum capabilities;
6. identify trust, privacy, retention, project-isolation, and side-effect boundaries;
7. place responsibility in the correct architectural layer;
8. add/update deterministic, regression, negative-security, and retention tests as applicable;
9. implement the smallest coherent safe change;
10. apply the destructive-action protocol when relevant;
11. run focused tests;
12. run repository audit and applicable quality/security/governance checks;
13. run the full Marketplace conformance gate when the change can affect acceptance behavior;
14. review security invariants, project isolation, provenance, retention, and provider-control claims;
15. open/update a reviewable pull request; and
16. report changed files, behavior, tests, risk, capabilities, security/retention impact, and unresolved external controls.

The established milestone workflow remains preferred:

```text
issue/scope
-> milestone branch
-> specification or implementation
-> deterministic vectors/tests
-> documentation
-> unified acceptance gate
-> pull request with objective evidence
-> review
-> merge
-> verify merged-main CI
```

## 14. Small coherent changes and read-before-edit

Inspect code and policy before editing unfamiliar areas. Do not claim files/functions/controls/tests exist or pass unless verified.

Prefer small coherent changes with one architectural purpose, relevant tests, stable unrelated behavior, easy review/revert, and no silent privilege or retention expansion.

Existing architecture SHOULD be followed unless it is demonstrably unsafe.

## 15. Repository governance

Repository-governance requirements are defined in `docs/REPOSITORY_GOVERNANCE.md`.

`.github/CODEOWNERS`, pull-request templates, CI, and repository audits are governance-as-code. They do **not** prove remote GitHub branch protection or rulesets are active.

Provider-side enforcement MUST be independently configured and verified through an authorized administrative control plane before it is described as enforced.

## 16. Exceptions

Security, retention, project-isolation, capability, and governance exceptions MUST record:

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

## 17. Completion standard

The preferred solution is the smallest safe solution that preserves Marketplace semantic constraints, minimizes privilege and retained data, validates trust boundaries, controls side effects, remains testable/recoverable, preserves provenance, and makes unsafe states difficult to represent.

A change MUST NOT be declared complete while a known material security defect, privacy violation, project-isolation breach, unauthorized retention condition, expired exception, required failing quality gate, or falsely claimed remote security control remains unresolved without an explicit authorized exception.
