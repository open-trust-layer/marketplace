# Specification 0014 — Domain Evaluator Method Profiles & Criterion Aggregation

**Status:** Draft v0.1
**Milestone:** 15 — Domain Evaluator Method Profiles & Criterion Aggregation
**Filename:** `specification/0014-market-domain-evaluator-methods.md`

---

## 1. Purpose

This specification defines a portable profile for domain-specific evaluator methods that derive one method-relative `domain_status` for an exact Marketplace/OLP Record Identity.

It extends the method-plurality point already defined by Specification 0009. It does not create another trust engine, evidence selector, reputation system, ranking system, universal score, truth oracle, or policy authority.

Independent implementations can therefore reproduce how one named domain method maps explicit criterion observations into a domain direction while preserving the wider M9 trust-evaluation boundaries.
## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are interpreted as described by RFC 2119 and RFC 8174 when written in all capitals.

## 3. Dependency baseline

M15 depends on Marketplace Specifications 0001–0013 and applicable Open Layer Protocol specifications for immutable records, deterministic encoding, Record Identity, evidence relationships, proof/identity/authority/lifecycle evidence, privacy, federation, dispute resolution, policy/authorization, and deployment boundaries.

The executable vectors use the repository OLP source pin:

```text
41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c
```

A released Marketplace version MUST bind to an explicit released OLP compatibility target rather than this draft source pin.
## 4. Constitutional boundaries

A conforming M15 implementation MUST preserve these separations:

```text
domain criterion result       != objective truth
method-local weight           != confidence probability
method-local threshold        != universal quality bar
domain status                 != overall M9 trust result
SUPPORTS                       != trusted
OPPOSES                        != universally adverse
UNKNOWN                        != negative evidence
method fingerprint             != method authority
result fingerprint             != result authentication
method agreement               != cross-method comparability
positive domain status         != authorization
```

Different conforming methods MAY legitimately disagree because they may define different domains, purposes, criteria, thresholds, weights, observation processes, and critical semantics.
## 5. Relationship to M9

Specification 0009 remains authoritative for candidate evidence selection, exact OLP Record Identity, source provenance, proof status, identity status, authority status, lifecycle status, source acceptance, dispute state, critical-semantics handling at the trust layer, and the overall trust result lattice.

M15 standardizes only one extension point: deriving the M9-compatible `domain_status` for one exact Record Identity under one named domain method.

An M15 result MAY be supplied as the domain observation input to an M9 evaluator. M15 MUST NOT silently infer, overwrite, or collapse the other M9 dimensions.

## 6. No universal evaluator record

M15 introduces no universal `Score`, `Quality`, `Risk`, `Rating`, `Reputation`, `Trust`, or `DomainVerdict` Marketplace record type.

A participant MAY publish an attributable OLP record describing its own method profile or evaluation result. Such publication is evidence from that participant, not protocol truth or a canonical evaluator state.
## 7. Reference processing profile

