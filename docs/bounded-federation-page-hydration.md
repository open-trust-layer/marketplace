# Bounded Federation Page Hydration

Status: Milestone 28 reference implementation

## Purpose

Milestone 28 coordinates one already-supplied Marketplace M8 snapshot/sync page with the accepted M27 immutable Record retrieval primitive.

It answers a narrow runtime question:

> Can one finite M8 page of exact Record identities be fully target-preflighted, retrieved sequentially, locally identity-verified, Marketplace-valid, and then handed to the existing M24 acceptance path without allowing the page to become unbounded network authority or partial pre-validation storage?

M28 does not obtain the M8 control page over the network. M26 remains the control-transport primitive. M28 begins with a caller-supplied prepared exchange and response envelope.

```text
page result                    != permission to fetch arbitrary URLs
record_ids                     != trusted Records
N record_ids                   != unbounded network permission
validated target set           != authorization safe forever
successful first retrieval     != permission to store partial page
all identities verified        != proof validity / truth / authority
hydration success              != global completeness
hydration success              != automatic cursor-follow permission
hydration success              != retry permission
hydration success              != agreement / protected action
```

## Components

M28 deliberately composes existing boundaries rather than creating a second federation interpretation stack.

### M24 page validation

`OfflineFederationService.validate_page(...)` performs the existing M8 response binding and page-control checks without receiving Record bodies or touching repository state.

It validates:

- expected M8 result message type;
- source binding;
- operation binding;
- scope fingerprint binding;
- global completeness remains `UNKNOWN`;
- absence does not become deletion evidence;
- Record identities are sorted and unique;
- page-size bounds;
- page truncation/cursor rules.

It returns `ValidatedFederationPage`.

`OfflineFederationService.accept_page(...)` calls the same `validate_page(...)` method again before validating supplied Records and before its first repository mutation. M28 therefore does not duplicate M8/M24 semantics.

### M27 target preflight

`AuthorizedHttpsRecordRetriever.preflight(...)` performs only conditions that can be checked before DNS/network activity:

- canonical bounded expected `r1_...` transport identity;
- current exact M25 endpoint authorization;
- exact `/v1/records/<record-id>` path binding;
- bounded GET request head.

Preflight performs no DNS lookup and creates no socket.

It is only an early rejection aid. `retrieve(...)` independently repeats the same pre-network validation when each GET begins and still revalidates endpoint authorization after fresh DNS immediately before connect. A successful preflight is not a reservation or future authorization.

### M27 pinned-OLP verification

The reference adapter `verified_retrieved_market_record_value(...)` delegates to the existing M27 `verify_retrieved_market_record(...)` implementation and returns only its already identity- and Marketplace-semantics-verified `RecordV1` value.

No Record Identity logic is duplicated for M28.

### M28 orchestrator

The base-runtime implementation is:

```text
marketplace.runtime.page_hydration.BoundedFederationPageHydrator
```

It remains OLP-independent. The OLP-aware Record verifier is injected.

## Explicit limits

Reference defaults:

```text
max hydrated Records per page = 16
page orchestration budget      = 60 seconds
```

Hard configuration maxima:

```text
max hydrated Records per page = 64
page orchestration budget      = 300 seconds
```

Limits cannot be zero, negative, boolean, non-finite, or unbounded.

The page orchestration budget is checked between phases and before starting additional retrievals. M28 does not cancel or extend one already-started M27 retrieval; that individual request remains bounded by M26/M27's own connect/read/total limits.

## Exact target set

The caller supplies exactly one `RecordHydrationTarget` per validated page Record identity.

Each target binds:

- exact `record_id`;
- exact HTTPS endpoint;
- exact M25 endpoint authorization.

Before any target preflight or retrieval, M28 requires:

- validated page Record count within the configured hydration bound;
- bounded target iterable;
- target Record identities unique;
- exact endpoints unique across distinct Record identities;
- target identity set exactly equals the validated page identity set.

M28 does not infer a base URL, perform service discovery, inspect peer-provided related links, or construct an endpoint from the M8 response.

## All-target preflight before first GET

M28 preflights every target in canonical page Record-identity order before the first call to `retrieve(...)`.

If any target preflight fails:

- zero Record GETs have started;
- zero Records are stored;
- no retry occurs.

The later `retrieve(...)` calls repeat the relevant authorization/path checks and perform fresh DNS validation, so preflight cannot make stale authorization safe.

## Deterministic sequential retrieval

After all targets pass preflight, M28 calls M27 `retrieve(...)` sequentially in the canonical M8 page Record-identity order.

For one M28 invocation:

- at most one M27 retrieval call is made per page Record identity;
- there is no parallel retrieval;
- there is no retry/backoff;
- there are no redirects;
- there is no connection pooling added by M28;
- there is no background work;
- there is no cursor following;
- there is no related-Record traversal.

M28 does not itself import or instantiate a socket, TLS client, URL client, proxy client, async runtime, thread pool, or subprocess interface.

## M27 transport-result invariants

A returned object from the injected M27 retriever is treated as untrusted runtime input.

M28 requires it to be exactly a `RetrievedRecordTransportResult` bound to the expected identity with:

