# Bounded Inbound HTTP Read Invocation

**Milestone:** 41  
**Risk:** HIGH  
**Runtime external-I/O capability:** possible only through an explicitly injected reader; development/CI uses deterministic in-memory doubles only.

## Purpose

M41 is the first Marketplace runtime layer that intentionally invokes an injected read capability. It remains deliberately one-step: one public `invoke_once()` call performs **zero or one** reader calls and then returns or fails closed.

```text
M37 exact READ budget
        |
        v
M41 invokes injected reader once(max_bytes)
        |
        v
exact M40 DATA / EOF / FAILURE outcome
        |
        v
M40 -> M39 -> M38 -> M37
```

M41 does not implement or discover a socket, listener, TLS stack, URL client, retry loop, timeout scheduler, writer, filesystem store, logger, process, or deployment primitive.

## Reader capability boundary

The constructor receives one explicit callable:

```text
reader(max_bytes: int) -> InboundHttpReadOutcome
```

The object identity of that capability is bound into M41's construction witness. M41 never replaces it from ambient configuration.

When the current M37 action is `READ`, M41 requires an exact positive `next_read_bytes` and invokes the reader **exactly once with exactly that value**. No second attempt is permitted by the same call.

When the current action is already `COMPLETE`, M41 invokes no reader. It transfers the existing M40/M39 one-shot completion handoff and closes the source session.

A DATA result that itself reaches COMPLETE does not cause an implicit second operation or completion transfer. A later explicit `invoke_once()` observes COMPLETE and transfers the handoff without invoking the reader.

## Failure semantics

Reader exceptions are not reflected to callers. Arbitrary exception text may contain remote or sensitive content, so M41 converts an exception into the generic M40 FAILURE outcome. M40 then clears/closes the underlying M39 raw-prefix owner. M41 reports only stable local/nested reason codes.

A reader that returns anything other than an **exact** `InboundHttpReadOutcome` is treated as a hostile/miswired capability. M41 closes the session and fails `INVALID_READER_RESULT` before adopting the value.

EOF, explicit FAILURE, malformed DATA, oversized DATA, and lower-layer framing failures retain the terminal/fail-closed semantics already established by M40.

## Authority boundary

M41 can establish the narrow operational fact that its injected reader callable was invoked. It cannot infer what that callable did internally.

```text
reader_invoked=True          != socket accessed
reader_invoked=True          != network origin proven
returned bytes               != authenticated requester
TLS elsewhere                != M41 peer identity proof
M41 progress                 != request truth/trust
M41 completion               != response transmission
M41 invocation               != retry/listener permission
```

The result therefore records `socket_access_proven=False` and `network_origin_proven=False`. These are non-establishment statements, not claims that a future concrete reader performed no network action.

Requester authentication, peer identity, Marketplace truth, trust, authorization, and protected-side-effect authority remain false/not established.

## Content and retention

M41 progress results contain no raw request prefix or DATA chunk. Integrity witnesses bind only nested progress/completion witnesses and operational metadata.

A `COMPLETED` result may carry the existing explicit M39 one-shot completion handoff. M41 does not make a second copy of those raw request bytes in its own witness.

Reader-returned DATA, M40 outcome values, progress, and completion material are **EPHEMERAL**, maximum **10 seconds post-use**. M41 adds no durable cache, log, journal, checkpoint, filesystem persistence, or background retention.

## Deliberately absent features

M41 does **not** add:

- `socket.recv()` or any concrete `.read()` implementation;
- socket creation, bind/listen/accept/connect;
- TLS termination or certificate/SNI handling;
- a full request-read loop;
- retry/backoff;
- connection timeout policy;
- response write/send;
- requester authentication or mTLS;
- rate limiting;
- deployment/service activation;
- live Marketplace peer execution.

A future concrete socket reader remains a separate HIGH-risk capability. Implementing its source can be reviewed independently; actually invoking it against a real peer/public endpoint requires the applicable explicit external-execution authorization immediately before execution.
