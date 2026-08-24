# Marketplace — Settlement Interfaces & Economic Exchange Semantics

**Status:** Draft v0.1
**Milestone:** 7 — Settlement Interfaces & Economic Exchange Semantics
**Filename:** `specification/0007-market-settlement-interfaces.md`

---

## 1. Purpose

This specification defines how Marketplace implementations represent and evaluate evidence concerning economic settlement of Agreement Commitments while remaining payment-rail, asset-system, currency, escrow, blockchain, banking, and jurisdiction neutral.

It covers settlement attempts, partial and claimed-complete settlement, failures, reversals, refunds, escrow holds/releases, asset-transfer evidence, rail verification, Agreement settlement preferences, disputes, and method-relative settlement conclusions.

It does **not** execute a payment, transfer custody, create title, guarantee finality, mutate an Agreement, define a universal currency, or create a fourth Marketplace record type.

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are interpreted as described by RFC 2119 and RFC 8174 when written in all capitals.

## 3. Dependency baseline

Marketplace Settlement Interfaces v1 depends on Marketplace Specifications 0001–0006 and the applicable Open Layer Protocol specifications.

OLP remains authoritative for immutable Record Identity, proofs, relationship records, lifecycle evidence, resolution, privacy, transport, and identity/authority evaluation. Marketplace does not fork those mechanisms for settlement.

The Milestone 7 executable vectors use the same draft OLP reproducibility pin as Milestones 3–6:

```text
41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c
```

## 4. Core invariants

1. Settlement evidence is additive evidence, not mutable Agreement state.
2. A settlement event is not proof that money, assets, rights, or title objectively moved.
3. A rail-native reference is not universal proof of finality.
4. Settlement does not imply fulfillment or acceptance.
5. Settlement does not imply ownership, title, legality, or enforceability.
6. Missing settlement evidence is not non-payment evidence.
7. Partial settlement does not imply a universal percentage or remaining balance.
8. Refund/reversal evidence does not erase the original settlement evidence.
9. Conflicting evidence MUST be preserved rather than resolved by arrival order or timestamp.
10. Rail-specific verification and finality remain external/profile-relative.
11. Different rails MAY coexist for one Commitment without one canonical winner.
12. Core MUST NOT perform universal arithmetic across incompatible value forms or rails.
13. Unknown critical settlement semantics MUST fail closed for positive conclusions.

## 5. Reuse of existing Marketplace records

Milestone 7 introduces no new universal first-class Marketplace record.

Settlement evidence uses ordinary `MarketEventV1` records. Agreement/Intent constraints reuse `SettlementPreferenceV1`, and economic quantities reuse `ValueExpressionV1`.

Every core settlement event MUST target exactly one Commitment using the existing `CommitmentRefV1`:

```text
CommitmentRefV1 = {
  record: RecordRef,  // exact containing MarketAgreement
  id: LocalId        // exact container-local Commitment id
}
```

The `record` member MUST identify the exact Agreement supplied to the evaluator, and `id` MUST identify one Commitment in that Agreement. A bare local Commitment id is never a portable settlement target.

## 6. Core settlement event identifiers
Core v1 defines these event identifiers:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/event/settlement-attempt
https://open-trust-layer.github.io/marketplace/semantics/v1/event/settlement-completion
https://open-trust-layer.github.io/marketplace/semantics/v1/event/settlement-failure
https://open-trust-layer.github.io/marketplace/semantics/v1/event/settlement-reversal
https://open-trust-layer.github.io/marketplace/semantics/v1/event/settlement-refund
https://open-trust-layer.github.io/marketplace/semantics/v1/event/escrow-hold
https://open-trust-layer.github.io/marketplace/semantics/v1/event/escrow-release
https://open-trust-layer.github.io/marketplace/semantics/v1/event/asset-transfer
```

These are attributable assertions/observations. The identifier does not make the issuer a bank, custodian, clearing system, title registry, or authoritative rail observer.

## 7. Settlement outcome details

Every core settlement event MUST contain an `OutcomeV1` whose `type` is:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/outcome/settlement-evidence
```

Its `details` map has the exact core shape below.
```text
SettlementEvidenceDetailsV1 = {
  method: AbsoluteURI,
  extent?: settlement-partial | settlement-claimed-complete,
  value?: ValueExpressionV1,
  reference?: Text
}
```

