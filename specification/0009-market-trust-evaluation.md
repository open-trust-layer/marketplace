# Marketplace — Trust Evaluation & Evidence Query Semantics

**Status:** Draft v0.1  
**Milestone:** 9 — Trust Evaluation & Evidence Query Semantics  
**Filename:** `specification/0009-market-trust-evaluation.md`

---

## 1. Purpose

This specification defines transport-neutral, method-relative semantics for querying Marketplace evidence and producing explainable evaluation results over that evidence.

It exists so independent applications and agents can reproduce what evidence was selected, how each selected item was treated, and why a named evaluator method reached a particular conclusion without turning Marketplace into a universal trust authority.

It does **not** define a universal trust score, universal reputation object, canonical ranking, mandatory risk model, global evaluator, platform truth, or centralized moderation authority.

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are interpreted as described by RFC 2119 and RFC 8174 when written in all capitals.

## 3. Dependency baseline

Marketplace Trust Evaluation v1 depends on Marketplace Specifications 0001–0008 and applicable Open Layer Protocol specifications for immutable records, proof verification, identity/authority evidence, lifecycle evidence, relationships, resolution/discovery, evidence bundles, privacy, transport and conformance.
The executable vectors use the same OLP reproducibility pin as Milestones 3–8:

```text
41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c
```

## 4. Constitutional boundaries

A conforming M9 evaluator MUST preserve these separations:

```text
selected evidence           != supporting evidence
supporting evidence         != objective truth
proof verification          != identity acceptance
identity acceptance         != authority acceptance
authority acceptance        != legal sufficiency
source acceptance           != evidence truth
lifecycle evaluation        != trust
method-relative conclusion  != universal trust score
missing evidence            != negative evidence
receiver policy             != protocol truth
```

Different conforming evaluators MAY legitimately disagree because they may use different methods, purposes, contexts, accepted sources, authority policies, domain observations, or weighting strategies.

## 5. No new universal trust record

Milestone 9 introduces no new universal first-class Marketplace record type and no universal `Trust`, `Reputation`, `Risk`, `Score`, or `Rating` object.

An evaluator MAY publish an attributable OLP record containing its own evaluation result. Such a publication remains evidence from that evaluator; it does not become protocol truth or a canonical score.
## 6. Core evaluator method

