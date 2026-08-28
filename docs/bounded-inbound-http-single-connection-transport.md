# M51 — Bounded Inbound HTTP Single-Connection Transport

## Status

M51 introduces the first inbound adapter that can invoke an already-established
caller-supplied byte-stream connection. It remains deliberately below any
listener, endpoint, TLS, deployment, or service-activation boundary.

The implementation is `marketplace.runtime.inbound_http_connection`.

## Capability boundary

M51 accepts one connection capability exposing exactly the operations needed by
the existing M41/M48 contracts:

- `recv(max_bytes) -> bytes`;
- `send(data) -> int`;
- `close() -> None`.

M51 does **not** bind, listen, accept, resolve DNS, connect, negotiate TLS, load
keys/certificates, configure endpoints, retry, pool connections, start threads,
run background work, persist data, or deploy a service.

The supplied connection may be an in-memory test double. Therefore successful
M51 execution does not itself prove that a network socket was used.
## Composition

`BoundedInboundHttpSingleConnectionIO` captures the original `recv`, `send`,
and `close` callables once. It exposes stable M41/M48-compatible reader and
writer callables. Every read receives the exact M37-derived byte budget already
passed through M41; every write receives the exact M44-derived byte slice
already passed through M48.

`BoundedInboundHttpSingleConnectionTransport` then verifies that the supplied
M43 preparer retains an exact M42 → M41 graph whose reader is the same captured
M51 reader. The read session must still be pristine: no bytes or read-count
state may have been preloaded before M51 construction.

Only after those predicates hold does M51 construct M50 with the same M51
adapter's writer. M50 remains the request/response transaction owner and M49
remains the only response-write orchestration loop.

The M51 `run()` method is one-shot and contains no loop or retry path.

## Read semantics

One M51 reader invocation calls captured `recv` at most once. The returned
value must be exact immutable `bytes` and may not exceed the supplied budget.
Non-empty bytes become one M40 `DATA` outcome; empty bytes become `EOF`.
Connection exceptions and malformed results flow into the existing M41
terminal fail-closed path without reflecting arbitrary exception text.
## Write semantics

One M51 writer invocation calls captured `send` at most once. The return value
must be an exact integer, not a boolean, in `0..len(data)`. Positive progress
becomes one M47 `PROGRESS` outcome; zero becomes the existing terminal `ZERO`
outcome. Negative, oversized, non-integer, or exceptional results fail closed
through the existing M48/M49 path. No automatic retry is introduced.

## Binding and cleanup integrity

M51 checks the connection method bindings before I/O and again immediately
after each connection call. A `recv`, `send`, or `close` rebinding is terminal.
The transport also verifies that the M41 reader and M50 writer still point to
the exact M51 adapter callables.

Cleanup uses the originally captured connection `close`, not a later replacement.
Close is attempted at most once. A failed close is reported as
`CONNECTION_CLEANUP_UNCERTAIN`; M51 does not retry and does not claim the
connection is closed.

After a successful or failed close attempt, M51 releases its references to the
connection and captured read/write/close callables. The public completion result
contains only detached scalar accounting and integrity witnesses, never raw
request or response bytes. M51 adds no durable storage, cache, queue, or log.

Project retention remains `EPHEMERAL`, with the repository-wide maximum of
10 seconds; M51 normally releases connection references immediately at terminal
cleanup rather than waiting for that maximum.
## Authority semantics

A successful M51 result establishes only local accounting facts: the supplied
connection capability returned enough request bytes, accepted the bounded
response byte sequence, and its captured close operation completed locally.

M51 does **not** establish or claim:

- network origin or use of a real socket;
- peer receipt or remote acknowledgement;
- TLS termination or certificate identity;
- requester authentication or peer identity;
- Marketplace truth, trust, agreement, or authorization;
- authorization for protected economic or external side effects.

Accordingly the completion result keeps the corresponding authority flags
explicitly false. `transmitted` remains false because a caller-supplied abstract
connection cannot prove remote delivery merely by returning local write counts.

## Acceptance and live-network boundary

M51 source acceptance uses deterministic in-memory connection doubles only.
It requires focused functional/adversarial/security tests, runtime export and
wheel-membership checks, the unchanged Marketplace conformance gate, exact-head
self-hosted Windows CI, and merged-main verification under valid governance.

Using M51 with a real socket or any real external peer is a separate
`NETWORK_EXTERNAL` action. That action is outside ordinary M51 source acceptance
and requires explicit authorization immediately before execution. Listener/TLS
or production service activation remains a later, separately reviewed boundary.
