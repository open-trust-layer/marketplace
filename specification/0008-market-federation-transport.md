# Marketplace — Federation Transport & Interoperability APIs

**Status:** Draft v0.1  
**Milestone:** 8 — Federation Transport & Marketplace Interoperability APIs  
**Filename:** `specification/0008-market-federation-transport.md`

---

## 1. Purpose

This specification defines transport-neutral federation semantics for exchanging Marketplace evidence between independent participants, applications, indexes, and federation nodes.

It standardizes Marketplace-specific capability identifiers, source-scoped snapshot and incremental-sync requests/results, scope fingerprints, opaque cursor binding, replay/idempotency boundaries, receiver outcomes, provenance requirements, and resource/privacy controls.

It does **not** define a global Marketplace server, global database, canonical peer graph, universal replication topology, mutable shared federation state, mandatory HTTP deployment, or a second evidence/wire envelope parallel to Open Layer Protocol (OLP).

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are interpreted as described by RFC 2119 and RFC 8174 when written in all capitals.

## 3. Dependency baseline

Marketplace Federation Transport v1 depends on Marketplace Specifications 0001–0007 and applicable OLP specifications, especially OLP 0008–0013.
OLP remains authoritative for Record/Proof identity, evidence bundles, resolution/discovery, reversible transport encodings, transport envelopes, streaming frames, capability/conformance semantics, HTTP transport profiles, authentication/authorization separation, privacy, and version/extension governance.

Marketplace M8 profiles those primitives; it does not fork them.

The executable vectors use the same draft OLP reproducibility pin as Milestones 3–7:

```text
41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c
```

## 4. Core invariants

1. Transport serialization and delivery MUST NOT define Marketplace or OLP Record Identity.
2. Federation is exchange among sources; it is not a global source of truth or global index.
3. A source-scoped complete result MUST NOT be upgraded to global completeness.
4. Absence from a later page/sync response MUST NOT be interpreted as deletion, withdrawal, retirement, invalidity, or nonexistence.
5. Repeated delivery of an exact immutable Record MUST be replay-safe by exact OLP Record Identity.
6. Idempotency does not create exactly-once transport semantics.
7. Transport authentication, API authorization, OLP proof validity, Marketplace semantic validity, local policy acceptance, trust, and truth are separate dimensions.
8. Capability advertisement is not proof of continuous availability, correctness, trustworthiness, or authorization.
9. Cursor validity is not authorization, freshness, completeness, or source trustworthiness.
10. Receiver acceptance/rejection is source-local policy state, not protocol truth.
11. Transport ordering MUST NOT imply evidence chronology, precedence, trust, or canonical state.
12. Resource consumption MUST be finite and explicitly bounded.
## 5. No new Marketplace record type

Milestone 8 introduces no new universal first-class Marketplace record.

`MarketIntentV1`, `MarketAgreementV1`, and `MarketEventV1` remain the complete universal Marketplace record set. Federation requests, pages, cursors, capability advertisements, idempotency bindings, and receiver outcomes are transport/processing structures, not identity-bearing Marketplace records.

A participant MAY intentionally publish an attributable OLP record about a federation event or service. Doing so does not make ephemeral transport state part of the core Marketplace record model.

## 6. OLP transport envelope reuse

Marketplace federation messages MUST reuse OLP `TransportEnvelopeV1` when transported as OLP messages:

```text
[
  "OLP-TRANSPORT",
  1,
  messageType,
  payload
]
```

Marketplace message types are third-party OLP transport extensions and therefore use globally unambiguous absolute URIs.

A Marketplace implementation MUST NOT invent a second envelope whose serialization changes the identity of contained OLP Records.

JSON, CBOR, JSON Sequence, CBOR Sequence, HTTP, message queues, P2P links, local IPC, files, and offline exchange MAY all carry the same abstract semantics where an appropriate transport profile exists.
## 7. Marketplace federation capabilities

