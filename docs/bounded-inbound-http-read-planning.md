# Bounded Inbound HTTP Read Planning

## Status

Milestone 37 reference-runtime security boundary.

M37 is a **transport-free read-budget planning layer** immediately below completed M36. It accepts one already-buffered immutable request prefix and an exact count of reads already completed, asks M36 for its pure request-completion facts, and derives the maximum size of the next read a future transport adapter may request.

M37 does not invoke a reader and does not perform external I/O.

## Boundary

```text
read plan                    != read execution
next_read_bytes              != socket authority
already-buffered bytes       != authenticated requester
M36 COMPLETE                 != transmitted response
read-call count              != peer identity
reported read-call count     != proof an external read occurred
bounded planner              != listener / TLS / deployment
```

M37 preserves:

```text
network_read_performed          = False
socket_bound                    = False
tls_terminated                  = False
transmitted                     = False
request_authenticated           = False
peer_identity_proven            = False
establishes_marketplace_truth   = False
establishes_trust               = False
establishes_authorization       = False
authorizes_protected_side_effects = False
```

A plan is local resource-control metadata. It is not an authorization token and does not establish that any read occurred.

## Read-count accounting boundary

`reads_completed` is caller-supplied **local accounting**, not externally verifiable evidence. M37 validates its exact type and finite range and binds the reported value into the returned plan integrity witness, but because M37 performs no I/O it cannot prove that the count corresponds to actual transport calls or that a caller advanced it monotonically across separate invocations.

A future concrete reader MUST therefore own the count, increment it consistently for its governed read attempts, and obey the returned `next_read_bytes` bound. It MUST NOT treat a caller-controlled count as authority to reset or extend the budget. EOF/zero-byte transport semantics remain outside M37 and require explicit handling in that future reader.

Accordingly, M37's finite call limit is a planning constraint for a conforming future reader; it is not a claim that this transport-free module can police external calls it never performs.

## Placement

```text
future external transport reader
          |
          | MUST obey a finite plan before any read
          v
M37 bounded read planner
          |
          | pure completion query only
          v
M36 bounded stream assembler / progress probe
          |
          v
M35 strict HTTP/1.1 wire framing
          |
          v
M34 application adapter
          |
          v
M32 / M33 disclosure preparation
```

M37 stops at the planning boundary. There is no concrete reader, socket, listener, TLS termination, response write, deployment adapter, or live peer execution in this milestone.

## Why a separate planning boundary exists

M36 deliberately exposes `NEED_MORE` / `COMPLETE` progress facts while refusing to own a read loop. A future transport implementation still needs a safe answer to a different question:

> If another read is needed, what is the largest read that can be requested without widening the already-reviewed framing bounds?

M37 answers only that question.

Without this boundary, a future reader could request arbitrary buffer sizes even though M35/M36 already know tighter bounds. In particular, once M36 has validated a canonical `Content-Length`, the future reader should not request more than the exact remaining body bytes.

## Finite limits

Reference defaults:

```text
max read calls = 64
max read bytes = 16 KiB
```

Hard ceilings:

```text
max read calls = 1024
max read bytes = 1 MiB
```

M37 limits are additionally constrained by the configured M36 limits:

```text
M37 max_read_calls <= M36 max_chunks
M37 max_read_bytes <= M36 max_chunk_bytes
```

This keeps every future read result representable as one M36 chunk without widening M36's finite resource profile.

## Construction-time binding

At construction M37 snapshots, into primitive M37-owned values:

- M36 maximum chunk count;
- M36 maximum chunk bytes;
- M36's snapshotted M35 Host authority;
- M36's snapshotted M35 header limit;
- M36's snapshotted M35 body limit;
- M36's snapshotted M35 response-body limit;
- the bound M36 `probe` method used as the planning authority.

Public limit properties return fresh detached values.

Before and after the captured M36 probe boundary, M37 checks that the retained M36 public configuration still equals the construction snapshot. M36 itself continues to check its underlying M35 authority and wire-limit snapshot. Therefore later M36/M35 configuration mutation fails closed before or immediately after the probe boundary.

M37 captures the bound M36 probe at construction. Replacing the public `probe` attribute on the M36 instance later does not substitute a new framing authority for an already-constructed M37 planner.

## Planning algorithm

