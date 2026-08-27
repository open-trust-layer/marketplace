# Bounded Inbound HTTP Read Outcome Semantics (M40)

M40 defines the transport-free semantic boundary for one **already-returned** inbound HTTP read outcome immediately above M39.

It does **not** invoke a reader, open a socket, terminate TLS, accept a connection, or perform any external I/O.

## Architecture

```text
future external read
        |
        v
already-returned M40 outcome: DATA / EOF / FAILURE
        |
        +-- DATA(non-empty bytes) --> captured M39 accept_chunk --> progress
        |                              \-> rejection/drift -> close/clear -> terminal rejection
        |
        +-- EOF while READ --------> close/clear M39 --> terminal rejection
        |
        +-- FAILURE while READ ----> close/clear M39 --> terminal rejection
        |
        +-- any outcome after COMPLETE -> close/clear M39 --> terminal rejection
```

M40 deliberately stops before the future external-read arrow. Supplying an `InboundHttpReadOutcome` is not proof that a network read occurred, that bytes came from a particular peer, or that any requester was authenticated.

## Outcome shapes

`InboundHttpReadOutcome` is exact, immutable, integrity-witnessed, and has one canonical kind:

- `DATA`: requires exact non-empty immutable `bytes`;
- `EOF`: carries no payload bytes;
- `FAILURE`: carries no payload bytes and intentionally retains no arbitrary exception object or external error text.

The integrity witness binds DATA bytes by SHA-256 digest and byte count. It does not retain a second raw copy.

The outcome itself contains negative authority facts describing what M40 does **not** establish. These facts do not prove the provenance of caller-supplied bytes.

## Construction binding

`BoundedInboundHttpReadOutcomeHandler` is constructed with one exact M39 `BoundedInboundHttpReadSession`.

At construction it captures the original M39:

- `progress`;
- `accept_chunk`;
- `take_completed`;
- `close`;
- `closed` getter.

A construction-time binding witness also records the exact session and captured helper functions. Later replacement of public M39 methods cannot substitute a different authority path. Private helper/function rebinding that changes the captured binding set is detected fail-closed.

M40 owns no request prefix and no read counter. Those remain exclusively M39 state.

## DATA semantics

Before accepting DATA, M40 obtains and integrity-replays current M39 progress.

If the plan action is `READ`, M40 delegates the supplied non-empty DATA chunk exactly once to the captured M39 `accept_chunk` method.

After return, M40 independently requires:

- exact M39 progress type and valid integrity replay;
- `reads_completed == prior + 1`;
- `buffered_bytes == prior + len(DATA)`;
- `last_accepted_chunk_bytes == len(DATA)`;
- a fresh current M39 progress view whose byte count, read count, and exact M37 plan witness match the returned progress.

Because a DATA outcome represents bytes that have already been returned by a future reader, **any M39 rejection of that DATA is terminal at M40**. M40 closes/clears the M39 session before raising the preserved rejection. The same terminal close occurs for any post-delegation M40 consistency failure. A consumed malformed, oversized, exhausted-budget, or otherwise rejected chunk is therefore never treated as safely retryable from the old partial state.

M39 remains authoritative for raw prefix continuity, M38 transition integrity, M37 next-plan derivation, and inherited M36/M35 framing limits.

M40 creates no second prefix accumulator.

## EOF semantics

EOF is terminal only when M39 still reports action `READ`.

M40 first closes the captured M39 session. M39 clears its raw prefix. M40 then raises stable local error:

`READ_EOF_BEFORE_COMPLETE`

EOF is therefore never interpreted as an empty DATA chunk and never turns a truncated request into success.

## FAILURE semantics

A generic already-returned failure while M39 still reports `READ` is terminal.

M40 closes/clears M39 and raises:

`READ_FAILURE_BEFORE_COMPLETE`

No arbitrary external exception object or error text is retained or reflected by M40.

Future concrete transport code may map its own failures into this generic semantic outcome, but that transport mapping is out of scope for M40.

## Extra outcomes after completion

Once current M39 progress reports `COMPLETE`, no further read outcome is semantically valid.

DATA, EOF, and FAILURE are all rejected as:

`READ_OUTCOME_AFTER_COMPLETE`

M40 closes/clears M39 before raising. This prevents an accidental or hostile over-read result from being normalized into success.

## Completion handoff

M40 completion transfer is only a delegation to the captured M39 `take_completed` method.

The returned object remains exact `CompletedInboundHttpReadSession`, including its M39 integrity witness and one-shot close/clear semantics.

M40 does not reinterpret or copy the completed prefix.

## Error provenance

M40 uses `InboundHttpReadOutcomeError` with stable fields:

- `code`;
- `session_code`;
- `transition_code`;
- `plan_code`;
- `stream_code`;
- `wire_code`.

DATA-path M39 rejection is wrapped as `READ_SESSION_REJECTED` while preserving nested M39/M38/M37/M36/M35 reason codes, and the consumed-DATA session is closed first.

Terminal M40 EOF/failure/after-complete errors intentionally have local semantic codes and no arbitrary external error string.

## Authority boundary

```text
supplied DATA outcome          != proof of network I/O
supplied DATA bytes            != authenticated requester
EOF outcome                    != successful request completion
FAILURE outcome                != transport diagnosis
M40 DATA acceptance            != socket authority
M40 completion handoff         != response transmission
M40 handler                    != reader / listener / TLS / deployment
```

M40 itself records no reader invocation, socket access, TLS termination, transmission, requester authentication, peer identity proof, marketplace truth, trust, authorization, or protected-side-effect authority.

M40 grants **no `NETWORK_EXTERNAL` authority**.

## Retention

The following are **EPHEMERAL** with maximum retention **10 seconds post-use**:

- M40 outcome objects;
- supplied DATA bytes;
- replayed M39 progress;
- completed M39 handoff material.

M40 adds no filesystem persistence, durable buffer, log, journal, cache, session store, checkpoint, credential store, background retention, retry queue, or transport state.

Terminal EOF/failure/after-complete handling and consumed-DATA rejection explicitly close M39 so its owned raw prefix is cleared.

## Explicitly out of scope

M40 does not provide or authorize:

- reader callbacks;
- `recv` / transport `read`;
- socket creation, bind, listen, accept, or connect;
- TLS termination or mTLS;
- timeout clocks;
- retry/backoff;
- response write/send;
- requester authentication;
- keep-alive or multiple requests per connection;
- deployment/systemd/container listener services;
- live Marketplace federation peer execution.

A future concrete reader/driver/listener remains a separate HIGH-risk `NETWORK_EXTERNAL` capability requiring explicit operator authorization immediately before external execution.

## Recovery

M40 creates no migration, deployment, secret, credential, durable state, or live network side effect. Recovery after merge is a normal source revert of the M40 merge commit.
