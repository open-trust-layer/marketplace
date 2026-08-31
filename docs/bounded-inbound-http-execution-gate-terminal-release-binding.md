# M65 — Loopback Execution Gate Terminal Release-Binding Hardening

## Status and scope

M65 is a HIGH source/security hardening change for the existing M62-M64 `BoundedInboundHttpLoopbackExecutionGate`.

It changes only terminal cleanup binding. It does not alter the public constructor, `dry_run()`, `execute_once()`, `close()`, the exact opt-in token, the M59 -> M55 graph, one-shot limits, result semantics, or failure-code policy.

M65 does not construct a real socket, bind/listen/accept/connect, perform DNS/TLS, contact a peer, deploy a service, access credentials, or broaden Marketplace semantic authority.

## Security finding

M64 clears construction-retained execution and policy authority when the gate becomes terminal, but the cleanup method itself was still dynamically resolved through `self._release()`.

The reviewed `_release` implementation was not retained in the binding witness. A class-level `_release` substitution before invocation was therefore not detected by `_validate_bindings()`. More importantly, the caller-supplied constructor could mutate the gate class `_release` binding during the one-shot path; the finalizer would then resolve and execute the substituted function instead of the reviewed cleanup authority.

The M65 RED specification demonstrates all four relevant cases, including pre-call dry-run and execute substitution, constructor-time mutation, and explicit close.

## M65 invariant

Construction now retains the exact reviewed `_release` function and includes it in the existing binding witness and helper-graph validation.

After `_begin_once()` has validated the graph, `dry_run()` and `execute_once()` capture that reviewed release function before any caller-supplied constructor can execute. Their terminal `finally` blocks invoke only the captured function.

`close()` likewise captures the retained reviewed release function before validation and uses that exact function for cleanup. A pre-call class drift is ignored only under the existing close semantics after validation reports drift; substituted cleanup code is never invoked.

The reviewed `_release()` implementation clears `_release_function` itself together with the other retained authorities, so M65 does not add residual terminal authority.

## Tests-first provenance

The tests-only M65 specification is commit `aa225849b77afa93c98f06bd8e42289839a75f31`.

Against unchanged merged M64 source it produced four failures. Every failure showed the substituted `_release` function executing, including the caller-supplied constructor mutation path.

The smallest implementation is commit `ac51240b7dd91c37428de1974219aad3a2f225dc`. It adds one retained cleanup binding, one witness entry, validation of that binding, local use of the reviewed function on terminal paths, and terminal release of the retained reference.

The focused M62-M65 plus manual-tool compatibility set passes 38/38 after the implementation.

## Security and semantic boundaries

M65 does not establish network authorization, deployment authorization, peer identity, authentication, truth, ownership, agreement, trust, global existence, or protected-side-effect authority.

The exact M62 execution token remains defense in depth, not project/user authorization. Actual invocation with a real operating-system socket constructor remains a separate `NETWORK_EXTERNAL` event requiring fresh explicit authorization immediately before execution. Production/service activation remains separately `DEPLOY`.

No raw request, response, Record identity, credential, cursor, or peer content is added to retained state, output, logs, or documentation by M65. Existing EPHEMERAL retention policy remains unchanged.

## Performance / optimization

No performance improvement is claimed. M65 adds constant-size binding checks and removes a dynamic cleanup-method lookup from terminal paths. The security objective is deterministic cleanup authority, not throughput or latency improvement, and no quality/security/integration gate may be reduced on performance grounds.

## Recovery / blast radius

Recovery is an ordinary source-control revert of the M65 source/tests/documentation. Source acceptance creates no listener, port, peer connection, service, deployment, credential, certificate, schema, durable content, or protected external effect.

The blast radius is limited to cleanup dispatch and retained in-memory binding state of one execution-gate instance.
