# Marketplace — Object Model and Representation Boundaries

**Status:** Draft v0.1
**Milestone:** 2 — Marketplace Object Model & Representation
**Filename:** `specification/0002-market-object-model.md`

---

## 1. Purpose

This specification defines the conceptual object model for the Marketplace semantic layer built on Open Layer Protocol (OLP).

It determines:

- which marketplace concepts are represented as first-class immutable OLP Records;
- which concepts are reusable embedded structures;
- which concepts remain derived, contextual, or application-specific;
- how marketplace objects relate to OLP Records, Proofs, relationships, lifecycle evidence, Participants, Subjects, and external resources; and
- which representation decisions are intentionally deferred to later specifications.

The object model is intentionally small.

The Marketplace should standardize portable economic coordination evidence, not every business concept, UI object, legal conclusion, market score, or operational database field.

---

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are to be interpreted as described by RFC 2119 and RFC 8174 when written in all capitals.

This document defines conceptual object boundaries and semantic invariants. It does not yet freeze a final Marketplace wire serialization, transport API, persistence schema, or domain profile.

---

## 3. Normative dependencies and inheritance

Marketplace objects defined here are built on OLP and inherit OLP semantics.

In particular:

- OLP Specification 0001 supplies foundational vocabulary such as Participant, Subject, Claim, Evidence, Event, Outcome, Record, History, and Context;
- OLP Specification 0002 defines one universal immutable Record envelope and the distinction between first-class records, reusable structures, and derived concepts;
- OLP Specification 0003 defines deterministic Record identity, the abstract OLP value model, canonical identity encoding, semantic identifiers, references, and immutable identity-bearing content;
- OLP Specification 0004 defines detached cryptographic proofs and verification semantics;
- OLP Specification 0005 defines immutable evidence relationships and evidence graphs;
- OLP Specification 0006 defines identity and authority evidence; and
- OLP Specification 0007 defines additive lifecycle evidence and status evaluation boundaries.

Marketplace specifications MUST NOT silently redefine those semantics incompatibly.

The following OLP separations remain authoritative:

```text
proof validity        != truth
identity              != trust
identity              != authority
authority evidence    != final authorization decision
status evidence       != historical mutation
resolution            != verification
```

Marketplace adds corresponding separations:

```text
subject representation      != ownership
listing                     != transfer right
intent                      != agreement
agreement                   != legal enforceability
agreement                   != settlement
settlement                  != fulfillment
fulfillment evidence        != acceptance
price                       != value
match                       != compatibility proof
policy decision             != protocol truth
```

---

## 4. Core design rule: no second record envelope

Marketplace MUST NOT define a second identity-bearing record envelope.

Every first-class Marketplace evidence object defined as a record is an ordinary OLP `RecordV1` whose `type`, `content`, optional `profiles`, optional semantic bindings, optional relationships, and optional extensions conform to the applicable Marketplace profile.

Conceptually:

```text
OLP RecordV1
├── envelope_version
├── type
├── content                  <- Marketplace profile content
├── semantic_bindings?
├── profiles?
├── relationships?
└── extensions?
```

OLP remains responsible for:

- Record identity;
- canonical identity encoding;
- immutable identity-bearing content;
- detached Proofs;
- verification;
- Evidence Relationships;
- status/lifecycle evidence;
- resolution semantics; and
- evidence exchange/bundling.

Marketplace defines economic-coordination meaning inside those boundaries.

---

## 5. Criterion for first-class Marketplace records

A Marketplace concept SHOULD become a first-class record profile only when at least one of the following is materially useful across implementations:

