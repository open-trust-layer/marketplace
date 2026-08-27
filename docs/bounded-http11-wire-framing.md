# Bounded HTTP/1.1 Wire Framing Adapter

## Status

Milestone 35 reference-runtime security boundary.

M35 is a **transport-free, one-shot HTTP/1.1 wire framing adapter** immediately below the completed M34 inbound HTTP application adapter. It accepts one complete already-received request byte sequence, validates a deliberately tiny HTTP/1.1 wire profile, binds one exact `Host` value to one configured local HTTP authority string, constructs a fresh M34 `InboundHttpRequest`, invokes M34 once, frames one exact success response, and stops before transmission.

M35 is **HIGH risk** because HTTP framing ambiguity, request smuggling, Host confusion, or response-binding drift could cross the M32/M33 disclosure boundaries indirectly through M34.

## Boundary

```text
raw HTTP bytes                 != authenticated requester
valid HTTP/1.1 framing         != disclosure authorization
Host header syntax             != peer identity
Host == configured authority   != TLS/SNI binding
Host == configured authority   != requester authentication
parsed M34 request             != permission to disclose
M34 prepared response          != transmitted response
framed response bytes          != socket write
HTTP 200                       != Marketplace truth / trust / authority
```

M35 establishes only that the one accepted wire `Host` value exactly equals the adapter's configured local HTTP authority string. It explicitly preserves:

```text
host_authority_validated = True
tls_sni_bound            = False
request_authenticated    = False
peer_identity_proven     = False
transmitted              = False
```

A future listener/TLS layer must separately bind local listener configuration, TLS SNI/certificate handling, and the same intended service authority before live use.

## Placement

```text
future socket/TLS receive loop
          |
          | one complete bounded request byte sequence
          v
M35 HTTP/1.1 wire framing adapter
          |
          | canonical Host-stripped M34 request
          v
M34 application adapter
          |
          +---- control POST ----> M32 disclosure/page preparation
          |
          +---- Record GET ------> M33 Record-body disclosure preparation
          |
          v
M34 prepared JSON response
          |
          v
M35 exact HTTP/1.1 success frame
          |
          X  STOP: no socket write in M35
```

M35 does not accumulate a TCP stream, perform partial reads, create a listener, terminate TLS, authenticate a peer, rate-limit a remote address, or write bytes to a connection.

## Request input and total bounds

Input is exact immutable `bytes` containing exactly one complete request as supplied by a future transport layer.

Reference defaults are aligned with the accepted M34/M26 scale:

```text
max request head       = 32 KiB
max request body       = 1 MiB
max response body      = 1 MiB
```

Hard ceilings remain finite:

```text
request head           = 128 KiB
request body           = 16 MiB
response body          = 16 MiB
```

M35's configured limits may not exceed the corresponding running M34 application limits. The constructor copies the caller-supplied limit values into a fresh immutable M35 limit object, so later alias mutation cannot relax a running adapter.

## Request line profile

M35 accepts exact HTTP/1.1 origin-form request lines only:

```text
GET <path> HTTP/1.1
POST <path> HTTP/1.1
```

The request line must use exactly two ASCII SP separators. M35 rejects:

- HTTP/1.0 or other versions;
- absolute-form request targets;
- authority-form or asterisk-form targets;
- tabs or extra spaces in the request line;
- methods other than exact `GET` or `POST`;
- non-ASCII/control-bearing request lines.

The path is then reconstructed through M34's canonical request type, which preserves M34's no-percent-decoding, no-query/fragment, no-dot-segment, no-repeated-slash and finite-path rules.

## Line endings and header parsing

M35 requires exact `CRLF` line endings and one `CRLFCRLF` head terminator within the configured header bound.

It rejects:

- bare LF or bare CR;
- obs-fold / continuation lines;
- empty header lines before the terminator;
- malformed colon spacing;
- non-ASCII header text;
- control-bearing header values;
- leading or trailing ordinary spaces in header values;
- case-insensitive duplicate header names.

Every wire header line must use exact:

```text
Header-Name: value
```

