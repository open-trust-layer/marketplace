# Marketplace — Matching & Discovery Semantics

**Status:** Draft v0.1
**Milestone:** 5 — Matching & Discovery Semantics
**Filename:** `specification/0005-market-matching-discovery.md`

---

## 1. Purpose

This specification defines how Marketplace implementations discover immutable market evidence, construct source-scoped market views, evaluate candidate compatibility, combine federated discovery results, and expose ranking without turning any derived result into protocol truth.

It builds on the object-model distinction established in Specification 0002: `Listing`, `Match`, `MarketView`, `Ranking`, `Recommendation`, reputation, risk, and current availability are derived or application-specific concepts by default.

It does **not** create a fourth Marketplace record type, a universal search engine, a universal Match record, a canonical ranking algorithm, a global index, a universal reputation score, or a protocol-wide definition of compatibility.

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are interpreted as described by RFC 2119 and RFC 8174 when written in all capitals.

## 3. Dependency baseline

Marketplace Matching & Discovery v1 depends on Marketplace Specifications 0001–0004 and Open Layer Protocol (OLP) Specifications 0003–0010 where applicable.
OLP remains authoritative for Record Identity, exact evidence references, resolution provenance, discovery hints, lifecycle evidence, proofs, privacy boundaries, and the principle that absence is not negative evidence.

The Milestone 5 executable vectors use the same OLP reference source pin as Milestones 3–4:

```text
41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c
```

This is a draft reproducibility pin, not a fork of OLP.

## 4. Core invariants

1. Discovery is a projection over available evidence; it is not the source of truth of that evidence.
2. Search visibility is not legitimacy, authority, ownership, availability, safety, or endorsement.
3. A Match is an evaluator conclusion under an identified method and input context; it is not protocol truth.
4. Ranking and recommendation are algorithm-dependent views; Marketplace defines no universal ranking.
5. A missing search result is not evidence that the corresponding Intent or Subject does not exist.
6. A source may describe completeness only relative to a declared source or processing scope; Marketplace defines no globally complete index.
7. Search results MUST NOT be treated as uniquely resolved evidence until exact Record Identity is independently checked.
8. Mandatory constraints MUST NOT be silently reinterpreted as preferences.
9. Unknown, unsupported, unresolved, or missing mandatory matching semantics MUST NOT silently produce compatibility.
10. Different conforming matching or ranking methods MAY disagree without creating a protocol conflict.
11. Index metadata is derived and untrusted until checked against the referenced immutable record.
12. Network discovery MUST remain explicit, policy-controlled, bounded, and privacy-aware.

## 5. Marketplace discovery service type

Marketplace v1 defines one service-type URI for advertising a market-discovery endpoint through the existing OLP discovery-hint mechanism:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/service/market-discovery
```

A Marketplace discovery service SHOULD advertise this value as a third-party absolute `serviceType` in OLP `DiscoveryHintStatementV1` when portable endpoint discovery is required.

A valid discovery hint states only that an endpoint may provide the service. It does not establish operator authority, trustworthiness, completeness, availability, safety, or permission to contact the endpoint.

## 6. Processing pipeline

A typical implementation may process discovery as:

```text
immutable Marketplace records
          |
          v
source-local index / cache / supplied set
          |
          v
DiscoveryQueryV1
          |
          v
source-scoped candidate RecordRefs
          |
          v
resolve + recompute Record Identity + validate
          |
          v
method-specific matching evaluation
          |
          v
