# Bounded Inbound TCP Listener Construction

Milestone 53 adds the smallest listener-construction boundary above M52 while
remaining source-only and offline during acceptance. It configures one
caller-supplied listener-shaped capability and transfers that capability into
the exact M52 `BoundedInboundHttpSingleAccept` boundary.

M53 is intentionally **not** an operating-system socket server. The runtime
module does not import `socket`, `ssl`, an HTTP server framework, subprocess,
filesystem, logging, or concurrency modules. Source acceptance never creates,
binds, listens on, or accepts from a real OS socket.

## Configuration boundary

M53 accepts only this deliberately narrow local endpoint configuration:

- host: exact IPv4 loopback `127.0.0.1`;
- port: explicit integer from 1024 through 65535; and
- backlog: exactly `1`.

Wildcard, hostname, IPv6, privileged-port, ephemeral-port-zero, and larger
backlog configurations are rejected before the injected factory is invoked.

## Injected capability model

The caller supplies one factory callable. The factory may return one object
with callable `bind`, `listen`, `accept`, and `close` members. M53 captures the
factory type and exact call implementation at construction time, validates the
binding graph by identity, and invokes that captured implementation at most
once.

The listener methods are captured before use and revalidated around bind and
listen. Method rebinding, hostile attribute lookup, or M52 class substitution
fails closed. Arbitrary caller exception text is never reflected into stable
M53 errors.

Source acceptance uses deterministic in-memory doubles for every factory and
listener operation. A double recording a `bind(("127.0.0.1", port))` call is
only evidence of local method invocation; it is not evidence that a kernel
socket was created or that the address became reachable.

## One-shot construction

`construct_once()` is terminal. On the success path M53 performs exactly:

1. one captured factory invocation;
2. one `bind(("127.0.0.1", port))` invocation;
3. one `listen(1)` invocation; and
4. one exact M52 boundary construction.

There is no retry, loop, backoff, worker, queue, pool, or background task.
After successful M52 construction, M53 releases its own factory and endpoint
references. Listener lifetime transfers to M52, whose existing one-shot accept
and cleanup rules remain authoritative.

Calling `close()` before construction releases M53 state without invoking the
factory. Calling it after a terminal path is idempotent and does not retry any
failed operation.

## Failure and cleanup semantics

If factory construction fails, no listener cleanup can be claimed. If a
listener exists but is malformed, bind/listen fails, or binding drift is
detected, M53 attempts the originally captured `close` callable once.

A close failure is `LISTENER_CLEANUP_UNCERTAIN`. M53 never retries that close
or claims cleanup succeeded when it cannot verify the call completed. Factory,
bind, listen, getter, and close exception bodies are redacted from stable error
messages.

No successful M53 result exposes a listener handle directly. The returned
object is the exact M52 single-accept boundary.

## Retention

M53 adds no durable payload storage, cache, queue, content-bearing log, or
filesystem state. Project transient retention remains `EPHEMERAL` with a
maximum of 10 seconds. M53 releases its construction/configuration references
at the terminal boundary; the transferred acceptor is governed by M52.

## Authority semantics

A successful M53 construction proves only local capability/accounting facts:
the injected factory returned an object with the required listener shape, and
its captured bind/listen operations completed for the bounded local
configuration before an exact M52 boundary was created.

It does **not** prove or establish:

- that an operating-system socket exists;
- that a port is bound, listening, reachable, or externally accessible;
- that a peer connected or any network packet moved;
- DNS resolution, TLS termination, certificate identity, or authentication;
- peer identity, request origin, transmission, receipt, or acknowledgement;
- Marketplace truth, agreement, trust, or authorization; or
- authority for settlement, fulfillment, deployment, or another protected
  external side effect.

## Live-network boundary

Any later adapter that imports/creates a real socket or any test/operator action
that actually binds, listens, accepts, or reaches a real peer is a distinct
`NETWORK_EXTERNAL` action. It requires separate explicit authorization
immediately before execution. Production service activation additionally
requires its own deployment authorization.

M53 source acceptance must remain valid without such authorization because all
listener effects are deterministic in-memory doubles only.

## Acceptance

M53 requires tests-first evidence, focused functional/adversarial/security and
retention coverage, runtime export and wheel-membership checks, repository
audit, the unchanged Marketplace conformance gate, exact-head self-hosted
Windows CI, review under repository governance, SHA-guarded merge, and exact
merged-main CI before the milestone is complete.

Because the runtime surface is listener-adjacent, M53 is treated as HIGH
source/security work even though source acceptance has no live network side
effect. Maintainer/security self-review and automated CI are not independent
human review.

## Rollback / recovery

M53 is additive and source-only. Rollback is an ordinary source-control revert
of the runtime module, exports, package-member requirement, tests, and this
document. Source acceptance creates no listener, socket, service, credential,
certificate, external resource, schema, user/content data, or production state
that would require operational rollback.