M35 deliberately accepts only these canonical header spellings:

```text
Host
Accept
Connection
Content-Length
Content-Type
```

All other headers fail closed, including transfer/content encoding, Upgrade, authorization/cookies, proxy credentials, `Forwarded`, `X-Forwarded-*`, method override, ranges, trailers, TE, and extension headers.

This is a small reference interoperability profile, not a general-purpose HTTP server parser.

## Host authority binding

The M35 constructor receives one exact canonical authority string, such as:

```text
market.example
market.example:8443
```

The configured authority is bounded ASCII lowercase text with conservative DNS-label syntax and an optional canonical decimal port. The incoming `Host` header must equal it **byte-for-byte**.

M35 performs no:

- DNS lookup;
- wildcard or suffix matching;
- case folding;
- IDNA conversion;
- trailing-dot equivalence;
- default-port inference;
- proxy/forwarded-host trust;
- TLS SNI or certificate comparison.

Therefore:

```text
Host exact match != TLS/SNI binding
Host exact match != peer identity
Host exact match != disclosure authorization
```

A future TLS/listener milestone must independently prove the transport-side authority binding before live exposure.

## Message delimitation and request-smuggling resistance

After the one header terminator, all remaining bytes are the request body for this one-shot profile.

If `Content-Length` is absent, any trailing body bytes are rejected.

If `Content-Length` is present, it must be canonical decimal ASCII text with no leading zeroes except the single value `0`. M35 compares it directly against:

```text
str(len(body))
```

M35 **does not convert untrusted Content-Length text to a Python integer**. The only integer conversion in the module is for the already bounded, trusted configuration port text. This avoids unnecessary arbitrary-size integer work and makes message delimitation exact at the wire boundary.

Consequences:

- bytes beyond the declared body fail before M34;
- a pipelined second request appended to a declared body fails the exact length comparison;
- body bytes without a declaration fail before M34;
- duplicate `Content-Length` names fail case-insensitively;
- `Transfer-Encoding` is not in the accepted header set and cannot create a second framing interpretation.

M34 still independently validates application-specific entity-body rules. M35's framing checks do not replace M34's disclosure and route policy.

## Conversion into M34

After strict wire validation M35:

1. verifies exact Host authority and `Connection: close`;
2. removes transport-only `Host` from the application representation;
3. lowercases the four possible M34 application header names;
4. sorts those header pairs into M34's canonical name order;
5. constructs a fresh `InboundHttpRequest` under the M35/M34 shared header bound;
6. leaves request authentication and peer-identity facts false;
7. invokes the exact configured M34 application adapter once.

M35 does not retain caller-owned mutable route or request-header containers. Input is exact bytes; the M34 request is reconstructed into immutable host values.

## M34 response revalidation

M35 does not assume an object is safe merely because it was returned from M34.

The order is deliberate:

1. require the exact `PreparedInboundHttpResponse` type;
2. inspect the **returned object's** `transmitted`, authentication, peer-identity, truth, trust, authorization, and protected-side-effect flags directly and require exact `False`;
3. replay M34's original integrity witness with `dataclasses.replace(result)`; changed request, route, status, headers, body, or message type must therefore fail against the original M34 snapshot;
4. require the witnessed M34 request to equal the canonical request parsed by M35;
5. independently cross-bind the witnessed route semantics to the parsed wire route;
6. require a bounded exact response body;
7. reconstruct one fresh valid `PreparedInboundHttpResponse` before framing.

The direct authority check occurs **before** witness replay because Python dataclass replacement reconstructs `init=False` fields from their defaults. Relying on replacement alone could otherwise hide a low-level mutation of a negative authority flag.

The original M34 integrity witness is still necessary for `init=True` authoritative fields. Adversarial tests prove that a same-length body mutation or route-operation mutation cannot be re-canonicalized into a new M35 response.

### Independent route cross-binding

M35 also rejects a response that is internally self-consistent under M34's generic response shape but semantically mismatched to the wire request.

For a Record request path under `/v1/records/`, success requires all of:

