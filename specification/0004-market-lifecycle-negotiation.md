# Marketplace — Lifecycle & Negotiation Semantics

**Status:** Draft v0.1
**Milestone:** 4 — Lifecycle & Negotiation Semantics
**Filename:** `specification/0004-market-lifecycle-negotiation.md`

---

## 1. Purpose

This specification defines additive lifecycle and negotiation semantics for Marketplace records established by Specifications 0002 and 0003.

It defines proposal and counterproposal graphs; acceptance and decline evidence; intent withdrawal; intrinsic expiration; agreement-formation evidence; agreement amendment; supersession conflicts; and evaluation boundaries for incomplete, concurrent, or contradictory evidence.

It does not introduce a fourth Marketplace record type, a mutable negotiation session, a canonical current proposal, a global clock, or a universal winner-selection algorithm.

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are interpreted as described by RFC 2119 and RFC 8174 when written in all capitals.

## 3. Dependency baseline

Marketplace Lifecycle & Negotiation v1 builds on Marketplace Specification 0003 and Open Layer Protocol record identity, detached proofs, evidence relationships, identity/authority evidence, and lifecycle evidence.

The Milestone 4 executable vectors use OLP reference implementation source commit `41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c` as a draft reproducibility baseline.

## 4. Core invariants

The following invariants are normative.

1. Lifecycle and negotiation history are additive immutable evidence.
2. Existing `MarketIntent`, `MarketAgreement`, and `MarketEvent` records MUST NOT be mutated to express later state.
3. Marketplace MUST NOT define a universal `current_state`, `accepted`, `withdrawn`, `expired`, `superseded`, `active`, or similar authoritative mutable field.
4. `response_to` expresses negotiation response context; it is not OLP `supersedes`.
5. Acceptance or decline evidence does not erase the proposal it concerns.
6. Withdrawal is distinct from decline, rejection, expiration, supersession, revocation, and agreement formation.
7. Natural expiration is derived from an Intent's authenticated validity bounds and does not require a lifecycle event.
8. A `MarketAgreement` record does not self-prove formation.
9. An amended Agreement is a new immutable Agreement plus explicit supersession evidence; it is never an in-place edit.
10. Conflicting or concurrent evidence MUST remain visible.
11. No timestamp-only, arrival-order, retrieval-order, or majority-vote rule selects a universal winner.
12. Incomplete evidence MUST remain distinguishable from invalid evidence.
13. Cryptographic validity, attribution, authority, chronology, legal effect, and application policy remain separate evaluation dimensions.
14. OLP lifecycle and relationship semantics remain authoritative where reused.

## 5. Semantic identifiers

