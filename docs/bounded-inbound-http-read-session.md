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
2. validates retained M38/M37/M36/M35 configuration and captured helper bindings;
3. replays the current M37 plan witness;
4. invokes the construction-bound M38 transition exactly once using M39-owned prefix/count state;
5. integrity-replays the returned M38 transition;
6. requires the returned prior M37 plan to match M39's exact current plan;
7. verifies one-step count/buffer accounting and exact accepted-chunk byte count;
8. independently verifies byte continuity by incrementally hashing the prior prefix and supplied chunk and comparing that digest with the returned M38 prefix digest, without allocating a second `prefix + chunk` buffer;
9. independently re-derives the next plan through M39's separately captured M37 planning authority and requires the M38 `next_plan` witness to match exactly;
10. only then replaces the owned prefix, count, and current plan, adopting the independently re-derived M37 plan.

A lower-layer rejection or hostile/inconsistent result therefore leaves the M39 state unchanged.

M37's plan witness intentionally does **not** claim to bind raw prefix content; M37 retains no raw prefix. M39's own state witness binds the actual owned prefix by SHA-256 digest, and the independent continuity check above proves that an accepted M38 result is byte-for-byte the prior M39 prefix followed by the supplied chunk before M39 adopts it. This is a local integrity property only; it still does not prove that the supplied chunk came from a network peer.

M39 also does not trust M38 alone to define the next read budget. Even after the M38 result passes its own integrity replay, M39 calls its separately captured M37 `plan` implementation on the returned prefix/count and requires exact witness equality before state mutation. A hostile or replaced M38-private planning helper therefore cannot silently widen or alter the session's next M37 budget.

M39 keeps a local SHA-256-based state witness. Direct same-process mutation of the private prefix/count/plan/helper bindings is not an authorization boundary and is not supported; if it occurs, subsequent session operations fail closed with `READ_SESSION_STATE_DRIFT` or `READ_CONFIGURATION_DRIFT` rather than silently accepting a reset or helper substitution.

## Construction-bound lower authority

M39 is constructed from one exact `BoundedInboundHttpReadTransitioner`. It binds to that transitioner's retained exact M37 planner and captures the reviewed class implementations of M38 `transition` and M37 `plan` rather than trusting later public method replacement.

The captured bound-method identities are revalidated as part of the M39 configuration guard, while the captured function identities are also bound into the open-session state witness. Public method replacement after construction therefore cannot substitute authority, and direct private rebinding fails closed rather than becoming a new transition/planning authority.

M39 snapshots and guards:

- M37 read-call and per-read limits;
- inherited M36 chunk-count and chunk-size limits;
- inherited M35 wire authority;
- inherited M35 header/body/response limits;
- the M38-to-M37 helper binding;
- the captured M38 transition and M37 plan bindings.

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

M39 performs no independent prefix append, join, `bytearray`, `memoryview`, or accumulation loop. The single raw-buffer append remains M38's bounded `prefix + chunk` operation. M39's extra continuity check uses two incremental hash updates over the already-existing prefix and supplied chunk and compares them with a digest of the already-returned prefix; it does not create a second assembled raw request buffer.

M39 cannot widen M37/M36/M35 limits. Its owned read count advances only by adopting a fully validated M38 transition whose count is exactly prior count + 1 and whose `accepted_chunk_bytes` equals the exact supplied chunk length. The next budget is then independently reproduced through M39's captured M37 planner before adoption.

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
- private captured-helper rebinding detection;
- M37 configuration mutation during initial planning and during a transition;
- a self-consistent but M39-inconsistent M38 prior plan;
- a self-consistent forged M38 next plan rejected by independent M37 re-planning;
- independent accepted-chunk count and prefix-content continuity checks;
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