1. **Independent identity** — another object needs to reference the exact semantic object unambiguously.
2. **Independent proof** — participants need to cryptographically attribute or countersign the object itself.
3. **Independent lifecycle** — withdrawal, supersession, correction, dispute, expiration-related evidence, or other lifecycle evidence must target the object directly.
4. **Independent dispute** — a participant must be able to challenge the object without challenging a larger unrelated container.
5. **Independent portability** — the object needs to move between implementations without requiring platform-local reconstruction.
6. **Cross-party coordination** — multiple participants need to bind, respond to, or rely on the exact same immutable object.
7. **Independent provenance** — the origin, derivation, or evidentiary history of the object matters on its own.

A concept SHOULD remain embedded when it is normally meaningful only as part of a containing record and does not require independent identity by default.

A concept MUST remain derived/application-specific when its meaning is an evaluator judgment, computed view, policy result, ranking, mutable cache state, or other non-portable conclusion unless a participant explicitly makes that conclusion as a separate OLP Claim or other evidence record.

---

## 6. Marketplace object taxonomy

Milestone 2 defines three core first-class Marketplace record profiles:

    MarketIntent
    MarketAgreement
    MarketEvent

Proposal, Offer, Request, Bid, Ask, and similar negotiation or direction forms are specializations/profiles of MarketIntent, not separate universal record categories.

The following are reusable embedded structures by default:

```text
SubjectBinding
ActionDescriptor
PartyBinding
Terms
Constraint
Commitment
ValueExpression
Quantity
TemporalCondition
LocationCondition
EvidenceRequirement
SettlementPreference
AcceptanceCriterion
ProfileBinding
```

The following remain derived, contextual, or application-specific by default:

```text
Listing
Match
MarketView
CurrentAvailability
CurrentIntentStatus
CurrentAgreementStatus
FulfillmentConclusion
Trust
Reputation
RiskScore
Ranking
Recommendation
PriceIndex
FairValue
PolicyDecision
LegalConclusion
OwnershipConclusion
AuthoritySufficiency
```

This taxonomy does not prohibit an application or participant from recording an attributable claim about a derived concept using ordinary OLP evidence.

It prohibits the Marketplace core from pretending that the derived conclusion is an objective protocol state.

---

## 7. First-class record profile: MarketIntent

A **MarketIntent** is a first-class immutable OLP Record representing an attributable expression of desired, proposed, available, requested, or conditional coordination concerning one or more Subjects.

MarketIntent is first-class because it commonly requires:

- stable identity for discovery and response;
- detached proof by or on behalf of its expressing Participant;
- direct references from Proposals and Agreements;
- withdrawal or supersession evidence;
- correction and dispute; and
- portability across marketplace implementations.

Conceptually:

```text
MarketIntentContentV1 = {
    "issuer": PartyBinding,
    "subjects": [SubjectBinding, ...],
    "action": ActionDescriptor,
    "terms": Terms,
    "constraints"?: [Constraint, ...],
    "evidence_requirements"?: [EvidenceRequirement, ...],
    "validity"?: TemporalCondition,
    "profiles"?: [ProfileBinding, ...]
}
```

The exact field names and canonical Marketplace representation are deferred to a later representation specification.

### 7.1 Intent identity is not participant identity

The identity of a MarketIntent is its OLP Record Identity.

That identity does not establish the real-world identity, legal identity, authority, ownership, or trustworthiness of the issuer.

### 7.2 Intent does not contain mutable marketplace state

A MarketIntent MUST NOT rely on mutable identity-bearing fields such as:

```text
is_active
is_withdrawn
is_matched
is_sold
is_completed
current_status
view_count
ranking_score
```

Later state is represented through additional evidence or derived application state.

### 7.3 Intent direction remains profile-defined

`Offer`, `Request`, `Bid`, `Ask`, `Demand`, `Supply`, and similar terms MAY be profiles or specializations of MarketIntent.

Marketplace core MUST NOT require one closed direction taxonomy when the generic Intent grammar is sufficient.

---

## 8. MarketIntent specialization: Proposal

A **Proposal** is a specialized MarketIntent that responds to one or more prior MarketIntents and presents specific Terms for possible agreement.

