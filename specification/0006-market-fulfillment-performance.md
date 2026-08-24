# Marketplace — Fulfillment & Performance Semantics

**Status:** Draft v0.1
**Milestone:** 6 — Fulfillment & Performance Semantics
**Filename:** `specification/0006-market-fulfillment-performance.md`

---

## 1. Purpose

This specification defines how Marketplace implementations represent and evaluate evidence concerning performance of commitments after Agreement formation.

It covers commitment-targeted performance and delivery assertions, inspection observations, acceptance and rejection evidence, partial performance, completion and failure assertions, disputes, and method-relative fulfillment conclusions.

It does **not** create a fourth Marketplace record type, mutate an Agreement or Commitment, define one universal fulfillment truth, equate payment with completion, or define a universal dispute-adjudication system.

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are interpreted as described by RFC 2119 and RFC 8174 when written in all capitals.

## 3. Dependency baseline

Marketplace Fulfillment & Performance v1 depends on Marketplace Specifications 0001–0005 and the applicable Open Layer Protocol specifications.
OLP remains authoritative for immutable Record Identity, proofs, relationship records, lifecycle evidence, resolution, privacy, evidence exchange, and identity/authority evaluation.

The Milestone 6 executable vectors use the same draft OLP reproducibility pin as Milestones 3–5:

```text
41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c
```

## 4. Core invariants

1. A MarketAgreement and its embedded Commitments remain immutable.
2. Fulfillment evidence is additive evidence, not mutable Agreement state.
3. A performance or delivery assertion does not prove objective performance.
4. Delivery does not imply acceptance.
5. Acceptance does not imply absence of dispute.
6. Payment or settlement evidence does not imply fulfillment or completion.
7. A completion assertion does not itself establish fulfillment.
8. A failure assertion does not itself establish universal failure.
9. Missing, private, unresolved, or unavailable evidence is not non-performance evidence.
10. Conflicting evidence MUST be preserved rather than silently resolved by timestamp or ingestion order.
11. Positive fulfillment is always relative to an identified evaluation method/profile.
12. Unknown critical semantics MUST NOT silently produce a positive fulfillment conclusion.

## 5. Reuse of existing Marketplace records
Milestone 6 introduces no new universal first-class Marketplace record. Fulfillment evidence uses ordinary `MarketEventV1` records plus existing OLP relationship records where the relationship itself must be attributable.

Every core fulfillment event MUST target exactly one Commitment using the existing `CommitmentRefV1`:

```text
CommitmentRefV1 = {
  record: RecordRef,   // exact containing MarketAgreement
  id: LocalId         // exact container-local Commitment id
}
```

The `record` member MUST resolve to the exact Agreement supplied to the evaluator, and `id` MUST identify one Commitment in that Agreement.

A bare local Commitment id is never a portable cross-record reference.

## 6. Fulfillment event identifiers

Core v1 defines these Marketplace event identifiers:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/event/commitment-performance
https://open-trust-layer.github.io/marketplace/semantics/v1/event/commitment-delivery
https://open-trust-layer.github.io/marketplace/semantics/v1/event/commitment-inspection
https://open-trust-layer.github.io/marketplace/semantics/v1/event/commitment-acceptance
https://open-trust-layer.github.io/marketplace/semantics/v1/event/commitment-rejection
https://open-trust-layer.github.io/marketplace/semantics/v1/event/commitment-completion-assertion
https://open-trust-layer.github.io/marketplace/semantics/v1/event/commitment-failure-assertion
```
These identifiers describe attributed assertions or observations. They do not by themselves establish objective occurrence, legal effect, or final state.

## 7. Performance and delivery extent

A core `commitment-performance` or `commitment-delivery` event MUST be issued by the principal named by the targeted Commitment's `party.principal` under the core processing profile.

This issuer equality is a syntactic/profile rule for whose performance is being asserted. It does not self-prove identity or authority; relying applications MUST evaluate attribution and authority separately.

Performance and delivery events MUST include an `OutcomeV1` whose `type` is one of:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/outcome/performance-partial
https://open-trust-layer.github.io/marketplace/semantics/v1/outcome/performance-claimed-complete
```

`performance-partial` states only that the issuer asserts some performance occurred without claiming complete performance under the selected Commitment.