This specification adds the following exact identifiers under the Marketplace v1 semantic namespace:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/profile/agreement-formation-v1
https://open-trust-layer.github.io/marketplace/semantics/v1/scope/market-negotiation
https://open-trust-layer.github.io/marketplace/semantics/v1/reason/intent-withdrawal
https://open-trust-layer.github.io/marketplace/semantics/v1/event/proposal-acceptance
https://open-trust-layer.github.io/marketplace/semantics/v1/event/proposal-decline
```

## 6. Negotiation graph

A Proposal remains exactly the `MarketIntentV1` specialization defined by Specification 0003 with the `proposal-v1` profile and non-empty `response_to`.

For every Proposal P and every RecordRef R in `P.content.response_to`, a processor MAY project:

```text
P --respondsTo--> R
```

This projected edge is a Marketplace negotiation view derived from P's authenticated content. It is not a separate OLP relationship record and MUST NOT be confused with `supersedes`.

If R resolves to a non-Proposal `MarketIntent`, P is classified as a Proposal relative to that resolved parent.

If at least one R resolves to another Proposal, P is classified as a Counterproposal for negotiation-view purposes.

A Proposal MAY respond to more than one prior MarketIntent when a profile permits multi-source negotiation context. `response_to` remains set-like under Specification 0003.

## 7. Missing response targets

An unresolved `response_to` reference does not make the Proposal malformed merely because the referenced record is not locally available.

If no resolved parent establishes Counterproposal status and at least one parent is unresolved, classification as first-level Proposal versus Counterproposal MUST remain indeterminate.

A negotiation evaluator MUST preserve the missing exact RecordRef and MUST report the supplied negotiation graph as incomplete.

It MUST NOT fabricate a missing parent, silently drop the edge, or classify the proposal history as complete.

When a referenced record is supplied, its OLP Record Identity MUST be recomputed and matched to the reference before its semantics are used.

## 8. Branching, cycles, and heads

Multiple Proposals MAY respond to the same prior Intent or Proposal. Such branching is valid evidence of competing negotiation paths.

Marketplace core does not select one branch as canonical, preferred, latest, accepted, or winning.

A local negotiation view SHOULD expose branching explicitly.

Because `response_to` contains exact content-addressed OLP RecordRefs inside identity-bearing Proposal content, ordinary construction naturally points from a newly created Proposal to already identified records. Under the collision-resistance assumptions of OLP Record Identity, mutually referential valid Proposals are not an ordinary constructible workflow shape.

Processors SHOULD nevertheless use bounded graph algorithms and detect repeated/cyclic anomalies defensively, because malformed inputs, identity collisions, implementation defects, or future extension profiles must not cause unbounded traversal. A detected anomaly MUST NOT produce a canonical head.

Marketplace v1 defines no universal `head`, `tip`, or current proposal even for a finite acyclic graph.

Applications MAY select a working head under explicit policy, but that result MUST remain an application decision with provenance to the evidence used.

## 9. Acceptance and decline evidence

Proposal response decisions are represented as ordinary immutable `MarketEventV1` records.

A Proposal acceptance event uses:

```text
event = https://open-trust-layer.github.io/marketplace/semantics/v1/event/proposal-acceptance
```

A Proposal decline event uses the corresponding `/event/proposal-decline` identifier.

In core-v1, each such event MUST reference exactly one Proposal in `related_records`.

The event `issuer` is the participant asserting acceptance or decline. It does not prove authority to bind another participant.

Acceptance evidence means only that an immutable attributed event asserts acceptance of the exact referenced Proposal.

Decline evidence means only that an immutable attributed event asserts decline of the exact referenced Proposal.

Marketplace core uses `proposal-decline` as the universal negative proposal-response event. A domain term such as `rejection` is not a separate core lifecycle primitive; a profile MAY map it to decline or define a narrower event when its semantics materially differ.

Neither event:

- creates a `MarketAgreement` by itself;
- proves all required parties assented;
- makes the Proposal universally current;
- deletes competing proposals; or
- establishes legal enforceability.

## 10. Intent withdrawal

Marketplace v1 reuses OLP generic lifecycle evidence for withdrawal rather than defining a new Marketplace status object.

A core Marketplace withdrawal of a `MarketIntentV1` MUST use an OLP `LifecycleStatusStatementV1` inside the ordinary OLP lifecycle-status record envelope defined by OLP, with:

```text
targetType      = record
target           = exact RecordRef of the MarketIntent
event            = retire
statusAuthority  = intent.content.issuer.principal
scope            = https://open-trust-layer.github.io/marketplace/semantics/v1/scope/market-negotiation
reason           = https://open-trust-layer.github.io/marketplace/semantics/v1/reason/intent-withdrawal
nextUpdate       = null
qualifiers       = {}
critical         = []
```

`effectiveAt` MAY be null or an OLP-conforming RFC 3339 value. `sequence` MAY be null or an OLP-conforming source-local sequence value.

A conforming Marketplace withdrawal processor MUST validate the underlying OLP lifecycle statement under OLP rules and MUST separately evaluate whether the named status authority and proof producer are acceptable for the Intent.

The `retire` event is used because Marketplace withdrawal means the issuer asserts that the Intent is no longer intended for new market use. It does not imply compromise or cryptographic invalidity.

Withdrawal evidence does not erase the Intent or its prior Proposal descendants. Historical proofs and references remain valid artifacts.

## 11. Expiration and temporal applicability

Natural expiration is not withdrawal.

For a `MarketIntentV1` with `content.validity`, Marketplace v1 interprets the temporal applicability interval as half-open:

```text
[not_before, not_after)
```

If `not_before` is absent there is no declared lower bound. If `not_after` is absent there is no declared upper bound.

At exactly `not_after`, the Intent is outside its declared temporal window.

A processor SHOULD report temporal applicability as a structured evaluation such as:

```text
BEFORE_DECLARED_WINDOW
WITHIN_DECLARED_WINDOW
AFTER_DECLARED_WINDOW
NO_DECLARED_WINDOW
```

Temporal applicability does not by itself prove that an Intent was published, withdrawn, accepted, legal, or available at a particular historical time.

## 12. Agreement formation profile

A `MarketAgreementV1` that requests the universal Marketplace v1 formation evaluation MUST include:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/profile/agreement-formation-v1
```

The profile requires evidence coverage for every distinct principal named in `agreement.content.parties`.

Coverage is evaluated over detached OLP proofs that bind to the exact Agreement record.

For a proof to cover a required principal in the universal profile, all of the following MUST hold:

1. the proof structurally conforms to OLP;
2. its record commitment matches the exact `MarketAgreementV1`;
3. its cryptographic signature verifies under supplied verification material;
4. its proof purpose is the OLP `assertion` purpose expected by this profile;
5. proof/version/cryptosuite/commitment processing is supported;
6. verification-method compatibility succeeds; and
7. the application accepts attribution of that verification method to the claimed principal for this formation evaluation.

