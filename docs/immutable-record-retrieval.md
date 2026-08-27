# Authorized Immutable OLP Record Retrieval

Status: Milestone 27 reference implementation

## Purpose

Milestone 27 adds one immutable-object retrieval primitive above the accepted M25/M26 network boundary.

It retrieves exactly one OLP `record` transport envelope from one exact M25-authorized HTTPS URL, then requires a separate pinned-OLP reference verifier to reconstruct `RecordV1`, recompute Record Identity locally, compare it to the requested `r1_...` identity, and validate Marketplace semantics.

Retrieval itself does not store the record.

```text
requested Record Identity      != received Record
HTTP 200                       != identity match
record envelope                != valid RecordV1
RecordV1 structure             != Marketplace semantic validity
identity match                 != proof validity
identity match                 != truth / ownership / authority
retrieval success              != local ingest
retrieval success              != agreement / authorization
remote server assertion        != local identity recomputation
```

## Source-derived HTTP basis

Pinned OLP Specification 0012 defines immutable Record retrieval as:

```text
GET {base}/v1/records/{recordIdText}
```

with a successful OLP transport envelope whose message type is exactly:

```text
record
```

The OLP server-side profile requires the server to recompute identity before returning a successful immutable Record representation. M27 deliberately does the same check again on the receiving side; the server is not trusted to have enforced its own requirement.

Marketplace M8 separately requires a receiver to recompute every supplied Marketplace Record identity before consequential use.

## Runtime transport

The transport-only implementation lives at:

```text
marketplace.runtime.record_retrieval
```

The reference retriever requires:

- an exact endpoint authorized through M25;
- the local M27 egress-operation identifier;
- one expected canonical bounded `r1_...` transport identity;
- the M26 strict JSON decoder boundary;
- the accepted M26 resolver/connector/HTTP response helpers.

The local operation identifier is:

```text
https://open-trust-layer.github.io/marketplace/runtime/v1/operation/olp-record-retrieval
```

It is **local runtime egress-policy scope only**. It is not added to Marketplace M8 core federation operations and does not become protocol authority.

## Exact path binding before DNS

M27 does not construct a remote endpoint from an untrusted peer response.

The caller supplies one exact M25-authorized endpoint. Before DNS, the runtime requires the authorized canonical path to end with:

```text
/v1/records/<expected-r1-identity>
```

Before endpoint authorization or DNS, the expected identity must have the bounded textual transport shape:

```text
r1_<43 base64url characters>
```

The runtime also decodes that base64url payload, requires exactly 32 octets, re-encodes it canonically without padding, and requires byte-for-byte textual equality. This is a pre-network transport-presentation guard only; it does not recompute the identity of any received Record. The pinned-OLP verifier remains responsible for authoritative Record reconstruction and Record Identity recomputation after retrieval.

A non-canonical expected identity or path/identity mismatch fails before DNS.

## Reuse of the M26 network boundary

M27 does not introduce another URL client.

It imports and reuses the accepted M26:

- resolver protocol/default resolver;
- direct numeric-address TLS connector;
- TLS hostname separation;
- response parser;
- connect/read/total timeout calculation;
- response header/body limits;
- strict OLP envelope outer-shape validation.

For each retrieval:

1. validate the expected `r1_...` transport identity as canonical and bounded;
2. validate M25 endpoint authorization under the current wall clock;
3. bind the authorized exact path to the requested identity;
4. build the complete bounded GET request before DNS;
5. freshly resolve the authorized hostname;
6. validate every supplied address through M25;
7. revalidate the same endpoint authorization after DNS immediately before connect;
8. recheck exact path/identity binding;
9. connect to the selected numeric address;
10. verify TLS using the authorized DNS hostname as SNI/certificate name;
11. send exactly one HTTP/1.1 GET;
12. accept only the existing bounded M26 response profile;
13. decode exactly one OLP envelope;
14. require message type `record`.