Core M8 defines these capability identifiers:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/federation/capability/snapshot-v1
https://open-trust-layer.github.io/marketplace/semantics/v1/federation/capability/incremental-sync-v1
https://open-trust-layer.github.io/marketplace/semantics/v1/federation/capability/submission-v1
```

They MAY appear in OLP capability advertisements as absolute-URI extension capabilities.

Unknown third-party capabilities remain valid absolute-URI capability identifiers. A receiver MUST NOT reinterpret an unknown capability as one of the Marketplace core capabilities merely because its name is similar.

## 8. Capability advertisement state

The executable M8 profile models a source advertisement as:

```text
FederationCapabilitiesV1 = {
  version: 1,
  source: AbsoluteURI,
  implemented: SortedUniqueCapabilities,
  enabled: SortedUniqueCapabilities,
  configured: SortedUniqueCapabilities,
  limits: FederationLimitsV1
}
```

`enabled` and `configured` MUST each be subsets of `implemented`. A capability is available to the core negotiation profile only when it is both enabled and configured.
Advertising an implemented capability does not prove that it is enabled, correctly configured, reachable, reliable, authorized for the caller, conforming, or trustworthy.

The core limit map is exact:

```text
{
  max_page_records: 1..10000,
  max_cursor_bytes: 1..4096,
  max_submission_records: 1..1000
}
```

A profile MAY negotiate lower operational limits. Callers MAY lower local page/merge processing limits but MUST NOT raise the M8 v1 ceiling above 10,000 records. M8 v1 MUST NOT silently accept values above these executable-profile bounds when claiming M8 vector compatibility.

## 9. Capability negotiation

A caller supplies a sorted, unique set of required absolute-URI capabilities.

The core negotiation result is one of:

```text
SUPPORTED
UNAVAILABLE
UNSUPPORTED
```

`UNSUPPORTED` means at least one required capability is not implemented. `UNAVAILABLE` means all required capabilities are implemented but at least one is not both enabled and configured. `SUPPORTED` means every required capability is available under the advertisement.

Unsupported or unavailable required capabilities MUST NOT be silently downgraded to a weaker operation. Optional unknown capabilities in an advertisement do not block a request whose required capabilities are understood and available.
## 10. Federation operations and message types

Core operation identifiers are:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/federation/operation/snapshot-v1
https://open-trust-layer.github.io/marketplace/semantics/v1/federation/operation/incremental-sync-v1
https://open-trust-layer.github.io/marketplace/semantics/v1/federation/operation/submission-v1
```

