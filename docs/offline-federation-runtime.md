# Offline Federation Runtime Boundary

Status: Milestone 24 reference implementation

## Purpose

Milestone 24 creates the first runtime-facing Marketplace federation boundary without granting the runtime any network capability.

The boundary can prepare an M8 federation request, bind the request to exact local expectations, validate a caller-supplied response, and ingest fully validated immutable Marketplace records into the existing bounded EPHEMERAL runtime.

It cannot transmit the prepared request.

```text
prepared exchange          != transmitted request
received envelope          != trusted evidence
transport delivery         != record identity
transport authentication   != object proof
remote source              != global completeness
response absence           != deletion evidence
receiver acceptance        != protocol validity
replay/idempotency         != exactly-once transport
compatible federation data != agreement or authorization
```

## Packaged M8 reference semantics

The complete non-normative Milestone 8 federation/interoperability helper implementation now lives at:

```text
src/marketplace/reference/federation_v1.py
```

The historical repository tool path remains:

```text
tools/marketplace_federation_v1.py
```

but it is only a thin compatibility re-export. The package module is the single implementation source.

This preserves existing generator, validator, and developer command imports without maintaining a second M8 algorithm.

Packaging does not make the reference helper normative or mandatory.

```text
packaged M8 reference helper != protocol authority
```

## Transport-neutral runtime composition

`marketplace.runtime` continues to have zero runtime dependencies and does not import OLP.

Federation semantics are dependency-injected through explicit protocols for:

- request validation;
- abstract transport-envelope construction;
- supplied transport-envelope validation;
- exchange-result validation;
- Marketplace record validation;
- Record Identity derivation.

`compose_offline_federation_service(...)` attaches the offline federation service to an existing `MarketplaceRuntime` and therefore to the same bounded in-memory repository and node lifecycle.

The project reference composition may explicitly supply the separately installed pinned OLP implementation and `marketplace.reference.federation_v1` helpers.

## Operation profiles

The runtime does not guess which request/result message type belongs to an operation.

Each supported operation is explicitly configured as a `FederationOperationProfile` containing:

```text
operation
request_message_type
result_message_type
```

Duplicate operation profiles are rejected.

Milestone 24 reference tests configure snapshot and incremental-sync profiles. Submission execution remains outside the offline page-ingest service.

## Preparing an exchange

`OfflineFederationService.prepare(request)` performs local work only.

It validates the request through the injected M8 request validator and creates an abstract OLP transport envelope through the injected envelope maker.

The returned `PreparedFederationExchange` contains:

- the abstract envelope;
- an immutable local `FederationRequestBinding`;
- `transmitted = false`.

The binding records the exact:

```text
source
operation
scope_fingerprint
required_capabilities
page_size
expected_result_message_type
```

No hostname is resolved, no endpoint is connected, and no request is sent.

## Response validation before mutation

`accept_page(...)` accepts three caller-supplied inputs:

1. the previously prepared local exchange;
2. a response transport envelope value;
3. the corresponding `RecordV1` objects supplied by the caller.

The service validates the entire page before the first repository mutation.

The pre-ingest checks include:

- exact expected federation result message type;
- result payload shape;
- exact source equality with the prepared request;
- exact operation equality;
- exact scope-fingerprint equality;
- `global_completeness = UNKNOWN`;
- `absence_is_deletion_evidence = false`;
- sorted unique result Record Identities;
- result count not exceeding the original requested page size;
- valid page controls;
- bounded opaque next cursor when truncated;
- no cursor on a final page;
- bounded consumption of caller-supplied records;
- Marketplace semantic validation of every supplied record;
- canonical Record Identity derivation for every supplied record;
- no duplicate supplied Record Identity;
- exact set equality between response `record_ids` and derived supplied-record identities.

A failure in any of those checks occurs before local ingest starts.

## Bounded input handling

Milestone 24 does not convert an arbitrary record iterable to an unbounded tuple.

The service reads at most:

```text
prepared page_size + 1
```

records from the caller-supplied iterable. The extra element is used only to detect an over-limit page and fail closed.

The offline runtime maximum is aligned with the current M8 v1 page bound:

```text
max page records = 10,000
max cursor bytes = 4,096
```

The original prepared request may impose a smaller page limit, and the response is constrained by that smaller limit.

