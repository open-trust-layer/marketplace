# Bounded Inbound HTTP Read Transition (M38)

M38 adds a transport-free transition immediately below M37. It validates one already-returned immutable byte chunk against the exact M37 next-read budget, performs one bounded append, increments local read accounting once, and derives the next authoritative M37 plan.

## Authority boundary

M38 performs **no transport I/O**. A supplied chunk is data only; it is not evidence that a network read occurred, that a remote peer exists, or that any requester was authenticated.

```text
supplied chunk                != proof of network I/O
validated chunk length       != socket authority
next buffered prefix         != authenticated requester
next M37 plan                != read execution
M38 transition               != listener / TLS / deployment
```

The returned transition therefore keeps these local authority facts negative:

```text
reader_invoked                  = False
socket_accessed                 = False
tls_terminated                  = False
transmitted                     = False
request_authenticated           = False
peer_identity_proven            = False
establishes_marketplace_truth   = False
establishes_trust               = False
establishes_authorization       = False
authorizes_protected_side_effects = False
```

These fields describe what **M38 itself** did. They do not attempt to prove where the caller obtained the supplied bytes.

## Transition profile

For `transition(prefix, reads_completed=N, chunk=C)` M38:

1. requires exact immutable `bytes` for `prefix` and `chunk` and an exact non-negative integer count;
2. rejects an empty chunk because EOF/zero-byte transport semantics are not part of M38;
3. obtains the authoritative current plan from the construction-bound M37 planner;
4. rejects a chunk if M37 already reports `COMPLETE`;
5. rejects `len(C) > prior_plan.next_read_bytes`;
6. rejects a chunk outside the retained M36 chunk-size limit;
7. performs one `prefix + chunk` append;
8. increments the local read count exactly once;
9. derives the next authoritative M37 plan from the new prefix and new count;
10. returns one immutable integrity-witnessed transition.

M38 never invokes M36, M35, M34, M32, or M33 directly. M37 remains the sole planning authority used by the transitioner.

## Configuration and TOCTOU binding

At construction M38 snapshots detached views of:

- M37 read-call and per-read limits;
- inherited M36 chunk-count and chunk-size limits;
- inherited M35 wire authority;
- inherited M35 header/body/response bounds.

Those values are checked before and after each construction-bound M37 planning call. Later mutation of the retained M37/M36/M35 configuration fails closed. Replacing the public `plan` method on the M37 instance after M38 construction cannot substitute a different planning authority because M38 captures the original bound method.

Nested M37 errors are wrapped in `InboundHttpReadTransitionError` while preserving `plan_code`, `stream_code`, and `wire_code` metadata.

## Buffer and accounting bounds

M38 intentionally returns the single next buffered prefix because a future reader loop needs a deterministic local buffer state. That prefix is bounded by the existing M35 request framing limits.

A successful transition performs exactly one append allocation and no join/copy accumulation loop. The raw chunk is not retained as a separate field; it exists only as part of the next prefix. The integrity witness binds the returned prefix by SHA-256 digest rather than retaining a second raw-byte copy.

M38 cannot prove that `reads_completed` corresponds to real external reads. It validates local accounting only. A future concrete reader must own the actual I/O operation and advance the count exactly once per accepted read result.

## EOF and zero-byte behavior

M38 rejects empty chunks with `EMPTY_READ_CHUNK`. It does not interpret an empty result as EOF, retry, timeout, half-close, connection failure, or completion. Those are transport semantics and remain outside this milestone.

## Retention and privacy

The caller-supplied prefix, supplied chunk, returned prefix, M37 plans, and M38 transition witness are **EPHEMERAL** and have maximum retention **10 seconds post-use**.

M38 adds no durable buffer, filesystem persistence, access log, journal, cache, session, checkpoint, credential store, or background retention mechanism.

## Security properties

The acceptance suite covers:

- in-budget header transitions without application disclosure;
- exact final body completion;
- exact-budget and oversized chunk behavior;
- explicit empty-chunk rejection;
- reads after completion;
- invalid input types and read counts;
- preservation of M37/M36/M35 reason metadata;
- read-call exhaustion propagation;
- M37 configuration drift and mutation during planning;
- construction-bound M37 planning authority;
- transition integrity and raw-prefix digest binding;
- no duplicate raw chunk field;
- no reader/socket/TLS/server/client/process/concurrency/filesystem/logging/deployment surface;
- one append and no accumulation loop;
- no direct lower-layer application/disclosure invocation.

## Explicitly out of scope

M38 does not implement:

- reader callbacks;
- socket creation or `recv`;
- bind/listen/accept;
- TLS termination, certificate validation, or SNI binding;
- response writes or sends;
- EOF/half-close/zero-byte transport interpretation;
- remote requester authentication or mTLS;
- keep-alive or multiple requests per connection;
- deployment/systemd/container service;
- live Marketplace federation peer execution.

A future concrete reader/listener is a separate **HIGH-risk `NETWORK_EXTERNAL` capability**. External execution requires separate explicit operator authorization immediately before use.

## Recovery

M38 creates no migration, deployment, listener, secret, credential, durable state, or live network side effect. Recovery after merge is a normal source revert of the M38 merge commit.
