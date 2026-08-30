# M61 — Inbound Record Responder Retained-Binding Hardening

## Status

Source-only HIGH security hardening for M33 `BoundedInboundRecordResponder`.

M61 does not activate a listener, construct a real socket, perform DNS/TLS, contact a peer, deploy a service, or broaden Marketplace semantic authority.

## Security problem

M59 retains the exact M33 responder and its effective preparation binding, but pre-M61 M33 retained its own disclosure, source, validation, identity, payload, and envelope capabilities as mutable instance references.

A same-process post-construction or mid-call substitution could therefore select changed authority while an upstream composition root still observed the same M33 object.

## Security objective

M61 binds M33 to the exact construction-time authority graph and fails closed when that graph drifts.

The hardening covers:

- exact local source configuration;
- exact Record source object, type, and class `get` function;
- disclosure authorizer;
- Marketplace Record validator;
- Record Identity provider;
- payload preparer;
- Record envelope maker;
- Record envelope verifier;
- M33 private binding-validation and guarded-selection method graph.

## Binding model

Callable capabilities are witnessed by object identity, exact runtime type, and the exact type-level `__call__` implementation. M61 does not compare caller-supplied capabilities with `==` or `!=`.

The Record source is separately witnessed by object identity, exact runtime type, and exact type-level `get` function. M61 invokes that captured function against the captured source object instead of resolving a replacement attribute at use time.

The responder also witnesses its reviewed private method graph and captured validation/selection functions. Instance shadowing, class substitution, or private-function rebinding therefore fails before replacement authority is selected.

Stable local drift failures are:

- `INBOUND_RECORD_BINDING_DRIFT` for retained authority/helper/call-graph changes;
- `INBOUND_RECORD_CONFIGURATION_DRIFT` for retained local-source configuration drift.

## Callback boundaries

M61 validates bindings immediately before retained capability selection and again after attacker-influenced callbacks before selecting later authority.

This includes the boundaries around disclosure authorization, local Record retrieval, Record validation, Record Identity derivation, payload preparation, envelope construction, and envelope verification.

If a callback both mutates retained authority and fails, binding drift takes precedence over reflecting arbitrary callback text.

## Preserved semantics

M61 does not change the M33 disclosure decision, Record Identity rules, Marketplace validation requirements, payload/envelope semantics, or authority-negative result facts.

Existing M33 valid behavior remains reusable and transport-free. M34 routing and M59 end-to-end source composition remain the upstream integration boundaries.

No new truth, ownership, trust, authentication, peer identity, agreement, global existence, authorization, or protected-side-effect claim is introduced.

## Tests-first provenance

The first M61 commit is tests-only and demonstrates the retained-binding gap before implementation. The initial implementation closes those cases.

HIGH self-review then identified a second issue: replacing the private captured binding-validator function could execute the replacement once before drift was detected. A second tests-only RED commit preserves that finding before the final fix.

Adversarial coverage includes post-construction and mid-call substitution, source/get replacement, helper replacement, private method poisoning, module class poisoning, binding-validator poisoning, and hostile equality callbacks.

## Performance / optimization

M61 makes no performance-improvement claim. The additional checks are security invariants and MUST NOT be removed, bypassed, cached across unsafe mutation boundaries, or weakened merely to reduce execution or CI time.

Any future optimization of this path requires representative baseline/candidate evidence while preserving the same binding, semantic, resource, retention, and security guarantees.

## Recovery and authority boundary

Recovery is an ordinary source-control revert of M61 source/tests/docs. No external state, schema, listener, peer session, credential, certificate, or durable content is created by source acceptance.

Real M55/M59 socket construction or `run_once()` remains `NETWORK_EXTERNAL` and requires fresh explicit authorization immediately before execution. Production activation remains separately `DEPLOY`.
