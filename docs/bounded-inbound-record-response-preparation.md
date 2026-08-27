# Bounded Inbound Immutable Record Response Preparation

## Status

Milestone 33 reference-runtime security boundary.

M33 prepares exactly one immutable Marketplace Record body for a future transport adapter and stops before transmission. It is the transport-free server-side counterpart to M27 immutable Record retrieval.

M33 is **HIGH risk** because disclosure of a Record body can reveal materially more information than an M32 federation control page containing only Record IDs.

## Authority boundary

```text
canonical Record ID             != permission to disclose Record body
Record exists locally           != permission to disclose it
M32 page membership             != Record-body disclosure authorization
request route/path              != authenticated peer identity
prepared Record envelope        != transmitted Record
Record Identity equality        != proof verification
successful local policy         != truth / trust / ownership / legal authority
local not-found                 != deletion evidence
local not-found                 != global nonexistence
```

M33 establishes no requester authentication, peer identity proof, proof validity, truth, ownership, authority, trust, agreement, or protected-action permission.

## Composition

M33 deliberately reuses existing reviewed boundaries:

- `ExactRecordSource.get(record_id)` for one exact local lookup;
- `RecordValidator` for Marketplace semantic validation;
- `RecordIdentityProvider` for authoritative OLP Record Identity derivation;
- `marketplace.reference.record_serving_v1.market_record_transport_payload` for pinned-OLP RecordV1-to-host-payload materialization;
- `TransportEnvelopeV1(message_type="record", ...)` only in the reference layer;
- the existing M27 `verify_retrieved_market_record` semantics, wrapped by `verify_prepared_record_transport_envelope`, to re-verify the completed prepared envelope;
- M30 `detach_host_value` / `host_value_integrity_snapshot` and the same depth/item constants for bounded deep detachment, pre-copy conversion limits, and immutable integrity witnesses.

The runtime module does not import OLP and contains no concrete network/server implementation.

## Execution order

One call to `BoundedInboundRecordResponder.prepare(...)` follows this fail-closed order:

1. validate the requested Record Identity in the exact M27-compatible `r1_` + canonical 43-character base64url form;
2. construct immutable `InboundRecordRequestContext` with the configured local source and the shared M27 retrieval operation URI;
3. invoke the local disclosure authorizer exactly once;
4. require exact boolean `True`;
5. perform at most one exact local `get(record_id)` lookup;
6. treat `None` only as local unavailability, never deletion/global nonexistence;
7. validate Marketplace semantics of the returned local Record;
8. derive authoritative OLP Record Identity and require exact equality to the requested ID;
9. invoke the pinned reference payload preparer, applying M30's depth/item profile before copying frozen OLP containers into mutable host values;
10. re-run semantic validation and identity derivation after that helper boundary to detect mutation of a mutable/custom source Record;
11. deeply detach the prepared payload with M30 bounded host-value machinery;
12. require a string-keyed mapping;
13. prepare one abstract OLP transport envelope;
14. require exact marker `OLP-TRANSPORT`, integer version `1`, message type `record`, and payload integrity-snapshot equality to the validated payload;
15. independently re-verify the completed envelope using the existing M27 Record verifier semantics;
16. require exact identity equality, Marketplace semantic verification, and negative proof/truth/ownership/authority/trust/authorization/ingest facts;
17. bind an immutable integrity snapshot to request context + completed envelope;
18. return `PreparedInboundRecordResponse(transmitted=False)`;
19. stop.

No listener, transmission, retry, loop, scheduler, persistent token, or background continuation is present.

## Prepared-response semantics

`PreparedInboundRecordResponse` explicitly preserves:

```text
transmitted = False
local_record_found = True
identity_verified = True
marketplace_semantics_verified = True
proofs_verified = False
request_authenticated = False
peer_identity_proven = False
global_existence = UNKNOWN
absence_is_deletion_evidence = False
creates_agreement = False
establishes_truth = False
establishes_ownership = False
establishes_authority = False
establishes_trust = False
establishes_authorization = False
authorizes_protected_side_effects = False
```

The prepared value intentionally does not retain a second reference to the local source `RecordV1`; the body exists only in the deeply detached envelope that a future transport adapter would need.

## Reference payload round trip and resource profile