`performance-claimed-complete` states only that the issuer asserts complete performance. It is not itself a fulfillment conclusion.

Profiles MAY place structured progress, quantity, measurement, deliverable, resource, or other evidence in `OutcomeV1.details`, but core v1 does not define one universal percentage or quantity model.

## 8. Delivery is not acceptance

A `commitment-delivery` event is a specialized performance assertion that something was delivered or handed off under the targeted Commitment.

Delivery MUST NOT be interpreted as acceptance, successful inspection, completion, settlement, or absence of dispute merely because the event is conforming.
## 9. Inspection observations

A `commitment-inspection` event represents an attributed observation about one acceptance criterion or another profile-defined inspection target.

The core conformance profile requires inspection of an embedded required or informational `AcceptanceCriterionV1` to identify that criterion by its exact abstract value inside the targeted Commitment.

For the executable profile, the event outcome is:

```text
OutcomeV1 = {
  type: https://open-trust-layer.github.io/marketplace/semantics/v1/outcome/acceptance-criterion-observation,
  details: {
    criterion: AcceptanceCriterionV1,
    status: SATISFIED | UNSATISFIED | UNKNOWN | UNSUPPORTED
  }
}
```

A semantically similar criterion URI is not sufficient if the exact embedded structure differs.

Inspection is evidence supplied by an issuer or process. It does not become objective fact merely because it is represented as a MarketEvent.

## 10. Acceptance and rejection

`commitment-acceptance` and `commitment-rejection` are attributable response events concerning the exact targeted Commitment.

Core v1 does not infer either event from performance, delivery, inspection, payment, silence, elapsed time, or application UI state.
The event issuer states who asserts acceptance or rejection. Whether that principal is entitled to accept or reject under the Agreement, organizational authority, delegation, law, or local policy remains a separate evaluation dimension.

Acceptance does not erase contradictory inspection, rejection, dispute, correction, or later evidence.

## 11. Completion and failure assertions

A `commitment-completion-assertion` event records that its issuer asserts the targeted Commitment is complete.

A `commitment-failure-assertion` event records that its issuer asserts failure or non-performance concerning the targeted Commitment.

Neither event mutates the Agreement or Commitment. Neither is a universal state transition.

A completion assertion without sufficient performance/acceptance evidence remains insufficient for a positive core fulfillment conclusion.

A failure assertion may support a method-relative negative conclusion when the relying method accepts its attribution and authority, but it does not establish universal failure.

## 12. Evidence acceptance dimensions

Before an event contributes to the core evaluator, the relying processor MUST separately decide whether its attribution and authority are accepted for that evaluation.

The executable profile models these dimensions explicitly as:

```text
attribution_accepted: bool
authority_accepted: bool
```

Both must be true for the event to count under the core evaluator.
An event rejected on either dimension remains historical evidence; it is simply not counted toward that evaluator's conclusion.

The profile does not prescribe one universal identity or authority policy. Implementations may derive those booleans from OLP proofs, authority statements, organizational policy, local trust configuration, or other accepted evidence.

## 13. Required acceptance criteria

For the core fulfillment method, every `AcceptanceCriterionV1` with `mode = required` on the targeted Commitment participates in positive fulfillment evaluation.

A required criterion is satisfied only when accepted inspection evidence reports `SATISFIED` and no accepted `UNSATISFIED` observation creates a conflict.

The states are interpreted as follows:

```text
SATISFIED              contributes positive criterion evidence
UNSATISFIED            blocks positive fulfillment under the method
UNKNOWN                keeps positive fulfillment indeterminate
UNSUPPORTED            keeps positive fulfillment indeterminate
missing observation    keeps positive fulfillment indeterminate
```

Contradictory accepted `SATISFIED` and `UNSATISFIED` evidence for the same exact criterion produces conflicting evidence; core does not select a winner.

Informational criteria MAY be reported or used by profile-specific methods but MUST NOT silently become required core conditions.

## 14. Core fulfillment method