The reference conformance method is identified by:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/trust-evaluation/method/core-evidence-v1
```

The URI identifies one reproducible reference method only. It does not reserve the field of trust evaluation, and implementations MUST NOT imply that this method is globally preferred or authoritative.

Other methods MUST use distinct absolute URIs and MAY define different weighting, thresholds, evidence classes, or domain policies while preserving the constitutional boundaries in this specification.

## 7. Evidence query

The executable core query is:

```text
EvidenceQueryV1 = {
  version: 1,
  method: AbsoluteURI,
  purpose: AbsoluteURI,
  target: EvaluationTargetV1,
  context?: SemanticMap,
  record_types?: SortedUniqueCoreMarketplaceRecordTypes,
  profiles_all?: SortedUniqueAbsoluteURIs,
  sources_any?: SortedUniqueAbsoluteURIs,
  max_records: 1..4096
}
```

The exact integer value `1` is required for `version`; boolean `true` MUST NOT be accepted as integer version 1.

A query is a processing request. It is not an identity-bearing Marketplace record, authorization credential, proof, trust decision, or claim that all selected evidence is relevant or supportive.
## 8. Evaluation targets

The core target is exactly one of:

```text
{ kind: "principal",   value: AbsoluteURI }
{ kind: "subject-uri", value: AbsoluteURI }
{ kind: "record",      value: CanonicalOLPRecordIdentity }
```

A target identifies what the relying application is evaluating. It does not by itself establish identity, ownership, authority, legal status, existence, relevance, or trustworthiness.

## 9. Purpose and context

`purpose` is REQUIRED and uses an absolute URI so the same evidence may be evaluated differently for different decisions such as provider selection, fraud review, fulfillment risk, credit assessment, safety screening, or another application-defined purpose.

`context`, when present, is a bounded semantic map whose keys are absolute URIs and whose values are valid OLP record values. Context may carry method-specific parameters, policy inputs, jurisdictional context, risk classes, weighting inputs, or other evaluator configuration.

M9 core does not assign universal meaning to application context keys. A changed purpose or context changes the normalized query and therefore its deterministic query fingerprint.

## 10. Evidence scope

`record_types`, `profiles_all`, and `sources_any` constrain candidate selection.

Core `record_types`, when present, may contain only the three first-class Marketplace record types. `profiles_all` requires every listed profile URI to be present on a selected record. `sources_any` limits which declared federation/source provenances may contribute candidates.

Selection by these fields is **not** a conclusion that the selected record supports the target. It means only that the record passed the declared candidate scope.
## 11. Candidate evidence and Record Identity

Each candidate supplied to the reference processor consists of a conforming Marketplace `RecordV1` plus an explicit source URI describing where that record was obtained.

The receiver MUST validate the Marketplace record and recompute its exact OLP Record Identity before consequential evaluation.

Exact duplicate delivery from the same source MAY be deduplicated by Record Identity. The same exact record supplied by multiple sources remains one immutable record with multiple source-provenance associations.

If the same computed Record Identity is associated with unequal records, the processor MUST fail rather than select a winner by delivery order.

## 12. Open-world selection

Evidence selection is open-world.

A query result MUST report global completeness as unknown. Evidence omitted because of source scope, profile scope, record-type scope, privacy, authorization, unavailability, pagination, network policy, or any other reason MUST NOT automatically become negative evidence.

The executable profile records deterministic exclusion reasons for query-scoped exclusions:

```text
SOURCE_SCOPE_MISMATCH
RECORD_SCOPE_MISMATCH
```

Those reasons describe query processing only. They MUST NOT be interpreted as invalidity, falsity, untrustworthiness, or adverse evidence.

## 13. Query fingerprint

The executable profile computes a deterministic query fingerprint as base64url-no-padding SHA-256 over the OLP deterministic encoding of the normalized `EvidenceQueryV1`.

The fingerprint binds method, purpose, target, context, scope and resource limit. It is processing metadata, not Marketplace Record Identity, a proof, authorization token, globally meaningful query identity, or privacy-safe public identifier.
## 14. Evidence observations

Every selected Record Identity requires exactly one evaluator observation in the core reference method.

```text
EvidenceObservationV1 = {
  record_id: CanonicalOLPRecordIdentity,
  proof_status: VERIFIED | FAILED | UNKNOWN | UNSUPPORTED | NOT_APPLICABLE,
  identity_status: ACCEPTED | REJECTED | UNKNOWN | UNSUPPORTED | NOT_APPLICABLE,
  authority_status: ACCEPTED | REJECTED | UNKNOWN | UNSUPPORTED | NOT_APPLICABLE,
  lifecycle_status: ACCEPTABLE | ADVERSE | UNKNOWN | UNSUPPORTED | NOT_APPLICABLE,
  domain_status: SUPPORTS | OPPOSES | NEUTRAL | UNKNOWN | UNSUPPORTED,
  source_accepted: Boolean,
  critical_understood: Boolean,
  disputed: Boolean
}
```

These dimensions MUST remain separate. A cryptographically verified record may still have rejected or unknown authority, and an authoritative record may still be adverse, neutral, disputed, or irrelevant under the selected purpose.

The observation is an evaluator input. M9 does not claim that every relying party must accept the same identity, authority, source, lifecycle, or domain assessment.
## 15. Structural validity boundary

Structural Marketplace validity is checked before a candidate becomes selected evidence in the reference method. A structurally invalid candidate is rejected as an invalid Marketplace record rather than being converted into negative trust evidence.

Proof failure, identity rejection, authority rejection, source rejection, lifecycle adversity, unsupported semantics, and domain opposition are not interchangeable with structural invalidity.

## 16. Countable evidence under the core method

A selected observation is countable only when all of these method-specific conditions hold:

```text
source_accepted == true
critical_understood == true
proof_status in { VERIFIED, NOT_APPLICABLE }
identity_status in { ACCEPTED, NOT_APPLICABLE }
authority_status in { ACCEPTED, NOT_APPLICABLE }
lifecycle_status in { ACCEPTABLE, NOT_APPLICABLE }
domain_status in { SUPPORTS, OPPOSES, NEUTRAL }
```

This countability rule belongs only to `core-evidence-v1`. It is not a universal definition of trustworthy evidence.

A different evaluator method MAY require stronger proof, different authority policy, domain-specific weighting, temporal decay, threshold rules, source diversity, or another explicit method.
## 17. Unresolved and unusable evidence

The core method distinguishes unresolved evidence from evidence that is unusable under the selected method.

An observation is unresolved when unknown or unsupported semantics prevent a consequential directional conclusion. Examples include unknown proof, identity, authority, lifecycle, domain, or critical semantics.

An observation may instead be excluded as unusable when the method has a definite reason not to count it, such as failed proof verification, rejected identity/authority, rejected source policy, or adverse lifecycle evaluation without a countable domain direction.

Neither category is automatically negative evidence.

Unknown or unsupported critical semantics MUST block a positive conclusion under the core method.

## 18. Directional evidence

Countable evidence is classified only as:

```text
SUPPORTS
OPPOSES
NEUTRAL
```

These labels describe how the selected evaluator method treats a specific Record for the specific purpose/target/context. They are not properties permanently attached to the Record itself.

A Record supporting one purpose MAY be neutral or opposing under another purpose or method.
## 19. Result lattice

The core method returns exactly one of:

```text
EVIDENCE_SUFFICIENT_UNDER_METHOD
EVIDENCE_INSUFFICIENT_UNDER_METHOD
CONFLICTING_EVIDENCE
DISPUTED_EVIDENCE
INDETERMINATE
```

The names are intentionally method-relative. `EVIDENCE_SUFFICIENT_UNDER_METHOD` does not mean universally trustworthy, safe, legal, solvent, honest, or recommended. `EVIDENCE_INSUFFICIENT_UNDER_METHOD` does not mean universally untrustworthy or false.

## 20. Result precedence

The reference method applies this deterministic precedence:

1. countable disputed evidence present → `DISPUTED_EVIDENCE`;
2. countable support and opposition both present → `CONFLICTING_EVIDENCE`;
3. unresolved selected evidence present → `INDETERMINATE`;
4. countable support without opposition/unresolved evidence → `EVIDENCE_SUFFICIENT_UNDER_METHOD`;
5. countable opposition without support/unresolved evidence → `EVIDENCE_INSUFFICIENT_UNDER_METHOD`;
6. otherwise → `INDETERMINATE`.

The underlying supporting, opposing, neutral, disputed, unresolved, and excluded sets remain visible even when one result status has precedence.
## 21. Explainable trace

The reference result includes a deterministic trace entry for every selected Record Identity. Each entry identifies:

```text
record_id
decision
domain_status
disputed
reasons
```

`decision` is one of `COUNT_SUPPORTS`, `COUNT_OPPOSES`, `COUNT_NEUTRAL`, `UNRESOLVED`, or `EXCLUDED_UNUSABLE`.

`reasons` exposes the observation dimensions that prevented countability, including source rejection, unknown critical semantics, failed/unknown/unsupported proof, identity, authority, lifecycle, or domain evaluation.

Trace order is canonical Record Identity order for reproducibility only. It MUST NOT be interpreted as chronology, priority, trust, rank, weight, or causal order.

## 22. Evaluation input fingerprint

The executable profile computes a deterministic evaluation-input fingerprint over:

```text
normalized query
one observation per selected Record Identity
accepted source-provenance set per selected Record Identity
```

Observation and provenance ordering is normalized before hashing. Exact transport replay from the same source therefore does not create a different semantic evaluation input, while a genuinely different provenance set does.
## 23. Result fingerprint

The reference result fingerprint is deterministic processing metadata derived from the normalized method-relative result core, including the evaluation-input fingerprint and exact evidence partitions.

It is not Marketplace Record Identity, a universal trust identifier, an authorization token, a consensus hash, or proof that another evaluator must agree.

Two evaluators using different methods, purposes, contexts, accepted sources, or observations MAY produce different fingerprints over the same underlying evidence graph.

## 24. Disputes and conflicts

Disputed evidence and conflicting evidence MUST be preserved rather than resolved by arrival order, source popularity, latest timestamp, or hidden platform policy.

A dispute is evidence of challenge, not proof that the challenged evidence is false and not proof that the challenger is correct.

Conflicting countable evidence remains `CONFLICTING_EVIDENCE` unless another explicitly named method defines and explains a different treatment. M9 core defines no universal conflict winner.

## 25. No latest-wins semantics

Transport order, discovery order, page order, Record creation order, and observed timestamps MUST NOT silently select a canonical trust state.

OLP relationships such as correction, supersession, dispute, derivation, and lifecycle evidence retain their own semantics and MAY be evaluated under the selected method. They do not create a generic latest-record-wins rule.
## 26. Source and authority weighting

M9 core standardizes no universal source weight, authority weight, reputation coefficient, confidence percentage, or trust probability.

A method MAY use source diversity, source policy, authority class, temporal relevance, domain-specific evidence quality, or another weighting scheme. Such behavior MUST be attributable to the named method and SHOULD be representable through explicit method/context inputs rather than hidden platform state.

A weighting scheme MUST NOT be presented as protocol truth merely because it is deterministic.

## 27. Numeric confidence

Numeric confidence is deliberately not standardized by the core profile.

An extension MAY publish method-specific probabilities, scores, intervals, grades, or confidence measures, but it MUST identify their method and semantics explicitly. Implementations MUST NOT imply comparability between unrelated scoring methods without a separate profile establishing such comparability.

The core reference result therefore reports `numeric_confidence_standardized = false` and `universal_trust_score = false`.

## 28. Privacy and selective disclosure

Queries and traces may reveal sensitive information about targets, evaluator purpose, risk policy, accepted sources, authority assumptions, investigated evidence, business relationships, or screening criteria.

Implementations SHOULD minimize stored or transmitted query/trace metadata and SHOULD disclose only what is necessary for the relying use.

A private or selectively disclosed evaluation remains conforming. Failure to disclose evidence MUST NOT be converted into evidence that the omitted evidence does not exist or is adverse.
## 29. Resource and recursion bounds

Trust evaluation processes untrusted evidence and MUST use finite resource bounds.

The executable profile limits candidate evidence to at most 4096 delivered records per query, query URI sets to 128 entries, semantic-context entries to 128, and trace observations to 4096.

Implementations SHOULD additionally bound recursive relationship traversal, resolution depth, network fetches, evidence-bundle expansion, proof verification work, wall-clock time, memory, concurrency, and retained trace size.

No URI in a query, target, context, source, profile, Record, or trace implies permission for implicit network dereference.

## 30. Network and federation boundary

M9 may consume evidence obtained through M5 discovery, M8 federation, local stores, bundles, direct peers, or other sources. The evaluation layer MUST preserve source provenance and MUST NOT silently broaden an explicitly scoped source set through hidden fallback.

Transport authentication and successful federation delivery remain separate from proof, identity, authority, domain relevance, trust, and policy acceptance.

## 31. Method plurality and interoperability

Interoperability means independent processors can reproduce the observable semantics of a named method from the same normalized inputs. It does not mean all methods must agree.

A Marketplace implementation SHOULD permit multiple evaluator methods to coexist. Applications MAY compare their outputs, but MUST preserve method identifiers, query purpose/context, evidence scope, and trace basis so disagreement remains inspectable.
## 32. Conformance processing profile

The non-normative reference helper implements deterministic processing for:

```text
EvidenceQueryV1 validation and normalization
query fingerprints
source/profile/type-scoped evidence selection
exact Record-Identity deduplication and provenance preservation
query-exclusion reasons
EvidenceObservationV1 validation
core-evidence-v1 countability and result lattice
explainable per-record traces
evaluation-input fingerprints
result fingerprints
```

The helper is not a reputation service, ranking engine, policy authority, identity provider, legal decision maker, fraud oracle, or universal recommender.

## 33. Executable vectors

The committed M9 vector file is:

```text
conformance/vectors/trust-evaluation-v1.json
```

The acceptance set contains **56 vectors**: 27 positive/evaluation cases and 29 negative/adversarial cases.

Coverage includes principal/record/subject targets, purpose/context/source/profile scope, exact replay deduplication, multi-source provenance, support/opposition/conflict/dispute/indeterminate results, unknown critical semantics, proof/authority/lifecycle/source treatment, ordering stability, resource ceilings, malformed queries, incomplete/duplicate observations, and invalid observation domains.
## 34. Core invariant table

```text
query scope                   != trust conclusion
selected evidence             != supporting evidence
supporting evidence           != truth
source provenance             != source authority
proof verification            != identity acceptance
identity acceptance           != authority acceptance
authority acceptance          != legal sufficiency
method-relative sufficiency   != universal trust
missing evidence              != negative evidence
dispute                       != falsity
conflict                      != latest-wins resolution
result fingerprint            != Record Identity
numeric confidence            != core requirement
```

## 35. Cross-scale examples

A local-services agent may evaluate a provider for one task using fulfillment evidence, accepted authority and a particular dispute policy. Another application may use the same records for a different purpose and reach a different method-relative conclusion.

An enterprise procurement system may require stronger authority evidence and source policy than a consumer marketplace. Both remain conforming when their methods and evidence treatment are explicit.
A scientific marketplace may treat a disputed provenance record as requiring investigation rather than as automatically false. The exact dispute and supporting evidence remain visible in the trace.

An offline agent may evaluate only a disclosed evidence bundle. Its result remains explicitly incomplete with global completeness unknown rather than assuming absent online evidence is negative.

## 36. Intentionally deferred

Milestone 9 does not define:

- a universal trust, reputation, safety, credit, fraud, quality, or risk score;
- one canonical weighting or confidence formula;
- one global trust graph or reputation database;
- mandatory transitive trust propagation;
- universal source reputation;
- mandatory temporal decay or recency weighting;
- one canonical dispute resolver;
- universal legal/compliance/admission policy;
- mandatory recommendation or ranking behavior;
- a universal model for cross-method score conversion; or
- a requirement to publish private evaluation traces.

Future profiles MAY define narrower domain methods while preserving method identity, evidence transparency, open-world semantics, conflict preservation, and evaluator plurality.

## 37. Acceptance boundary
Milestone 9 is satisfied when independent processors can reproduce the committed M9 query/evaluation outcomes while preserving these properties:

1. no universal trust/reputation/risk score or new universal first-class Marketplace record is introduced;
2. every portable conclusion is bound to an absolute evaluator method URI, purpose, target, context and exact evidence scope;
3. exact OLP Record Identity and source provenance are preserved for selected evidence;
4. query selection remains open-world and exclusion is not converted into adverse evidence;
5. structural validity, proof, identity, authority, lifecycle, source policy, critical semantics and domain direction remain separate dimensions;
6. unknown/unsupported critical semantics fail closed for consequential positive conclusions;
7. conflicting and disputed evidence remain visible and are not silently resolved by latest-wins logic;
8. explainable traces identify every selected Record and the method-specific treatment that contributed to the result;
9. deterministic query, evaluation-input and result fingerprints remain processing metadata rather than evidence identity;
10. transport replay does not create new semantic evidence or change an equivalent semantic input;
11. numeric confidence and weighting remain method-specific rather than universal core truth;
12. privacy, resource, recursion, network and source-scope boundaries are explicit;
13. Milestones 3–8 regression suites remain green; and
14. README/specification/conformance indexes and executable vectors are synchronized.

---

**End of Marketplace Specification 0009 — Trust Evaluation & Evidence Query Semantics — Draft v0.1**
