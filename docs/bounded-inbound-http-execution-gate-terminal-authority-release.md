# M64 — Loopback Execution Gate Terminal Authority-Release Hardening

## Status and scope

M64 is a HIGH source/security hardening change for the existing M62/M63 `BoundedInboundHttpLoopbackExecutionGate`.

It changes only terminal reference release. It does not alter the public constructor, `dry_run()`, `execute_once()`, `close()`, the exact opt-in token, the M59 -> M55 graph, one-shot limits, result semantics, or failure-code policy.

M64 does not construct a real socket, bind/listen/accept/connect, perform DNS/TLS, contact a peer, deploy a service, access credentials, or broaden Marketplace semantic authority.

## Security finding

M63 releases nearly all construction-retained execution and policy authority when the gate becomes terminal. Three reviewed references remained live after terminal cleanup even though later execution is impossible and those references are no longer needed:

- `_error_type`;
- `_bounded_lower_code_function`;
- `_fail_function`.

Keeping unnecessary capability-bearing references after terminal use increases retained authority without providing operational value.

## M64 invariant

Every terminal path now clears those three residual references together with the already-released source root, policy values, class/method graph, downstream error/class authority, and binding witness.

Covered terminal paths are:

- network-inert `dry_run()` completion;
- successful deterministic `execute_once()` completion;
- failed deterministic `execute_once()` completion;
- explicit `close()` before use.

A later call remains terminal and still raises stable `LOOPBACK_EXECUTION_EXHAUSTED`; terminal release is not a mechanism for reopening or weakening the gate.

## Tests-first provenance

The tests-only M64 specification is commit `177d5e574e9a61e8aab848ab8087863606c33c00`.

Against unchanged merged M63 source it produced five failing test scenarios and fifteen failed assertions: each terminal scenario retained all three residual reviewed authority references.

The smallest implementation is commit `6f75d7917421a522ca50468858498274eb71b29d`. It adds only three terminal assignments to `None`. The same M64 suite then passes 5/5, and the existing M62/M63/manual-tool compatibility set passes 29/29.

## Security and semantic boundaries

Terminal release does not establish network authorization, deployment authorization, peer identity, authentication, truth, ownership, agreement, trust, global existence, or protected-side-effect authority.

The exact M62 execution token remains defense in depth, not project/user authorization. Actual invocation with a real operating-system socket constructor remains a separate `NETWORK_EXTERNAL` event requiring fresh explicit authorization immediately before execution. Production/service activation remains separately `DEPLOY`.

No raw request, response, Record identity, credential, cursor, or peer content is added to retained state, output, logs, or documentation by M64. Existing EPHEMERAL retention policy remains unchanged.

## Performance / optimization

No performance improvement is claimed. The change reduces unnecessary terminal reference retention; it must not be used to justify weakening validation, one-shot behavior, cleanup, or conformance gates.

## Recovery / blast radius

Recovery is an ordinary source-control revert of the M64 source/tests/documentation. Source acceptance creates no listener, port, peer connection, service, deployment, credential, certificate, schema, durable content, or protected external effect.

The blast radius is limited to the terminal in-memory state of one already-used or explicitly closed execution-gate instance.