`market_record_transport_payload(...)` validates the local `RecordV1`, validates Marketplace semantics, verifies the expected Record Identity, converts frozen OLP host containers to ordinary bounded host values, reconstructs a fresh `RecordV1` from that payload, revalidates it, and recomputes the same identity.

Pinned OLP permits a broader reference-value resource profile than M30's prepared-host representation. M33 therefore enforces `MAX_PREPARED_SNAPSHOT_DEPTH` and `MAX_PREPARED_SNAPSHOT_ITEMS` **during** OLP-container conversion, before allocating the corresponding mutable dict/list representation. A Record may be valid OLP evidence yet be locally undisclosable through this bounded M33 profile; that is an explicit implementation/resource result, not a semantic invalidity claim.

`verify_prepared_record_transport_envelope(...)` then reuses M27's `verify_retrieved_market_record(...)` over the final envelope. This provides an independent post-envelope proof that the body a future M27 client would receive is the same immutable Marketplace Record identified by the requested identity.

## Alias and TOCTOU resistance

The payload is deeply detached before the envelope-maker boundary. Later mutation of the payload provider's caller-owned alias cannot change authoritative prepared content.

Envelope payload preservation is checked with `host_value_integrity_snapshot(...)`, not ordinary container equality. This is necessary because M30's tuple-backed `FrozenDict`/`FrozenList` deliberately keep inherited base-class storage non-authoritative; authoritative equality for security binding is the type-tagged snapshot.

The completed envelope is deeply detached before verification and return. M30 tuple-backed `FrozenDict` / `FrozenList` authoritative state means even explicit base-class writes affect ignored backing storage rather than the values consumed by Marketplace/OLP logic.

The prepared response integrity witness prevents `dataclasses.replace(...)` or similar host-side rebinding of an old witness to a changed request/envelope.

## Local source semantics

M33 performs one exact lookup only after disclosure authorization.

A local miss means only:

```text
requested Record is not currently available in this local source
```

It does **not** mean:

- the Record never existed;
- the Record was deleted;
- another peer does not have it;
- the Marketplace has globally removed it;
- the requested fact is false.

## M32 relationship

M32 prepares control pages containing canonical Record IDs. M33 does not require evidence that a requested Record ID appeared in a prior M32 page, and page membership is never converted into disclosure authorization.

A future server may choose a policy that uses an authenticated session or prior control exchange as an input to its **local authorizer**, but that is outside M33 and cannot be inferred from the Record ID itself.

## Retention and privacy

Requested identity, local Record body, prepared payload/envelope, and authorization context are EPHEMERAL. Project policy limits their retention to at most **10 seconds post-use**.

M33 introduces no durable storage and logs none of these values.

Repository `get(...)` may refresh the existing local runtime's EPHEMERAL retention window for the one returned Record; this is the established runtime repository behavior and remains bounded by the same 10-second maximum.

## Network / server boundary

M33 contains no:

- socket or socket accept loop;
- TLS termination;
- HTTP server/client;
- URL fetcher;
- listener;
- remote authentication/session mechanism;
- retry/backoff;
- async/thread worker;
- subprocess;
- filesystem read/write;
- logging of Record/request content;
- deployment/persistence primitive.

Actually exposing M33 through a listener or contacting/serving a live Marketplace peer is a later **HIGH-risk `NETWORK_EXTERNAL`** action requiring explicit operator authorization immediately before live execution.

## Acceptance

M33 acceptance requires:

- focused functional and adversarial tests;
- malformed identity rejection before policy/source access;
- authorization-before-read proof;
- local-not-found non-authority proof;
- wrong-identity/non-Marketplace Record rejection;
- source-Record mutation detection across payload helper boundary;
- payload alias detachment proof;
- pre-copy depth/item resource-bound rejection;
- envelope marker/version/type/payload integrity-snapshot binding checks;
- verifier identity-drift and authority-escalation rejection;
- base-container mutation resistance;
- prepared-object integrity rebinding rejection;
- no-network/server/filesystem/background/logging source guard for runtime and reference adapter;
- actual built-wheel membership checks for M33 runtime and reference adapter;
- repository presence check for this security document;
- full existing conformance gate, deterministic vector replays, package smokes, artifact reproducibility, and whitespace checks;
- honest review provenance and governance;
- exact-head guarded merge only when governance permits;
- green exact merged-main push CI before M33 is COMPLETE.