The executable profile identifies its default method with:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/fulfillment/method/core-acceptance-v1
```
Under this method, positive fulfillment requires accepted claimed-complete performance or delivery, all required acceptance criteria satisfied, and acceptance evidence when `require_acceptance = true`.

Core v1 conclusions are:

```text
FULFILLED_UNDER_METHOD
PARTIALLY_PERFORMED_UNDER_METHOD
NOT_FULFILLED_UNDER_METHOD
INDETERMINATE
CONFLICTING_EVIDENCE
DISPUTED_EVIDENCE
```

These are evaluator outputs, not authenticated mutable Agreement fields.

`FULFILLED_UNDER_METHOD` means only that the supplied, accepted evidence satisfies the selected method's declared conditions.

`PARTIALLY_PERFORMED_UNDER_METHOD` means accepted partial performance exists without accepted claimed-complete performance or stronger blocking/conflicting evidence.

`NOT_FULFILLED_UNDER_METHOD` is a method-relative negative conclusion based on accepted rejection/failure/unsatisfied required criteria; it is not proof of universal non-performance.

`INDETERMINATE` means the evidence supplied to the method is insufficient, incomplete, unknown, unsupported, or otherwise unable to justify a stronger conclusion.

## 15. Conflict preservation

Accepted acceptance and rejection evidence may coexist. Accepted completion and failure evidence may coexist. Complete-performance and accepted failure evidence may coexist.

Core v1 MUST preserve these conflicts and MUST NOT choose a winner by record order, ingestion order, asserted timestamp, or source popularity.
## 16. Disputes

Marketplace reuses OLP `disputes` relationship records when one record challenges fulfillment evidence.

A conforming dispute may target a performance, delivery, inspection, acceptance, rejection, completion, or failure event by exact RecordRef.

The existence of an accepted dispute MUST NOT erase or mutate the disputed event. It causes the core evaluator to report disputed evidence when the targeted event otherwise participates in the selected evaluation.

OLP `disputes` does not establish that either side is correct. Dispute adjudication remains outside this core specification.

## 17. Critical semantics

Before returning a positive fulfillment conclusion, the evaluator MUST understand every Marketplace content-extension URI marked `critical` on the Agreement and every accepted fulfillment event used by the method.

If any required critical semantic is not understood, the core result is `INDETERMINATE`.

A syntactically valid event with an unknown critical extension MUST NOT silently count as fully processed fulfillment evidence.

## 18. Duplicate evidence

Exact duplicate evidence MUST be identified by OLP Record Identity, not by object identity, source, or arrival order.

The executable profile counts an identical evidence event at most once. Repeating the same event MUST NOT inflate fulfillment, ignored-event, performance, acceptance, rejection, inspection, completion, or failure counts.

If the same exact event identity is supplied with conflicting evaluator attribution/authority acceptance context in one evaluation, the evaluation MUST fail as ambiguous rather than silently selecting one context. The executable profile reports `DUPLICATE_EVIDENCE_CONTEXT_CONFLICT`.
## 19. Open-world and missing evidence

Marketplace fulfillment evaluation is open-world. Absence of an event from a supplied evidence set does not prove that the event does not exist elsewhere.

Missing performance evidence is therefore not automatic non-performance. Missing acceptance is not automatic rejection. Missing dispute evidence is not proof that no dispute exists.

An evaluator MAY conclude only from the evidence and coverage assumptions it actually accepts.

## 20. Settlement and payment remain separate

Payment, settlement, escrow, refund, reversal, asset-transfer, or other settlement events MAY appear in the same evidence graph, but the core fulfillment method does not evaluate them.

A settlement-completion event MUST NOT be counted as performance, delivery, acceptance, inspection, or completion of a Commitment.

Likewise, a fulfillment conclusion does not prove settlement or payment.

## 21. Privacy and selective disclosure

Fulfillment evidence may reveal counterparties, work products, delivery locations, inspection results, failures, disputes, or commercially sensitive details.

Implementations SHOULD minimize disclosure and MAY use private, selectively disclosed, encrypted, or peer-to-peer evidence exchange consistent with OLP privacy semantics.

Private or withheld evidence MUST NOT be treated as nonexistent merely because one evaluator cannot access it.
## 22. Security and resource limits

Fulfillment evaluators process untrusted evidence and MUST use bounded resource limits.

Core v1 bounds supplied fulfillment evidence and understood-critical sets in the executable profile. Implementations MUST likewise bound candidate evidence, relationship processing, resolution, network access, payload size, and expensive profile-specific inspection work.

Untrusted MarketEvent content MUST NOT cause implicit network dereference or execution of embedded code.

Identity, authority, proof validity, lifecycle, policy permission, and fulfillment remain independent evaluation dimensions.

## 23. Method plurality

Marketplace does not define one universal fulfillment method for every market domain.

Profiles MAY define methods requiring different inspection evidence, recipient acceptance, quorum rules, measurement standards, milestones, quantities, tolerances, authority evidence, or other domain semantics.

Different conforming methods MAY reach different conclusions over the same immutable evidence without creating a protocol contradiction.

A method identifier MUST be an absolute URI when its result is intended to be portable or comparable. The reference evaluator in this repository implements only `core-acceptance-v1` and MUST reject any other method identifier rather than apply core semantics under a misleading label. Such an unsupported identifier is reported as `UNSUPPORTED_FULFILLMENT_METHOD`.

## 24. Attributable conclusions

An evaluator MAY intentionally publish a fulfillment conclusion as an ordinary OLP Claim, Attestation, Observation, or Event with explicit method and input provenance.

Publishing such a conclusion makes the evaluator's assertion portable; it does not transform the conclusion into universal truth.
## 25. Executable conformance profile

The Milestone 6 helper implementation is non-normative. The normative contract is the observable behavior defined by this specification and the committed conformance vectors.

The executable profile covers:

```text
exact Agreement + Commitment targeting
performance and delivery extent validation
inspection against exact AcceptanceCriterionV1
separate attribution and authority acceptance
method-relative aggregation
required criterion handling
conflict preservation
OLP dispute relationships
critical-extension fail-closed behavior
Record-Identity deduplication
resource limits
settlement non-substitution
```

## 26. Executable vectors

The committed vector file is:

```text
conformance/vectors/fulfillment-performance-v1.json
```

The initial acceptance set contains 47 vectors: 25 positive/evaluation cases and 22 negative cases.

Vector processing is deterministic and uses OLP's implementation-neutral projection. The JSON file is not a mandatory Marketplace wire format.
## 27. Core invariant table

```text
performance assertion          != objective performance
delivery                       != acceptance
partial performance            != completion
completion assertion           != fulfillment truth
failure assertion              != universal failure
acceptance                      != absence of dispute
settlement/payment              != fulfillment
missing evidence                != non-performance
inspection observation          != objective criterion truth
dispute                         != adjudication
method-relative fulfillment     != universal completion
repeated evidence               != additional evidence
```

## 28. Cross-scale examples

A software task may use delivery for a submitted patch, inspection for test/security criteria, and acceptance from the requester. Passing tests can contribute evidence without making the patch universally correct.

A physical-goods exchange may use delivery evidence for handoff, inspection for condition criteria, and recipient acceptance. Payment settlement remains a separate evidence stream.

A compute service may report partial performance over a time window, measurement observations, and later completion/failure assertions under a domain-specific method.

A large infrastructure or scientific project may use many profile-defined commitment methods while retaining the same immutable Agreement/Commitment/Event substrate.

## 29. Intentionally deferred

Milestone 6 does not define settlement execution, escrow, universal milestone arithmetic, dispute adjudication, warranties/remedies, legal breach, damages, universal quality metrics, or one authoritative completion clock.
## 30. Acceptance boundary

Milestone 6 is satisfied when independent processors can reproduce the committed fulfillment/performance vector outcomes while preserving these properties:

1. no new universal first-class Marketplace record type is introduced;
2. every core fulfillment event targets an exact Agreement Commitment;
3. delivery/performance evidence does not self-prove fulfillment or acceptance;
4. partial performance is representable without mutating Agreement commitments;
5. acceptance/rejection remains attributable evidence with separately evaluated authority;
6. completion/failure claims remain evidence rather than universal current state;
7. missing/private/unresolved evidence is not converted into negative evidence;
8. conflicting and disputed evidence remains visible without latest-wins selection;
9. payment/settlement remains separate from fulfillment;
10. unknown critical semantics fail closed for positive conclusions;
11. duplicate evidence cannot inflate evaluator counts; and
12. Milestones 3–5 regression suites remain green.

---

**End of Marketplace Specification 0006 — Fulfillment & Performance Semantics — Draft v0.1**