optional ranking / recommendation / policy view
```
Each stage remains replaceable. An implementation MAY omit an index, matching step, ranking step, or network hop entirely.

## 7. Listing and index projections

A Listing or index entry remains a derived projection. It MAY cache selected authenticated fields from a `MarketIntentV1`, but it MUST preserve the exact RecordRef of the source record when it claims to represent that record.

The Milestone 5 verified-index baseline permits these projected fields:

```text
VerifiedIntentIndexEntryV1 = {
  record_ref: RecordRef,
  issuer?: PrincipalIdentifier,
  action?: AbsoluteURI,
  profiles?: [AbsoluteURI, ...]
}
```

The structure is a processing/cache format, not a Marketplace evidence record.

When the referenced record is available, a consumer MUST recompute its OLP Record Identity before treating cached fields as projections of that record. Any projected `issuer`, `action`, or `profiles` value used for consequential processing MUST agree exactly with authenticated record content.

A mismatching index projection is not repaired by overwriting the immutable record. The projection is stale, corrupt, malicious, or otherwise unsuitable for that use.

Index-only metadata such as popularity counters, ranking scores, moderation state, click counts, or source-local availability MAY exist in applications, but MUST NOT be confused with authenticated `MarketIntentV1` fields.

## 8. `DiscoveryQueryV1`

The core discovery query is a processing input, not an OLP Record and not a Marketplace evidence object.

```text
DiscoveryQueryV1 = {
  version: 1,
  profiles_all?: [AbsoluteURI, ...],
  issuer_principals_any?: [PrincipalIdentifier, ...],
  action_ids_any?: [AbsoluteURI, ...],
  subject_uris_any?: [AbsoluteURI, ...]
}
```

The four optional arrays are non-empty set-like arrays when present. They MUST be duplicate-free and sorted by ascending UTF-8 byte order. Core-v1 limits each array to at most 64 values.

`profiles_all` requires every requested profile to be present on the candidate record. The three `_any` fields match when at least one requested value equals the corresponding authenticated value.

Core-v1 deliberately standardizes only exact filters over authenticated Intent fields. Full-text search, vector similarity, geospatial search, category expansion, ontology inference, price-range interpretation, and domain-specific semantic search remain profile- or implementation-defined.

Unknown core query fields MUST fail rather than be silently ignored.

## 9. Query fingerprints

A processor MAY bind source-local result pages, caches, cursors, or audit records to a normalized query fingerprint.

For the Milestone 5 conformance profile, the fingerprint is:

```text
base64url-no-padding(
  SHA-256(
    OLP-CIE-1(normalized DiscoveryQueryV1)
  )
)
```

This fingerprint identifies the exact normalized processing query used by the conformance profile. It is not an OLP Record Identity, does not create a new Marketplace identity system, and MUST NOT be represented as evidence that the result set is globally complete.

## 10. Source-scoped discovery result

A conforming discovery evaluator SHOULD expose at least the service type, source URI, query fingerprint, exact result Record identities, result count, source-relative completeness, freshness, and whether nonconforming candidates were ignored.

Result records in the executable profile are ordered lexically by canonical OLP `r1_` presentation solely to make serialization and vectors reproducible. That ordering MUST NOT be described as rank, relevance, preference, quality, trust, recency, value, or protocol priority.

## 11. Completeness, freshness, and absence

Core-v1 source-relative completeness values are:

```text
COMPLETE_FOR_DECLARED_SOURCE
PARTIAL_SOURCE
UNKNOWN_SOURCE
```

Core-v1 freshness values are:

```text
FRESH
STALE
HISTORICAL
UNKNOWN
NOT_APPLICABLE
```

These values describe the discovery processor's declared source context. `COMPLETE_FOR_DECLARED_SOURCE` MUST NOT be upgraded to global completeness.

Marketplace v1 defines global completeness as unknown. A discovery source MUST NOT claim that its result set proves the global absence of another Intent, Subject, participant, listing, or opportunity.

Zero results therefore mean only that the evaluated source returned no conforming matches under the declared query and processing context.

## 12. Matching methods

Marketplace v1 does not define one universal compatibility algorithm.

Every portable matching evaluation MUST identify its method using an absolute URI. The method determines how it interprets domain semantics, Subjects, Actions, Terms, evidence requirements, context, and any additional data it is authorized to use.

Two conforming methods MAY evaluate the same pair of Intents differently without either result becoming a protocol conflict.

The Milestone 5 aggregation layer accepts a method-supplied `base_status` from:

```text
SATISFIED
UNSATISFIED
UNKNOWN
UNSUPPORTED
```

`base_status` summarizes method-specific compatibility outside the generic Constraint aggregation defined below. It is an evaluator input, not authenticated Marketplace record state.

A matching implementation MUST retain enough provenance to identify the exact left and right Record identities and the matching method used.

Before returning a positive compatibility conclusion, the processor/method MUST understand every Marketplace content-extension URI marked `critical` on either selected Intent. Unknown critical semantics force `INDETERMINATE`; they MUST NOT be ignored merely because structural validation or other constraints succeed.

## 13. Constraint observations

A matching method MAY produce one observation for an exact `ConstraintV1` embedded in either selected Intent.

Each observation identifies:

```text
side        = left | right
constraint  = exact embedded ConstraintV1 value
status      = SATISFIED | UNSATISFIED | UNKNOWN | UNSUPPORTED | NOT_EVALUATED
```

The observation MUST reference an exact constraint present in the selected Intent. Duplicate observations for the same side and exact constraint are invalid in the core aggregation profile.

An omitted observation is equivalent to `NOT_EVALUATED` for aggregation purposes.

The core does not infer what a domain constraint means merely from its identifier or value. A method that does not understand a required semantic must report that uncertainty instead of manufacturing compatibility.

## 14. Mandatory versus non-mandatory constraints

For `mode = mandatory`, only `SATISFIED` satisfies the constraint for a positive compatibility conclusion.

`UNSATISFIED` is a hard failure under the selected method. `UNKNOWN`, `UNSUPPORTED`, `NOT_EVALUATED`, or a missing observation keep the result indeterminate rather than silently treating the constraint as a preference.
For `preferred`, `negotiable`, and `informational` constraints, an unsatisfied or unknown observation MAY affect a method-specific score, explanation, or recommendation, but MUST NOT be silently promoted into a mandatory core rejection.

The core aggregation profile therefore preserves counts of mandatory failures, mandatory uncertainty, non-mandatory failures, and non-mandatory uncertainty without defining one universal score.

## 15. Match conclusions

The Milestone 5 aggregation profile returns one of:

```text
COMPATIBLE_UNDER_METHOD
INCOMPATIBLE_UNDER_METHOD
INDETERMINATE
```

The conclusion is `INCOMPATIBLE_UNDER_METHOD` when the method's base status is `UNSATISFIED` or any mandatory constraint is observed as `UNSATISFIED`.

The conclusion is `INDETERMINATE` when the base status is `UNKNOWN` or `UNSUPPORTED`, when required method inputs are incomplete/unknown, or when any mandatory constraint lacks a `SATISFIED` observation.

Only when the base status is `SATISFIED`, method inputs are complete for the declared method, and every mandatory constraint is satisfied may the core aggregation return `COMPATIBLE_UNDER_METHOD`.

Even then, the result remains method-relative. It neither creates an Agreement nor proves legal, operational, economic, safety, authority, or fulfillment compatibility.

## 16. Ranking and recommendation

A ranking is an ordered evaluator view over exact RecordRefs under an identified method. The method MUST be an absolute URI.

A core ranked view MUST NOT repeat the same RecordRef. Its ordering is explicitly non-canonical and non-authoritative.

Two ranking methods MAY return opposite orderings over the same records. Marketplace v1 treats that disagreement as algorithm plurality, not as evidence corruption.

A recommendation is likewise an application/evaluator conclusion. It MAY combine match results, preferences, trust models, policy, private context, reputation, prices, risk, or other permitted inputs, but those inputs and methods remain outside universal Marketplace truth.

If a participant or service intentionally publishes a Match, ranking, or recommendation as portable evidence, it MAY use an ordinary OLP Claim, Attestation, Observation, or Event with explicit provenance. Publishing the claim does not convert the conclusion into protocol truth.

## 17. Federation

Marketplace federation combines source-scoped discovery views. It does not create a global index.

A federated merge MUST preserve the query fingerprint and source provenance of returned Record identities. Exact duplicate results are deduplicated only by canonical OLP Record Identity.
All views in one merge MUST represent the same normalized query fingerprint. A source view with inconsistent result counts, duplicate result identities, malformed OLP identity presentation, invalid completeness/freshness metadata, a claim of global completeness, or a rule that treats absence as negative evidence MUST be rejected by the core federation profile.

The merged result MUST retain, for each Record identity, the set of discovery sources that returned it.

The merge MUST NOT infer that a result returned by more sources is more truthful, more relevant, more trustworthy, more legal, or more valuable.

The merge MUST NOT create a canonical ranking. Applications MAY rank the merged set afterward under an explicit method.

## 18. Pagination and cursors

Pagination is source- and method-specific. Marketplace v1 does not define one universal page size, offset model, snapshot protocol, or cursor encoding.

A cursor used by the executable profile is opaque bytes bound to:

```text
source URI
method URI
normalized query fingerprint
```

A cursor MUST NOT be replayed against another source, method, or normalized query. Core-v1 limits the opaque cursor value to 1..4096 bytes.

Cursor validity does not prove that the underlying source is complete, stable, fresh, trustworthy, or unchanged between pages.

## 19. Resolution before consequential use

A search result that names a Record identity is still only a discovery result until the referenced record is obtained and its OLP Record Identity is recomputed.

Implementations MUST keep discovery and resolution separate. Network access MUST NOT occur merely because an untrusted search result contains a URI or endpoint.

When a result is resolved, cryptographic proof validity, lifecycle evidence, identity/authority evidence, current policy, and application authorization remain separate evaluation dimensions.

A record that no longer appears in an index is not thereby withdrawn, expired, superseded, invalid, or unavailable. Those conclusions require their own applicable evidence and evaluation.

## 20. Freshness and market availability

Discovery freshness describes the source view or source material under its declared policy. It does not create a universal `current availability` field.

A `FRESH` discovery result may still refer to an Intent that has relevant withdrawal, expiration, supersession, dispute, or other lifecycle evidence outside the source view.

Conversely, a `STALE` or `UNKNOWN` discovery result is not automatically invalid evidence. Applications decide whether to re-resolve or refresh before consequential action.

## 21. Privacy

Discovery queries can reveal economic interests, subjects, counterparties, locations, actions, profiles, or private negotiation intent.

Implementations SHOULD minimize query disclosure, avoid unnecessary stable correlation identifiers, and prefer local/batched/privacy-preserving evaluation where compatible with the task.

A participant's ability to prove or exchange an Intent does not imply consent to place that Intent in a public or globally enumerable index.

Selective disclosure and private discovery remain valid deployment patterns. A source MUST NOT infer that withheld/private evidence does not exist.

Federation operators SHOULD avoid exposing more source provenance, query history, result metadata, or access logs than required for the declared service and policy.

## 22. Security and resource limits

Discovery and matching operate on untrusted inputs and MUST use finite resource limits.

Implementations MUST bound at least candidate counts, query cardinality, response size, recursion/resolution depth where applicable, network timeouts, and expensive method-specific evaluation work.

Core-v1 query syntax MUST NOT contain executable code, scripts, expressions, callbacks, or implicit network dereferences.
Network discovery MUST inherit the applicable OLP resolver protections: explicit network policy, SSRF defenses, redirect controls, authentication/authorization boundaries, provenance retention, and no hidden network fallback.

A matching or ranking method that performs external calls MUST make that behavior explicit to the caller and remain bounded by application policy.

A discovered endpoint, result count, popularity signal, ranking score, or recommendation MUST NOT be trusted merely because it came from a syntactically conforming service.

## 23. Policy and moderation

Applications MAY filter, hide, quarantine, rank down, block, or refuse to process records under local policy.

Such a decision MUST remain distinguishable from protocol invalidity. A record filtered from one MarketView may remain valid evidence and may remain visible in another conforming MarketView.

Moderation metadata SHOULD retain provenance sufficient to distinguish authenticated Marketplace content from source-local or application-local policy state.

Protocol expressibility does not require a discovery operator to index, display, match, recommend, or execute an action concerning every representable subject.

## 24. Attributable match evidence

When portability is required, an evaluator MAY publish an OLP evidence record asserting that method M evaluated exact Record identities A and B with conclusion C and declared inputs/context.

The published record SHOULD identify enough method and input provenance for another processor to understand what was asserted.
Such evidence remains a claim about an evaluator's result. It does not prove that the parties are objectively compatible, that the method is correct, that all relevant evidence was supplied, that the result remains current, or that an Agreement formed.

The Marketplace core does not require every ephemeral search or match result to become an immutable record.

## 25. Conformance processing profile

The Milestone 5 executable profile standardizes deterministic processing boundaries for:

```text
DiscoveryQueryV1 validation and fingerprinting
source-scoped exact-field discovery
verified index projection checking
method-relative match aggregation
ranked-view validation
federated result deduplication/provenance
source+method+query cursor binding
```

The helper implementation is non-normative. The normative requirements are the observable semantics defined by this specification and the committed conformance vectors.

A conforming independent implementation MAY use another programming language, storage model, search engine, transport, index technology, or matching architecture and still produce the required observable results for the vector profile.

## 26. Executable vectors

The committed vector file is:

```text
conformance/vectors/matching-discovery-v1.json
```
The initial acceptance set contains 31 positive/evaluation and negative cases. It covers exact action/subject/issuer discovery; zero-result non-negativity; federated Record-Identity deduplication; verified index projections; mandatory and preference aggregation; incomplete/unsupported matching; algorithm-plural ranking; cursor binding; and malformed/adversarial inputs.

Vector processing MUST remain deterministic. The vector JSON uses OLP's implementation-neutral projection and is not a mandatory Marketplace wire format.

Positive Marketplace Record identities inside the vectors are derived through the OLP reference implementation pinned by the vector metadata. Matching/discovery does not introduce a second record identity algorithm.

## 27. Core invariant table

```text
search result                  != resolved evidence
listing                        != source-of-truth record
visibility                     != legitimacy
source completeness            != global completeness
zero results                   != non-existence
freshness                      != current availability
match                          != protocol truth
compatibility under method     != agreement
mandatory unknown              != satisfied
preference                     != mandatory constraint
ranking                        != canonical ordering
recommendation                 != endorsement
index projection               != authenticated content
federated frequency            != truth or relevance
cursor validity                != source trustworthiness
policy filtering               != protocol invalidity
```

## 28. Cross-scale examples

A software-bug marketplace may discover Intents by an exact action URI and Subject URI, then use a method that understands repository/test/reward profile semantics. A mandatory licensing constraint that the method cannot evaluate keeps the match indeterminate.

A compute marketplace may discover provider Intents by action/profile, then apply method-specific capacity, location, duration, privacy, and settlement preferences. No core ranking says which provider is universally best.

A physical-goods application may federate multiple source indexes, deduplicate the same Intent by exact Record Identity, and retain that three indexes returned it. Source frequency alone does not establish authenticity, ownership, value, or trust.

A galaxy-observation funding network may discover Intents concerning a galaxy Subject URI while matching telescope access, observation windows, data rights, and funding constraints through domain profiles. The core object model and discovery semantics do not privilege or prohibit the subject because of scale.

## 29. Intentionally deferred

This specification does not freeze:

- a universal HTTP, ActivityPub, message-queue, P2P, or other federation transport;
- one full-text, semantic-vector, ontology, geospatial, or faceted query language;
- a global category/action registry;
- a universal scoring or ranking function;
- reputation, trust, fraud, risk, or fair-value algorithms;
- a universal availability computation;
- a universal recommendation protocol;
- a global crawler or index topology;
- a mandatory privacy-preserving search construction; or
- application-specific moderation and legal-policy rules.
Future profiles MAY standardize any of those capabilities while preserving the constitutional boundaries in Specifications 0001–0005.

## 30. Acceptance boundary

Milestone 5 is satisfied when independent processors can use the committed profile to reproduce the required discovery, verified-index, matching, ranking, federation, and cursor outcomes while preserving these properties:

1. no fourth first-class Marketplace record is introduced;
2. discovery results remain projections with exact Record identity provenance;
3. missing/private/unresolved evidence is not converted into negative evidence;
4. mandatory constraints fail closed for positive compatibility when unsatisfied or not understood;
5. algorithm plurality remains valid for Match, ranking, and recommendation;
6. no universal global index, canonical ranking, or universal market view is created;
7. OLP resolution/discovery/privacy/security primitives are reused rather than weakened or duplicated; and
8. Milestones 3–4 regression suites remain green.

---

**End of Marketplace Specification 0005 — Matching & Discovery Semantics — Draft v0.1**
