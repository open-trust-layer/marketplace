# Milestone 48 — Bounded Inbound HTTP Response Write Invocation

## Status

M48 gives one injected writer capability a bounded, one-step source contract above M47.

```text
M46 state <- M47 outcome <- M48 one injected writer call
```

M48 owns no socket, TLS stack, listener, deployment, or concrete transport. Acceptance uses deterministic in-memory writer doubles only.

## Construction binding

`BoundedInboundHttpResponseWriteInvoker` requires one exact M47 handler and one callable writer. It captures exact M47 progress/accept/take/close/closed functions, exact M46 cleanup functions, the M47→M46 graph, and the exact M43 prepared-response identity/integrity present at construction.

Public method replacement after construction cannot substitute these captured functions. Private binding drift fails closed.

## One-step semantics

`invoke_once()` performs zero or one writer calls and contains no loop or retry.

If M46 is already locally COMPLETE, M48 transfers the one-shot M46 completion through M47 and invokes no writer.

For WRITE state M48:

1. validates current M47/M46 state;
2. validates original M43 authority-negative fields before replay;
3. derives the exact current response slice `response[bytes_written:bytes_written+next_write_bytes]`;
4. calls the construction-bound writer exactly once with that immutable slice;
5. validates bindings again after the writer returns;
6. requires an exact M47 outcome and validates original authority-negative fields before replay;
7. delegates the outcome exactly once to M47;
8. independently cross-checks accepted bytes and write-call accounting.

The offered slice is EPHEMERAL and is never retained in an M48 result or witness.

## Terminal writer outcomes

Writer exception text is never reflected. Exceptions become a generic terminal failure and M46 state is cleared when captured cleanup authority remains intact.

Non-exact writer returns, ZERO/FAILURE, oversized or otherwise rejected already-returned progress, post-writer binding drift, and hostile authority promotion are non-retryable terminal paths.

After a writer has been invoked, cleanup uses the construction-captured exact M46 close boundary directly. If that cleanup authority itself has drifted or cannot be verified, M48 reports `WRITE_INVOCATION_CLEANUP_UNCERTAIN` rather than falsely claiming erasure.

## Completion

A final successful writer count still returns `WRITE_INVOCATION_PROGRESS`. A later `invoke_once()` observes M46 COMPLETE and transfers completion without another writer call. This avoids synthesizing an extra write result.

M48 clears its own retained M43 reference whenever the underlying session becomes terminal or completion is transferred.

## Authority boundary

`writer_invoked=True` means only that the injected callable returned control to M48. It does **not** establish:

```text
socket_access_proven = False
tls_terminated = False
transmitted = False
request_authenticated = False
peer_identity_proven = False
establishes_marketplace_truth = False
establishes_trust = False
establishes_authorization = False
authorizes_protected_side_effects = False
```

In particular, an accepted byte count is local accounting, not proof that bytes reached a peer.

## Explicitly out of scope

No socket creation, connect/bind/listen/accept, concrete send/write transport, TLS, HTTP server, process, filesystem, persistence, logging, concurrency, deployment, credential handling, external service activation, or live network execution is introduced by M48.

A real network-backed writer remains a separate live-I/O boundary requiring separate authorization immediately before execution.

## Retention and recovery

All response references, offered slices, outcomes, progress, completion, and witnesses are EPHEMERAL and must be released within 10 seconds post-use. M48 does not claim automatic wall-clock deletion without caller lifecycle cooperation.

Recovery is ordinary source revert. No external state is mutated by M48 acceptance tests.
