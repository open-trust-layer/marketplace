# Authorized HTTPS Federation Control Transport

Status: Milestone 26 reference implementation

## Purpose

Milestone 26 introduces the first concrete outbound Marketplace network capability. The reference adapter performs exactly one synchronous HTTPS `POST` carrying one existing OLP JSON single-object transport envelope and accepts one bounded OLP JSON envelope response.

This is a **HIGH-risk** capability milestone because the runtime can open an external connection when deliberately invoked. Development and CI do not contact live external endpoints; the test suite injects resolver, socket and TLS doubles. A real invocation requires explicit operator authorization for `NETWORK_EXTERNAL` immediately before execution under `DEVELOPMENT_POLICY.md`.

```text
network connection          != trusted peer
TLS success                 != OLP proof validity
HTTP 200                    != Marketplace truth
transport response          != agreement
transport response          != authorization
endpoint authorization      != M11 protected-action authorization
resolved address validation != safe forever
one request                 != retry permission
```

## Source-derived wire basis

M26 does not invent a Marketplace wire envelope.

Marketplace Specification 0008 requires federation messages transported as OLP messages to reuse OLP `TransportEnvelopeV1`. The pinned OLP Specification 0012 defines the JSON single-object form:

```json
{
  "olp": 1,
  "type": "<message type>",
  "payload": <OJVE-1 value>
}
```

and uses the standard media type:

```text
application/json
```

M26 carries that representation over HTTPS. The configured exact endpoint path is a non-normative reference deployment choice; M26 does not make one Marketplace HTTP path mandatory.

## Runtime/reference separation

The concrete network client lives at:

```text
marketplace.runtime.https_transport
```

The base runtime remains independent of OLP and retains zero declared runtime dependencies.

The strict OLP JSON envelope codec lives separately at:

```text
marketplace.reference.transport_json_v1
```

That reference codec requires the separately supplied pinned OLP implementation and delegates envelope/OJVE semantics to `TransportEnvelopeV1`.

This preserves:

```text
runtime network capability != OLP semantic authority
reference codec             != mandatory implementation
transport representation   != evidence identity
```

## Authorization before DNS

`AuthorizedHttpsFederationTransport.exchange(...)` requires:

1. an M24 `PreparedFederationExchange` whose `transmitted` field is exactly `false`;
2. an M25 `FederationEndpointAuthorization`;
3. the exact endpoint that authorization binds;
4. the configured M25 `FederationEgressPolicy`.

Before invoking the resolver, the adapter revalidates the endpoint authorization using the current injected/default wall clock and the prepared M8 operation.

An expired, not-yet-valid, mismatched, malformed or authority-escalating authorization therefore fails before DNS or connection activity.

The request envelope is also encoded and bounded before DNS, so an oversized/malformed local request cannot trigger an external lookup.

## Fresh resolution and address pinning

After current authorization validation, the adapter performs a fresh resolver call for the authorized DNS hostname and port.

Every returned address is passed through the M25 `validate_resolved_addresses(...)` classifier. If any supplied result is malformed, private, loopback, link-local, multicast, reserved/non-global, IPv4-mapped IPv6, or one of the reviewed IPv6 transition/translation forms, the entire exchange fails before connect.

The validated addresses are canonicalized; the first deterministic address is selected.

**DNS resolution does not freeze authorization validity.** After fresh resolution and address classification, the adapter revalidates the same immutable endpoint authorization again using a fresh wall-clock value **immediately before opening the socket**. If the authorization expired or became invalid during DNS processing, the exchange fails without a connection attempt.

The default connector then:

- creates an IPv4 or IPv6 socket for that **numeric selected address**;
- connects directly to that numeric address so a higher-level HTTP client cannot silently re-resolve the hostname;
- preserves the authorized DNS hostname separately for TLS SNI and certificate hostname verification.

```text
selected numeric address != TLS identity name
authorized DNS hostname  = TLS SNI / certificate hostname
```

No prior/cached classification can authorize a later call. A new `exchange()` performs the sequence again.

## TLS profile

The default secure connector uses the platform trust store via `ssl.create_default_context()` and sets:

```text
minimum TLS version = TLS 1.2
certificate verify  = REQUIRED
hostname checking   = true
ALPN                 = http/1.1 only
```

There is no insecure verification flag and no plaintext fallback.

The TLS `server_hostname` is the M25-authorized DNS hostname, never the selected numeric address.

M26 is limited to HTTP/1.1. A peer selecting another ALPN protocol is rejected.

## Exact HTTP request profile

The reference client emits one request:

```text
POST <authorized exact path> HTTP/1.1
Host: <authorized hostname[:port]>
Content-Type: application/json
Accept: application/json
Connection: close
Content-Length: <exact bounded request body size>
```

It does not send:

- `Authorization`;
- cookies;
- `Proxy-Authorization`;
- userinfo-derived credentials;
- ambient environment-derived headers.

