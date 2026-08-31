# M63 — Loopback Execution Gate Retained Opt-In & Module-Binding Hardening

## Status

Source-only HIGH security hardening for the M62 `BoundedInboundHttpLoopbackExecutionGate`.

M63 does not construct a real socket, bind/listen/accept/connect, perform DNS/TLS, contact a peer, deploy a service, or broaden Marketplace semantic authority.

## Security problem

M62 correctly required the exact execution token before a caller-supplied constructor could reach the one-shot M59 → M55 path, but the token comparison still consulted the mutable module global `LOOPBACK_EXECUTION_OPT_IN` at execution time.

Its binding validator also consulted mutable module-level class, marker, helper, error/result type, and class-method authority through ordinary Python attribute lookup.

A same-process post-construction rebinding could therefore change the accepted token or execute poisoned equality, helper, result-type, or descriptor behavior before M62 rejected the drift.

## Security objective

M63 binds the execution gate to the exact reviewed construction-time policy and module authority graph, then fails closed before replacement authority can execute.

The retained policy covers the canonical opt-in token, binding/graph markers, lower-code bound, error/readiness types, offline constructor type, failure/bounding helpers, class snapshot helper, M59/M55 exception types, source-root type, M55 type, completed-result type, and the M62 public/private method graph.

## Binding model

The canonical M62 opt-in value is retained separately from the mutable public module binding. Validation requires both the retained value and current module export to remain exact `str` values with the reviewed content before `execute_once()` evaluates caller input.

Marker and numeric policy fields are type-checked before value comparison, so attacker-controlled `__eq__` / `__ne__` implementations are never selected.

Reviewed callable/type authorities are compared by identity. The retained `_fail` helper captures its reviewed error type and lower-code helper in function defaults, allowing binding drift to be reported without executing a poisoned module-level replacement.

Class-method integrity checks use raw class `__dict__` entries instead of normal descriptor-dispatching attribute access. This prevents hostile `__get__` execution when M62, M59, or M55 class methods are replaced after gate construction.

Stable drift failure remains:

- `LOOPBACK_EXECUTION_BINDING_DRIFT`

Existing M62 operational failures and lower-code redaction remain unchanged.

## Callback boundaries

M63 validates retained authority before execution policy selection, after M59 composition, after M55 `run_once()`, and after successful orchestrator cleanup before a successful result is returned.

Dry-run similarly revalidates after composition and after cleanup before constructing its authority-negative readiness result.

If a callback mutates later execution authority, drift is detected before that later authority is selected. Arbitrary callback exception text remains redacted.

## Preserved semantics

M63 does not change the public M62 constructor, `dry_run()`, `execute_once()`, or `close()` surface. It does not change the exact opt-in token, fixed M55 loopback host, one-shot listener/session/transaction limits, M59 composition path, response semantics, or authority-negative facts.

Dry-run remains network-inert. Deterministic injected-constructor tests remain the only execution path used by source/CI acceptance.

No new truth, ownership, trust, authentication, peer identity, authorization, agreement, global existence, or protected-side-effect claim is introduced.

## Tests-first provenance

The first M63 commit is tests-only and demonstrates six concrete post-construction module-policy failures: opt-in rebinding, marker equality poisoning, gate-class poisoning, failure-helper poisoning, and readiness-type poisoning.

After the initial binding fix, HIGH self-review identified a second issue: ordinary class attribute lookup could execute a poisoned descriptor before the retained validator rejected class-method drift. A second tests-only RED commit preserves that finding before the descriptor-safe fix.

Adversarial coverage therefore includes token rebinding, hostile equality, module class/helper/result-type poisoning, private retained authority drift, and descriptor poisoning across the M62/M59/M55 class graph.

## Performance / optimization

M63 makes no performance-improvement claim. The added checks are security invariants and MUST NOT be removed, bypassed, cached across attacker-influenced boundaries, or weakened merely to reduce execution or CI time.

Any future optimization requires baseline/candidate evidence while preserving identical opt-in, binding, one-shot, semantic, resource, retention, privacy, and security guarantees.

## Recovery and authority boundary

Recovery is an ordinary source-control revert of M63 source/tests/docs. Source acceptance creates no listener, port, peer connection, service, deployment, credential, certificate, schema, durable content, or protected external effect.

Actual invocation of the manual M62 harness with a real operating-system socket constructor remains a separate `NETWORK_EXTERNAL` event requiring fresh explicit authorization immediately before execution.

The harness token is defense in depth and is not project/user authorization. `NETWORK_EXTERNAL` does not authorize `DEPLOY`; production/service activation remains separately governed.
