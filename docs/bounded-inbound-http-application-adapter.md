# Bounded Inbound HTTP Application Adapter

## Status

Milestone 34 reference-runtime security boundary.

M34 is a **transport-free HTTP application adapter** above the completed M32 and M33 inbound disclosure-preparation boundaries. It accepts one already-received, already-parsed canonical HTTP-shaped request value, selects exactly one local application route, invokes M32 or M33, serializes one strict OLP JSON response, and stops before transmission.

M34 is **HIGH risk** because route confusion or responder-result confusion could cross a privacy/disclosure boundary even without a live listener.

Milestone 58 adds post-construction retained-binding hardening without changing M34 routing or disclosure semantics. See `docs/bounded-inbound-http-application-retained-binding-hardening.md`.

## Boundary

```text
HTTP-shaped request          != raw TCP/HTTP byte stream
HTTP method/path             != authenticated requester identity
valid application request    != disclosure authorization
route match                  != permission to disclose Record IDs
route match                  != permission to disclose Record body
M32 prepared response        != transmitted HTTP response
M33 prepared response        != transmitted HTTP response
HTTP 200                     != Marketplace truth / trust / authority
response serialization       != permission to write to a socket
```

M34 establishes no peer authentication, peer identity, truth, trust, ownership, legal authority, agreement, or protected-action permission.

## Placement

M34 deliberately sits between a future transport parser/listener and the existing disclosure responders:

```text
future socket/TLS/HTTP parser
          |
          | canonical already-parsed request value
          v
M34 bounded application adapter
          |
          +---- exact control POST ----> M32 disclosure/page preparation
          |
          +---- exact Record GET ------> M33 Record-body disclosure preparation
          |
          v
strict OLP JSON response bytes
          |
          X  STOP: no socket write in M34
```

A future listener must separately handle TCP, TLS, HTTP/1.1 byte-stream parsing, Host/SNI/virtual-host binding, connection lifetime, remote address facts, authentication, rate limiting, and actual writes. None of those facts are inferred by M34.

## Canonical application request representation

`InboundHttpRequest` is not a permissive HTTP parser. It is an immutable host representation expected **after** a future transport layer has parsed and normalized the wire protocol.

It requires:

- exact method text `GET` or `POST`;
- exact ASCII path bounded to 2,048 bytes;
- exact tuple of at most 16 header pairs;
- exact lowercase unique header names in canonical name order;
- exact ASCII header values under finite per-header and aggregate limits;
- exact immutable `bytes` body.

The request object carries:

```text
request_authenticated = False
peer_identity_proven   = False
```

M34 explicitly rejects either fact if it has been promoted before handling. It then reconstructs an adapter-owned canonical `InboundHttpRequest` under the adapter's own configured header bound and uses only that detached request for routing, responder calls, and response provenance. Mutating the caller's original request object after or during handling therefore cannot rewrite the prepared response's authoritative request context.

M34 never treats transport syntax as authentication.

## Path policy

Paths use the same conservative shape as the reviewed M25 endpoint policy:

- ASCII only;
- no backslashes;
- no percent-encoding;
- no query or fragment characters;
- no repeated slashes;
- no `.` or `..` path segments;
- no normalization or redirect behavior.

Configured federation control routes are exact local paths. A route must be non-root, must not have a trailing slash, and must not overlap `/v1/records/...`.

One M32 operation may appear at only one configured M34 path. This intentionally rejects route aliases that could make policy provenance ambiguous.

At adapter construction, M34 revalidates each supplied route and copies only its exact path and operation strings into adapter-owned state. It does not retain caller-owned route objects as live authority. Low-level mutation of a supplied route object after construction therefore cannot redirect a later request.

## Header profile

M34 accepts only the application-level header names:

```text
accept
connection
content-length
content-type
```

Unknown headers fail closed. This intentionally excludes credentials, cookies, authorization headers, proxy authorization, method-override headers, ambient tracing headers, and other application behavior from the M34 profile.

A future listener may process transport-level `Host` and connection syntax before constructing `InboundHttpRequest`; M34 does not use Host as an authority or routing input.

If present:

```text
Accept     = application/json
Connection = close
```

No keep-alive, upgrade, chunking, compression, content negotiation, or method override enters this milestone.

## Federation control route

A configured control route requires exact `POST`.

The request must contain:

```text
Content-Type: application/json
Content-Length: <canonical exact body length>
```

