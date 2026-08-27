# Bounded Inbound HTTP Stream Assembly

## Status

Milestone 36 reference-runtime security boundary.

M36 is a **transport-free, bounded HTTP stream assembly layer** immediately below completed M35. It accepts only already-received immutable byte chunks, determines whether those chunks contain exactly one complete M35 request, invokes M35 exactly once only after exact completion, and returns one prepared response witness without reading or writing any external transport.

M36 is **HIGH risk** because message-boundary ambiguity, request smuggling, unbounded buffering, or re-binding of a prepared M35 result could indirectly cross the M32/M33 disclosure boundaries.

## Boundary

```text
partial bytes                  != complete request
complete request bytes         != authenticated requester
chunk boundary                 != HTTP message boundary
stream completion              != disclosure authorization
M35 parse success              != peer identity
prepared M35 response          != transmitted response
M36 prepared response          != socket write
```

M36 explicitly preserves:

```text
request_complete        = True only after exact framing completion
network_read_performed  = False
socket_bound            = False
tls_terminated          = False
transmitted             = False
request_authenticated   = False
peer_identity_proven    = False
```

M36 does not make Host authority, transport authentication, TLS identity, Marketplace truth, trust, authorization, or protected-side-effect claims.

## Placement

```text
future bounded transport reader
          |
          | already-received immutable chunks
          v
M36 stream completion probe / finite chunk assembler
          |
          | exactly one complete request byte sequence
          v
M35 strict HTTP/1.1 wire framing adapter
          |
          v
M34 application adapter
          |
          +---- control POST ----> M32 disclosure/page preparation
          |
          +---- Record GET ------> M33 Record-body disclosure preparation
          |
          v
M35 prepared success response bytes
          |
          v
M36 integrity-bound prepared exchange
          |
          X  STOP: no read, write, socket, listener, or TLS operation in M36
```

A future concrete transport layer may use M36's pure completion facts to decide how many bytes remain, but live reading is not part of this milestone and remains a separate HIGH-risk `NETWORK_EXTERNAL` boundary.

## Reuse of M35 as framing authority

M36 intentionally does **not** create a second HTTP parser.

`BoundedInboundHttpStreamAssembler.probe()` delegates strict request-profile validation to M35's public, side-effect-free:

```text
BoundedInboundHttpWireAdapter.parse_request()
```

The only HTTP field M36 inspects itself is canonical `Content-Length`, and only after M35 has already validated the complete header block and returned the specific local reason `CONTENT_LENGTH_MISMATCH` for head-only bytes.

This means M36 does not independently normalize or reinterpret:

- request methods;
- target paths;
- HTTP versions;
- header names;
- duplicate headers;
- Host authority;
- Connection semantics;
- content type;
- request authentication or identity facts.

Those remain M35/M34 responsibilities.

## Progress probe

`probe(prefix)` accepts exact immutable `bytes` and performs no disclosure action.

### Incomplete head

If `\r\n\r\n` has not arrived and the configured M35 header bound is still satisfiable, M36 returns:

```text
state                = NEED_MORE
expected_total_bytes = None
missing_bytes        = None
head_complete        = False
head_validated       = False
request_complete     = False
```

If the header cannot complete within the M35 header limit, M36 fails closed.

### Complete head without declared body

M36 calls M35 `parse_request()` on head-only bytes.

If M35 accepts that input as a complete request, the exact request boundary is the end of the header terminator. Any byte already present after that boundary is rejected as trailing/pipelined material.

### Complete head with a positive canonical Content-Length

If and only if M35 rejects head-only bytes with exact reason `CONTENT_LENGTH_MISMATCH`, M36 extracts the one canonical:

```text
Content-Length: <decimal>
```

from the already M35-validated header block.

M36 then compares the decimal **as text** against `str(configured_m35_body_limit)` before any integer conversion. Length comparison and lexicographic comparison are sufficient because both values are canonical non-negative decimal text.

Only after the value is proven less than or equal to the finite M35 body limit does M36 execute the bounded conversion to an integer. Therefore attacker-sized decimal text is never converted into an arbitrary-size Python integer.

M36 then reports exact missing bytes until the body reaches the declared size.

### Exact completion

When the exact total byte count is present, M36 re-runs M35 `parse_request()` on the full bytes. Only an accepted exact request yields:

```text
state                = COMPLETE
expected_total_bytes = buffered_bytes
missing_bytes        = 0
head_complete        = True
head_validated       = True
request_complete     = True
```

Any additional byte beyond the exact request boundary fails as `TRAILING_OR_PIPELINED_BYTES`.

## Finite chunk assembly

`prepare_chunks()` accepts an **exact tuple** of **exact non-empty immutable `bytes`** chunks.

Reference defaults:

```text
max chunks      = 64
max chunk bytes = 64 KiB
```

Hard ceilings:

```text
max chunks      = 1024
max chunk bytes = 1 MiB
```

The aggregate byte ceiling is not a separate widening control; it remains exactly the configured M35 header limit plus configured M35 body limit.