Proposal does not require a separate universal record category. It uses the MarketIntent record profile plus profile semantics and explicit references or OLP relationship evidence identifying the records to which it responds.

This choice preserves the Milestone 1 rule that negotiation direction is contextual and keeps the universal object model small.

A Proposal may still have all properties of a first-class immutable record because the underlying MarketIntent is itself a first-class OLP Record: stable identity, detached proof, lifecycle evidence, dispute, supersession, and portability.

Conceptually, a Proposal specialization adds semantics such as:

`	ext
in_response_to: [OLPRecordRef, ...]
proposal_profile: SemanticIdentifier
`

while retaining the MarketIntent content model for issuer, subjects, action, terms, constraints, evidence requirements, validity, and profiles.

### 8.1 Proposal revision creates a new MarketIntent record

Changing identity-bearing Proposal Terms creates a different OLP Record Identity.

A later Proposal MUST NOT silently overwrite an earlier Proposal. Negotiation history is additive.

### 8.2 Proposal does not equal acceptance

A Proposal does not become a MarketAgreement merely because another participant publishes a compatible Proposal or because a matching engine associates them.

Agreement formation requires explicit evidence according to the applicable agreement profile.

---

## 9. First-class record profile: MarketAgreement

A **MarketAgreement** is a first-class immutable OLP Record that identifies the Participants, Subjects, Actions, and exact Terms to which the record asserts that identified parties assented according to a defined Marketplace agreement profile.

MarketAgreement is first-class because it requires:

- stable identity of the assented semantic object;
- exact binding of Terms;
- detached proofs or other assent evidence;
- direct reference by later Events, disputes, amendments, settlement evidence, and lifecycle evidence; and
- portability independent of the application that mediated formation.

Conceptually:

```text
MarketAgreementContentV1 = {
    "parties": [PartyBinding, ...],
    "subjects": [SubjectBinding, ...],
    "action": ActionDescriptor | [ActionDescriptor, ...],
    "terms": Terms,
    "commitments": [Commitment, ...],
    "source_records"?: [OLPRecordRef, ...],
    "evidence_requirements"?: [EvidenceRequirement, ...],
    "profiles": [ProfileBinding, ...]
}
```

### 9.1 Exact Terms binding

A MarketAgreement MUST identify the exact identity-bearing Terms to which assent evidence applies.

Later modification of Terms MUST NOT be confused with the original Agreement.

An amendment SHOULD create a new MarketAgreement or another immutable record linked through explicit relationship evidence, depending on the amendment profile.

### 9.2 Agreement is evidence, not universal contract law

A MarketAgreement MUST NOT be interpreted by Marketplace core as automatically establishing:

- legal enforceability;
- ownership;
- transfer of title;
- regulatory compliance;
- capacity to contract;
- authority sufficiency;
- settlement completion;
- fulfillment;
- acceptance; or
- absence of dispute.

Applications MAY use a MarketAgreement as evidence when making those contextual decisions.

### 9.3 Proofs remain detached

Participant signatures or other OLP proofs MUST NOT be embedded into the Agreement's identity-bearing OLP Record envelope merely for convenience.

They remain detached OLP Proofs.

An agreement profile MAY require a defined set of proofs or countersignature relationships before an application classifies formation as sufficient.

That sufficiency conclusion is still contextual to the selected profile and policy.

---

## 10. First-class record profile: MarketEvent

A **MarketEvent** is a first-class immutable OLP Record representing an asserted occurrence or state transition in marketplace coordination.

MarketEvent is a Marketplace specialization/profile of the OLP Event concept, not a replacement Event model.

MarketEvent may represent or specialize events such as:

```text
delivery
handoff
work submission
service interval
inspection
measurement
acceptance assertion
rejection assertion
settlement attempt
settlement completion
settlement reversal
refund
cancellation
completion assertion
failure assertion
```