The implementation uses direct sockets/TLS rather than an environment-aware URL opener, so it does not inherit `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `.netrc`, cookies, process-global opener handlers or browser/system credential stores.

## Exact response profile

M26 intentionally accepts a small HTTP/1.1 subset.

A response must have:

- an HTTP/1.1 status line;
- status `200`;
- exactly `Content-Type: application/json`;
- exactly one canonical decimal `Content-Length`;
- a non-empty body within the configured maximum.

M26 rejects:

- redirects and every non-200 status;
- `Transfer-Encoding` / chunked bodies;
- `Content-Encoding` / compressed bodies;
- missing/duplicate/noncanonical `Content-Length`;
- malformed/folded headers;
- ASCII control bytes in the status line or header values;
- header overflow;
- body overflow;
- truncated bodies;
- unsupported content type.

The connection is closed after one response; there is no pooling or persistent HTTP session.

## Strict JSON envelope codec

`marketplace.reference.transport_json_v1`:

- accepts/produces strict UTF-8 bytes;
- rejects UTF-8 BOM;
- rejects duplicate JSON object member names recursively before OLP interpretation;
- rejects non-finite JSON numeric constants;
- delegates OJVE/envelope validation to pinned OLP `TransportEnvelopeV1`;
- materializes decoded M8 payloads only with string map keys for the M8 schema boundary;
- uses deterministic compact JSON output for the reference sender.

After the injected/reference decoder returns, the runtime independently requires exactly one four-element abstract OLP transport envelope with marker `OLP-TRANSPORT`, exact integer version `1`, and a non-empty text message type. A hostile or incorrectly wired decoder cannot promote an arbitrary object into a successful transport result.

The codec does not change OLP Record/Proof identity.

## Resource and time limits

`HttpsFederationTransportLimits` provides bounded, non-disableable limits for:

```text
connect timeout
read timeout
total exchange timeout
maximum request body bytes
maximum response body bytes
maximum response header bytes
maximum resolved addresses
maximum concurrent exchanges
```

Reference defaults are conservative and every configurable limit has a finite ceiling.

A nonblocking bounded semaphore enforces concurrent-exchange capacity; the adapter fails immediately rather than silently queueing unbounded work.

The total timeout budget is recomputed between phases so DNS/connect/read work cannot intentionally receive a fresh unlimited phase budget.

## Exactly one attempt

Each `exchange()` call performs at most one connector invocation.

M26 includes:

```text
connection_attempts = 1
redirects_followed   = 0
retries_performed    = 0
proxy_used           = false
credentials_used     = false
```

A connection/TLS/write/read failure is returned as a local transport error. M26 does not retry snapshot, sync or submission operations.

Retry/idempotency policy is a separate capability and must not be inferred from the existence of M8 replay helpers.

## Result authority

`HttpsFederationExchangeResult` carries the decoded transport envelope plus bounded transport metadata. It explicitly states:

```text
establishes_peer_trust         = false
establishes_marketplace_truth  = false
establishes_agreement          = false
establishes_authorization      = false
```

The caller must still validate the response message type and M8 result semantics through the existing M24/M8 validation path.

A successful TLS connection and HTTP response therefore do not bypass Marketplace semantic validation or M11 authorization.

## Privacy and retention

M26 adds no durable transport journal, cache, DNS cache, body log, credential store, telemetry service, background task or filesystem persistence.

Request/response envelope bytes exist only in process memory for the synchronous exchange. The transport implementation does not log or persist their contents.

Diagnostics use stable local reason codes and exception type names rather than raw body content or remote exception messages where those might carry sensitive data.

Existing Marketplace record retention remains unchanged:

```text
default EPHEMERAL retention = 10 seconds
maximum configured EPHEMERAL retention = 10 seconds
```

M26 itself does not ingest records. M24 remains the local page validation/ingest boundary.

## Test isolation

M26 tests use injected resolver/connector/clock doubles. The default concrete connector is tested by patching socket and TLS context construction; CI does not intentionally resolve or contact a live federation peer.

This distinction is important:

```text
package contains NETWORK_EXTERNAL capability != CI exercises live Internet
```

No live peer endpoint or credential is committed to the repository.

## Packaging and provenance

The reproducible artifact gate requires both:

```text
marketplace/runtime/https_transport.py
marketplace/reference/transport_json_v1.py
```

in the built wheel in addition to the M25 security module.

The base Marketplace distribution still declares zero runtime dependencies. The reference JSON codec is usable only when the separately supplied pinned OLP implementation is present, consistent with the existing `marketplace.reference` boundary.

## What M26 does not do

M26 intentionally does not implement:

- a live peer configuration in this repository;
- authentication credentials or API keys;
- HTTP Message Signatures;
- mTLS/client certificates;
- redirects;
- proxies;
- retries/backoff;
- HTTP/2 or HTTP/3;
- chunked transfer coding;
- content compression;
- persistent connections or connection pooling;
- automatic cursor following;
- immutable Record body retrieval;
- streaming record/bundle transport;
- durable replication/index storage;
- background synchronization;
- inbound/server federation;
- agreement formation;
- settlement/fulfillment execution;
- package publication/signing.

## Follow-on boundary

M26 returns an M8 control/result envelope. For snapshot/sync results, that envelope identifies immutable records by exact OLP Record Identity but does not fetch their bodies.

A later milestone may add **authorized immutable OLP Record retrieval** with the same M25/M26 destination controls and mandatory recomputation of Record Identity before use. Authentication, retries, streaming, proxies and inbound federation remain separate reviewable capabilities.
