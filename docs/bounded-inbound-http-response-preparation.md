# Bounded Inbound HTTP Response Preparation (M43)

## Status and purpose

M43 is a transport-free, one-shot bridge from the completed M42 inbound read driver to the existing M35/M34 in-memory response-preparation path. It takes no caller-supplied request bytes, read count, reader, socket, writer, transport, credential, or deployment handle.

The runtime answers one narrow question: after the exact construction-bound M42 chain has produced a verified complete M39 request handoff, can Marketplace independently replay completion under the retained M37/M36 authority, prepare one exact M35 response, and stop before transmission?

## Construction binding

`BoundedInboundHttpResponsePreparer` accepts one exact `BoundedInboundHttpReadDriver`. At construction it derives and retains the exact M39 session, M37 planner, M36 assembler, M35 wire adapter, and M34 application adapter beneath that driver. It snapshots M37/M36/M35/M34 limits and the configured M35 Host authority, captures exact method/function bindings, and records one construction witness.

The preparer captures the original M42 `run_to_completion`/`close`, the exact M39 `close` cleanup primitive, M37 `plan`, M35 private parser, M35 `prepare`, and M35 private application-response validator. Public method replacement after construction cannot substitute those captured call paths. Configuration or binding drift fails closed.

## One-shot preparation flow

`prepare()` performs these steps exactly once:

1. validate the construction binding; if a pre-run drift is detected, mark the preparer terminal and clear any retained partial M39 prefix through the construction-captured exact M39 cleanup before returning the drift error;
2. mark the preparer used and call the captured M42 `run_to_completion()` once, with no retry;
3. require exact M42/M39 completion types, integrity replay, and authority-negative facts;
4. obtain the exact completed immutable M39 prefix from that one-shot handoff;
5. independently invoke the captured M37 planner on the exact prefix and cumulative M39 read count;
6. require exact `COMPLETE` and exact witness equality with the M39 completion plan;
7. independently parse the completed prefix through the captured original M35 parser;
8. call the captured M35 `prepare()` once on that same aggregate prefix;
9. require exact M35 result type, Host binding, authority-negative facts, request equality with the independent parse, and original M35 integrity replay;
10. reconstruct the canonical M34 response represented by the M35 wire result and replay it through the construction-captured original M35 application-response validator;
11. return one immutable `PreparedInboundHttpReadResponse` with the exact M35 prepared exchange, replayed M37 completion plan, and bounded M42/M39 accounting.

There is no fallback preparation path and no retry after any M42, M37, or M35 failure.

## Terminal cleanup and partial-state safety

An M43 instance may be constructed around a legitimate M42/M39 chain that already contains a partial request. Therefore a binding or configuration failure detected **before** M42 starts cannot merely return while leaving that prefix resident.

M43 captures the exact original `BoundedInboundHttpReadSession.close` binding at construction. On pre-run M43 drift, it marks the preparer used, invokes that captured M39 cleanup directly, and verifies that the retained session reports its private raw prefix as `b""` and its closed marker as exact `True`. Only after verified cleanup does M43 preserve the original binding/configuration failure.

If the captured cleanup binding itself has drifted, cleanup raises, or cleared/closed state cannot be verified, M43 reports `RESPONSE_PREPARATION_CLEANUP_UNCERTAIN` rather than claiming the request was erased. Explicit `close()` uses the same construction-captured M39 cleanup path and remains idempotent even when downstream M35/M34 configuration has drifted.

This direct cleanup path is lifecycle-only authority: it can clear the already-owned local M39 prefix but cannot read a socket, prepare or transmit a response, authenticate a requester, or authorize any external effect.

## Aggregate-prefix rule

M43 deliberately does **not** call `M36.prepare_chunks((prefix,))` with the final aggregate request prefix. M36's `max_chunk_bytes` is a historical per-read/per-chunk bound, while the M42/M39 prefix is the aggregate of all accepted chunks. Treating the aggregate as one synthetic historical chunk could reject a valid multi-read request. M43 instead replays aggregate completeness through M37/M36 and invokes M35 preparation directly on the already-complete aggregate request.

## Accounting semantics

`reader_invocations` retains M42's local count of M41 results that reported `reader_invoked=True` during that M42 run. `reads_completed` retains cumulative M39 local accounting and can therefore exceed M43-observed reader invocations for a session that was already partially or fully populated before M42 ran. Neither value proves external network I/O occurred.

`request_bytes` is not free-standing caller metadata: the result requires it to equal the replayed M37 COMPLETE plan's `buffered_bytes`. `response_bytes` must equal the exact M35 response-wire length.

The result contains no completed raw-request-prefix field. The nested M35 exchange retains the canonical parsed request and prepared response bytes required by the existing reviewed M35 contract; M43 does not add another raw aggregate request copy.

## Mid-call response-validator hardening

M35 `prepare()` internally calls its application adapter and then its response validator. A hostile same-process callback could otherwise try to replace the class validator temporarily, use it during `prepare()`, and restore it before M43's post-call binding check.

M43 closes that substitution path without invoking M34 twice: after M35 returns, M43 reconstructs the canonical application-response value represented by the framed wire result and replays that value through the **construction-captured original M35 response validator** against the independently parsed request. Route/message/body/profile drift rejected by the original validator therefore remains terminal even when a temporary validator replacement restores itself before M35 returns.

## Authority boundary

M43 prepares response bytes but never sends them. The following remain explicit:

```text
response_prepared = True
transmitted = False
socket_access_proven = False
network_origin_proven = False
request_authenticated = False
peer_identity_proven = False
establishes_marketplace_truth = False
establishes_trust = False
establishes_authorization = False
authorizes_protected_side_effects = False
```

A completed request is not an authenticated requester. A prepared response is not transmission. Application preparation is not authorization to execute a protected economic side effect. No M43 result establishes Marketplace truth or trust.

## Network and deployment boundary

M43 introduces no concrete socket, DNS, TLS, listener, accept/connect, `recv`, read-stream, writer/send, HTTP server/client, process, filesystem, logging, scheduler, asyncio, thread, deployment, credential, or provider-administration primitive. Development and CI use deterministic in-memory readers, clocks, and application harnesses only.

Any future concrete accepted-socket reader, response writer, listener, TLS terminator, or live deployment is separate `NETWORK_EXTERNAL` work and requires its own explicit authorization immediately before external execution.

## Retention

All request, completion, prepared-response, plan, and accounting material is **EPHEMERAL**, with a maximum retention of 10 seconds post-use. M43 adds no durable store, cache, journal, log, checkpoint, filesystem output, or background retention mechanism. Callers remain responsible for consuming or releasing the returned one-shot material within the project retention bound.

Pre-run drift is destructive with respect to the owned partial M39 prefix: M43 attempts immediate captured cleanup instead of relying on caller cooperation. Successful response preparation still returns the existing immutable prepared material to the caller, which remains subject to the same maximum 10-second post-use retention bound.

## Recovery

M43 adds source, tests, documentation, and package membership only. It creates no migration, durable state, credential, listener, deployed process, or live external side effect. Recovery is a normal source revert.