The order is deliberate:

1. require exact tuple representation;
2. reject tuple count before enumerating elements;
3. reject every element unless it is non-empty exact immutable `bytes`;
4. reject a chunk above the configured chunk-size bound before copying it;
5. reject aggregate overflow before appending;
6. append one chunk into a local temporary buffer;
7. invoke the pure M36 progress probe;
8. if the request completes before the final supplied chunk, fail before M35 `prepare()`;
9. after all chunks, require exact `COMPLETE`;
10. parse the exact bytes through M35 once more for canonical request binding;
11. invoke M35 `prepare()` exactly once;
12. revalidate the returned M35 negative authority facts directly;
13. replay M35's original integrity witness;
14. cross-bind the witnessed M35 request and Host authority to the bytes/configuration M36 used;
15. return one M36 integrity-bound prepared exchange;
16. stop.

No M34/M32/M33 disclosure helper can run during probing or while the request remains incomplete.

## M35 result revalidation

M36 does not trust a returned object merely because it came from the configured M35 adapter.

Before wrapping the result it requires exact M35 result type and directly checks:

```text
host_authority_validated                = True
tls_sni_bound                           = False
transmitted                             = False
request_authenticated                   = False
peer_identity_proven                    = False
establishes_marketplace_truth           = False
establishes_trust                       = False
establishes_authorization               = False
authorizes_protected_side_effects       = False
```

Direct checks occur before integrity replay for the same reason established in M35: Python dataclass replacement reconstructs `init=False` fields from defaults, so replay alone cannot prove that a low-level mutation of such a field did not occur.

M36 then replays M35's original integrity snapshot through `dataclasses.replace()`. A changed request, route, Host authority, response bytes, body count, status, or message type therefore fails before M36 wrapping.

Finally M36 independently requires:

- the witnessed M35 canonical request equals a fresh M35 parse of the exact assembled bytes;
- the witnessed Host authority equals the configured M35 authority.

Adversarial tests cover both post-construction mutation and fully self-consistent but wrong M35 request/authority objects.

## Prepared stream exchange integrity

`PreparedInboundHttpStreamExchange` retains only:

- one witnessed M35 `PreparedInboundHttpWireExchange`;
- the finite chunk count;
- the total request byte count;
- an M36 integrity snapshot;
- fixed negative/positive boundary facts.

It does **not** retain:

- the original chunk tuple;
- a duplicate raw assembled request byte image;
- a reader or connection handle;
- a socket address;
- TLS material;
- credentials;
- a write callback.

The M36 witness binds the full current M35 wire snapshot, chunk count, request byte count, completion fact, and every authority-negative fact. Dataclass replacement cannot reuse an old witness for changed values.

## Resource and smuggling properties

M36 provides an additional finite layer before any future network reader:

- arbitrary iterables are rejected rather than lazily consumed;
- chunk count is known before iteration;
- chunk size is checked before copying;
- aggregate size is checked before append;
- partial bodies cannot reach M35 `prepare()`;
- requests that finish before a later supplied chunk fail before disclosure;
- bytes beyond declared content length fail before disclosure;
- undeclared body bytes fail under the reused M35 profile;
- duplicate or transfer-encoding framing remains impossible under M35's strict header profile;
- no keep-alive or second request is accepted.

## No external I/O surface

`marketplace.runtime.inbound_http_stream` contains no concrete:

- socket primitive;
- TLS primitive;
- HTTP server/client library;
- URL client;
- reader callback or `.read()` invocation;
- `recv` call;
- writer callback or `.write()` invocation;
- `send` / `sendall` call;
- listener / accept loop;
- async/thread worker;
- subprocess;
- filesystem access;
- logging/access log;
- deployment primitive.

Its input is already-received bytes. Tests use only in-memory chunks.

## Retention

The following remain EPHEMERAL and subject to the project maximum retention of **10 seconds post-use**:

- supplied chunk tuple;
- temporary aggregate request buffer;
- M36 progress values;
- canonical M35 request;
- M35 prepared response;
- M36 prepared exchange and integrity witness.

M36 introduces no durable buffer, request journal, access log, response cache, session store, credential store, checkpoint, or filesystem persistence.

## Explicitly out of scope

- concrete `recv` / reader invocation;
- socket or listener creation;
- TLS termination / certificate validation / SNI binding;
- remote requester authentication / mTLS;
- connection writes / response transmission;
- remote error response mapping;
- keep-alive / connection reuse;
- multiple requests per connection;
- chunked/compressed request bodies;
- streaming;
- IP/identity rate limiting;
- deployment/systemd/container service;
- live Marketplace federation peer execution.

Any future live reader/listener remains a separate HIGH-risk `NETWORK_EXTERNAL` capability and requires explicit operator authorization immediately before actual external execution.

## Recovery

M36 adds no schema migration, deployment, listener, secret, credential, durable database state, or live network side effect. Code recovery is by reverting the eventual M36 merge commit.