`method` identifies the settlement rail, mechanism, or profile. It is semantic identity, not an instruction to dereference a URL or contact a service.

`value` is an attributed economic expression only. It MAY be monetary, quantity-based, or semantic using `ValueExpressionV1`.

`reference`, when present, is an opaque rail/profile-native reference. Core v1 requires it to be non-empty text of at most 1024 characters. It MUST NOT be implicitly dereferenced or treated as universal transaction proof.

Core extent identifiers are:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/settlement/extent/partial
https://open-trust-layer.github.io/marketplace/semantics/v1/settlement/extent/claimed-complete
```

The claimed-complete extent is an assertion about the event's settlement scope, not universal proof that the Agreement obligation is economically or legally satisfied.
## 8. Event-specific extent rules

`settlement-completion`, `settlement-reversal`, `settlement-refund`, `escrow-release`, and `asset-transfer` MUST carry an extent.

`settlement-attempt`, `settlement-failure`, and `escrow-hold` MUST NOT carry a core extent.

Profiles MAY define additional detail fields only through a separate profile/extension contract; core v1 does not silently accept undeclared fields in `SettlementEvidenceDetailsV1`.

## 9. Rail verification is external

A syntactically valid settlement event does not prove that a rail accepted, confirmed, finalized, or even observed the referenced operation.

The executable core evaluator therefore receives three independent relying-party decisions for every candidate event:

```text
attribution_accepted: bool
authority_accepted: bool
rail_evidence_accepted: bool
```

All three MUST be true before an event contributes to the core settlement conclusion.

`rail_evidence_accepted` may incorporate rail-specific signature verification, receipt validation, confirmation depth, bank status, escrow-provider evidence, ledger finality, or another method-specific check. Core does not define one universal verification algorithm.
## 10. Agreement settlement preferences

`SettlementPreferenceV1` remains an authenticated preference/constraint, not a payment instruction.

Core v1 evaluates only the parts it can interpret without rail-specific knowledge:

```text
excluded exact method, no parameters   -> rejected for core settlement evidence
required methods exist, no exact match -> rejected for core settlement evidence
required exact method, no parameters   -> admissible
accepted/preferred                     -> non-binding hints in core v1
```

If an exact `required` or `excluded` preference contains `parameters`, core v1 MUST NOT guess their meaning. The relevant evidence remains indeterminate unless a profile-aware evaluator understands those parameters.

A set of `required` preferences acts as an admissible-method set for each event under this core evaluator. This does not claim that one event satisfies every domain-specific requirement of every rail/profile.

An unconditional exact `excluded` preference takes precedence over a parameterized exclusion for the same method, and `excluded` takes precedence over `required` for that same method. This conservative precedence avoids weakening an unambiguous prohibition.

## 11. Settlement attempts

A `settlement-attempt` event states only that its issuer asserts an attempt was made using the identified method.

An attempt does not imply completion, acceptance by the rail, finality, fulfillment, or success.
## 12. Partial and claimed-complete settlement

A `settlement-completion` event with `settlement-partial` represents accepted evidence of partial settlement under the selected method.

Core v1 does not assign a universal percentage, remaining balance, exchange rate, or aggregation rule to partial evidence.

A `settlement-completion` event with `settlement-claimed-complete` can support `SETTLED_UNDER_METHOD` when its attribution, authority, rail evidence, preferences, critical semantics, and other evaluator conditions are accepted.

This conclusion does not prove that the event's `value` equals every economic obligation in the Agreement. Profiles that require amount, quantity, milestone, exchange-rate, fee, tax, or tolerance matching MUST define those semantics explicitly.

## 13. Asset-transfer evidence

An `asset-transfer` event may represent money-like, tokenized, physical, digital, contractual, or other profile-defined transfer evidence.

Under the core evaluator, an accepted claimed-complete asset-transfer event MAY support `SETTLED_UNDER_METHOD` for its targeted Commitment.

This does **not** establish ownership, title, custody, legality, transferability, registration, lien status, or jurisdictional effect. Those remain separate evidence/policy dimensions.
## 14. Escrow evidence

`escrow-hold` states that its issuer asserts value/assets were placed under an escrow-like mechanism identified by `method`.

`escrow-release` MUST reference exactly one prior `escrow-hold` event by exact RecordRef and MUST carry an extent.

An accepted hold without an accepted release may produce `HELD_IN_ESCROW_UNDER_METHOD`.

A release does not by itself produce `SETTLED_UNDER_METHOD`; release and settlement completion remain distinct assertions. A profile MAY define stronger semantics when an escrow rail contract makes release itself sufficient.

Escrow evidence does not make Marketplace the custodian, escrow provider, fiduciary, trustee, or legal guarantor.

## 15. Settlement failures

`settlement-failure` records an attributed failure/non-success assertion for the exact targeted Commitment and rail method.

An accepted failure without stronger settlement evidence may support `NOT_SETTLED_UNDER_METHOD`.

It does not prove universal non-payment, impossibility of later settlement, or absence of evidence on another rail.

## 16. Reversals and refunds
A `settlement-reversal` or `settlement-refund` event MUST reference exactly one prior accepted `settlement-completion` or `asset-transfer` event by exact RecordRef.

The causal reference is authenticated history, not mutable state. The original settlement evidence remains valid evidence that the earlier assertion existed.

If the referenced event is not supplied to the evaluator, the core result is indeterminate rather than assuming the target exists or does not exist.

If the supplied target is the wrong event type, the core result is indeterminate; it MUST NOT silently reinterpret the relationship.

A claimed-complete reversal/refund over accepted partial or claimed-complete settlement evidence may produce `REVERSED_OR_REFUNDED_UNDER_METHOD`.

A partial reversal/refund may produce `PARTIALLY_REVERSED_OR_REFUNDED_UNDER_METHOD`.

Core does not calculate a net balance from these events.

## 17. Value and arithmetic neutrality

`ValueExpressionV1` gives exact representation, not universal arithmetic.

Core v1 MUST NOT add, subtract, exchange-rate convert, net, compare purchasing power, or otherwise aggregate incompatible settlement values across rails, currencies, quantities, semantic value forms, fees, taxes, or jurisdictions.

Multiple partial events remain multiple attributable observations unless a profile defines compatible arithmetic and proves its inputs.
## 18. Core settlement evaluation method

The executable reference evaluator implements exactly one method:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/settlement/evaluation/core-evidence-v1
```

