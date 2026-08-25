# Specification 0012 — Marketplace Dispute Resolution Profiles & Resolution Evidence

**Status:** Draft v0.1
**Milestone:** 13 — Dispute Resolution Profiles & Resolution Evidence
**Depends on:** Marketplace Specifications 0001–0011 and Open Layer Protocol (OLP) evidence relationships, Record Identity, proof, lifecycle, privacy, and conformance semantics.

## 1. Purpose and scope

This specification defines a transport-neutral, method-relative processing profile for evaluating disputes and attributable resolution evidence over immutable OLP records.

Marketplace already preserves disputes as evidence. Milestone 13 adds a reproducible way to answer a narrower question:

> Given an explicit resolution method, exact challenged records, exact dispute evidence, explicit authority/source assumptions, and exact resolution observations, what conclusion does that method reach?

It does **not** create a universal court, arbitrator, regulator, legal judgment model, mutable case file, remedy engine, or protocol truth oracle.

A conforming M13 result is a process conclusion under one named method and one exact evidence set.

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, and **MAY** are to be interpreted as normative requirements for this Marketplace profile.

## 3. Constitutional boundaries

M13 preserves the following boundaries:

```text
dispute relationship           != falsity
resolution observation         != universal truth
resolution result              != legal judgment
resolution result              != remedy
resolution result              != authorization
source acceptance              != authority acceptance
proof validity                 != attribution
attribution                    != authority
authority                      != merits
latest timestamp               != winner
majority count                 != winner
record order                   != winner
missing evidence               != no evidence exists
published resolution evidence  != mutable case state
```

An implementation MUST preserve these distinctions even when an application later chooses to use an M13 result for a consequential decision.

## 4. OLP remains the evidence substrate

Marketplace MUST reuse OLP `disputes` relationship records for portable challenge evidence.

M13 does not define a second dispute edge, a Marketplace-specific evidence envelope, or an alternate identity scheme.

A dispute relationship:

- is an immutable OLP Record;
- has its own exact OLP Record Identity;
- uses OLP `RelationshipStatementV1` with relation type `disputes`;
- has a RecordRef subject;
- targets one or more exact RecordRefs; and
- may carry OLP relationship qualifiers and critical semantics.

The subject and targets remain ordinary evidence references. Their meaning is not rewritten by M13.

## 5. No universal Case record

M13 does not introduce a first-class mutable `Case`, `DisputeCase`, `Verdict`, or `ResolutionState` Marketplace record type.

Applications MAY publish attributable dispute-resolution conclusions as ordinary OLP evidence. Such a record has its own issuer/proof/profile semantics chosen by the publishing application or profile.

Publishing a conclusion does not mutate:

- the challenged record;
- the dispute relationship record;
- prior resolution evidence; or
- any Agreement, Event, fulfillment, or settlement evidence.

## 6. Processing model

The reference M13 process has four stages:

1. validate and normalize an exact `DisputeResolutionRequestV1`;
2. classify supplied OLP dispute evidence as admissible, excluded, unresolved, or out of scope;
3. classify supplied resolution observations against the admitted dispute set; and
4. aggregate admitted resolution outcomes under the named method.

All processing is local to the supplied inputs. There is no hidden resolver or network fallback.

## 7. Core resolution method

