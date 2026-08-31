# M66 — Loopback Execution Gate Begin-Binding Hardening

## Status and scope

M66 is a HIGH source/security hardening change for the existing M62-M65 `BoundedInboundHttpLoopbackExecutionGate`.

It hardens the private begin-once dispatch binding and the already-established terminal `LOOPBACK_EXECUTION_EXHAUSTED` error construction. It does not alter the public constructor, `dry_run()`, `execute_once()`, `close()`, the exact opt-in token, the M59 -> M55 graph, one-shot limits, result semantics, or authorization boundaries.

M66 does not construct a real socket, bind/listen/accept/connect, perform DNS/TLS, contact a peer, deploy a service, access credentials, or broaden Marketplace semantic authority.

## Security finding

On exact merged M65 baseline `d0847e19e91010e6333f443bcc0afc669d373022`, both public entrypoints dynamically invoked `self._begin_once()` before reviewed binding validation reached the begin helper itself.

`_begin_once` was not retained in `__slots__`, not represented in `_binding_witness`, and not checked in the execution-gate helper graph. A class-function or descriptor substitution could therefore execute attacker-selected code immediately from `dry_run()` or `execute_once()` before the existing retained validator could reject drift.

A pure in-memory probe confirmed hostile `_begin_once` execution while the source root remained unused and the gate remained open. No live network or deployment authority was exercised.

## M66 invariant

Construction now retains the exact reviewed `_begin_once` function as `_begin_once_function` and appends that identity to the binding witness without moving M65's reviewed release function from witness index 26.

The binding validator requires the retained begin function, witness entry, and raw class-dictionary `_begin_once` entry to be the same reviewed function. Descriptor lookup is never used for this comparison.
Before either public entrypoint invokes begin-once, it first verifies and runs the already-retained binding validator. Only after that validation succeeds does it invoke the captured reviewed begin function directly as `begin(self)`; `self._begin_once()` dynamic dispatch is removed from the public paths.

The reviewed `_release()` implementation clears `_begin_once_function` together with the other retained authorities. M65 close recovery continues to use release witness index 26 and now recognizes the 28-entry witness.

Terminal second calls still fail with stable `LOOPBACK_EXECUTION_EXHAUSTED` after retained callable authority has been released. A bounded non-callable error template anchors the original reviewed error type, and a fresh terminal exception is allocated through `BaseException` primitives rather than consulting the mutable module error-class name. The M64 `_error_type`, `_bounded_lower_code_function`, and `_fail_function` fields still release to `None`.

## Tests-first provenance

The tests-only M66 specification is commit `28aa1d33f1c8b61bc674e9eccfed70b8bdc8834e`.

Against unchanged merged M65 source it produced three failures and one error:

- hostile class `_begin_once` executed from `dry_run()`;
- hostile class `_begin_once` executed before the injected constructor in `execute_once()`;
- hostile `_begin_once` descriptor `__get__` executed;
- direct retained-begin poisoning could not yet be expressed because no retained begin slot existed.

The implementation commit is `568006b45c125a0ef025ff3bb4c9701504929ec4`. The first focused regression run exposed two compatibility regressions before commit acceptance: M65 close recovery still required witness length 27, and post-release second calls attempted to read cleared retained validation state before producing the established exhausted error. Both were corrected in the same implementation before it was committed.

The initial M62-M66 execution-gate regression set passed 35/35, and broad inbound coverage passed 677/677 before the late terminal-rebinding review.

A later tests-only security commit, `6c7f8d8f1f1ff9792d229bdb731682e8a979b01e`, added a fifth M66 adversarial case proving that a post-terminal call could still consult a rebound module `InboundHttpLoopbackExecutionGateError` constructor. The follow-up source fix is `40babe6e68ff356dc39b5b5e8666ffc496e42ad8`; it preserves M64 terminal callable release while recovering the stable exhausted error from a non-callable type anchor. Final post-fix regression and conformance counts are recorded only after self-hosted CI.

## Security and semantic boundaries

M66 does not establish network authorization, deployment authorization, peer identity, authentication, truth, ownership, agreement, trust, global existence, or protected-side-effect authority.
The exact M62 execution token remains defense in depth, not project/user authorization. Actual invocation with a real operating-system socket constructor remains a separate `NETWORK_EXTERNAL` event requiring fresh explicit authorization immediately before execution. Production/service activation remains separately `DEPLOY`.

No raw request, response, Record identity, credential, cursor, or peer content is added to retained state, output, logs, or documentation by M66. Existing EPHEMERAL retention policy remains unchanged.

## Performance / optimization

No throughput or latency improvement is claimed. M66 adds one constant-size retained function identity, one witness entry, one bounded non-callable terminal error template, and constant-size validation/allocation steps. It removes two dynamic begin-method lookups from public execution paths and avoids mutable module constructor lookup on terminal second calls.

The optimization evidence is therefore limited to reduced dynamic dispatch ambiguity and deterministic begin-authority selection; no quality, security, integration, package, or conformance gate is weakened or renamed.

## Recovery / blast radius

Recovery is an ordinary source-control revert of the M66 source/tests/documentation. Source acceptance creates no listener, port, peer connection, service, deployment, credential, certificate, schema, durable content, or protected external effect.

The blast radius is limited to begin-once dispatch and retained in-memory binding state of one execution-gate instance.
