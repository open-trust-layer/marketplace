# M45 — Bounded Inbound HTTP Response Write Transition

M45 validates one **already-returned** positive response-write count against the exact construction-bound M44 plan. It advances local `write_calls_completed` and `bytes_written` exactly once and independently derives the next M44 plan.

This is still transport-free. The accepted count is local accounting supplied after some future boundary; it is **not proof that bytes reached a socket, network stack, kernel buffer, peer, requester, or remote application**. M45 therefore keeps `writer_invoked`, `socket_accessed`, `tls_terminated`, `transmitted`, authentication, trust, authorization, and protected-side-effect authority facts false.

M45 stores no raw response bytes. Its immutable transition contains only the accepted positive count, cumulative local counters, and integrity-replayed prior/next M44 plan witnesses.

## Fail-closed rules

- exact M44 planner type and construction-time limits are bound;
- captured M44 plan method rebinding/configuration drift fails closed;
- current M44 plan must be `WRITE`;
- accepted count must be an exact positive integer (boolean is rejected);
- accepted count may not exceed the exact current `next_write_bytes` or remaining response;
- call count increments exactly once and byte count increments exactly by the accepted count;
- next M44 plan must bind the same M43 prepared-response integrity witness;
- low-level nested authority promotion is rejected before canonical `dataclasses.replace()` replay;
- M44 rejection code is preserved as nested reason metadata.

## Retention

All M43/M44/M45 request/response/planning material remains **EPHEMERAL**, maximum 10 seconds post-use. M45 adds no persistence, logging, journal, checkpoint, file, process, thread, timer, background worker, retry, or network surface.

## Out of scope

Writer invocation, concrete socket send, partial-write transport outcome classification, listener/TLS, connection transaction, deployment, and live peer execution are later boundaries.