```text
http_status                     = integer 200
connection_attempts             = integer 1
redirects_followed              = integer 0
retries_performed               = integer 0
proxy_used                      = false
credentials_used                = false
identity_verified               = false
marketplace_semantics_verified  = false
proofs_verified                 = false
establishes_truth               = false
establishes_authorization       = false
automatically_ingested          = false
```

The response envelope must still be exactly one tuple-shaped:

```text
("OLP-TRANSPORT", integer 1, "record", payload)
```

Boolean values cannot substitute for integer `0`, `1`, or `200` despite Python's numeric equality behavior.

If these invariants fail, the Record verifier is not called and no storage occurs.

## Local Record verification

For each accepted transport result, M28 invokes the injected verifier with:

- the exact `record` envelope;
- the expected page Record identity.

The packaged reference adapter reuses M27's pinned OLP verifier, which:

1. reconstructs `RecordV1`;
2. validates OLP Record structure;
3. recomputes the authoritative textual OLP Record Identity locally;
4. requires exact equality to the requested identity;
5. validates Marketplace semantics.

M28 keeps each verified Record only in process memory until the complete page has been verified.

Identity equality and Marketplace semantic validity still do not establish proof validity, truth, ownership, legal authority, trust, agreement, or protected-action authorization.

## Storage boundary

M28 does **not** call M24 `accept_page(...)` until every page Record has completed:

```text
page validation
-> exact target-set validation
-> all-target M27 preflight
-> sequential M27 retrieval
-> M27 transport-result invariant validation
-> local OLP identity recomputation
-> Marketplace semantic validation
```

If any failure occurs before the final M24 call, M28 has performed **no repository mutation** for that page.

At the final boundary M28 calls the existing `OfflineFederationService.accept_page(...)` once with the complete verified Record collection. M24 then independently re-runs page validation, Marketplace Record validation, Record Identity derivation, and exact Record-set equality before its first local mutation.

### Important transactional limitation

The statement above is a **pre-storage validation guarantee**, not a transactional database guarantee.

The existing M24 in-memory ingest path stores validated Records one by one. M28 does not add a transaction, rollback log, write-ahead journal, or reversible repository operation. Therefore, if the repository itself raises a local storage failure during the final already-validated M24 ingest loop, M28 does **not** claim that earlier successful local puts from that final loop can be rolled back.

A future transactional-storage milestone would need a separately reviewed atomic repository contract if that property is required.

This distinction prevents M28 from overstating “all-or-nothing storage.” M28 guarantees no local storage before complete page/network/identity/semantic validation; it does not claim atomic commit under local repository failure.

## Outcome semantics

`FederationPageHydrationOutcome` wraps the existing M24 `FederationPageOutcome` and adds operational facts:

- hydrated Record identities;
- number of M27 retrieval calls attempted;
- whether Record transport was invoked;
- retries performed = `0`;
- parallel retrieval = `false`;
- cursor automatically followed = `false`;
- proofs verified = `false`;
- truth established = `false`;
- authorization established = `false`;
- agreement created = `false`.

M28 does not rewrite M24's `transport_was_invoked` field. That M24 field continues to describe the transport-neutral/offline M24 acceptance service itself; the M28 wrapper separately records that M27 Record transport was invoked.

## Time-source safety

The injected monotonic clock is treated as a runtime dependency rather than trusted data.

M28 rejects:

- boolean values;
- non-numeric values;
- NaN;
- positive/negative infinity;
- clock rollback relative to the captured start value.

A failing clock causes local fail-closed termination; it never grants additional network work.

## Privacy and retention

M28 adds no:

- durable Record cache;
- HTTP cache;
- DNS cache;
- body journal;
- response-body log;
- credential store;
- background synchronization state.

Verified Record values remain in process memory during hydration. If pre-final-acceptance hydration fails, M28 performs no repository mutation. After successful explicit M24 ingest, the existing Marketplace runtime retention remains:

```text
retention class   = EPHEMERAL
default retention = 10 seconds
maximum retention = 10 seconds
```

M28 does not lengthen that retention.

## CI / live-network boundary

Tests use deterministic retriever/verifier doubles. CI must not intentionally contact a live federation peer.

A concrete invocation using M27's default resolver/connector remains a `NETWORK_EXTERNAL` operation requiring explicit operator authorization under `DEVELOPMENT_POLICY.md`.

## What M28 does not do

M28 intentionally does not implement:

- network acquisition of the M8 control page;
- automatic endpoint/service discovery;
- DNS SRV discovery;
- page sizes above the explicit hydration limit;
- parallel/concurrent page hydration;
- retries/backoff;
- automatic cursor following;
- multi-page synchronization;
- authentication/API keys;
- mTLS/client certificates;
- HTTP Message Signatures;
- proof/bundle/resource retrieval;
- proof verification;
- ETag/conditional GET/cache validators;
- chunked/compressed/streaming Record bodies;
- durable replication/index storage;
- transactional repository commit/rollback;
- background synchronization;
- inbound federation service;
- settlement/fulfillment/agreement/protected side effects.

## Follow-on boundary

A later milestone may consider bounded multi-page/cursor synchronization. Transactional repository commit, authentication, proof verification, retries, caching, concurrency, and inbound federation remain separate capabilities and require independent review.