It MUST reject any other evaluation-method identifier with `UNSUPPORTED_SETTLEMENT_EVALUATION_METHOD` rather than apply core semantics under a misleading label.

Core conclusions are:

```text
SETTLED_UNDER_METHOD
PARTIALLY_SETTLED_UNDER_METHOD
ATTEMPTED_UNDER_METHOD
HELD_IN_ESCROW_UNDER_METHOD
NOT_SETTLED_UNDER_METHOD
REVERSED_OR_REFUNDED_UNDER_METHOD
PARTIALLY_REVERSED_OR_REFUNDED_UNDER_METHOD
DISPUTED_EVIDENCE
CONFLICTING_EVIDENCE
INDETERMINATE
```

These are evaluator outputs only. They MUST NOT be serialized into an Agreement as authoritative mutable settlement state.
## 19. Core conclusion precedence

The reference evaluator applies this conflict-preserving precedence after evidence acceptance and causal checks:

```text
unsupported critical semantics,
parameterized required/excluded preference,
missing/wrong causal target                 -> INDETERMINATE
accepted dispute                            -> DISPUTED_EVIDENCE
claimed-complete settlement + failure       -> CONFLICTING_EVIDENCE
settlement + complete reversal/refund       -> REVERSED_OR_REFUNDED_UNDER_METHOD
settlement + partial reversal/refund        -> PARTIALLY_REVERSED_OR_REFUNDED_UNDER_METHOD
claimed-complete settlement/asset transfer  -> SETTLED_UNDER_METHOD
partial settlement/asset transfer           -> PARTIALLY_SETTLED_UNDER_METHOD
escrow hold without accepted release        -> HELD_IN_ESCROW_UNDER_METHOD
attempt                                     -> ATTEMPTED_UNDER_METHOD
failure                                     -> NOT_SETTLED_UNDER_METHOD
otherwise                                   -> INDETERMINATE
```

This precedence is an explicit property of the core evaluator, not a claim that every domain should use this policy.