MarketEvent is first-class when the occurrence requires independent identity, proof, provenance, dispute, cross-party reference, or later lifecycle/evidence relationships.

Conceptually:

```text
MarketEventContentV1 = {
    "event_type": SemanticIdentifier,
    "actors"?: [PartyBinding, ...],
    "subjects"?: [SubjectBinding, ...],
    "agreement"?: OLPRecordRef,
    "commitment_refs"?: [CommitmentReference, ...],
    "occurred_at"?: TemporalCondition,
    "outcome"?: Outcome,
    "evidence_refs"?: [EvidenceRef, ...],
    "profiles"?: [ProfileBinding, ...]
}
```

### 10.1 Event assertion is not objective occurrence

A cryptographically attributable MarketEvent establishes evidence that a participant or process asserted the event content.

It does not automatically establish that the represented event objectively occurred exactly as asserted.

### 10.2 Fulfillment and acceptance remain distinguishable

A delivery Event does not automatically establish acceptance.

A settlement Event does not automatically establish fulfillment.

An acceptance assertion does not automatically eliminate a later dispute.

Applications evaluate relevant evidence according to policy and profile.

---

## 11. Reusable embedded structure: SubjectBinding

A **SubjectBinding** identifies or describes a Subject in a Marketplace record without asserting ownership, control, authority, authenticity, or legal status.

A SubjectBinding MAY use:

- an OLP Record reference;
- an OLP-compatible EntityReference or Reference;
- a globally unambiguous external identifier;
- a profile-defined structured subject descriptor; or
- a reference to a specification describing something not yet created.

A SubjectBinding SHOULD be elevated into an independently identified OLP Record only when the subject description itself requires independent proof, lifecycle, dispute, or cross-record reference.

Subject scale is irrelevant to this rule.

A software bug, parcel, building, asteroid, or galaxy uses the same binding principle.

---

## 12. Reusable embedded structure: ActionDescriptor

An **ActionDescriptor** identifies the kind of coordination proposed, requested, or agreed.

It SHOULD contain a globally unambiguous semantic identifier plus any profile-defined parameters necessary to interpret the Action.

Examples include transfer, provide, perform, repair, transport, license, reserve, fund, insure, inspect, measure, observe, compute, and exchange.

The identifier MUST NOT by itself create universal legal meaning.

Action semantics belong to profiles where interoperability requires precision.

---

## 13. Reusable embedded structure: PartyBinding

A **PartyBinding** associates a Participant reference with one or more contextual roles in the containing Marketplace object.

Conceptually:

```text
PartyBinding = {
    "participant": EntityReference,
    "roles": [SemanticIdentifier, ...]
}
```

PartyBinding does not establish:

- verified identity;
- organizational authority;
- legal capacity;
- beneficial ownership;
- agency authority; or
- trustworthiness.

Those properties require separate evidence and evaluation where relevant.

---

## 14. Reusable embedded structure: Terms

**Terms** are the structured identity-bearing conditions proposed or assented to within a MarketIntent or MarketAgreement.

Terms MAY include profile-defined components for:

- scope;
- quantity;
- quality;
- timing;
- location;
- value or consideration;
- settlement preferences;
- delivery;
- acceptance criteria;
- warranties;
- dependencies;
- evidence requirements;
- privacy conditions;
- cancellation;
- dispute procedures;
- legal references; and
- performance metrics.

Terms SHOULD remain embedded by default because their meaning normally depends on the containing Intent, Proposal, or Agreement.

A reusable Terms package MAY become an independently identified OLP Record when independent reference, proof, versioning, or reuse materially requires it.

Such elevation MUST preserve exact semantic binding between the container and the referenced Terms Record.

---

## 15. Reusable embedded structure: Constraint

A **Constraint** limits what a Participant considers acceptable for coordination, matching, formation, disclosure, execution, or fulfillment.

A Constraint MUST distinguish semantics such as:

```text
mandatory
preferred
negotiable
informational
```

when that distinction affects behavior.

A matching engine MUST NOT silently reinterpret a mandatory Constraint as a preference.

Constraint evaluation is normally application behavior and does not become protocol truth merely because an engine returns a result.

---

## 16. Reusable embedded structure: Commitment

A **Commitment** describes an attributable undertaking expected under a Proposal or Agreement.

Examples include commitments to:

- deliver a Subject;
- perform work;
- make payment;
- provide resource capacity;
- disclose specified evidence;
- maintain a service level; or
- respond by a deadline.

A Commitment SHOULD be embedded in the exact MarketIntent (including a Proposal specialization) or MarketAgreement whose Terms give it meaning.

Each Commitment SHOULD have a container-local stable identifier when later MarketEvents or fulfillment evidence need to identify one commitment within the containing immutable record.

If a Commitment itself requires independent proof, transfer, delegation, lifecycle, or dispute beyond the containing Agreement, a later profile MAY define an independent OLP Record representation.

Marketplace core does not require every clause to become a separate record.

---

## 17. Reusable embedded structures for value, quantity, time, location, and evidence

### 17.1 ValueExpression

A **ValueExpression** represents attributed consideration or another value-related term.

It MAY express money, barter, credits, units of work, reciprocal obligations, no monetary consideration, or profile-defined value forms.

A ValueExpression is not universal value.

### 17.2 Quantity

A **Quantity** represents an amount using profile-defined units and precision rules.

Marketplace representation MUST avoid ambiguous floating-point identity semantics and SHOULD align with OLP deterministic value-model requirements.

### 17.3 TemporalCondition

A **TemporalCondition** expresses identity-bearing time-related Terms such as earliest start, latest completion, validity window, or asserted event time.

A TemporalCondition does not create a universal clock or universal "latest wins" rule.

### 17.4 LocationCondition

A **LocationCondition** represents a location-related term using an established open geospatial or address standard where practical.

Marketplace core SHOULD NOT invent a universal geospatial system when an established standard suffices.

### 17.5 EvidenceRequirement

An **EvidenceRequirement** describes evidence a Participant or profile requires for matching, formation, execution, acceptance, or another decision.

Meeting an EvidenceRequirement is an evaluator conclusion.

The requirement itself does not make referenced evidence sufficient or trustworthy.

### 17.6 SettlementPreference

A **SettlementPreference** identifies acceptable or preferred settlement mechanisms or constraints.

It does not make the Marketplace itself a payment processor or settlement system.

### 17.7 AcceptanceCriterion

An **AcceptanceCriterion** describes conditions relevant to acceptance evaluation.

The existence of a criterion does not make its satisfaction objectively true.

Evidence and policy determine evaluation.

---

## 18. Derived concept: Listing

A **Listing** remains a discovery/presentation concept rather than a universal first-class record type.

A Listing may be:

- an indexed projection of a MarketIntent;
- a UI presentation combining several Intents and evidence objects;
- a cached search document;
- a federated publication envelope; or
- a selective-disclosure view.

Different implementations MAY produce different Listings from the same underlying MarketIntent.

A Listing MUST NOT be treated as the identity or source of truth of the MarketIntent merely because a platform displays it.

If publication itself needs portable evidence, an application MAY record a separate OLP Event or Claim about publication.

---

## 19. Derived concept: Match

A **Match** remains an application-derived association between Intents or other market data.

A Match is not a universal Marketplace record by default because it depends on:

- a matching algorithm;
- selected inputs;
- policy;
- available evidence;
- preferences;
- context; and
- potentially private data.

Two conforming implementations MAY produce different Matches.

If a Participant or service needs to attest that a specific matching process produced a specific result, that result MAY be represented as an ordinary OLP Claim, Attestation, or Event with provenance identifying the method and inputs.

The attestation remains evidence about the match result, not protocol-level proof that the counterparties are actually compatible.