No prior DNS classification authorizes a later call.

## Exact request profile

```text
GET <authorized exact record path> HTTP/1.1
Host: <authorized hostname[:port]>
Accept: application/json
Connection: close
```

M27 sends no request body and no `Content-Length`.

It sends no:

- `Authorization`;
- cookies;
- proxy credentials;
- ambient environment headers.

There is no redirect following, retry, connection pool, automatic cursor following, or background retrieval.

## Transport result is deliberately unverified

`RetrievedRecordTransportResult` records transport metadata and the decoded `record` envelope while explicitly preserving:

```text
identity_verified              = false
marketplace_semantics_verified = false
proofs_verified                = false
establishes_truth              = false
establishes_authorization      = false
automatically_ingested         = false
```

A TLS-authenticated `200` response cannot promote these values.

## Pinned-OLP reference verification

The identity/semantic verification boundary lives at:

```text
marketplace.reference.record_retrieval_v1
```

`verify_retrieved_market_record(...)` performs, in order:

1. decode the expected textual identity through pinned OLP with `expected_kind="record"`;
2. require exactly one `OLP-TRANSPORT` v1 envelope;
3. require message type `record`;
4. require a string-keyed payload map;
5. reconstruct `RecordV1` from that payload;
6. validate the OLP Record structure;
7. compute `record_identity_text(record)` locally;
8. require exact equality with the requested identity;
9. run Marketplace `validate_market_record(record)`.

Only after all nine steps does it return `VerifiedRetrievedRecord` with:

```text
identity_verified              = true
marketplace_semantics_verified = true
```

Even then it explicitly preserves:

```text
proofs_verified          = false
establishes_truth        = false
establishes_ownership    = false
establishes_authority    = false
establishes_trust        = false
establishes_authorization = false
automatically_ingested   = false
```

Record identity equality proves exact immutable Record identity under OLP; it does not establish the truth or authority of the Record's claims.

## Storage / retention boundary

Neither the raw retrieval transport nor the reference verifier receives a repository and neither writes to the Marketplace runtime.

The M27 integration test requires the repository to remain empty after retrieval and local verification. It then supplies the verified `RecordV1` to the existing M24 `OfflineFederationService.accept_page(...)` path together with the exact M8 result that names that identity.

Only the pre-existing M24/node path stores the Record after all existing page/source/scope/record-set checks.

When stored, the existing runtime policy remains unchanged:

```text
retention class   = EPHEMERAL
default retention = 10 seconds
maximum retention = 10 seconds
```

M27 adds no durable record cache, HTTP cache, DNS cache, transport journal, body log, or filesystem persistence.

## Test isolation

M27 tests inject resolver and secure-connection doubles. They build OLP JSON Record envelopes locally through the pinned reference codec. CI does not intentionally contact a live external endpoint.

A real invocation of the default resolver/connector remains a `NETWORK_EXTERNAL` operation requiring explicit operator authorization.

## What M27 does not do

M27 intentionally does not implement:

- live production peer configuration;
- automatic hydration of a full page;
- concurrent/bulk record fetching;
- bundle retrieval;
- proof retrieval or proof verification;
- resource retrieval;
- ETag / conditional GET / cache validators;
- redirects;
- authentication or API keys;
- mTLS/client certificates;
- HTTP Message Signatures;
- retries/backoff;
- streaming/chunked/compressed transport;
- persistent connections;
- background synchronization;
- durable storage;
- inbound HTTP service;
- settlement/fulfillment execution;
- agreement formation;
- protected side effects.

## Follow-on boundary

A later milestone may build **bounded page hydration** above this single-record primitive: take a finite exact M8 `record_ids` set, retrieve each identity under separately valid endpoint authorization, require every body to pass M27 identity/semantic verification, and only then hand the complete set to M24 page acceptance.

That future orchestration must not weaken M27's per-record authorization, DNS, identity, resource, retention, or no-retry boundaries.