## 20. Conflict preservation

Accepted settlement-completion and failure evidence may coexist. Different rails may publish inconsistent outcomes. Refunds, reversals, and disputes may coexist with completion evidence.

Core MUST NOT choose a winner by `occurred_at`, record order, storage order, resolver order, lexical identity, confirmation count without a rail profile, or source popularity.
## 21. Disputes

Marketplace reuses OLP `disputes` relationship records for settlement evidence challenges.

An accepted dispute targeting an accepted settlement event by exact RecordRef causes the core evaluator to report `DISPUTED_EVIDENCE` before making a positive settlement conclusion.

The disputed event is not deleted, revoked, or made false by the relationship. OLP `disputes` records disagreement; it does not adjudicate it.

## 22. Critical semantics

Before returning a positive settlement conclusion, the evaluator MUST understand every Marketplace content-extension URI marked `critical` on the Agreement and every accepted settlement event used by the method.

If any required critical semantic is not understood, the core result is `INDETERMINATE`.

A syntactically valid rail receipt or completion event with an unknown critical extension MUST NOT silently count as fully processed settlement evidence.

## 23. Duplicate evidence

Exact duplicate evidence MUST be identified by OLP Record Identity, not source, object identity, arrival order, or rail reference.
Repeating the same event MUST NOT inflate settlement, ignored-event, failure, escrow, reversal, refund, or transfer counts.

If the same exact event identity is supplied with conflicting attribution/authority/rail-verification context in one evaluation, the evaluator MUST fail with `DUPLICATE_EVIDENCE_CONTEXT_CONFLICT` rather than selecting one context.

## 24. Open-world behavior

Marketplace settlement evaluation is open-world.

Absence of settlement evidence from the supplied set does not prove non-payment. Absence of refund evidence does not prove no refund occurred. Absence of a reversal, dispute, or rail receipt does not prove that none exists elsewhere.

Missing causal targets remain indeterminate rather than becoming negative evidence.

Private, selectively disclosed, encrypted, or inaccessible settlement evidence MUST NOT be treated as nonexistent merely because one evaluator cannot access it.

## 25. Finality boundaries

Marketplace core defines no universal finality threshold.

Examples of external/profile-specific concepts include card authorization vs capture, bank pending vs posted, ledger confirmation depth, probabilistic blockchain finality, escrow-provider release rules, chargeback windows, and legal settlement finality.

A relying application may incorporate those facts into `rail_evidence_accepted`; the core evaluator itself does not establish them.

## 26. Privacy and selective disclosure

Settlement evidence may reveal counterparties, account or rail references, asset identifiers, payment amounts, refund activity, escrow behavior, or commercially sensitive terms.

Implementations SHOULD minimize disclosure and MAY use private, selectively disclosed, encrypted, or peer-to-peer evidence exchange consistent with OLP privacy semantics.

A rail reference is opaque evidence metadata. Core MUST NOT assume that it is globally public, globally unique, dereferenceable, or safe to disclose.

## 27. Security and resource limits

Settlement evaluators process untrusted evidence and MUST apply bounded resource limits.

The executable profile bounds supplied events, dispute relationships, understood-critical URIs, and rail-reference text. Implementations MUST likewise bound resolution, network access, payload size, recursive processing, and rail-specific verification work.

Untrusted MarketEvent content MUST NOT trigger implicit payment execution, wallet interaction, bank access, blockchain submission, network dereference, or code execution.

Identity, authority, rail verification, legal permission, compliance, settlement evaluation, fulfillment, ownership/title, and finality remain independent dimensions.

## 28. Method and rail plurality

Marketplace does not define one universal settlement evaluator, payment rail, currency system, asset registry, escrow provider, or finality rule.

Profiles MAY define rail-specific verification, confirmation, custody, conversion, quorum, threshold, timeout, fraud, chargeback, or finality semantics.

Different conforming methods MAY reach different conclusions over the same immutable evidence without creating a protocol contradiction.

A settlement evaluation method identifier MUST be an absolute URI when its output is intended to be portable or comparable. The reference evaluator in this repository implements only `core-evidence-v1` and MUST reject any other evaluator method identifier rather than apply core semantics under a misleading label. Such an unsupported identifier is reported as `UNSUPPORTED_SETTLEMENT_EVALUATION_METHOD`.