---

## 20. Derived concept: MarketView

A **MarketView** remains an application-specific projection over Intents, evidence, policies, indexes, and derived data.

There is no canonical global MarketView.

Search results, category pages, recommendation feeds, geographic views, agent-specific opportunity sets, and moderation-filtered views are examples of MarketViews.

Marketplace core MUST NOT define one authoritative ordering or visibility set.

---

## 21. Derived concepts: trust, reputation, risk, ranking, and value

The following are evaluator conclusions rather than universal Marketplace state:

```text
trust
reputation
risk score
fraud score
ranking
recommendation
fair value
price index
market quality score
counterparty score
```

Marketplace core MUST NOT define one universal value for any of them.

Applications MAY compute them from portable evidence and MAY publish attributable claims about those computations.

Published claims remain evidence and MUST identify enough method/context information to avoid silently masquerading a local judgment as universal fact.

---

## 22. Derived concept: PolicyDecision

A **PolicyDecision** remains application-specific.

Examples include:

```text
allow
reject
hide
quarantine
require additional evidence
require human review
permit autonomous execution
block settlement
```

A PolicyDecision MAY be logged or attested as evidence when auditability requires it.

Marketplace core MUST NOT turn one implementation's PolicyDecision into universal permission or prohibition.

---

## 23. Derived concept: current status

The current status of an Intent, Proposal, Agreement, Commitment, or MarketEvent is not a mutable protocol field and not a universal function.

Examples of tempting but invalid universal fields include:

```text
ACTIVE
MATCHED
ACCEPTED
WITHDRAWN
COMPLETED
DISPUTED
SETTLED
EXPIRED
```

Applications derive current status from some combination of:

- the immutable target record;
- OLP lifecycle evidence;
- relationship evidence;
- relevant MarketEvents;
- accepted authority evidence;
- time/context;
- completeness/freshness assumptions; and
- local policy.

Absence of withdrawal or revocation evidence MUST NOT automatically prove that an Intent remains active unless a selected profile provides sufficient semantics for that conclusion.

---

## 24. Marketplace relationships use OLP relationship records

Marketplace MUST use OLP evidence-relationship records when a relationship itself carries evidentiary meaning.

Marketplace MUST NOT create unsigned mutable graph edges as a substitute for portable relationship evidence.

Examples of relationships that MAY be represented through OLP relationship records include:

```text
Proposal responds to Intent
Proposal supersedes earlier Proposal
Agreement derives from Proposal(s)
Agreement amends earlier Agreement
Event relates to Agreement
Evidence disputes Agreement or Event
Evidence corrects earlier evidence
Record supersedes earlier record
```

Where OLP already defines a suitable core relationship such as `references`, `derivesFrom`, `supersedes`, `corrects`, or `disputes`, Marketplace SHOULD reuse it rather than invent a synonym.

Marketplace-specific relationship identifiers SHOULD be added only when existing OLP semantics are insufficient.

No Marketplace relationship implies automatic transitivity, trust propagation, legal effect, or truth unless a later specification explicitly defines a narrower inference.

---

## 25. Marketplace lifecycle uses additive OLP lifecycle evidence

Withdrawal, suspension, resumption, retirement, revocation, deprecation, compromise, and other applicable lifecycle changes MUST use additive evidence consistent with OLP lifecycle semantics.

Historical MarketIntent, MarketAgreement, and MarketEvent records remain immutable.

For example:

```text
Intent I1
  |
  +-- lifecycle evidence: suspend
  +-- lifecycle evidence: resume
  +-- lifecycle evidence: retire
```

I1 never becomes a different record merely because later evidence changes whether an application considers it actionable.

Marketplace-specific lifecycle events not covered by OLP core MAY be defined by later profiles, but MUST preserve additive history and MUST NOT silently introduce one global status authority.

---

## 26. Subject descriptions and ownership evidence remain separate