The body must be non-empty and within the configured request-body limit.

`Content-Length` is validated as bounded canonical decimal text and compared directly with `str(len(body))`; M34 does not convert attacker-controlled decimal text into an arbitrary-size Python integer.

M34 then:

1. decodes exactly one strict OLP JSON transport envelope using the existing reference codec;
2. deeply detaches the decoded host value using M30 integrity machinery;
3. binds the selected local route to exactly one configured M8 operation;
4. calls `BoundedInboundFederationResponder.prepare_response(...)` once;
5. requires the M32 result to preserve that exact operation and all negative authority facts;
6. serializes the prepared response envelope through the strict reference codec;
7. verifies exact M30 host integrity before and after the encoder to detect in-process mutation;
8. locally decodes the encoded response and compares a separate bounded **wire-semantic snapshot** with the prepared envelope.

A snapshot body sent to a sync route, or any other route/message-profile mismatch, fails through M32 before disclosure authorization.

M34 does not duplicate M8 request/result semantics and cannot convert route selection into M32 disclosure authorization.

## Immutable Record route

M34 reserves:

```text
GET /v1/records/<canonical-r1-record-identity>
```

This matches the M27/pinned-OLP immutable Record retrieval path profile.

A Record GET:

- must have no body;
- must not contain `Content-Type` or `Content-Length`;
- extracts exactly one path segment after `/v1/records/`;
- reuses M33's existing canonical Record Identity transport validator before invoking the M33 responder;
- calls `BoundedInboundRecordResponder.prepare(...)` once;
- requires the returned request identity to equal the path identity exactly;
- requires M33 identity and Marketplace-semantic verification to remain exact true;
- requires proof/truth/ownership/authority/trust/authorization/side-effect facts to remain exact false;
- serializes and strict-round-trips the prepared `record` envelope before return.

A Record ID, route match, or prior M32 page membership remains insufficient disclosure authority. M33's explicit local authorizer still decides disclosure.

## Response profile

Successful handling returns one `PreparedInboundHttpResponse` with:

```text
status = 200
Connection: close
Content-Length: <exact encoded body length>
Content-Type: application/json
transmitted = False
```

The body is one deterministic strict OLP JSON transport envelope produced by the existing reference codec.

M34 uses **two different integrity views for two different purposes**:

1. M30's exact type-tagged host snapshot is taken before encoding and checked again immediately afterward. This detects mutation of the responder's authoritative frozen host object, including distinctions such as tuple versus list.
2. A bounded wire-semantic snapshot is used only across JSON encode/decode. JSON does not preserve Python tuple/list distinction, so this snapshot deliberately treats tuple and list as the same ordered sequence while preserving exact scalar types (`bool` remains distinct from `int`), map keys, sequence order, values, and M30 depth/item bounds.

This distinction is necessary for valid M33 Record envelopes whose OLP/JSON round trip can legitimately materialize an array with a different Python container class while preserving the exact Record identity and wire meaning. A valid alternate message type, payload value, map key, scalar type, or sequence content still changes the wire-semantic snapshot and is rejected as serialization drift.

The prepared HTTP response integrity witness binds:

- the adapter-owned canonical immutable request, including its negative authentication/peer-identity facts;
- route kind;
- exact route operation;
- status;
- exact canonical response headers;
- encoded response bytes;
- OLP message type.

Host-side dataclass replacement cannot reuse an old witness for changed response facts.

## Responder-result authority checks

M34 does not trust the fact that an object came from the configured responder alone.

For M32 it requires exact negative facts including:

```text
transmitted                       = False
request_authenticated             = False
peer_identity_proven              = False
global_completeness               = UNKNOWN
absence_is_deletion_evidence      = False
creates_agreement                 = False
establishes_truth                 = False
establishes_trust                 = False
authorizes_protected_side_effects = False
```

For M33 it requires exact identity/Marketplace verification and exact negative proof/authority facts including:

```text
transmitted                       = False
identity_verified                 = True
marketplace_semantics_verified    = True
proofs_verified                   = False
request_authenticated             = False
peer_identity_proven              = False
global_existence                  = UNKNOWN
absence_is_deletion_evidence      = False
creates_agreement                 = False
establishes_truth                 = False
establishes_ownership             = False
establishes_authority             = False
establishes_trust                 = False
establishes_authorization         = False
authorizes_protected_side_effects = False
```