`BoundedInboundHttpReadPlanner.plan(prefix, reads_completed=...)` accepts only exact immutable `bytes` and an exact non-negative integer read count.

The supplied prefix is never copied, joined, accumulated, or retained by M37. It is passed directly to the captured M36 pure probe exactly once.

### Head-incomplete phase

If M36 returns:

```text
state                = NEED_MORE
expected_total_bytes = None
head_complete        = False
```

M37 computes:

```text
remaining_header_bytes = snapshotted_m35_header_limit - buffered_bytes
next_read_bytes = min(configured_m37_max_read_bytes, remaining_header_bytes)
```

The next plan therefore cannot ask a future reader to cross the finite remaining header budget while the request boundary is still unknown.

### Validated-body-incomplete phase

If M36 has validated the HTTP head and reports an exact remaining body size:

```text
state                = NEED_MORE
expected_total_bytes = exact total request bytes
missing_bytes        = exact positive remaining bytes
head_complete        = True
head_validated       = True
```

M37 computes:

```text
next_read_bytes = min(configured_m37_max_read_bytes, missing_bytes)
```

A future reader following the plan therefore never needs to request more than the exact remaining request body once M36 knows that boundary.

### Complete phase

If M36 reports one exact complete request:

```text
state            = COMPLETE
request_complete = True
```

M37 returns:

```text
action          = COMPLETE
next_read_bytes = 0
```

No further read is planned. Completion is allowed when `reads_completed` equals the configured maximum because no additional read call is required.

### Exhaustion

If the request remains incomplete and `reads_completed` has reached the configured read-call maximum, M37 fails closed with:

```text
READ_CALL_LIMIT_EXHAUSTED
```

It does not silently widen the reported call budget.

## M36 error preservation

Malformed, over-limit, ambiguous, trailing, or otherwise rejected prefixes remain M36/M35 framing failures.

M37 wraps them in the stable local code:

```text
STREAM_PROFILE_REJECTED
```

while preserving M36 `stream_code` and, where present, the underlying M35 `wire_code`. This keeps layers distinguishable without reflecting untrusted raw request content into the error message.

## Progress integrity

M37 requires the exact `InboundHttpStreamProgress` type and replays its M36 dataclass invariants through `dataclasses.replace()` before deriving a read size.

A low-level mutation that makes M36 progress internally inconsistent therefore fails as:

```text
STREAM_PROGRESS_DRIFT
```

before a read budget is returned.

## Plan integrity

`InboundHttpReadPlan` binds its local facts into an integrity snapshot, including:

- action;
- buffered byte count;
- completed read count;
- next read byte budget;
- expected total / missing byte facts;
- head-completion / validation facts;
- request-completion fact;
- every authority-negative fact.

Dataclass replacement cannot reuse the original witness for changed values.

The plan intentionally does **not** retain the raw request prefix.

## No external I/O surface

`marketplace.runtime.inbound_http_read_plan` contains no concrete socket, TLS, HTTP client/server, URL client, reader, writer, listener, process, concurrency, filesystem, logging, environment, credential, or deployment primitive.

It contains no invocation of:

```text
recv
read
send
sendall
write
connect
listen
accept
open
```

Tests use in-memory bytes only.

## Retention

The following are EPHEMERAL and subject to the project maximum retention of **10 seconds post-use**:

- supplied request prefix;
- M36 progress material;
- M36/M35 configuration snapshots used by M37;
- M37 read plan and integrity witness.

M37 adds no durable buffer, journal, access log, response cache, session store, credential store, checkpoint, or filesystem persistence.

## Explicitly out of scope

- invoking a reader callback;
- socket creation / `recv`;
- bind / listen / accept;
- TLS termination, certificate validation, or SNI binding;
- response write / send;
- remote requester authentication / mTLS;
- remote error-response policy;
- keep-alive / multiple requests per connection;
- EOF/zero-byte read handling and read-count ownership in a concrete transport loop;
- deployment/systemd/container service;
- live Marketplace federation peer execution.

Any future actual reader or listener is a separate HIGH-risk `NETWORK_EXTERNAL` capability. Its external execution requires explicit operator authorization immediately before that execution.

## Recovery

M37 adds no schema migration, deployment, listener, secret, credential, durable state, or live network side effect. Code recovery is by reverting the eventual M37 merge commit.
