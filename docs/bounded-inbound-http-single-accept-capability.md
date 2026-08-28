# Bounded Inbound HTTP Single-Accept Capability

Milestone 52 adds the smallest listener-adjacent boundary above M51 without
creating or activating a network listener. It consumes one caller-supplied,
already-listening acceptor capability and may obtain exactly one connection.

M52 is intentionally **not** a socket server. It does not create a socket,
bind an address, call `listen`, configure a backlog, resolve DNS, connect to a
peer, negotiate TLS, load certificates or keys, start a service, or deploy an
endpoint. Source acceptance uses deterministic in-memory doubles only.

## Composition boundary

The caller supplies an object with exactly the capability shape needed by M52:

- `accept()` returns one connection capability; and
- `close()` closes the supplied acceptor capability.

M52 captures both callables at construction time. It validates those bindings
before and after the single accept attempt. The accepted object is validated by
constructing the exact M51 `BoundedInboundHttpSingleConnectionIO`; M52 does not
introduce an alternative reader/writer transport contract.
The accepted object must also be identity-distinct from the acceptor itself; an
acceptor cannot return itself and then be handed out after M52 closes it.

On successful handoff, M52 closes the acceptor before returning the M51 I/O
capability. There is no accept loop, retry, backoff, worker, queue, pool, or
background task.

## One-shot and cleanup semantics

`accept_once()` is terminal. It attempts the captured accept callable at most
once and never retries after an exception, malformed return, binding drift, or
cleanup failure.

The acceptor's originally captured `close` callable is attempted at most once.
A failure is reported as `ACCEPTOR_CLEANUP_UNCERTAIN`; M52 never retries the
close or claims that the acceptor is closed when it cannot verify that fact.

If an accepted connection already exists when acceptor cleanup becomes
uncertain, M52 closes the exact M51 connection-I/O capability before failing.
If a returned object cannot be adapted to M51, M52 attempts its callable
`close` once when available. Failure or absence of a usable cleanup capability
is reported as accepted-connection cleanup uncertainty rather than hidden.

All terminal M52 paths release references to the acceptor and its captured
accept/close methods. A successful M52 call retains no accepted connection at
the M52 layer; ownership transfers immediately in the returned M51 I/O object.
That capability remains subject to M51's own one-shot close and cleanup rules.

## Retention

M52 adds no durable storage, cache, queue, filesystem state, or content-bearing
log. Project retention remains `EPHEMERAL` with a maximum of 10 seconds.
Acceptors are released at terminal cleanup, normally immediately. The returned
M51 capability should be composed into its one-shot transaction promptly or
closed by the caller; M52 does not silently extend its lifetime.

## Authority semantics

A successful M52 handoff proves only local capability/accounting facts: the
caller-supplied acceptor returned an object compatible with the exact M51 I/O
adapter, and the captured acceptor close operation completed locally.

It does **not** prove or establish:

- that a real network socket was used;
- network origin, remote address, or peer identity;
- TLS termination, certificate identity, or requester authentication;
- transmission, peer receipt, or remote acknowledgement;
- Marketplace truth, agreement, trust, or authorization; or
- authority for settlement, fulfillment, remedy, deployment, or another
  protected external side effect.

M52 therefore does not accept or return peer-address metadata, endpoint
configuration, TLS state, authentication state, or raw request/response bytes.
Those facts cannot be manufactured from a generic caller-supplied acceptor.

## Security review boundary

The M52 runtime imports only the abstract typing surface and the existing M51
adapter. Source guards reject concrete socket/TLS/DNS, process, filesystem,
logging, persistence, concurrency, and service-construction imports. The public
constructor accepts only the caller-supplied `acceptor` capability.

## Acceptance and future live-network boundary

M52 source acceptance requires tests-first evidence, focused functional and
adversarial tests, runtime export and wheel membership checks, repository audit,
the unchanged Marketplace conformance gate, exact-head self-hosted Windows CI,
and merged-main verification under valid repository governance.

No test in M52 source acceptance may open, bind, listen on, or accept from a
real socket. No public endpoint is contacted or activated.

A later concrete socket-listener adapter would be a distinct capability and
security boundary. Any execution that actually binds/listens/accepts on a real
socket or interacts with a real external peer is `NETWORK_EXTERNAL` and requires
separate explicit authorization immediately before execution. Production
service activation additionally requires its own deployment authorization and
cannot be inferred from M52 source completion.

## Rollback / recovery

M52 is additive and source-only. Rollback is the ordinary source-control revert
of the M52 runtime, exports, artifact-membership requirement, tests, and this
document. It creates no persistent listener, schema, credential, certificate,
external resource, or production state that would require operational rollback.