The reference conformance method is:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/dispute-resolution/method/core-evidence-v1
```

The reference helper MUST reject any other method identifier with `UNSUPPORTED_DISPUTE_RESOLUTION_METHOD` rather than silently applying core semantics under a misleading label.

Other profiles MAY define different methods, but portable outputs MUST preserve the method identifier and exact input basis.

## 8. DisputeResolutionRequestV1

The exact v1 request shape is:

```text
{
  version: 1,
  method: AbsoluteURI,
  purpose: AbsoluteURI,
  challenged_record_ids: [RecordIdentity, ...],
  context?: { AbsoluteURI => OLPValue, ... },
  accepted_sources?: [AbsoluteURI, ...],
  accepted_authorities?: [AbsoluteURI, ...],
  understood_critical?: [AbsoluteURI, ...],
  max_disputes: Integer,
  max_resolutions: Integer
}
```

No additional fields are permitted in v1.

`challenged_record_ids` MUST be non-empty and contain canonical OLP Record Identity text.

`method` and `purpose` MUST be absolute URIs.

`max_disputes` and `max_resolutions` MUST be positive integers within the M13 v1 ceilings.

## 9. Canonical set representation

The following request arrays are set-like:

- `challenged_record_ids`;
- `accepted_sources`;
- `accepted_authorities`; and
- `understood_critical`.

They MUST be duplicate-free and deterministically sorted.

Record Identity sets use lexical ordering of canonical identity text.

URI sets use UTF-8 byte ordering.

Equivalent semantic requests therefore have one deterministic normalized representation.

## 10. Purpose and context

`purpose` identifies why the resolution is being evaluated.

`context` is a bounded semantic map whose keys are absolute URIs and whose values are valid OLP values.

Purpose and context are part of the request fingerprint and MUST NOT be silently changed when reusing a prior result.

A resolution for one purpose or context is not automatically reusable for another.

## 11. Accepted source and authority scope

`accepted_sources` and `accepted_authorities` are explicit method-local allowlists.

An empty list means that M13 does not apply an allowlist for that dimension. It does **not** mean all sources or authorities are universally trusted.

Source acceptance and authority acceptance remain separate dimensions.

A source may be permitted to supply evidence without being authoritative about the disputed subject.

An authority may be acceptable for one purpose and not another.

## 12. DisputeEvidence input

The reference helper accepts dispute evidence with these process observations:

```text
DisputeEvidence {
  record: OLP Record containing a disputes relationship,
  source: AbsoluteURI,
  authority: AbsoluteURI,
  proof_status: VERIFIED | FAILED | UNKNOWN | UNSUPPORTED | NOT_APPLICABLE,
  attribution_status: ACCEPTED | REJECTED | UNKNOWN | UNSUPPORTED,
  authority_status: ACCEPTED | REJECTED | UNKNOWN | UNSUPPORTED,
  lifecycle_status: ACCEPTABLE | ADVERSE | UNKNOWN | UNSUPPORTED
}
```

These observation fields are evaluator inputs. They are not permanently attached properties of the OLP dispute record.

## 13. Structural dispute validation

Before method admissibility is considered, a supplied dispute record MUST:

- be a valid `RecordV1`;
- contain a valid OLP relationship statement;
- use the core OLP relation type `disputes`;
- have a RecordRef subject;
- have only RecordRef targets;
- satisfy OLP relationship canonicalization; and
- satisfy OLP self-reference and critical-qualifier structural rules.

Malformed relationship evidence is an input error, not merely low-quality evidence.

## 14. Dispute scope

A dispute participates in the request only when at least one exact dispute target is in `challenged_record_ids`.

A structurally valid dispute with no challenged target is `OUT_OF_SCOPE`.

M13 MUST NOT broaden a request merely because a dispute record targets additional records elsewhere.

For an in-scope dispute, the trace preserves:

- dispute Record Identity;
- subject Record Identity;
- all exact target Record identities; and
- the exact in-scope target intersection.

## 15. Dispute admissibility states

A dispute observation is classified as one of:

```text
ADMISSIBLE
EXCLUDED
UNRESOLVED
OUT_OF_SCOPE
```

An in-scope dispute is `EXCLUDED` when the selected method explicitly rejects it because of source/authority scope, failed proof, rejected attribution, rejected authority, or adverse lifecycle treatment.

An in-scope dispute is `UNRESOLVED` when critical semantics, proof, attribution, authority, or lifecycle treatment required by the method is unknown or unsupported.

An `UNRESOLVED` dispute MUST NOT be silently treated as admitted or rejected.

## 16. Critical dispute semantics

Unknown critical OLP relationship qualifiers make an otherwise in-scope dispute `UNRESOLVED` under the core method.

A request MAY list explicitly understood critical qualifier URIs in `understood_critical`.

Understanding a qualifier permits processing of that semantic dependency. It does not imply that the dispute is true, authoritative, or meritorious.

## 17. Multiple deliveries and provenance

The same dispute Record may be observed from multiple sources.

Exact duplicate observations do not create additional semantic weight.

If at least one observation of a dispute Record is admissible, excluded or unresolved duplicate deliveries of the same immutable Record do not multiply the dispute itself.

The trace preserves the observation-level source and treatment so implementations can inspect provenance differences.

## 18. ResolutionObservationV1

The reference process uses this exact observation shape:

```text
{
  resolution_record_id: RecordIdentity,
  dispute_record_ids: [RecordIdentity, ...],
  target_record_ids: [RecordIdentity, ...],
  outcome: ResolutionObservationOutcome,
  source: AbsoluteURI,
  authority: AbsoluteURI,
  proof_status: ProofStatus,
  attribution_status: AttributionStatus,
  authority_status: AuthorityStatus,
  lifecycle_status: LifecycleStatus,
  critical_uris: [AbsoluteURI, ...],
  reason_uris: [AbsoluteURI, ...]
}
```

`resolution_record_id` identifies an attributable OLP Record that represents or anchors the observed resolution conclusion.

M13 does not prescribe that record's application-specific content type.

## 19. Resolution observation outcomes

The core method recognizes:

```text
UPHOLD
REJECT
PARTIAL
REQUIRE_ADDITIONAL_EVIDENCE
REQUIRE_HUMAN_REVIEW
UNKNOWN
UNSUPPORTED
```

These are observations attributed to a resolution source/authority. They are not universal truth values.

## 20. Exact resolution binding

Every resolution observation MUST identify:

- at least one exact dispute Record Identity; and
- at least one exact challenged target Record Identity.

A resolution observation that references a dispute not admitted in the current request is `UNRESOLVED` for that evaluation.

A resolution observation that contains both in-scope and out-of-scope targets is `UNRESOLVED` rather than being silently projected onto only part of its stated scope.

Every resolution target MUST be an in-scope target of at least one referenced admitted dispute, and every referenced dispute MUST overlap at least one target named by the resolution. A mismatch is `UNRESOLVED` with `DISPUTE_TARGET_BINDING_MISMATCH`.

A resolution with no requested target is `OUT_OF_SCOPE`.

## 21. Resolution admissibility

Resolution observations use the same separation of source, authority, proof, attribution, lifecycle, and critical-semantics dimensions as disputes.

A resolution is `ADMISSIBLE` only when:

- its target scope is valid for the request;
- all referenced dispute ids are admitted;
- source and authority pass any explicit request allowlists;
- required critical semantics are understood;
- proof is not failed;
- attribution and authority are accepted;
- lifecycle is acceptable; and
- the resolution outcome is supported by the core method.

Unknown/unsupported required dimensions make the resolution `UNRESOLVED`.

Explicitly rejected/adverse dimensions make it `EXCLUDED`.

## 22. Resolution identity consistency

Two observations carrying the same `resolution_record_id` MUST agree on the semantic resolution core:

- dispute bindings;
- target bindings;
- outcome;
- critical semantic dependencies; and
- reason URIs.

Conflicting semantic observations for the same immutable Record Identity are rejected as `RESOLUTION_IDENTITY_CONFLICT`.

Source-local acceptance metadata may still differ because relying parties may evaluate the same immutable evidence differently.

## 23. Core result lattice

The M13 core result is one of:

```text
UPHOLD_CHALLENGE_UNDER_METHOD
REJECT_CHALLENGE_UNDER_METHOD
PARTIAL_OR_MIXED_RESOLUTION
CONFLICTING_RESOLUTION_EVIDENCE
REQUIRE_ADDITIONAL_EVIDENCE
REQUIRE_HUMAN_REVIEW
INDETERMINATE
NO_ADMISSIBLE_DISPUTE
```

Every result remains bound to `METHOD_CORE`, the request, and the exact observed evidence set.

## 24. Result aggregation

The core method applies these rules:

1. no admissible dispute + unresolved in-scope dispute -> `INDETERMINATE`;
2. no admissible dispute + no unresolved in-scope dispute -> `NO_ADMISSIBLE_DISPUTE`;
3. admissible dispute + no admitted resolution + unresolved resolution -> `INDETERMINATE`;
4. admissible dispute + no admitted resolution -> `REQUIRE_ADDITIONAL_EVIDENCE`;
5. admitted `UPHOLD` and admitted `REJECT` -> `CONFLICTING_RESOLUTION_EVIDENCE`;
6. admitted `REQUIRE_HUMAN_REVIEW` -> `REQUIRE_HUMAN_REVIEW`;
7. admitted `REQUIRE_ADDITIONAL_EVIDENCE` -> `REQUIRE_ADDITIONAL_EVIDENCE`;
8. otherwise unresolved resolution evidence -> `INDETERMINATE`;
9. any admitted `PARTIAL` -> `PARTIAL_OR_MIXED_RESOLUTION`;
10. admitted `UPHOLD` only -> `UPHOLD_CHALLENGE_UNDER_METHOD`;
11. admitted `REJECT` only -> `REJECT_CHALLENGE_UNDER_METHOD`.

No rule chooses a winner by time, arrival order, source count, lexical Record Identity, or majority vote.

## 25. Conflicting resolutions

Competing admissible resolutions MUST remain visible.

If one admissible resolution upholds a challenge and another admissible resolution rejects it, core returns `CONFLICTING_RESOLUTION_EVIDENCE`.

The trace preserves both exact resolution Record identities and their provenance.

A later profile MAY define an arbitration hierarchy or authority-selection method, but that hierarchy MUST be explicit and method-bound.

## 26. Partial and mixed resolution

`PARTIAL` is used when a resolution observation does not fully uphold or reject the dispute under its own stated semantics.

The presence of an admissible partial resolution produces `PARTIAL_OR_MIXED_RESOLUTION` unless a stronger preceding core condition requires conflict, human review, additional evidence, or indeterminate processing.

Partial resolution MUST NOT be silently converted into full rejection or full uphold.

## 27. Open-world missing evidence

Marketplace remains open-world.

Absence of a dispute record from the supplied set does not prove that no dispute exists.

Absence of resolution evidence does not prove that no resolution exists.

Absence of a remedy record does not prove that no remedy was ordered elsewhere.

`NO_ADMISSIBLE_DISPUTE` therefore means only that this method admitted no supplied in-scope dispute evidence under this request.

It is not a global non-existence claim.

## 28. Request fingerprint

M13 computes a deterministic request fingerprint over the normalized `DisputeResolutionRequestV1`.

The fingerprint is processing metadata, not OLP Record Identity and not a signature.

Changing method, purpose, target set, context, source/authority assumptions, understood critical semantics, or resource bounds changes the request fingerprint.

## 29. Resolution input fingerprint

M13 computes a deterministic input fingerprint over:

- the normalized request;
- the complete normalized dispute trace; and
- the complete normalized resolution trace.

This binds the result to admitted, excluded, unresolved, out-of-scope, and duplicate-observation treatment—not only to the final admitted subset.

## 30. Result fingerprint

The result fingerprint covers the deterministic result core including:

- method and purpose;
- challenged record set and context;
- admitted/unresolved dispute ids;
- dispute trace;
- admitted/unresolved resolution ids;
- resolution trace;
- admitted outcomes;
- aggregate outcome;
- duplicate counts; and
- request/input fingerprints.

The result fingerprint is an integrity checksum over process metadata. It does not authenticate the evaluator.

## 31. Decision reuse

A prior M13 result is reusable under the reference helper only when the current request fingerprint and current resolution-input fingerprint are unchanged.

Reuse does not establish that:

- the prior result was authentically published by a trusted evaluator;
- no new evidence exists elsewhere;
- policy assumptions outside the request are unchanged; or
- a protected side effect is authorized.

Changed execution or policy assumptions require reevaluation by the consuming application.

## 32. Result publication

An evaluator MAY publish an M13 result as attributable OLP evidence.

If published, the record SHOULD identify the method, purpose, target scope, exact evidence/input binding, and result fingerprint needed to reconstruct the conclusion.

Publication makes the evaluator's assertion portable. It does not make the assertion protocol truth.

## 33. Relationship to Milestone 11 authorization

M13 resolution outcomes do **not** authorize protected operations.

In particular, these actions remain separate local-policy decisions:

- payment or refund execution;
- escrow release;
- settlement reversal;
- account suspension;
- content removal;
- federation blocking;
- disclosure of private evidence;
- autonomous fulfillment action; or
- any other protected side effect.

A consumer that wants to perform a protected side effect MUST pass the relevant request through the Milestone 11 authorization boundary before executing that side effect.

Every M13 core result therefore carries `protected_side_effect_authorized = false`.

## 34. Remedies are out of band

M13 does not define damages, specific performance, replacement, refund amount, cancellation, penalty, injunction, custody transfer, title transfer, or another remedy.

A later profile may define remedy evidence or workflow semantics, but resolution and remedy MUST remain separately attributable and separately authorized.

## 35. Relationship to fulfillment

A fulfillment evaluator may report `DISPUTED_EVIDENCE` when accepted dispute evidence targets relevant fulfillment events.

M13 may subsequently evaluate that dispute under an explicit resolution method.

An M13 result does not rewrite the historical fulfillment event and does not automatically replace the fulfillment evaluator's evidence trace.

A relying application MAY rerun fulfillment evaluation using its chosen method/policy after considering resolution evidence.

## 36. Relationship to settlement

Settlement evidence may be disputed and resolved under M13.

An M13 uphold/reject conclusion does not itself execute a refund, reversal, transfer, escrow release, or payment.

Settlement execution remains a protected side effect under local policy and rail-specific controls.

## 37. Relationship to trust evaluation

M9 trust/evidence evaluation may treat disputes and M13 resolution evidence as inputs.

M13 does not prescribe how every trust method must weight an upheld, rejected, partial, or conflicting resolution.

Algorithm plurality is preserved.

## 38. Relationship to privacy

Dispute materials can reveal commercially, personally, or legally sensitive information.

M10 selective-disclosure rules remain applicable.

A dispute-resolution workflow SHOULD request only evidence needed for its declared purpose and SHOULD preserve correlation warnings associated with disclosed parties, agreements, events, settlement details, or provenance graphs.

M13 does not create a disclosure entitlement.

## 39. Security boundaries

Untrusted dispute or resolution input MUST NOT trigger:

- code execution;
- implicit network dereference;
- wallet or bank access;
- payment submission;
- file-system side effects;
- credential use;
- autonomous moderation action; or
- recursive unbounded resolution.

All external side effects belong outside the reference evaluator.

## 40. Resource limits

The v1 reference profile bounds:

```text
max disputes                     4096
max resolution observations      4096
max set-like request members      256
max semantic context entries      128
max URI UTF-8 length             2048 bytes
```

Implementations MAY choose lower local limits.

A portable v1 request MUST NOT raise processing beyond these core ceilings.

Subsequent resolution, proof, network, graph, or domain-specific work MUST have its own explicit bounds and timeouts.

## 41. Deterministic ordering and deduplication

Exact duplicate dispute or resolution observations are deduplicated for semantic counting.

Duplicate delivery count remains visible as process metadata.

Deduplication MUST NOT erase differing provenance/treatment observations that are not exact duplicates.

All traces are deterministically ordered by canonical OLP encoding.

## 42. Replay safety

Transport replay of the same immutable evidence does not create a new dispute or new resolution merely because it was delivered twice.

A different immutable resolution Record is separate evidence even when it reaches the same outcome.

A new observation of the same immutable Record from another source may change provenance treatment, but not the Record Identity itself.

## 43. Explainable trace

The dispute trace records, at minimum:

- dispute Record Identity;
- subject Record Identity;
- target ids and in-scope target ids;
- source and authority;
- proof/attribution/authority/lifecycle statuses;
- critical semantic dependencies;
- state; and
- reasons.

The resolution trace records the exact resolution observation plus its state and reasons.

A consumer can therefore reconstruct why evidence participated or did not participate.

## 44. Boundary flags

The reference result explicitly states `false` for:

```text
universal_truth_established
legal_judgment_established
challenged_record_mutated
dispute_record_erased
remedy_or_side_effect_implied
protected_side_effect_authorized
hidden_network_fallback_used
resolution_is_marketplace_record
result_authentication_established
global_evidence_completeness_established
```

These flags prevent process metadata from being accidentally promoted into stronger claims.

## 45. Core invariant table

```text
accepted dispute                  != true dispute claim
excluded dispute                  != false dispute claim
unresolved dispute                != rejected dispute
no admissible dispute             != no dispute exists
uphold under method               != universal correctness
reject under method               != universal falsity
partial resolution                != full resolution
conflicting resolutions           != latest-wins
resolution fingerprint            != evaluator authentication
resolution record                 != Marketplace universal record type
resolution outcome                != remedy
resolution outcome                != authorization
```

## 46. Example: software work dispute

A provider publishes completion evidence for a software task. The requester publishes an OLP `disputes` relationship targeting that completion event.

A project-specific reviewer later publishes attributable resolution evidence upholding the challenge.

M13 can reproduce `UPHOLD_CHALLENGE_UNDER_METHOD` for that method and evidence set.

The completion event still exists, the dispute still exists, and the M13 result does not issue a refund. A refund workflow requires separate settlement semantics and local authorization.

## 47. Example: competing arbitration evidence

Two admitted resolution records address the same admitted dispute. One upholds and one rejects the challenge.

Core returns `CONFLICTING_RESOLUTION_EVIDENCE` and preserves both.

Core does not choose the newest, most popular, or lexically smaller Record Identity.

A later explicit arbitration-hierarchy method may do so only if its authority-selection rule is declared and reproducible.

## 48. Example: unknown critical procedure

A dispute relationship declares a critical procedure qualifier that the selected request does not understand.

The dispute remains structurally valid but is `UNRESOLVED` under the reference method.

The evaluator returns `INDETERMINATE` rather than pretending the qualifier is irrelevant.

## 49. Conformance processing profile

The non-normative reference implementation is:

```text
tools/marketplace_dispute_resolution_v1.py
```

Deterministic vectors are generated and replayed with:

```text
python tools/generate_dispute_resolution_vectors.py
python tools/validate_dispute_resolution_vectors.py
```

The vector artifact is:

```text
conformance/vectors/dispute-resolution-v1.json
```

## 50. Conformance coverage

M13 conformance covers positive/evaluation and adversarial cases for:

- canonical request validation;
- exact target binding;
- valid OLP `disputes` relationships;
- out-of-scope disputes;
- source and authority allowlists;
- proof, attribution, authority, and lifecycle separation;
- unknown critical semantics;
- no-dispute and needs-evidence outcomes;
- uphold, reject, partial, human-review, and additional-evidence outcomes;
- conflicting independent resolutions;
- resolution target/dispute binding failures, including cross-binding between dispute ids and their exact targets;
- duplicate transport observations;
- multi-target disputes;
- result/request/input fingerprints;
- exact reuse and changed-input rejection;
- result integrity tampering;
- boundary-flag tampering; and
- resource ceilings.

## 51. Deferred and out of scope

M13 does not standardize:

- universal arbitrator selection;
- court hierarchy;
- governing law;
- jurisdiction;
- legal enforceability;
- burden or standard of proof for every domain;
- evidence discovery procedure;
- testimony or deposition rules;
- appeal deadlines;
- universal remedy calculation;
- damages;
- escrow/payment execution;
- account/moderation action;
- identity recovery;
- mandatory AI adjudication;
- mandatory human adjudication;
- universal trust consequences; or
- one canonical arbitration provider.

These belong to explicit later profiles, application policy, legal systems, or domain-specific methods.

## 52. Acceptance boundary

Milestone 13 is satisfied when independent processors can reproduce the committed M13 vector outcomes while preserving these properties:

1. OLP `disputes` remains the portable challenge relationship;
2. no mutable universal case/verdict object is introduced;
3. dispute, source, proof, attribution, authority, lifecycle, and merits remain separate dimensions;
4. exact target and dispute Record identities are preserved;
5. unknown critical semantics fail closed to unresolved/indeterminate processing;
6. missing/private/unresolved evidence is not converted into falsity, guilt, breach, or global absence;
7. competing admissible resolutions remain visible without latest-wins or majority selection;
8. every result is method-, purpose-, request-, and evidence-bound;
9. result fingerprints are process integrity metadata rather than authentication;
10. protected side effects are never authorized by M13 itself;
11. no hidden network fallback or executable untrusted input is introduced;
12. all processing is resource-bounded and deterministic; and
13. all earlier Marketplace conformance suites remain green.