Marketplace does not make step 7 automatic. Identity and authority evidence remain separate OLP/application inputs.

Proof expiration or later verification-method lifecycle evidence MUST remain a separate temporal/reliance dimension. It MUST NOT retroactively erase the historical existence or mathematical validity of an assent proof; historical reliance policy may require additional time/status evidence.

## 13. Formation result

When every required principal is covered, a processor MAY report:

```text
formation_evidence = EVIDENCE_SUFFICIENT_FOR_PROFILE
```

If one or more required principals lack accepted coverage, the result MUST remain incomplete rather than silently assuming assent.

A conforming processor SHOULD expose at least:

```text
required_principals
covered_principals
missing_principals
proof/verification observations
formation_evidence
```

A successful formation-evidence result does not establish universal truth, legal enforceability, capacity, absence of duress, regulatory compliance, settlement, fulfillment, or acceptance by a court or jurisdiction.

## 14. Duplicate, extra, and conflicting assent evidence

Multiple proofs MAY cover the same principal. Marketplace core does not increase evidentiary weight by proof count.

Proofs attributed to principals not required by the Agreement MAY be retained as extraneous evidence but do not satisfy a missing required party.

Conflicting identity, authority, verification-method lifecycle, or proof-policy evidence MUST remain visible to the application. A formation evaluator MUST NOT hide such conflicts merely to produce a Boolean success result.

A cryptographically valid proof whose purpose, record binding, verification method, attribution, or required principal does not match MUST NOT count toward universal formation-profile coverage.

## 15. Agreement amendment

An Agreement amendment MUST create a new immutable `MarketAgreementV1` with its own OLP Record Identity.

The new Agreement MUST NOT replace or mutate the bytes or identity of the previous Agreement.

A core amendment relationship MUST be an ordinary OLP relationship record with:

```text
relationType = supersedes
subject      = RecordRef(amended agreement)
objects      = [RecordRef(previous agreement)]
```

The core amendment profile requires exactly one previous Agreement target per amendment relationship. More complex consolidation/split semantics MAY be defined by later profiles.

A valid `supersedes` relationship does not prove that the amendment is effective, authoritative, or legally binding. It records attributable supersession evidence.

An amended Agreement that requires formation evidence MUST be evaluated as a new Agreement. Assent proofs over the previous Agreement do not automatically cover the amended identity.

## 16. Multiple successors

A prior Agreement MAY have multiple records that claim to supersede it.

Marketplace core MUST preserve every conforming successor relationship supplied to the evaluator.

If more than one distinct successor is present, the evaluator SHOULD report a `MULTIPLE_SUCCESSORS` conflict and MUST NOT select a canonical successor.

The existence of multiple successors does not mutate or invalidate the prior Agreement.

## 17. Correction and dispute are not amendment

OLP `corrects`, `disputes`, and `supersedes` have distinct semantics.

A Marketplace amendment MUST NOT be represented merely by relabeling a `corrects` or `disputes` relationship as though it were `supersedes`.

A correction asserts that a prior statement was erroneous or needs correction. A dispute asserts that a statement is contested. Neither relationship automatically forms a replacement Agreement.

## 18. Acceptance and withdrawal races

An acceptance event and withdrawal lifecycle statement concerning the same Proposal can coexist.

The presence of both does not establish which event should control a later business or legal decision.

Without accepted evidence that establishes relevant ordering, authority, and policy consequences, a conforming Marketplace evaluator MUST preserve both and report chronology as not established.

It MUST NOT use:

- local arrival order;
- storage insertion order;
- resolver response order;
- largest unauthenticated timestamp;
- record identity lexical order; or
- majority count

as a universal winner-selection rule.

A local application MAY resolve the race under an explicit policy and accepted temporal/authority evidence, but MUST retain provenance to both underlying artifacts.

## 19. Lifecycle sequence conflicts

Where Marketplace withdrawal uses OLP source-local `sequence`, OLP sequence semantics apply unchanged.

Two materially incompatible lifecycle statements from the same accepted authority for the same target, scope, and sequence MUST remain a conflict.

Marketplace MUST NOT silently choose one sequence-conflicting lifecycle statement merely because one was observed later by the local implementation.

## 20. Negotiation history construction

A portable negotiation history is a contextual view assembled from supplied or explicitly resolved immutable evidence.

It MAY include:

- `MarketIntentV1` records;
- Proposal `response_to` references;
- Proposal acceptance/decline `MarketEventV1` records;
- OLP lifecycle records concerning Intents;
- `MarketAgreementV1` records;
- detached proofs over those records;
- OLP relationship records such as `supersedes`, `corrects`, and `disputes`; and
- identity/authority evidence required by the relying application.

A history view MUST retain exact OLP identities for the artifacts on which it relies.

A history view is not itself a protocol-global authoritative object unless separately published as attributable evidence under an appropriate profile.