Core OLP extension message types are:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/federation/message/snapshot-request-v1
https://open-trust-layer.github.io/marketplace/semantics/v1/federation/message/snapshot-result-v1
https://open-trust-layer.github.io/marketplace/semantics/v1/federation/message/sync-request-v1
https://open-trust-layer.github.io/marketplace/semantics/v1/federation/message/sync-result-v1
https://open-trust-layer.github.io/marketplace/semantics/v1/federation/message/submission-result-v1
```

Snapshot and sync requests/results use Marketplace extension message types inside OLP transport envelopes. Marketplace submission MAY profile OLP's existing bundle-submission transport rather than defining a parallel record-submission envelope; `submission-result-v1` provides Marketplace per-record receiver outcomes where required.

The M8 **core conformance helper** accepts exactly the five message types listed above. Other absolute-URI transport extensions require a separate extension profile and MUST NOT be silently treated as one of the M8 core messages.

## 11. Federation scope

The core scope is:

```text
FederationScopeV1 = {
  version: 1,
  record_types: SortedUniqueCoreMarketplaceRecordTypes,
  profiles_all?: SortedUniqueAbsoluteURIs
}
```
`record_types` MUST be non-empty and, in core v1, may contain only the three exact first-class Marketplace record-type URIs.

`profiles_all` means every returned Record must contain every listed profile URI. It is a filtering scope, not proof that no other records exist.

Unknown scope fields or unsupported record types MUST NOT be guessed or silently ignored by the executable core profile.

## 12. Scope fingerprint

Processors MAY bind pages, cursors, caches, audit entries, and replay state to a deterministic normalized scope fingerprint.

The M8 executable profile computes:

```text
base64url-no-padding(
  SHA-256(
    OLP deterministic encoding of normalized FederationScopeV1
  )
)
```

The fingerprint is processing metadata. It is not OLP Record Identity, a proof, authorization token, or global query identifier.

## 13. Snapshot and sync request

The core request shape is:

```text
FederationExchangeRequestV1 = {
  version: 1,
  source: AbsoluteURI,
  operation: snapshot-v1 | incremental-sync-v1,
  scope: FederationScopeV1,
  required_capabilities: SortedUniqueAbsoluteURIs,
  page_size: 1..10000,
  cursor?: OpaqueBytes
}
```
The required-capability set MUST include the capability corresponding to the requested operation. A request MUST NOT rely on generic “supports Marketplace” or “supports OLP” flags.

A boolean `true` MUST NOT be accepted as integer version `1`; version-domain types are exact.

## 14. Snapshot semantics

A snapshot asks one declared source to return records within one declared scope under source-local processing policy.

A snapshot is not a global index, transactionally consistent world state, canonical marketplace view, proof of current availability, or statement about records withheld by policy/privacy.

A source MAY paginate a snapshot. Page boundaries have no semantic effect on contained immutable Records.

## 15. Incremental sync semantics

Incremental sync asks a source for bounded additional immutable evidence under a declared scope and source-local cursor state.

M8 does not define a universal change log, global sequence number, deletion feed, or total order across sources.

A source MAY use private internal mechanisms to determine what to include after a cursor. The cursor is opaque to the peer unless a separate profile defines its contents.

Incremental sync conveys records supplied by the source; it does not mutate previously received records.

## 16. Request cursors

A request cursor, when present, MUST be opaque bytes of length 1..4096 in the executable profile.

A cursor used by M8 MUST be bound to:

```text
source URI
operation URI
normalized scope fingerprint
```
A cursor MUST NOT be replayed against another source, operation, or scope. Cross-context reuse is a protocol-processing error even when the opaque bytes happen to be accepted by the remote transport.

Cursor possession or successful parsing does not prove authorization, completeness, freshness, continuity, source identity, or trustworthiness.

## 17. Source-scoped exchange pages

A conforming source page carries or yields enough information to reconstruct:

```text
source
operation
scope fingerprint
contained Marketplace Records / exact Record identities
source-relative completeness
whether the page is truncated
next cursor when truncated
```

Every supplied Record MUST validate as a conforming Marketplace `MarketIntentV1`, `MarketAgreementV1`, or `MarketEventV1`, and its OLP Record Identity MUST be recomputed by the receiver before consequential use.

A record outside the declared scope MUST be rejected by the executable core profile rather than silently reclassified into the scope.

Result ordering in the conformance helper is lexical canonical `r1_` ordering only for reproducible serialization. It is explicitly **not** chronology, ranking, trust, recency, priority, or source ordering.

### 17.1 Core exchange-result payload

The M8 core result payload is:

```text
FederationExchangeResultV1 = {
  version: 1,
  source: AbsoluteURI,
  operation: snapshot-v1 | incremental-sync-v1,
  scope_fingerprint: CanonicalSHA256Base64url,
  record_ids: SortedUniqueCanonicalOLPRecordIdentities,
  source_completeness: COMPLETE_FOR_DECLARED_SOURCE | PARTIAL_SOURCE | UNKNOWN_SOURCE,
  page_truncated: Boolean,
  next_cursor?: OpaqueBytes
}
```

The scope fingerprint MUST be canonical unpadded base64url for exactly 32 SHA-256 bytes. Every `record_ids` entry MUST be canonical OLP Record Identity text, sorted and unique. A truncated result requires a bounded `next_cursor`; a final result MUST NOT carry one. Result metadata does not replace transmission of the corresponding Records and does not prove global completeness, authorization, or deletion-by-absence.

## 18. Completeness, pagination, and truncation

Core source-relative completeness values reuse the M5 vocabulary:

```text
COMPLETE_FOR_DECLARED_SOURCE
PARTIAL_SOURCE
UNKNOWN_SOURCE
```
`COMPLETE_FOR_DECLARED_SOURCE` describes only the source and scope declared by the operation. Global completeness remains `UNKNOWN`.

If `has_more` is true, a bounded next cursor is REQUIRED. If `has_more` is false, a next cursor MUST NOT be supplied by the core page profile.

A truncated or partial page remains explicitly incomplete. A receiver MUST NOT infer that omitted records are absent globally, deleted, retired, superseded, invalid, private, or nonexistent.

## 19. Record Identity and source provenance

Federation transports immutable evidence; they do not allocate Marketplace Record identities.

The receiver MUST preserve:

```text
exact recomputed OLP Record Identity
source URI that supplied the record/page
operation/scope provenance sufficient for the relying use
```

Page-level source provenance MUST remain distinguishable from authenticated fields inside the Record. A source saying “I supplied record X” is not proof that the source issued X, owns its Subject, controls its issuer, or is authoritative about its content.

When records from multiple sources are combined, exact duplicate evidence MAY be deduplicated only by exact OLP Record Identity. Implementations that retain a federated view SHOULD preserve all source associations for each deduplicated identity, consistent with Specification 0005.

## 20. Replay and immutable deduplication

Repeated delivery of the same exact Record Identity is replay, not a new immutable record.

A receiver MAY suppress duplicate storage or processing side effects after it has independently verified identity equality. It MUST NOT mutate the first Record to incorporate transport metadata from the replay.
If the same computed Record Identity is associated with unequal abstract Records, the processor MUST fail with an identity-collision/conflict condition rather than choose one by arrival order.

The executable merge helper also enforces the configured resource bound **after union**; separately bounded existing/incoming sets MUST NOT be allowed to create an oversized merged set.

## 21. Submission idempotency

Marketplace submission idempotency is a processing guarantee, not exactly-once transport.

The executable profile binds an idempotency key to:

```text
receiver endpoint URI
submission operation URI
opaque idempotency key
fingerprint of the exact unique submitted Record identities
```

The payload fingerprint is deterministic over the sorted unique OLP Record identities. Reordering or repeating an identical immutable Record does not change that semantic submission set.

Reusing the same binding with a different endpoint, operation, key, or record set MUST fail. A receiver MUST NOT silently apply the previous result to changed content.

Idempotency keys are bounded non-empty text (maximum 256 characters in the executable profile) and MUST NOT contain control characters.

## 22. Submission and receiver outcomes

Marketplace submission MAY reuse the OLP bundle-submission transport profile for carrying records/evidence. Transport acceptance does not imply Marketplace acceptance, trust, truth, authority, legality, or successful downstream action.

For each unique submitted Record, the M8 receiver-outcome profile uses exactly one source-local status:

```text
RECEIVER_ACCEPTED
RECEIVER_REJECTED
RECEIVER_IGNORED
RECEIVER_DEFERRED
```
A submission result MUST cover each unique submitted Record exactly once. Outcomes for unknown records, duplicate outcomes, invalid statuses, and incomplete outcome sets MUST be rejected by the executable profile.

An empty submission is invalid.

Receiver policy is explicitly not protocol validity, proof validity, truth, trust, authority, legality, or universal moderation state.

## 23. No deletion by sync absence

Incremental sync and snapshots are open-world source views.

If a Record seen previously is absent from a later response, the receiver MUST NOT infer deletion, withdrawal, retirement, supersession, invalidity, or revocation.

Marketplace lifecycle changes remain represented by the evidence mechanisms defined in Specification 0004 and OLP lifecycle/relationship specifications. Federation transport does not create a hidden mutable delete channel.

A source MAY stop serving content according to policy. That serving decision is not itself portable lifecycle evidence unless separately represented as evidence.

## 24. Ordering and time

Transport order, page order, retry order, queue order, and source-local sequence order MUST NOT be treated as Marketplace semantic chronology unless a separate authenticated profile explicitly defines such semantics.

`occurred_at`, OLP lifecycle evidence, Record relationships, and other authenticated content keep their existing meanings independent of delivery timing.

Receiving a Record later does not make it semantically newer, stronger, more trustworthy, or a canonical successor.
## 25. Transport security, authentication, and authorization

TLS, message-queue authentication, P2P channel authentication, HTTP Message Signatures, API keys, OAuth-like credentials, mutual TLS, or another transport mechanism MAY authenticate/protect a connection or request.

Those mechanisms do not replace OLP object proofs and MUST NOT be treated as proof that contained Marketplace claims are true, authorized, valid, legal, or trusted.

Likewise, a valid OLP proof does not automatically authorize a caller to query, synchronize, retrieve, or submit content at a federation service.

Implementations MUST keep at least these dimensions separate:

```text
transport confidentiality/integrity
transport endpoint authentication
API authorization
OLP object proof validity
Marketplace structural/semantic validity
identity/authority evaluation
local receiver policy
trust / truth / legality
```

## 26. Errors and processing states

Transport success and Marketplace federation success are separate.

An HTTP `200`, queue acknowledgement, successful P2P delivery, or file transfer proves only transport-level processing appropriate to that mechanism. Structured Marketplace/OLP processing errors remain necessary where applicable.

Malformed input, unsupported semantics/capabilities, unavailable capabilities, policy rejection, resource exhaustion, and network/service failure SHOULD remain distinguishable rather than collapsing into one generic failure.
## 27. Retry, rate limits, and backpressure

Federation peers SHOULD assume that transport delivery can fail, duplicate, delay, reorder, or time out.

Retry policy is transport/application specific. Retries MUST preserve the original immutable Record identities and, for state-changing submission operations, SHOULD reuse the same valid idempotency binding when the semantic payload is unchanged.

A retry with changed content MUST NOT masquerade as the same idempotent operation.

Servers/peers MAY apply rate limits, admission control, quotas, backpressure, or temporary unavailability. Such service policy does not make the underlying Marketplace evidence invalid.

When a transport supports structured retry hints, an implementation MAY expose them. Retry hints are operational metadata, not protocol chronology or guarantees of future service.

## 28. Resource limits

Federation processes untrusted, potentially attacker-controlled input and MUST apply finite limits before unbounded materialization or recursive work.

At minimum, implementations SHOULD bound:

```text
request/body size
record count per page/submission
cursor and idempotency-key size
capability set cardinality
record/extension nesting and decoding work
resolution/network recursion
timeouts and concurrent requests
queued work and retained replay state
```

The executable profile bounds candidate iterables using look-ahead before full materialization and verifies the merged-set bound after union.
## 29. Network safety and no hidden fallback

A Marketplace federation profile MUST inherit applicable OLP network safety controls, including explicit network enablement, SSRF/private-address protections, redirect policy, credential forwarding restrictions, response-size limits, and timeout bounds.

A request, Record, profile URI, capability URI, Subject URI, source URI, or cursor MUST NOT trigger implicit network dereference merely because it syntactically contains a URI.

Implementations MUST NOT silently fall back from an explicitly selected peer/source to unrelated network sources while presenting the result as though it came from the original source.

## 30. Privacy and data minimization

Federation metadata can reveal commercially sensitive information even when the exchanged Records are public.

Potentially sensitive metadata includes peer/source identifiers, query/scope fingerprints, requested profiles, cursor continuity, synchronization frequency, submission patterns, receiver outcomes, IP/network metadata, and access logs.

Implementations SHOULD minimize retention/disclosure of federation metadata and SHOULD avoid stable cross-context identifiers where not operationally required.

Private, selectively disclosed, encrypted, access-controlled, offline, or direct peer federation remains conforming when it preserves the required semantics.

A source's inability or refusal to disclose a Record MUST NOT be converted into evidence that the Record does not exist.

## 31. Transport neutrality

HTTP is an optional practical profile inherited from OLP 0012, not Marketplace federation identity.

Conforming implementations MAY use message brokers, replicated logs, peer-to-peer protocols, direct agent channels, removable/offline bundles, local IPC, or future transports, provided the same abstract Marketplace/OLP identities and required federation semantics are preserved.
A transport adapter MUST NOT alter Record content merely to satisfy transport-local identifiers, ordering, retry, cursor, or acknowledgement requirements.

## 32. Version and extension handling

M8 v1 version fields require the integer value `1`. Boolean values MUST NOT be accepted as integers.

Unknown future versions MUST NOT be reinterpreted as v1 merely because some fields look familiar.

Marketplace federation capability and message extensions MUST use absolute URI identifiers. Security-relevant or semantics-critical future extensions require explicit profile/version/capability handling; they MUST NOT be silently ignored when doing so would change the meaning of a required operation.

Capability negotiation follows the OLP no-silent-downgrade principle.

## 33. Capability and source claims are evidence, not trust

A capability advertisement is a service assertion about implementation/configuration. It does not establish that the source is honest, currently reachable, globally complete, legally permitted, or safe.

A source URI identifies the declared federation source context. It is not automatically a Principal Identifier, identity proof, authority credential, ownership claim, or trust score.

Applications MAY combine transport authentication and independent OLP evidence to evaluate source identity/authority under local policy.

## 34. Conformance processing profile

The non-normative reference helper implements deterministic processing for:

```text
capability advertisement + negotiation
FederationScopeV1 validation + fingerprinting
snapshot/sync request validation with optional opaque cursor
source-scoped exchange-page validation
exact Record-Identity deduplication
source/operation/scope cursor binding
submission idempotency binding
per-record receiver outcome validation
OLP TransportEnvelopeV1 extension-message handling
```
The helper is not a server, peer-discovery system, message broker, or replication daemon. Independent implementations MAY use different architectures while reproducing the required observable vector semantics.

## 35. Executable vectors

The committed M8 vector file is:

```text
conformance/vectors/federation-transport-v1.json
```

The acceptance set contains **93 vectors**: 28 positive/evaluation cases and 65 negative/adversarial cases.

Coverage includes capability state/negotiation, scope fingerprints, snapshot and sync requests, cursor-carrying sync requests, complete/partial/truncated pages, source-scoped Record validation, replay deduplication, post-union resource bounds, cursor context isolation, idempotency payload binding, receiver outcomes, OLP extension envelopes, exact version-domain typing, and malformed/unsupported/resource-abuse cases.

Vector JSON uses OLP's implementation-neutral projection where abstract OLP values require transport-neutral representation. It is not a mandatory Marketplace wire format.

## 36. Core invariant table

```text
transport serialization       != Record Identity
transport authentication      != OLP proof validity
OLP proof validity             != API authorization
capability implemented        != capability available
capability advertised         != trust or uptime
source completeness           != global completeness
partial/truncated page        != deletion
sync absence                  != retirement/nonexistence
transport order               != chronology
replayed Record               != new evidence
idempotency                   != exactly-once delivery
cursor validity               != authorization/completeness
receiver acceptance           != protocol validity
receiver rejection            != record invalidity
source provenance             != source authority
federation                    != global Marketplace state
```
## 37. Cross-scale examples

A local services marketplace may synchronize public Intents from several independent indexes. Seeing the same Intent at three sources records three source observations around one exact Record Identity; it does not make the Intent three times more true or authoritative.

An enterprise procurement network may exchange private Agreements and Events over mutually authenticated queues. Queue authentication controls transport access; Agreement proofs and authority evidence remain independently evaluated.

An agent-to-agent market may retry an immutable submission after a timeout using the same idempotency binding. The receiver may suppress duplicate side effects without claiming that the underlying transport delivered exactly once.

An offline scientific market may exchange snapshot bundles by removable media. A later partial bundle does not delete evidence present in an earlier bundle, and transport ordering does not define chronology.

## 38. Intentionally deferred

Milestone 8 does not define:

- a universal peer-discovery or routing protocol;
- a global Marketplace domain, registry, index, database, ledger, or event log;
- one mandatory HTTP path layout beyond reusable OLP transport profiles;
- a universal replication/consensus algorithm;
- cross-source deletion/tombstone semantics;
- a universal total-order sequence number or clock;
- mandatory push subscriptions, WebSockets, ActivityPub, pub/sub, or P2P topology;
- universal authentication, authorization, moderation, or reputation policy;
- one globally persistent cursor format;
- universal exactly-once delivery; or
- transport-specific operational deployment requirements.

Future profiles MAY standardize selected transports or peer-discovery mechanisms while preserving the constitutional boundaries above.
## 39. Acceptance boundary

Milestone 8 is satisfied when independent processors can reproduce the committed federation transport outcomes while preserving these properties:

1. no new universal first-class Marketplace record or parallel OLP evidence envelope is introduced;
2. Marketplace extension messages and capabilities use OLP-compatible absolute-URI identifiers;
3. snapshot/sync scopes are explicit, deterministic, and source-scoped;
4. exact OLP Record Identity is recomputed and preserved across exchange;
5. source provenance remains distinct from authenticated Record content and authority;
6. partial/truncated/source-complete results never become global completeness or deletion evidence;
7. cursor reuse is restricted to the exact source + operation + scope context;
8. retries/replays are safe by Record Identity and explicit submission idempotency without claiming exactly-once transport;
9. receiver policy outcomes do not redefine conformance, proof validity, truth, authority, trust, or legality;
10. transport security, API authorization, OLP proof validity, Marketplace validity, and local policy remain independent;
11. capability negotiation cannot silently downgrade a required unavailable/unsupported capability;
12. resource, timeout, backpressure, network-safety, and privacy boundaries are explicit;
13. boolean/inexact version-domain values are not accepted as v1 integers;
14. lifecycle deletion/withdrawal/retirement remains evidence-driven rather than inferred from sync absence; and
15. Milestones 3–7 regression suites remain green.

---

**End of Marketplace Specification 0008 — Federation Transport & Interoperability APIs — Draft v0.1**
