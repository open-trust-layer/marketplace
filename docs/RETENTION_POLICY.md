# Marketplace Retention Policy

**Status:** Project engineering policy
**Applies to:** development tooling, coding-agent workflows, CI diagnostics, future runtime/reference-node implementations, adapters, caches, logs, temporary artifacts, and retained project context

This policy governs retention of project-scoped data. It does not change Marketplace protocol record identity or lifecycle semantics.

## 1. Governing rule

Data minimization is the default. Project content MUST NOT be retained merely because storage is convenient.

Retention classes are explicit:

```text
EPHEMERAL
OPERATIONAL_METADATA
DURABLE_PROJECT_ARTIFACT
SECURITY_INCIDENT_HOLD
```

If classification is unclear, use the shorter applicable retention until the ambiguity is resolved.

## 2. EPHEMERAL

Default maximum post-use retention: **10 seconds**.

Examples include:

- message bodies;
- prompts and responses;
- temporary extracted text;
- temporary file contents;
- process-local conversation turns;
- tool payload/result content that is not intentionally durable;
- content-bearing caches;
- content-bearing traces or diagnostics;
- temporary generated/intermediate data.

The post-use clock starts when the content is no longer required for active processing. Legitimate active use MAY refresh the deadline.

Expiry/deletion MUST be automatic rather than dependent on operator memory.

Deletion failure is a security/privacy event and MUST be surfaced rather than silently converted into indefinite retention.

## 3. OPERATIONAL_METADATA

Default project profile: **30 days**, subject to provider/environment configuration and stricter requirements.

This class MAY retain bounded metadata required for operation, security, CI traceability, or reliability, such as:

- timestamp;
- component or job name;
- correlation/request ID;
- high-level operation name;
- pseudonymous actor/target identifier where appropriate;
- duration;
- outcome/status;
- authorization decision category;
- error category;
- retention/deletion status;
- non-secret integrity references.

It MUST NOT contain message/file/prompt/response bodies, raw media, secrets, credentials, or equivalent project payload content.

Long metadata retention is never permission for long content retention.

## 4. DURABLE_PROJECT_ARTIFACT

Intentional project artifacts MAY remain durable when persistence is part of the project record. Examples include:

- source code;
- Marketplace specifications;
- tests;
- approved documentation;
- reviewed configuration;
- ADRs and project-policy documents;
- committed conformance vectors;
- reviewed build/release artifacts;
- accepted issue/PR content needed as project history, subject to provider policy and content minimization.

Persistence by accident does not make an artifact durable.

Secrets, raw transient conversation content, or temporary tool payloads MUST NOT be promoted to durable status merely by committing, logging, attaching, or copying them.

## 5. SECURITY_INCIDENT_HOLD

A security/incident hold MAY temporarily override normal deletion when preservation is necessary for an authorized investigation or legal obligation.

A hold MUST be:

- narrowly scoped;
- explicitly justified;
- owned;
- access controlled;
- reviewable;
- removable;
- time-bounded where possible.

The hold record MUST identify owner, reason, scope, approval, issued time, expiry/review time, and removal condition.

A hold does not authorize unrelated retention.

## 6. Marketplace repository mapping

The current repository is primarily specification/conformance infrastructure.

### Durable

The following are normally `DURABLE_PROJECT_ARTIFACT`:

```text
PRINCIPLES.md
DEVELOPMENT_POLICY.md
README.md
specification/**
conformance/vectors/**
docs/**
tests/**
tools/**
.github/**
LICENSE
```

This classification applies to reviewed repository artifacts, not arbitrary sensitive content placed inside them.

### Ephemeral

The following are normally `EPHEMERAL` unless explicitly promoted to an approved durable artifact:

- temporary generator output outside committed vector artifacts;
- temporary repository copies used for deterministic replay;
- local scratch files;
- transient extracted text;
- temporary diagnostic payloads;
- agent/tool message content;
- process-local conversation/history data;
- content-bearing caches.

The existing conformance gate already runs generator replay in an isolated temporary repository copy; temporary replay content SHOULD be destroyed at the end of the operation.

### Operational metadata

CI status, job timing, high-level pass/fail information, correlation IDs, and repository-audit counts MAY be `OPERATIONAL_METADATA` provided they remain content-free.

## 7. CI and provider-managed logs

Marketplace does not control every provider retention setting.

Therefore:

1. CI output MUST avoid project payload content and secrets;
2. provider-managed CI logs SHOULD contain metadata-only diagnostics;
3. longer provider retention MUST NOT be used as justification to emit content-bearing logs;
4. inability to enforce a provider-side retention setting MUST be reported as an external-control limitation rather than misrepresented as locally guaranteed.

## 7.1 Authorized Marketplace application-state MVP profile

The owner-authorized Product M17.1A source-level persistence profile is `MARKETPLACE_APPLICATION_STATE_MVP`.

It applies only to validated user-authored Marketplace records and the minimum local coordination state needed to browse, respond, and synchronize through the shared Marketplace application backend. PostgreSQL is the authoritative store for this profile.

The default and maximum content retention is **30 days** after last legitimate application use. Retention refresh is allowed only for a successful semantically valid operation that actually uses the record. Automatic startup and transaction-triggered expiry/deletion are required. Expired sync metadata MUST advance a local synchronization floor so stale cursors fail closed rather than silently missing history.

Deletion failure remains a security/privacy event and MUST be surfaced. Deleting a local application copy MUST NOT be represented as deleting an immutable protocol record from the wider world. Payload content remains prohibited from long-lived operational logs and telemetry.

This is a **source-level** authorization recorded in Issue #175. It grants **no production deployment**, no live database provisioning or administration, no migration of real-user databases, no credential issuance, and no payment, settlement, fulfillment, or other protected external side effect. A later production/deployment profile requires separate authorization and operational controls.
## 8. Future runtime requirement

Marketplace currently has no production message/conversation runtime. Before a future reference runtime accepts or persists transient content, it MUST define and test:

```text
ACTIVE_DATA
-> EXPIRED
-> DELETION_PENDING
-> DELETED | DELETION_FAILED
```

At minimum, runtime retention tests MUST cover:

- default 10-second post-use expiry;
- access/use deadline refresh when explicitly intended;
- startup cleanup of already-expired transient data where applicable;
- deletion retry behavior that cannot become silent indefinite retention;
- metadata/content separation;
- explicit authorized retention override/hold behavior;
- project-boundary isolation.

Persistent content retention beyond the default requires an explicit project design decision and authorized retention exception/profile.

## 9. Logs, metrics, traces, and provenance

Logs SHOULD use static event names and structured metadata fields.

Metric labels MUST NOT contain project payload content or secrets.

Provenance records SHOULD identify origin, time, producer/tool, transformations, classification, retention class, and integrity reference where useful, but provenance MUST NOT become a reason to retain unnecessary sensitive content.

## 10. Exceptions

Retention exceptions MUST include:

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

Expired exceptions cease to authorize retention.

## 11. Acceptance rule

A change that introduces transient data handling is incomplete unless:

- the retention class is explicit;
- automatic expiry/deletion is implemented where required;
- metadata and content are separated;
- deletion failure is observable;
- retention behavior is covered by deterministic tests where practical; and
- no provider-side retention guarantee is claimed without verification.