A Marketplace record MAY describe or reference any Subject that the applicable profile can identify.

The record MUST NOT infer ownership or transfer authority from the SubjectBinding itself.

Claims such as:

```text
"Participant A owns Subject X"
"Participant A may license right Y"
"Participant A is authorized to sell Subject X"
```

require separate evidence where relevant.

That evidence may use OLP identity/authority records, Claims, Attestations, external registry evidence, legal evidence, or domain-specific profiles.

Marketplace object validity and authority sufficiency are separate evaluations.

This rule is essential to subject-scale neutrality: the same object model can reference a bicycle, a company, an asteroid, or a galaxy without pretending that all such subjects are ownable or transferable in the same way.

---

## 27. External resources and established standards

Marketplace profiles SHOULD reuse established open standards when they adequately represent domain concepts.

Examples may include standards for:

- product/service semantics;
- addresses and geospatial coordinates;
- units and quantities;
- currencies and monetary values;
- invoices and orders;
- procurement;
- logistics;
- legal documents;
- identity credentials;
- payment instructions; and
- activity publication/federation.

Referencing an external standard does not make every external assertion part of OLP identity or proof semantics.

Profiles MUST define what data is identity-bearing, what is externally referenced, and what validation is required.

---

## 28. Profile composition

A **Marketplace Profile** may specialize:

- MarketIntent;
- MarketAgreement;
- MarketEvent;
- Actions;
- Terms;
- Constraints;
- Commitments;
- evidence requirements;
- lifecycle rules;
- agreement-formation requirements; and
- interoperability mappings.

Profiles MUST NOT silently redefine foundational semantics from Specifications 0001 or 0002.

Profiles SHOULD compose rather than duplicate concepts when multiple domains share the same underlying semantics.

For example, a logistics profile and a physical-goods profile may both use the same settlement/value structures while defining different Actions, fulfillment evidence, and acceptance criteria.

---

## 29. Extension model

Marketplace extensions MUST follow OLP semantic-identifier and extension rules.

Third-party semantic identifiers MUST be globally unambiguous according to OLP requirements unless a later Marketplace registry defines another collision-resistant mechanism.

Security- or interoperability-critical extension semantics require explicit criticality behavior in the profile that defines them.

Unknown non-critical extensions MAY be preserved without being understood where OLP rules permit.

Unknown critical semantics MUST NOT be silently ignored when doing so could change interpretation of the object.

---

## 30. Object identity and equality

Two Marketplace records are the same identity-bearing evidence object only when they have the same OLP Record Identity under the applicable OLP specification.

Application-level concepts such as:

```text
same listing
same opportunity
same transaction
same product
same negotiation
same agreement family
```

are not automatically equivalent to OLP Record identity.

Applications MAY group multiple immutable records into one higher-level conceptual object or history, but the grouping rule MUST NOT erase the identities of the underlying records.

---

## 31. Local metadata is not Marketplace evidence by default

The following are examples of local metadata that MUST NOT become identity-bearing Marketplace semantics accidentally:

```text
database primary key
cache timestamp
search index score
UI sort order
favorite flag
read/unread state
view counter
internal moderation queue ID
local ingestion time
retry count
HTTP request ID
local synchronization cursor
```

If such information needs portable evidentiary meaning, it must be intentionally represented as an appropriate OLP Record or external evidence object rather than leaking in from infrastructure state.

---

## 32. Privacy and disclosure boundary

First-class record status does not imply public visibility.

A MarketIntent, MarketAgreement, or MarketEvent MAY be private, selectively disclosed, peer-to-peer, encrypted at transport/storage layers, or disclosed only to selected Participants according to later profiles.

Implementations MUST NOT assume that all Marketplace records belong in a globally enumerable public index.

Discovery and evidence portability are separate concerns.

Profiles SHOULD minimize unnecessary correlation identifiers and disclosure while retaining enough context to prevent misleading interpretation.