## 29. Attributable settlement conclusions

An evaluator MAY intentionally publish a settlement conclusion as an ordinary OLP Claim, Attestation, Observation, or Event with explicit evaluator method, input provenance, and coverage assumptions.

Publishing such a conclusion makes that evaluator's assertion portable. It does not transform the conclusion into universal payment truth, legal finality, title transfer, or fulfillment.

## 30. Executable conformance profile

The Milestone 7 helper implementation is non-normative. The normative contract is the observable behavior defined by this specification and the committed vectors.

The executable profile covers:

```text
exact Agreement + Commitment targeting
rail-neutral settlement event validation
attempt / completion / failure / reversal / refund
escrow hold / release and asset-transfer evidence
separate attribution / authority / rail-verification acceptance
SettlementPreference admissibility boundaries
partial and claimed-complete extent
causal reversal/refund/release targeting
multi-rail preservation without cross-rail arithmetic
OLP disputes relationships
critical-extension fail-closed behavior
Record-Identity deduplication
resource limits and opaque bounded rail references
```

The helper does not execute settlement and is not a rail adapter.

## 31. Executable vectors

The committed vector file is:

```text
conformance/vectors/settlement-interfaces-v1.json
```

The initial acceptance set contains 57 vectors: 32 positive/evaluation cases and 25 negative cases.

Vector processing is deterministic and uses OLP's implementation-neutral projection. The JSON file is not a mandatory Marketplace wire format.

## 32. Core invariant table

```text
settlement evidence           != objective transfer
rail reference                != universal transaction proof
settlement                    != fulfillment
settlement                    != acceptance
asset-transfer evidence       != ownership or legal title
claimed-complete settlement   != universal economic sufficiency
escrow evidence               != Marketplace custody
rail verification             != legal finality
missing evidence              != non-payment
refund / reversal             != deletion of history
multi-rail evidence           != canonical rail
ValueExpression               != universal arithmetic
```

## 33. Cross-scale examples

A software-service Agreement may record a card, bank, token, or credit settlement event for a payment Commitment while fulfillment remains evaluated independently from delivery and acceptance evidence.

A physical-goods exchange may record an escrow hold, later asset-transfer evidence, and a refund or reversal without asserting that Marketplace itself held custody or transferred legal title.

A barter Agreement may use semantic or quantity `ValueExpressionV1` values. Core preserves the evidence without inventing a fiat exchange rate or universal value comparison.

A large infrastructure project may combine bank transfers, milestone escrows, credits, guarantees, or asset transfers across multiple rails while retaining one immutable Agreement and independently attributable evidence streams.

## 34. Intentionally deferred

Milestone 7 does not define payment execution APIs, wallet protocols, banking APIs, blockchain transaction formats, universal currency registries, exchange rates, taxation, sanctions/compliance policy, chargeback adjudication, legal title transfer, universal escrow law, universal settlement arithmetic, or one authoritative finality clock.

Rail adapters and domain profiles may be defined later without changing the universal Marketplace record model.

## 35. Acceptance boundary

Milestone 7 is satisfied when independent processors can reproduce the committed settlement vector outcomes while preserving these properties:

1. no new universal first-class Marketplace record type is introduced;
2. every core settlement event targets an exact Agreement Commitment;
3. settlement/transfer evidence does not self-prove fulfillment, acceptance, ownership, legal title, legality, or finality;
4. partial settlement is representable without mutating Agreement commitments;
5. multiple rails remain representable without a mandatory rail or universal cross-rail arithmetic;
6. SettlementPreference constraints are enforced only where core semantics are understood, and parameterized semantics are not guessed;
7. attribution, authority, and rail verification remain separately evaluated;
8. reversals, refunds, failures, conflicts, and disputes remain visible without latest-wins selection;
9. missing/private/unresolved evidence is not converted into non-payment;
10. unknown critical semantics fail closed for positive conclusions;
11. duplicate evidence cannot inflate evaluator counts;
12. rail-specific finality remains external/profile-relative; and
13. Milestones 3–6 regression suites remain green.

---

**End of Marketplace Specification 0007 — Settlement Interfaces & Economic Exchange Semantics — Draft v0.1**