## Opaque cursor handling

A next cursor is treated as opaque bytes.

The offline runtime checks only whether it is present when required and whether its byte length is within the M8 bound. It does not decode, parse, compare, rank, reinterpret, or automatically follow the cursor.

```text
cursor bytes != chronology
cursor bytes != authorization
cursor bytes != global continuation truth
```

Automatic cursor following is outside Milestone 24.

## Local ingest and replay

After complete page validation, records are passed individually through the existing `MarketplaceNode.ingest(...)` path.

That preserves existing validation, Record Identity, capacity, collision, duplicate, and EPHEMERAL retention behavior.

A repeated identical immutable record is reported as a local duplicate. It does not create an exactly-once transport claim.

```text
local duplicate != exactly-once remote delivery
```

A same-identity/different-content conflict continues to fail closed through the existing repository invariants.

### Storage atomicity boundary

Milestone 24 guarantees that **page validation failures do not cause partial ingest** because all page-level semantic, binding, resource, cursor, and identity checks finish before the first write.

It does not introduce a transactional multi-record repository primitive.

Therefore a later local repository failure during the storage phase—for example, capacity exhaustion—can occur after earlier records from the already validated page were stored. That is a local storage failure, not a failed page-validation case.

A future milestone requiring all-or-nothing multi-record local commits must add an explicit transactional/batch repository contract and test it separately rather than implying atomicity here.

## Result authority

`FederationPageOutcome` deliberately carries negative authority statements:

```text
global_completeness             = UNKNOWN
absence_is_deletion_evidence    = false
transport_exactly_once_claimed  = false
transport_was_invoked           = false
creates_agreement               = false
authorizes_side_effects         = false
```

The service does not reinterpret remote data into trust, legitimacy, ownership, agreement, authorization, or global market state.

## Executable no-network invariant

Milestone 24 makes the offline boundary mechanically testable.

AST-based tests inspect both:

```text
src/marketplace/runtime/federation.py
src/marketplace/reference/federation_v1.py
```

and reject concrete network/process client imports including socket, HTTP client libraries, TLS modules, URL clients, websockets, and subprocess access. They also reject dynamic `__import__`, `eval`, and `exec` calls.

The public service implementation is constrained to:

```text
__init__
prepare
accept_page
```

There is no `send`, `fetch`, `connect`, `request`, or `transmit` method.

The repository audit separately requires the packaged M8 reference source and the thin historical wrapper, while the reproducible artifact gate requires both the M8 reference module and offline federation runtime module to be present in the built wheel.

## Retention and privacy

Milestone 24 does not change evidence retention.

Records ingested through a validated offline federation page enter the same bounded EPHEMERAL in-memory repository used by the existing runtime:

```text
default post-use retention = 10 seconds
maximum configured retention = 10 seconds
```

The runtime introduces no durable replication database, remote cache, synchronization journal, filesystem record store, or background retention mechanism.

The `PreparedFederationExchange` and response outcome are ordinary process-local Python values; M24 adds no persistence mechanism for them.

## What M24 does not do

Milestone 24 intentionally does not implement:

- sockets;
- DNS resolution;
- HTTP clients or servers;
- TLS configuration;
- proxy support;
- remote credentials;
- endpoint discovery;
- live peers;
- remote retries or backoff;
- rate limiting;
- background synchronization;
- automatic cursor following;
- durable replication or indexing;
- automatic discovery-to-match workflows;
- agreement formation;
- settlement or fulfillment execution;
- protected side effects.

## Boundary for a future network milestone

A concrete network adapter is a separate, higher-risk capability milestone.

Before any external endpoint can be contacted, that milestone must explicitly address at least:

- endpoint allowlisting and scheme restrictions;
- DNS resolution and DNS-rebinding resistance;
- SSRF and egress controls;
- loopback, link-local, private, metadata-service, and other prohibited address ranges;
- TLS certificate and hostname verification;
- authentication and credential scope;
- proxy/environment-variable behavior;
- request and response byte limits;
- connect/read/total timeout budgets;
- bounded retries tied to idempotency semantics;
- rate limiting and concurrency limits;
- remote-retention assumptions;
- privacy-safe logging;
- abuse and denial-of-service controls;
- explicit operator authorization for external network capability.

M24 intentionally stops before that boundary.