## 21. Completeness

Marketplace negotiation evidence is open-world by default.

A locally supplied graph MUST NOT be called globally complete merely because every locally known reference resolves.

`COMPLETE_FOR_SUPPLIED_RESPONSE_GRAPH` means only that every `response_to` reference encountered in the supplied finite Marketplace negotiation view resolved within that input set.

It does not prove that no additional Proposals, Events, lifecycle statements, proofs, or relationship records exist elsewhere.

## 22. No silent current-state synthesis

A conforming core processor MAY calculate contextual views for user interfaces or automation, but it MUST NOT expose a derived mutable state as though it were an immutable protocol fact.

Examples of prohibited universal conclusions include:

```text
currentProposal
currentAgreement
accepted = true
withdrawn = true
expired = true
amendmentIsEffective = true
winner = proposalX
```

unless the result is explicitly identified as an application-policy evaluation over named evidence.

## 23. Security considerations

Implementations MUST validate exact record identities before following negotiation references.

They MUST impose resource limits on graph traversal, including proposal depth, node count, edge count, recursion, and resolver activity.

Generic lifecycle/negotiation evaluation MUST NOT automatically dereference arbitrary untrusted URLs or network locations.

Applications SHOULD distinguish malformed evidence, unresolved evidence, unsupported semantics, invalid proofs, rejected attribution, conflicts, and policy rejection.

A malicious participant can create syntactically valid records naming other principals. Therefore names inside Intent, Event, Agreement, lifecycle, or relationship content MUST NOT be treated as self-authenticating authority.

## 24. Privacy considerations

Negotiation graphs can reveal commercial strategy, counterparty identities, timing, pricing, bargaining history, declined offers, and relationship structure.

Applications SHOULD minimize unnecessary disclosure and SHOULD avoid publishing complete negotiation histories when narrower evidence is sufficient.

Private transport or selective-disclosure mechanisms MAY be used without changing Marketplace record identity semantics.

## 25. Conformance surface

Milestone 4 provides executable vectors in:

```text
conformance/vectors/lifecycle-negotiation-v1.json
```

The vector file is an implementation-neutral conformance projection, not a Marketplace wire format.

The acceptance set covers at least:

- linear Proposal/counterproposal history;
- branching proposals with no canonical head;
- unresolved response targets reported as incomplete;
- Proposal acceptance and decline events;
- OLP `retire`-based withdrawal with Marketplace scope/reason;
- half-open Intent validity boundaries;
- complete and incomplete Agreement formation evidence;
- wrong-purpose assent proof rejection;
- Agreement amendment via OLP `supersedes`;
- multiple successor conflict preservation;
- OLP lifecycle sequence conflict preservation;
- acceptance/withdrawal race preservation; and
- malformed or semantically mismatched negative cases.

## 26. Processing result boundaries

Conforming processors SHOULD return structured results rather than one Boolean.

Useful result dimensions include:

```text
record_conformance
reference_resolution
negotiation_completeness
branching
cycles
proposal_response_evidence
lifecycle_evidence
proof_validity
principal_attribution
formation_evidence
supersession_conflict
chronology
local_policy_decision
```

A processor MUST NOT collapse an unevaluated dimension into success.

## 27. Foundational separations

The following distinctions are normative design constraints:

```text
response_to             != supersedes
proposal                != agreement
acceptance event        != agreement formation
acceptance              != legal enforceability
decline                 != withdrawal
withdrawal              != expiration
withdrawal              != revocation-by-default
expiration              != rejection
supersedes              != corrects
corrects                != disputes
amendment record        != mutation
valid proof             != accepted attribution
accepted attribution    != legal authority
sufficient formation    != universal truth
conflict                != automatic invalidity
missing evidence        != negative evidence
```

## 28. Implementation guidance

A Marketplace implementation SHOULD keep lifecycle evaluation, proof verification, authority resolution, graph construction, and business-policy decisions as separate components.

Deterministic offline evaluation from supplied evidence is a first-class requirement. Network collection MAY be layered on top through explicit resolvers.

Implementations SHOULD preserve unknown non-critical OLP evidence rather than deleting it merely because the local application does not use it.

## 29. Deferred work

This milestone does not standardize:

- global discovery or federation;
- matching/ranking algorithms;
- negotiation transport sessions or chat protocols;
- auction-specific bidding rules;
- escrow or settlement state machines;
- fulfillment evaluation;
- dispute adjudication;
- legal contract formation rules for any jurisdiction;
- authoritative wall-clock services;
- universal authority policies; or
- user-interface status labels.

Those concerns may be defined by later Marketplace profiles while preserving the additive evidence model established here.

## 30. Milestone 4 acceptance boundary

Milestone 4 is complete when this specification, executable vectors, validator/generator tooling, README/conformance documentation, and regression gates are merged to `main` with all acceptance checks green.