Adversarial tests use low-level host mutation to prove M34 rejects promoted responder and request authority facts.

## Error and privacy behavior

M34 returns local `InboundHttpError` failures with stable reason codes. It does not construct network error pages in this milestone.

When an injected codec or M32/M33 responder fails, M34 deliberately replaces the underlying exception with a bounded local error message rather than reflecting:

- raw request bodies;
- Record bodies;
- cursors;
- disclosure-policy details;
- helper exception text;
- secrets or credential-like request content.

A future listener will need a separately reviewed public error-response policy. Local error codes must not automatically become remote diagnostics.

## Resource profile

Reference defaults deliberately mirror the already reviewed M26 body/header resource scale:

```text
max request body  = 1 MiB
max response body = 1 MiB
max headers       = 32 KiB
```

Hard ceilings are:

```text
body              = 16 MiB
headers           = 128 KiB
path              = 2,048 bytes
header count      = 16
control routes    = 64
```

All limits are finite and non-disableable.

At adapter construction, M34 copies the supplied numeric limits into a fresh, revalidated `InboundHttpApplicationLimits` value. Mutation of a caller-retained limit object cannot relax a running adapter's bounds.

M34 receives a complete already-parsed body; streaming/chunked parsing belongs to a future transport layer and remains out of scope. A future raw transport parser must itself enforce a pre-allocation wire bound; M34's object-level body check cannot retroactively prevent memory already allocated by an earlier layer.

## Alias / TOCTOU resistance

M34 requires exact tuples/bytes for request authority-bearing host values rather than arbitrary iterables.

Consequences:

- arbitrary header generators are rejected without enumeration;
- arbitrary route generators are rejected without enumeration;
- request bytes are immutable;
- caller request objects are reconstructed into adapter-owned canonical requests;
- caller route objects are copied into adapter-owned path→operation scalars;
- caller limit objects are copied into adapter-owned revalidated limits;
- promoted request authentication/peer identity is rejected before disclosure;
- decoded control envelopes are deeply detached before M32;
- M34 checks that M32 did not mutate its detached request envelope;
- prepared responder envelopes use M30 tuple-backed frozen host values;
- explicit `dict.__setitem__` writes against inherited `FrozenDict` backing storage remain non-authoritative;
- exact host integrity is checked around response encoding;
- wire-semantic integrity is checked across the JSON round trip.

These controls defend the application-object boundary, not arbitrary process memory corruption or hostile interpreter modification.

## Reference codec bridge

`marketplace.reference.inbound_http_v1` is intentionally tiny. It delegates to the already reviewed M26 `transport_json_v1` codec for strict OLP single-envelope JSON decode/encode.

It contains no HTTP parser, URL client, socket, TLS, listener, thread, subprocess, filesystem, or logging primitive.

The base runtime remains importable without OLP and retains zero declared runtime dependencies.

## No network/server surface

`marketplace.runtime.inbound_http` contains no:

- `socket`;
- `ssl`;
- `http` / `http.server`;
- `urllib`;
- listener or `accept()` loop;
- TLS context;
- async/thread worker;
- subprocess;
- filesystem access;
- request/response logging;
- retry/backoff;
- deployment primitive.

A source-level adversarial test enforces this import boundary for both runtime and reference modules.

## Retention

The following remain EPHEMERAL and subject to the project maximum of **10 seconds post-use**:

- canonical request object;
- headers;
- body bytes;
- decoded control envelope;
- route context;
- M32/M33 prepared response;
- encoded response body;
- integrity witness.

M34 introduces no durable journal, request log, response cache, session store, credential store, or filesystem persistence.

## Explicitly out of scope

- raw HTTP byte-stream parsing;
- socket/listener creation;
- TLS termination;
- `Host`/SNI authority binding;
- remote requester authentication;
- API keys/cookies/sessions;
- mTLS/client certificates;
- IP/identity rate limiting;
- keep-alive or connection pooling;
- chunked/compressed request or response bodies;
- streaming;
- reverse-proxy trust configuration;
- public remote error-page policy;
- systemd/container/service deployment;
- live Marketplace peer execution.

Any future live listener remains a separate HIGH-risk `NETWORK_EXTERNAL` capability and requires explicit operator authorization immediately before actual external execution.

## Recovery

M34 adds no migration, deployment, listener, credential, durable database state, or live network side effect. Code recovery is by reverting the future M34 merge commit.