```text
request method   = GET
route_kind       = IMMUTABLE_RECORD
route_operation  = exact M33/M27 immutable Record retrieval operation
olp_message_type = record
```

The reserved `/v1/records` collection path cannot produce M35 success.

For any non-Record successful request, M35 requires:

```text
request method = POST
route_kind     = FEDERATION_CONTROL
```

and the route operation may not impersonate the immutable Record retrieval operation.

Adversarial tests construct **self-consistent** M34 response objects with the wrong route kind, wrong Record operation, or wrong Record message type. Those objects pass their own M34 integrity witness but are rejected by M35 with route-binding drift. This provides an independent composition check rather than merely detecting post-construction mutation.

## Exact success response frame

M35 frames successful M34 output exactly as:

```text
HTTP/1.1 200 OK\r\n
Content-Type: application/json\r\n
Content-Length: <exact decimal body length>\r\n
Connection: close\r\n
\r\n
<body>
```

The body is byte-for-byte the M34 encoded strict OLP JSON body. M35 does not decode or re-encode OLP JSON.

Compatibility tests prove that the existing accepted M26 HTTP/1.1 response parser accepts the M35 success frame.

M35 intentionally does not construct public remote error pages. A future listener must define a separately reviewed, non-reflective remote error policy.

## Prepared wire exchange integrity

`PreparedInboundHttpWireExchange` binds under an integrity witness:

- canonical M34 request;
- configured Host authority;
- route kind and bounded route operation;
- exact status code;
- exact framed response bytes;
- bounded exact response body byte count;
- bounded OLP message type;
- `host_authority_validated=True`;
- `tls_sni_bound=False`;
- `transmitted=False`;
- request authentication and peer identity false;
- Marketplace truth, trust, authorization, and protected-side-effect authority false.

Every positive/negative authority fact above is independently checked before witness construction and is included in the witness itself. The constructor reconstructs the canonical response prefix from the claimed body length and requires exact frame length. Dataclass replacement cannot reuse an old witness for changed authority, route, body count, response bytes, message type, or authority facts.

The prepared result does **not** retain the original raw request byte sequence; it retains only the canonical M34 request required for provenance plus the prepared response wire image.

## Compatibility with M26 and M27

M35's accepted request profile intentionally includes the exact one-shot request shapes emitted by the existing reviewed clients:

- M26 control POST: Host, Content-Type, Accept, Connection close, Content-Length;
- M27 immutable Record GET: Host, Accept, Connection close.

M35 canonicalizes the accepted application header order only after duplicate rejection and exact Host verification. It does not broaden either client's semantics.

The M35 success frame is also checked against the existing strict M26 response parser.

## No network/server surface

`marketplace.runtime.inbound_http_wire` contains no concrete:

- socket or TLS primitive;
- HTTP server implementation;
- URL client;
- async/thread worker;
- subprocess;
- filesystem access;
- logging/access log;
- listener or accept loop;
- connection send/write primitive;
- retry/backoff;
- deployment primitive.

A source-level adversarial test enforces this import boundary.

## Retention

The following remain EPHEMERAL and subject to the project maximum of **10 seconds post-use**:

- raw request bytes;
- parsed request head and Host;
- body bytes;
- canonical M34 request;
- M34 prepared response;
- framed response bytes;
- integrity witness.

M35 introduces no durable request journal, access log, response cache, session state, credential store, or filesystem persistence.

## Explicitly out of scope

- socket/listener creation;
- TLS termination / certificate validation / SNI binding;
- TCP stream accumulation / partial-read loop;
- remote requester authentication or mTLS;
- reverse-proxy trust;
- IP/identity rate limiting;
- keep-alive / connection reuse;
- chunked/compressed request bodies;
- streaming;
- public remote error-page policy;
- deployment/systemd/container service;
- live Marketplace federation peer execution.

Any future live listener remains a separate HIGH-risk `NETWORK_EXTERNAL` capability and requires explicit operator authorization immediately before actual external execution.

## Recovery

M35 adds no migration, deployment, listener, secret, credential, durable database state, or live network side effect. Code recovery is by reverting the eventual M35 merge commit.