---

## 33. Safety and policy boundary

The ability to represent a MarketIntent, MarketAgreement, MarketEvent, Action, Term, or Subject does not make it safe, lawful, ethical, authorized, or executable.

Marketplace implementations MUST treat externally supplied Marketplace data as untrusted.

Implementations SHOULD support:

- authorization before protected side effects;
- policy evaluation;
- validation;
- moderation;
- rate/resource limits;
- bounded automated execution;
- safe external resolution; and
- auditable decisions where appropriate.

The semantic layer MUST NOT require an implementation to execute a represented Action merely because the object is validly encoded or cryptographically proven.

---

## 34. Representation decisions intentionally deferred

Milestone 2 does not yet freeze:

- final Marketplace semantic identifiers;
- exact field names for the four record profiles;
- exact canonical content schemas;
- JSON or CBOR transport representation;
- mandatory proof purposes;
- agreement countersignature thresholds;
- negotiation state machines;
- matching protocols;
- federation/discovery APIs;
- settlement APIs;
- domain-specific Action registries;
- unit/currency vocabularies;
- privacy/disclosure profiles;
- moderation protocols; or
- conformance test vectors.

Those decisions belong to later milestones after the object boundaries are stable.

---

## 35. Object-model summary

The resulting architecture is:

```text
                           Open Layer Protocol
                 records / proofs / relations / lifecycle
                                  |
                                  v
+----------------------------------------------------------------+
|                Marketplace first-class records                 |
|                                                                |
|  MarketIntent          MarketAgreement          MarketEvent |
+-----------------------+----------------+-----------------------+
                        |
                        v
+----------------------------------------------------------------+
|                     Embedded structures                        |
|                                                                |
| SubjectBinding  Action  Party  Terms  Constraint  Commitment  |
| Value  Quantity  Time  Location  EvidenceRequirement  ...      |
+-----------------------+----------------+-----------------------+
                        |
                        v
+----------------------------------------------------------------+
|                 Derived / application-specific                 |
|                                                                |
| Listing  Match  MarketView  Status  Trust  Reputation  Risk    |
| Ranking  Recommendation  FairValue  PolicyDecision  ...        |
+----------------------------------------------------------------+
```

A derived conclusion may itself become attributable evidence if a Participant intentionally publishes it as an OLP Claim, Attestation, Observation, Event, or other appropriate record.

That does not change its conceptual status from evaluator conclusion to universal truth.

---

## 36. Foundational invariants

A conforming Marketplace object model MUST preserve all of the following:

```text
one OLP record envelope                 — no second marketplace envelope
record identity                         — inherited from OLP
proofs                                  — detached OLP artifacts
relationships                           — immutable OLP evidence records
lifecycle                               — additive OLP evidence
subject representation                  != ownership
participant reference                   != identity proof
identity                                != authority
intent                                  != agreement
proposal compatibility                  != assent
agreement                               != legal enforceability
agreement                               != settlement
settlement                              != fulfillment
delivery                                != acceptance
match                                   != protocol truth
listing                                 != source-of-truth record
current status                          != mutable record field
price                                   != value
verification                            != endorsement
policy decision                         != protocol permission
subject scale                           != object-model privilege
participant type                        != object-model privilege
```

---

## 37. Milestone 2 acceptance boundary

Milestone 2 is complete when:

- the three first-class Marketplace record profiles are accepted as the initial universal set;
- embedded structures are distinguished from first-class records;
- derived/application concepts are explicitly kept out of universal protocol state;
- OLP identity, proofs, relationships, and lifecycle remain the evidence substrate;
- subject-scale and participant-type neutrality are preserved;
- no final wire serialization is prematurely frozen; and
- the repository documentation and specification index reflect this object model.

The next specification should make these conceptual profiles concrete enough for independent implementations to construct and validate exact Marketplace record contents without yet coupling the system to one transport or application architecture.
