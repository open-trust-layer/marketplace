# Milestone 50 — Bounded Inbound HTTP Request/Response Transaction

## Status and purpose

M50 composes the already-reviewed bounded inbound request/read response-preparation boundary with the bounded response-write chain.

```text
M43 prepare -> M44 plan -> M45 transition -> M46 session
            -> M47 outcome -> M48 invoke -> M49 driver -> M50 detached result
```

M50 is HIGH source-only / I/O-adjacent. It owns no socket, TLS stack, listener, deployment, process, address, credential, or concrete transport.

## One-shot composition

`BoundedInboundHttpRequestResponseTransaction` is one-shot. It captures one exact M43 preparer, one injected writer, one injected monotonic clock, and detached M44/M49 limits at construction.

`run()` contains no loop. It invokes the construction-bound M43 `prepare()` at most once, constructs the existing M44→M49 write chain around that exact prepared response, and calls the construction-captured M49 driver once. M49 alone owns the finite write orchestration loop.

The transaction marks itself used before consuming preparation authority. Success or failure is terminal; no automatic retry is performed.
## Construction and drift binding

M50 freezes the exact M43 `prepare`, `close`, and `used` functions plus the public M44–M49 method graph present at construction. A reader or writer callback cannot silently substitute a later public method and have it treated as original authority.

M44 write limits and optional M49 driver limits are detached at construction. Explicit M49 steps may not exceed the retained M44 write-call ceiling plus the one zero-writer completion-transfer step.

M43 and M49 outputs are independently integrity-replayed. The M49 completion must bind the exact M43 prepared-response integrity witness and locally account exactly the prepared response length.

## Failure provenance and cleanup

M43 rejection is surfaced as stable `TRANSACTION_PREPARATION_REJECTED` while preserving read-driver, invocation, outcome, session, transition, plan, stream, and wire reason metadata.

M49 rejection is surfaced as stable `TRANSACTION_WRITE_REJECTED` while preserving write-driver, invocation, outcome, session, transition, and write-plan reason metadata. Arbitrary reader/writer/clock exception text is not reflected.

Terminal paths close the captured M43 read state and verify its request prefix is cleared. Once M46 exists, terminal failure also closes the exact M46 session and verifies that its retained M43 response reference is released. Unverifiable cleanup is reported as `TRANSACTION_CLEANUP_UNCERTAIN` rather than claimed as successful.
## Detached completion result

The public M50 result intentionally does **not** retain the M43 prepared object, M49 completion object, raw request prefix, raw response bytes, or their byte-bearing nested integrity tuples.

It retains bounded route/status metadata, read/write accounting, elapsed write-driver time, and two SHA-256 integrity digests. Digesting streams exact integrity values into SHA-256 under finite recursion/item ceilings; the result stores only lowercase hexadecimal digests.

Local write completion means only that the injected writer returned accepted counts covering the prepared response under M44–M49 semantics. It is not peer-receipt or transmission evidence.

## Authority boundary

Successful M50 completion leaves all of these facts false:

```text
socket_access_proven = False
network_origin_proven = False
tls_terminated = False
transmitted = False
request_authenticated = False
peer_identity_proven = False
establishes_marketplace_truth = False
establishes_trust = False
establishes_authorization = False
authorizes_protected_side_effects = False
```

## Explicitly out of scope

No concrete socket/read/recv/send/write transport, connect/bind/listen/accept, TLS termination, HTTP server, keep-alive loop, concurrent request processing, retry/backoff, deployment/service activation, filesystem persistence, durable logging, credentials, provider administration, settlement/payment, or protected economic side effect is introduced.

Acceptance uses deterministic in-memory reader, writer, and clock doubles only. A real network-backed reader/writer remains a separate live-I/O capability boundary requiring separate authorization immediately before execution.

## Retention and recovery

All request/response material, nested preparation/write objects, temporary integrity hashing inputs, and accounting are EPHEMERAL and must be released within 10 seconds post-use. The detached public result contains no raw request or response bytes.

Recovery is ordinary source revert. M50 source acceptance mutates no external marketplace, peer, payment, credential, or deployment state.