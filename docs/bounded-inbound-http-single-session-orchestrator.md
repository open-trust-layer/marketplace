# Bounded Inbound HTTP Single-Session Orchestrator

Milestone 55 adds the smallest one-shot orchestration boundary above the
reviewed inbound infrastructure chain. It composes exact M54, M53, M52, M51,
and M50 for one bounded session while preserving every lower-layer ownership
and authority boundary.

M55 is not a server loop or deployment surface. Source acceptance uses only
deterministic in-memory constructor, listener, connection, and application
doubles. It does not authorize or exercise live networking.

## Exact composition

The orchestrator accepts only four keyword inputs:

- one explicit Python TCP constructor capability for M54;
- one response-preparer factory that receives the exact accepted M51 reader and
  must return an exact M43 preparer;
- one clock callable consumed by the existing M50/M51 bounded drivers; and
- one explicit non-privileged TCP port.

M55 fixes the endpoint host to `127.0.0.1` and backlog to exactly `1` before
handing construction to M53. It does not add another endpoint policy.

One `run_once()` performs, at most, the following lower-layer sequence:

1. M53 invokes the explicit M54 factory once and applies the exact loopback
   bind/listen configuration.
2. Exact M52 performs one accept and closes the listener capability.
3. M55 passes the exact M51 reader to the explicit preparer factory.
4. The factory must return exact M43, still bound to that exact M51 reader.
5. Exact M51 runs one exact M50 transaction and closes the accepted connection.
6. M55 returns the exact detached M51 completion result without wrapping or
   promoting it.

There is no retry, polling loop, accept loop, worker, thread, task queue,
background service, connection pool, or second transaction.

## Result and authority

Successful M55 output is exactly `CompletedInboundHttpSingleConnectionTransport`.
M55 creates no new result schema and therefore no second source of truth for
request, response, transport, trust, identity, authorization, or settlement.

The result contains accounting and integrity digests only. It contains no raw
request bytes, raw response bytes, peer address, socket object, listener object,
credential, certificate, secret, or preparer/application capability.

All existing authority-negative facts remain exact `False`, including network
origin proof, TLS termination, transmission proof, request authentication, peer
identity proof, Marketplace truth, trust, authorization, and protected-side-
effect authority.

## Binding and handoff hardening

M55 captures the exact lower-layer class and method graph it intends to invoke,
and revalidates its complete witness after every untrusted lower callback before
invoking the next capability. Private captured call authority is never selected
through caller equality.

The M55 security review also closed four inherited binding/handoff gaps:

- M53 now captures and revalidates the M52 construction graph. A constructor,
  bind, or listen callback cannot keep the M52 class identity while replacing
  its constructor or validation helper before the M53-to-M52 handoff.
- M52 now captures and revalidates the M51 I/O construction graph. An accept
  callback cannot keep the M51 class identity while replacing its constructor
  or validation/read/write/close helpers before M52 constructs the adapter.
- M51 captures its own validation/cleanup/result helper graph and keeps trusted
  validator references across caller-supplied `recv` and `send` callbacks, so a
  callback cannot replace a class helper and have the replacement execute on
  re-entry.
- M43 captures its own validation, cleanup, and independent-replay helpers and
  keeps trusted validator references across the M42 read/application path, so
  callback-time replacement of its validator/helper graph fails closed.

These checks happen across untrusted callback boundaries and before downstream
construction or helper re-entry, so substituted constructor/helper code is not
executed merely because the enclosing class object itself remained unchanged.

## Live-network boundary

M55 deliberately does not import `socket`, call `bind`, `listen`, `accept`,
`recv`, `send`, connect to a peer, resolve DNS, negotiate TLS, load certificates,
or activate a service directly. Those operations remain encapsulated behind the
explicit capabilities and reviewed lower boundaries.

Supplying the real operating-system socket constructor and executing M55 would
create or operate live network resources. That is a separate `NETWORK_EXTERNAL`
action requiring fresh explicit authorization immediately before execution.
Production service activation additionally requires separate `DEPLOY`
authorization.

## Retention, rollback, and acceptance

M55 retains no content-bearing request/response state in its public result.
Construction, preparer-factory, and clock references are released on terminal
paths. Project transient retention remains `EPHEMERAL <=10s`.

Source acceptance creates no real listener, port, peer connection, certificate,
credential, service, schema, user data, or production state. Rollback is an
ordinary source-control revert.

Acceptance requires tests-first evidence, deterministic functional and
adversarial coverage, source guards, runtime exports, wheel membership,
repository audit, the unchanged full conformance gate, HIGH maintainer/security
review, exact-head self-hosted CI, zero unresolved threads, governance-qualified
SHA-guarded merge, and exact merged-main self-hosted acceptance.
