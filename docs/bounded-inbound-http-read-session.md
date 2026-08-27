# Bounded Inbound HTTP Read Session (M39)

M39 adds a transport-free state owner above M37/M38. Its purpose is narrow: keep the buffered request prefix and local read-call counter inside one bounded object so ordinary callers cannot reset `reads_completed` between validated M38 transitions.

## Authority boundary

M39 performs **no transport I/O**. It never invokes a reader and does not create, bind, accept, read from, write to, or close a socket.

```text
owned read count             != proof external reads occurred
owned buffered prefix        != authenticated requester
M37 current plan             != permission to read a socket
M38 accepted transition      != proof bytes came from a peer
completed M39 handoff        != transmitted response
M39 session                  != listener / TLS / deployment
```

Every public M39 progress/completion object keeps transport, identity, trust, authorization, and protected-side-effect authority facts negative.

## State ownership

A `BoundedInboundHttpReadSession` has one canonical start state:

```text
prefix = b""
reads_completed = 0
```

The constructor accepts neither a prefix nor a read count. The public `accept_chunk(chunk)` API accepts only one already-returned exact immutable `bytes` chunk and has no count parameter.

For each accepted chunk M39:

1. validates its own state-integrity witness;
2. validates retained M38/M37/M36/M35 configuration;
3. replays the current M37 plan witness;
4. invokes the construction-bound M38 transition exactly once using M39-owned prefix/count state;
5. integrity-replays the returned M38 transition;
6. requires the returned prior M37 plan to match M39's exact current plan;
7. verifies one-step count/buffer accounting;
8. only then replaces the owned prefix, count, and current plan.

A lower-layer rejection or hostile/inconsistent result therefore leaves the M39 state unchanged.

M39 also keeps a local SHA-256-based state witness. Direct same-process mutation of the private prefix/count/plan is not an authorization boundary and is not supported; if it occurs, subsequent session operations fail closed with `READ_SESSION_STATE_DRIFT` rather than silently accepting a reset.

## Construction-bound lower authority

M39 is constructed from one exact `BoundedInboundHttpReadTransitioner`. It binds to that transitioner's retained exact M37 planner and captures the reviewed class implementations of M38 `transition` and M37 `plan` rather than trusting later public method replacement.

It snapshots and guards:

- M37 read-call and per-read limits;
- inherited M36 chunk-count and chunk-size limits;
- inherited M35 wire authority;
- inherited M35 header/body/response limits;
- the M38-to-M37 helper binding.

Configuration drift before or during initial planning/transition processing fails closed.

M39 preserves lower failure provenance through `InboundHttpReadSessionError` fields:

- `transition_code` for M38;
- `plan_code` for M37;
- `stream_code` for M36;
- `wire_code` for M35.

## Public progress without raw bytes

`InboundHttpReadSessionProgress` exposes bounded metadata only:

- `buffered_bytes`;
- `reads_completed`;
- `last_accepted_chunk_bytes` (zero for a snapshot-only `progress()` call);
- an integrity-replayed M37 plan;
- negative authority facts.

It contains no raw prefix or raw chunk field.

## Completion handoff

Raw request bytes are exposed only by `take_completed()`, and only when the current M37 plan is `COMPLETE`.

M39 first constructs an integrity-bound `CompletedInboundHttpReadSession`, then clears its internal raw prefix, marks itself closed, and only then returns the handoff. The handoff witness binds the raw prefix by SHA-256 digest rather than storing a second raw copy.

Completion handoff is one-shot. A second handoff, additional chunk acceptance, or progress request fails with `READ_SESSION_CLOSED`.

`close()` is idempotent and clears the internal raw prefix even when completion has not been reached.

## Buffer and accounting bounds

M39 performs no independent prefix append, join, `bytearray`, `memoryview`, or accumulation loop. The single raw-buffer append remains M38's bounded `prefix + chunk` operation.

M39 cannot widen M37/M36/M35 limits. Its owned read count advances only by adopting a fully validated M38 transition whose count is exactly prior count + 1.

M39 does **not** prove that accepted bytes came from a real network read. A future concrete reader must own the external I/O operation and obey the M37 next-read budget. M39 only prevents the normal orchestration API from resetting local count/buffer state between transitions.

## EOF and zero-byte behavior

Empty chunks are rejected. M39 does not interpret them as EOF, timeout, retry, half-close, connection failure, or request completion. Those meanings belong to a future transport layer.

## Retention and privacy

The session prefix, supplied chunks while in use, completion handoff, plans, progress values, and integrity witnesses are **EPHEMERAL** with maximum retention **10 seconds post-use**.

M39 adds explicit `close()` and one-shot completion transfer but deliberately adds no clock, thread, timer, filesystem, journal, cache, access log, session store, checkpoint, or background erasure mechanism. It therefore does not claim automatic wall-clock deletion without lifecycle cooperation. A conforming caller MUST close or consume the session promptly within the project retention bound.

## Security properties

The M39 acceptance suite covers:

- canonical empty/zero session start;
- no public prefix/read-count reset parameter;
- sequential one-step count advancement;
- no state mutation after rejected chunks;
- exact request completion and one-shot transfer;
- explicit close/clear behavior and post-close rejection;
- private-state tamper detection by the M39 state witness;
- public M37/M38 method replacement resistance;
- M37 configuration mutation during initial planning and during a transition;
- a self-consistent but M39-inconsistent M38 prior plan;
- nested M38/M37/M36/M35 reason preservation;
- progress metadata with no raw prefix/chunk;
- completed-handoff digest witness and rebinding resistance;
- no independent M39 accumulation path;
- no network, reader, writer, TLS, server, client, process, concurrency, filesystem, logging, or deployment surface;
- exact public runtime exports and wheel membership.

## Explicitly out of scope

M39 does not implement:

- reader callbacks;
- socket creation or `recv`;
- bind/listen/accept;
- TLS termination, certificate validation, or SNI binding;
- response writes/sends;
- EOF/half-close/zero-byte transport interpretation;
- requester authentication or mTLS;
- keep-alive or multiple requests per connection;
- deployment/systemd/container services;
- live Marketplace federation peer execution.

A future concrete reader/listener is a separate **HIGH-risk `NETWORK_EXTERNAL` capability**. External execution requires separate explicit operator authorization immediately before use.

## Recovery

M39 creates no migration, deployment, listener, secret, credential, durable state, or live network side effect. Recovery after merge is a normal source revert of the M39 merge commit.