The non-normative reference profile is identified by:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/domain-evaluator/profile/criterion-threshold-v1
```

This URI identifies one reproducible processing profile only. It does not make the profile globally preferred, authoritative, safe for every domain, or sufficient for every purpose.

Concrete evaluator methods MUST use their own distinct absolute method URIs.

## 8. Domain evaluator method profile

The reference method descriptor is:

```text
DomainEvaluatorMethodV1 = {
  version: 1,
  profile: AbsoluteURI,
  method: AbsoluteURI,
  domain: AbsoluteURI,
  purposes: SortedUniqueAbsoluteURIs,
  criteria: SortedUniqueCriterionProfiles,
  support_threshold: PositiveInteger,
  oppose_threshold: PositiveInteger,
  critical: SortedUniqueAbsoluteURIs
}
```
The exact integer `1` is required for `version`; boolean `true` MUST NOT be accepted as integer version 1.

The reference profile MUST be exactly the criterion-threshold profile URI above. Other processing profiles require distinct profile URIs.

`method` identifies the concrete evaluator semantics. Reusing one method URI for materially different normalized method profiles is non-conforming unless the change is explicitly versioned by a distinct method identity.

`domain` identifies the semantic domain in which the criteria are interpreted. `purposes` bounds the relying uses for which the method declares itself applicable.

## 9. Criterion profile

Each criterion is:

```text
CriterionProfileV1 = {
  id: AbsoluteURI,
  required: Boolean,
  weight: Integer 1..1000,
  critical: SortedUniqueAbsoluteURIs
}
```

Criterion identifiers MUST be unique within a method profile and sorted by UTF-8 bytes for deterministic processing.

A criterion `weight` is a method-local aggregation parameter only. It MUST NOT be presented as standardized confidence, probability, monetary value, reputation, global importance, or a cross-method comparable score.
## 10. Threshold semantics

`support_threshold` and `oppose_threshold` are positive integers bounded by the total declared criterion weight.

The thresholds belong only to the named method profile. They are not universal acceptance/rejection thresholds and MUST NOT be inferred across unrelated methods.

The same criterion observation set MAY therefore produce different domain statuses under different method profiles without either processor being non-conforming.

## 11. Evaluation request

The reference evaluation request is processing metadata:

```text
DomainEvaluationRequestV1 = {
  version: 1,
  method: AbsoluteURI,
  domain: AbsoluteURI,
  purpose: AbsoluteURI,
  target_record_id: CanonicalOLPRecordIdentity,
  context: SemanticMap,
  understood_critical: SortedUniqueAbsoluteURIs
}
```

The request method/domain MUST exactly match the method profile, and the purpose MUST be one of the profile's declared purposes.
`target_record_id` binds the evaluation to one exact immutable OLP Record Identity. The request does not assert that the record is true, authoritative, safe, current, legal, or trustworthy.

`context` is a bounded semantic map whose keys are absolute URIs and whose values are valid OLP record values. A context change changes the normalized request and exact reuse binding.

## 12. Criterion observations

Each supplied observation is:

```text
CriterionObservationV1 = {
  criterion: AbsoluteURI,
  state: SUPPORTS | OPPOSES | NEUTRAL | UNKNOWN | UNSUPPORTED | NOT_APPLICABLE,
  critical: SortedUniqueAbsoluteURIs,
  reason_uris: SortedUniqueAbsoluteURIs
}
```

An observation MUST reference a criterion declared by the method profile.

Exact duplicate observations MAY be deduplicated. Conflicting observations for the same criterion MUST fail explicitly; arrival order MUST NOT choose a winner.
## 13. Open-world and missing criteria

Missing information is not automatically adverse evidence.

A missing required criterion is unresolved and causes the reference profile to fail closed to `UNKNOWN`.

A missing optional criterion is ignored for directional aggregation and does not create opposition points.

Likewise, an optional criterion observed as `UNKNOWN`, `UNSUPPORTED`, or `NOT_APPLICABLE` is not automatically negative evidence under the reference profile.

## 14. Critical semantics

Unknown critical semantics at the method, criterion, or observation layer MUST block a consequential directional result.

The reference profile returns `UNKNOWN` with an explicit `UNKNOWN_CRITICAL_SEMANTICS` final rule whenever any applicable critical URI is not present in `understood_critical`.

Declaring a URI understood means only that the processor claims to implement the named semantics. It does not prove that the implementation is correct or authoritative.
## 15. Explainable criterion trace

The reference processor emits one deterministic trace entry per declared criterion containing:

```text
criterion
required
weight
state
decision
critical
observation_critical
unknown_critical
reason_uris
```

`decision` is one of `COUNT_SUPPORTS`, `COUNT_OPPOSES`, `COUNT_NEUTRAL`, `UNRESOLVED_REQUIRED`, `UNRESOLVED_CRITICAL`, `IGNORED_OPTIONAL_MISSING`, or `IGNORED_OPTIONAL_UNRESOLVED`.

Trace order follows canonical criterion-id order for reproducibility only. It is not chronology, importance, trust rank, or causal order.
## 16. Reference aggregation

The criterion-threshold profile sums weights independently for `COUNT_SUPPORTS` and `COUNT_OPPOSES` trace entries.

The method then applies this deterministic precedence:

1. unknown critical semantics present → `UNKNOWN`;
2. unresolved required criteria present → `UNKNOWN`;
3. support and oppose thresholds both met → `UNKNOWN` with explicit conflict;
4. support threshold met → `SUPPORTS`;
5. oppose threshold met → `OPPOSES`;
6. otherwise → `NEUTRAL`.

The reference final rules are `UNKNOWN_CRITICAL_SEMANTICS`, `REQUIRED_CRITERIA_UNRESOLVED`, `CONFLICTING_CRITERIA`, `SUPPORT_THRESHOLD_MET`, `OPPOSE_THRESHOLD_MET`, and `NO_DIRECTIONAL_THRESHOLD_MET`.

Conflict is preserved rather than silently resolved by majority, latest observation, largest individual criterion, or hidden policy.
## 17. M9-compatible domain status

The reference output domain status is exactly one of:

```text
SUPPORTS
OPPOSES
NEUTRAL
UNKNOWN
```

These values are intentionally compatible with the directional domain input used by M9. M15 does not emit `UNSUPPORTED` as an aggregate result; unsupported required criteria become unresolved and optional unsupported criteria are ignored by the reference aggregation.

A relying M9 evaluator still decides whether the resulting domain observation is countable together with proof, identity, authority, lifecycle, source, critical, and dispute dimensions.

## 18. Fingerprints

M15 defines deterministic SHA-256 base64url fingerprints over OLP deterministic encoding for the normalized method profile, evaluation request, complete normalized input, and result core.

These fingerprints are processing/integrity metadata. They are not Record Identity, signatures, authenticated timestamps, authorization tokens, consensus hashes, or evidence that another evaluator must agree.
## 19. Exact reuse

A prior result is exactly reusable only when the normalized method-profile fingerprint, request fingerprint, complete input fingerprint, and result fingerprint are unchanged.

A method profile changed under the same method URI therefore produces `NOT_REUSABLE` with `DOMAIN_METHOD_PROFILE_CHANGED`; implementations MUST NOT silently treat that as identical method semantics.

Changes to purpose, target Record Identity, context, understood-critical set, or normalized criterion observations likewise invalidate exact reuse.

Reuse does not establish that the method is authoritative, that the result is true, or that current external conditions are unchanged.

## 20. Result boundary flags

Every reference result explicitly reports `false` for proof, identity, authority, lifecycle, source-policy, dispute, authorization, protected-side-effect authorization, truth establishment, universal trust-score establishment, standardized numeric confidence, cross-method comparability, Record-Identity mutation, method authority, and result authentication.

These explicit negatives prevent a domain result from being accidentally promoted into a stronger claim than the evaluator actually performed.
## 21. Resource and processing bounds

Domain methods process untrusted method profiles, context, and observations and MUST use finite resource bounds.

The executable reference profile limits criteria to 256, supplied observations to 512, URI set fields to 256 entries, semantic context to 128 entries, URI values to 2048 UTF-8 bytes, and each criterion weight to 1..1000.

Implementations SHOULD additionally bound parser work, recursive extraction logic, external evidence lookups, model execution, memory, wall-clock time, concurrency, and retained trace size.

No domain, purpose, criterion, critical, reason, or context URI implies permission for network dereference.

## 22. Purity and side-effect boundary

The reference evaluator is pure processing over supplied method metadata and criterion observations.

Untrusted M15 input MUST NOT itself trigger network calls, filesystem mutation, subprocess execution, credential access, payment, moderation, settlement, publication, or another protected side effect.

Applications MAY perform separate evidence collection or domain-specific extraction before invoking the evaluator, but those activities remain outside this reference profile and require their own authorization and resource controls.

## 23. Privacy and selective disclosure

Domain-method profiles, purposes, criteria, context, observations, reason URIs, and traces may reveal sensitive policy, screening, risk, quality, operational, or commercial information.

Implementations SHOULD minimize retained and disclosed method inputs and traces and SHOULD preserve M10 selective-disclosure boundaries.

Omitted private observations MUST NOT automatically become opposition or evidence that no favorable evidence exists.

## 24. Cross-method comparison

Two methods that evaluate the same Record for the same purpose MAY legitimately disagree.

M15 standardizes no conversion between unrelated method-local weights, thresholds, grades, probabilities, or outputs. Numeric values from different methods MUST NOT be treated as comparable merely because they use the same integer range.

A future comparison profile MAY define an explicit mapping between named methods, but such a mapping would itself be attributable method semantics rather than Marketplace truth.

## 25. Relationship to policy and authorization

M15 domain evaluation is not a policy or authorization engine.

An application MAY feed a domain result into an M11 policy decision as one explicit input. The M11 authorization boundary still decides whether a protected operation may proceed.

`SUPPORTS` therefore MUST NOT be interpreted as permission, approval, legal compliance, safety clearance, payment authority, moderation authority, or side-effect authorization.

## 26. Reference conformance profile

The non-normative reference helper implements deterministic processing for method-profile normalization, request binding, criterion-observation normalization, required/optional handling, critical-semantics gating, weighted threshold aggregation, explainable traces, fingerprints, integrity checking, and exact reuse.

It does not fetch evidence, verify proofs, authenticate identities, evaluate authority, determine lifecycle, resolve disputes, select accepted sources, authorize actions, or establish universal trust.

## 27. Executable vectors

The committed M15 vector file is:

```text
conformance/vectors/domain-evaluator-methods-v1.json
```

The acceptance set contains **104 vectors**: 28 positive/evaluation cases and 76 negative/adversarial cases.

## 28. Core invariant table

```text
domain criterion observation != proof
criterion SUPPORTS            != objective truth
method-local weight           != confidence
method threshold              != universal quality bar
aggregate SUPPORTS            != universal trust
aggregate UNKNOWN             != adverse evidence
method URI                    != method authority
same integer score range      != cross-method comparability
result fingerprint            != result authentication
exact reuse                   != current-world freshness
positive domain result        != authorization
```

## 29. Cross-scale examples

A software marketplace may define a release-readiness method using reproducible-build, test, static-analysis, and provenance criteria. Another application may use different criteria or thresholds over the same release Record and legitimately derive another domain status.

A physical-goods application may use inspection, provenance, condition, and custody criteria. Its weights are meaningful only under that named method and MUST NOT be compared numerically with software-release weights.A scientific marketplace may use data-quality and reproducibility criteria while keeping disputed provenance visible to M9 and M13 rather than encoding a hidden dispute winner into the domain method.

A large infrastructure procurement system may require all safety-critical criteria to be understood before a directional result, while a low-risk application may use a different named method with different required criteria.

## 30. Intentionally deferred

Milestone 15 does not define:

- a universal trust, reputation, quality, risk, safety, fraud, or credit score;
- one canonical domain taxonomy or evaluator method;
- universal criterion identifiers for every domain;
- mandatory machine-learning, statistical, or rules-engine execution;
- standardized cross-method confidence or score conversion;
- universal temporal decay or recency weighting;
- proof, identity, authority, lifecycle, source-policy, or dispute evaluation;
- universal recommendation or ranking behavior;
- legal, compliance, moderation, settlement, remedy, or enforcement policy; or
- protected-side-effect authorization.

Future profiles MAY define narrower evaluator methods or explicit comparison profiles while preserving method identity, explainability, open-world semantics, critical-semantics handling, and algorithm plurality.## 31. Acceptance boundary

Milestone 15 is satisfied when independent processors reproduce the committed M15 method-profile outcomes while preserving these properties:

1. M15 plugs into M9 as a domain-status derivation layer rather than duplicating the M9 trust lattice;
2. every portable result is bound to an exact method profile, method URI, domain, purpose, Record Identity, context, understood-critical set, and normalized criterion observations;
3. method-local weights and thresholds remain algorithm parameters rather than universal confidence, truth, reputation, quality, or risk scores;
4. required unresolved criteria and unknown critical semantics fail closed to `UNKNOWN`;
5. missing optional criteria are not converted into opposition;
6. support/opposition conflict remains explicit and is not silently resolved by arrival order, majority, or hidden policy;
7. method/profile changes under the same method URI invalidate exact reuse;
8. result fingerprints detect tampering without becoming signatures or Record Identity;
9. the evaluator performs no hidden network, filesystem, process, credential, or protected-side-effect activity;
10. a positive domain result never establishes proof, identity, authority, lifecycle, source acceptance, dispute resolution, universal trust, or authorization;
11. the 103 committed M15 vectors regenerate byte-for-byte and independently validate;
12. the unified acceptance gate includes M15 and all earlier registered suites remain green; and
13. README, specification, conformance documentation, and executable manifests remain synchronized.

---

**End of Marketplace Specification 0014 — Domain Evaluator Method Profiles & Criterion Aggregation — Draft v0.1**
