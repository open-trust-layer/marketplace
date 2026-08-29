# Bounded Python TCP Socket Factory

Milestone 54 adds the smallest Python-standard-library construction adapter
above M53. It converts one explicitly supplied socket-constructor capability
into M53's zero-argument `InboundTcpListenerFactory` shape while fixing the
construction profile to IPv4 TCP stream semantics.

M54 is an infrastructure edge, not a server. It does not bind, listen, accept,
connect, resolve DNS, negotiate TLS, start workers, deploy a service, or create
Marketplace semantic authority.

## Explicit authority boundary

M54 deliberately does **not** import or expose `socket.socket` as an implicit
default. The caller must supply the constructor capability explicitly.

The runtime module imports only the standard-library constants needed to define
the reviewed construction profile:

- `AF_INET`;
- `SOCK_STREAM`; and
- `IPPROTO_TCP`.

Supplying and invoking the real operating-system socket constructor is a
separate live `NETWORK_EXTERNAL` action. Source acceptance uses deterministic
constructor doubles only and therefore exercises no real network resource.

## Construction contract

`BoundedPythonTcpSocketFactory` accepts one keyword-only `constructor`.
Construction captures the exact constructor object, its exact type, and the
class-level call implementation used by Python's special-method lookup.
Identity-only binding checks run before the constructor is invoked.

One successful factory call performs exactly one captured invocation equivalent
to:

```text
constructor(AF_INET, SOCK_STREAM, IPPROTO_TCP)
```

There is no retry, loop, backoff, alternate family, UDP/raw/Unix socket mode,
IPv6 widening, hostname handling, endpoint selection, or socket-option surface.
The returned object is only a candidate listener capability for exact M53.
M54 itself never calls `bind`, `listen`, `accept`, `connect`, `send`, or `recv`.

After a terminal success or failure, M54 releases its constructor and profile
references. A second call fails with a stable terminal error and cannot invoke
the constructor again.

## Failure semantics

Non-callable or unverifiable constructors fail before invocation. Constructor
binding drift and factory binding drift fail closed by identity. Arbitrary
constructor exception text is redacted into stable M54 errors.

Constructor results may not alias the M54 factory or the constructor capability
itself. Other listener-shape validation and listener cleanup remain M53
responsibilities; M54 intentionally does not duplicate that lifecycle boundary.

A successful M54 call proves only that the supplied callable returned an object
when invoked with the exact reviewed Python TCP construction profile. It does
**not** prove that the object is a genuine OS socket, that a port is bound or
reachable, that a peer connected, that packets moved, or that any HTTP request
or response occurred.

## M53 composition

M54 composes directly into `BoundedInboundTcpListenerConstruction`. M53 remains
authoritative for:

- exact host `127.0.0.1`;
- explicit non-privileged port `1024..65535`;
- backlog exactly `1`;
- listener `bind` / `listen` / `accept` / `close` binding integrity;
- one-shot listener construction and cleanup semantics; and
- transfer into exact M52 single-accept handling.

M54 must not become a second listener lifecycle or broaden M53's endpoint rules.

## Retention and privacy

M54 stores no request bytes, response bytes, peer address, identity, payload,
credential, certificate, message, cache, queue, or content-bearing log.

Project transient retention therefore remains `EPHEMERAL <=10s`; intentional
source, tests, and this reviewed document are durable project artifacts.

## Live-network and deployment boundary

No M54 source-acceptance action authorizes real networking. A future operator or
adapter that supplies the real `socket.socket` constructor and invokes the M54
factory through M53 would create an operating-system networking resource and
requires separate explicit `NETWORK_EXTERNAL` authorization immediately before
that execution.

A real bind/listen/accept exercise remains live networking as well. Starting or
activating a production service additionally requires separate `DEPLOY`
authorization. M54 does not authorize secrets, certificates, provider
administration, settlement, fulfillment, or other protected external effects.

## Acceptance

M54 requires tests-first evidence, deterministic functional and adversarial
coverage, source guards, public runtime exports, wheel-membership enforcement,
repository audit, the unchanged Marketplace conformance gate, exact-head
self-hosted Windows CI, explicit HIGH maintainer/security review, governance
approval/authorization, SHA-guarded merge, and exact merged-main CI.

## Rollback

M54 is additive and source-only while tested with constructor doubles. Rollback
is an ordinary source-control revert of the runtime module, exports, package
member requirement, tests, and this document. Source acceptance creates no
socket, listener, port, service, credential, certificate, user data, schema, or
production state requiring operational rollback.
