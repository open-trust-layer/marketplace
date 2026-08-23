# Marketplace — Foundational Vocabulary

**Status:** Draft v0.1
**Milestone:** 1 — Foundations
**Filename:** `specification/0001-market-vocabulary.md`

---

## 1. Purpose

This specification defines the foundational vocabulary for an open marketplace and economic-coordination layer built on Open Layer Protocol (OLP).

Its purpose is to establish stable conceptual boundaries before defining wire formats, APIs, matching algorithms, payment integrations, user interfaces, or domain-specific marketplace profiles.

The vocabulary is designed to remain meaningful across extreme differences in subject scale and domain. A marketplace subject may concern a software bug, a physical object, a service, a company, a piece of infrastructure, an astronomical body, or another referable thing.

Representability is not a claim of ownership, transferability, legality, truth, authority, value, or trust.

---

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are to be interpreted as described by RFC 2119 and RFC 8174 when written in all capitals.

This document primarily defines concepts and invariants. It does not yet define a normative serialization.

---

## 3. Relationship to Open Layer Protocol

The marketplace is a semantic layer above OLP, not a replacement evidence protocol.

Where this specification uses OLP concepts such as **Participant**, **Subject**, **Claim**, **Evidence**, **Event**, **Outcome**, **Record**, **Proof**, **Reference**, **Identity**, **Authority Evidence**, or **History**, their OLP meanings are preserved.

Marketplace specifications MUST NOT silently redefine OLP semantics in incompatible ways.

In particular:

```text
proof validity        != truth
identity              != trust
identity              != authority
authority evidence    != final authorization decision
status evidence       != historical mutation
resolution            != verification
```

Marketplace-specific objects may later be represented as OLP Records and related OLP artifacts. The exact semantic identifiers, record profiles, canonical representations, proof requirements, and version bindings are deferred to later specifications.

OLP itself remains independent of this marketplace.

---

## 4. Core design rule: coordinate around Subjects through Intents

The foundational marketplace grammar is:

```text
Participant
    |
    | expresses
    v
Intent
    |
    +-- concerns ------> Subject
    |
    +-- proposes ------> Action
    |
    +-- under ---------> Terms
    |
    +-- may reference -> Evidence
```

This grammar is intentionally more general than a product catalog.

The universal core SHOULD NOT require every market domain to be expressed through a closed taxonomy such as:

```text
Product
Service
Job
Vehicle
RealEstate
Patent
Security
...
```

Those concepts may be useful in domain profiles, but they are not universal marketplace primitives.

---

## 5. Imported foundational concepts

### 5.1 Participant

A **Participant** is an OLP Participant acting in a marketplace context.

A Participant may be a human, organization, software agent, service, device, account-like entity, or another actor recognized by an application.

Marketplace core MUST NOT assign automatic privilege solely by participant type.

A Participant's presence in marketplace data does not itself establish identity, authority, legal capacity, or trustworthiness.

### 5.2 Subject

A **Subject** is the thing an Intent, Claim, Event, Agreement, or other market evidence is about.

A Subject may be existing, proposed, abstract, digital, physical, composite, extremely small, extremely large, or externally referenced.

Examples include:

- a software issue;
- a desired software change;
- a file;
- a physical item;
- a parcel shipment;
- a machine;
- a service engagement;
- a company;
- a construction project;
- an energy-delivery interval;
- a satellite;
- an asteroid;
- a planet;
- a galaxy; or
- a specification describing something not yet created.

Subject representation MUST NOT imply:

- existence;
- ownership;
- custody;
- control;
- right to transfer;
- legal status;
- availability;
- uniqueness;
- authenticity; or
- value.

Those properties require separate evidence and interpretation where relevant.

### 5.3 Evidence

**Evidence** retains its OLP meaning: information an evaluator may use when deciding what to believe, trust, permit, rank, investigate, or require.

Marketplace evidence may concern identity, authority, prior interactions, subject provenance, inspection, fulfillment, acceptance, settlement, dispute, or other facts and claims.

Evidence is not truth.

---

## 6. Intent

An **Intent** is an attributable expression by or on behalf of a Participant describing desired, proposed, available, requested, or conditional coordination concerning one or more Subjects.

An Intent is the central marketplace concept.

Conceptually, an Intent contains or references enough information to identify:

```text
issuer / expressing participant
subject or subjects
action
terms
optional constraints
optional evidence references
optional validity / lifecycle context
optional profile identifiers
```

The exact representation is deferred.

Examples:

```text
"I will fix this software bug under these conditions."
"I want to acquire this bicycle under these conditions."
"I can provide 500 GPU-hours during this interval."
"I seek transport for this package."
"I seek funding for this bridge project."
"I can license these rights if the stated conditions are satisfied."
"I seek telescope time to observe this galaxy."
```

An Intent does not itself establish that the issuer can lawfully or practically perform the proposed Action.

### 6.1 Intent direction is contextual

Terms such as `offer`, `request`, `bid`, `ask`, `demand`, `supply`, `proposal`, and `invitation` are useful specializations but MUST NOT be assumed to cover every market structure.

The universal core therefore treats them as profiles or specializations of Intent rather than as mutually exclusive foundations.

### 6.2 Intent is not agreement

Publication or discovery of an Intent does not create an Agreement.

Compatibility between multiple Intents does not create an Agreement.

A Match does not create an Agreement.

---

## 7. Action

An **Action** describes the kind of coordination an Intent proposes or seeks concerning its Subjects.

Examples may include:

```text
transfer
provide
perform
repair
build
transport
store
license
lend
lease
reserve
fund
insure
inspect
measure
observe
publish
compute
exchange
donate
```

This list is illustrative and non-exhaustive.

Marketplace core MUST NOT assign universal legal meaning to an Action solely from its label.

Domain profiles SHOULD define precise Action semantics where interoperability requires them.

The same Subject may support many different Actions.

For example, a telescope may be sold, leased, repaired, insured, reserved, operated, inspected, or used to perform an observation. The subject type alone does not determine the market relationship.

---

## 8. Role

A **Role** is a contextual function a Participant occupies within an Intent, Agreement, Event, or other market context.

Examples may include:

```text
requester
provider
buyer
seller
licensor
licensee
shipper
carrier
insurer
investor
contractor
reviewer
arbiter
agent
```

Roles are context-specific.

A Role MUST NOT automatically imply organization-wide authority, legal capacity, ownership, or permission outside the context in which the role is asserted.

A single Participant may hold multiple roles.

---

## 9. Terms

**Terms** are the structured conditions proposed, requested, or assented to for an Action or coordination relationship.

Terms may concern:

- quantity;
- quality;
- scope;
- timing;
- location;
- price or other value expressions;
- settlement method;
- delivery;
- acceptance criteria;
- warranties;
- dependencies;
- required evidence;
- privacy conditions;
- cancellation conditions;
- dispute process;
- governing-law references;
- performance metrics; or
- profile-specific conditions.

Terms are attributable expressions, not universal facts.

The presence of Terms does not imply that they are lawful, complete, fair, enforceable, feasible, or mutually accepted.

---

## 10. Constraint

A **Constraint** is a condition limiting what an Intent considers acceptable for matching, agreement, execution, disclosure, or fulfillment.

Examples include:

```text
maximum price
minimum quantity
required jurisdiction
required certification
deadline
geographic boundary
privacy requirement
accepted settlement rails
required evidence profile
counterparty capability requirement
```

Whether a Constraint is mandatory, preferred, negotiable, private, or externally evaluated MUST be explicit when that distinction affects behavior.

Matching systems MUST NOT silently reinterpret a mandatory constraint as a preference.

---

## 11. Listing

A **Listing** is a discoverable publication or presentation of one or more marketplace Intents.

A Listing is a discovery concept, not an ownership primitive.

A Listing may be hosted, indexed, replicated, cached, federated, selectively disclosed, or presented by multiple implementations.

A Listing MUST NOT be interpreted merely by its existence as proof of:

- ownership;
- authority;
- availability;
- authenticity;
- legality;
- endorsement; or
- right to transact.

The normative relationship between Listing and Intent will be defined in a later discovery/representation specification.

---

## 12. Offer and Request

### 12.1 Offer

An **Offer** is an Intent specialization in which a Participant expresses willingness or availability to perform, provide, transfer, permit, or otherwise coordinate an Action under stated Terms.

The term `Offer` in marketplace core is semantic and does not automatically carry the legal meaning of "offer" in any particular jurisdiction.

### 12.2 Request

A **Request** is an Intent specialization in which a Participant seeks another Participant, resource, Action, capability, or outcome under stated Terms.

An Offer and a Request may be potentially compatible without forming an Agreement.

---

## 13. Proposal

A **Proposal** is an attributable response that presents specific Terms for possible agreement, usually in relation to one or more existing Intents.

A Proposal may:

- accept an existing term set subject to explicit conditions;
- modify terms;
- introduce additional constraints;
- bind previously abstract quantities or participants; or
- propose a concrete coordination plan.

A Proposal does not become an Agreement until the applicable agreement profile has sufficient evidence of assent.

---

## 14. Match

A **Match** is a derived association indicating that two or more Intents may be compatible according to a stated matching method or policy.

A Match is an application judgment.

It is not:

- proof of compatibility;
- participant assent;
- an Agreement;
- authorization;
- endorsement;
- legal permission; or
- proof that execution is possible.

Different matching engines may produce different Matches from the same underlying Intents.

The marketplace MUST permit algorithm plurality.

---

## 15. Agreement

An **Agreement** is marketplace evidence that identified Participants assented, according to a defined profile, to a specific set of Terms concerning one or more Actions and Subjects.

An Agreement SHOULD bind the exact Terms or their immutable identity so later modification cannot be confused with the originally assented terms.

Agreement formation semantics, signatures/proofs, countersigning, amendments, cancellation, and partial acceptance are deferred to later specifications.

An Agreement does not by itself establish:

- legal enforceability;
- ownership transfer;
- regulatory compliance;
- settlement completion;
- fulfillment;
- factual correctness of participant claims; or
- universal authorization.

### 15.1 Agreement is evidence, not universal contract law

Applications may treat an Agreement as relevant evidence for contract formation.

The universal marketplace layer does not decide which jurisdiction's contract law applies or whether a legally enforceable contract exists.

---

## 16. Commitment

A **Commitment** is an attributable undertaking by a Participant within an Intent, Proposal, Agreement, or related market context.

Examples include commitments to:

- deliver an item;
- perform work;
- make a payment;
- make a resource available;
- provide evidence;
- maintain a service level; or
- respond by a deadline.

A Commitment is a marketplace semantic concept and does not automatically establish a legal obligation.

Commitments SHOULD be explicit enough to evaluate later fulfillment claims.

---

## 17. Fulfillment

**Fulfillment** is the contextual evaluation that one or more Commitments or agreed Terms have been satisfied.

Because fulfillment may be disputed, marketplace history SHOULD preserve attributable evidence rather than mutate one universal `fulfilled=true` field.

Relevant evidence may include:

- delivery events;
- work artifacts;
- measurements;
- inspections;
- acceptance statements;
- rejection statements;
- service telemetry;
- external receipts;
- OLP observations; or
- other profile-defined evidence.

### 17.1 Fulfillment Claim

A **Fulfillment Claim** is an attributable Claim that specified Commitments or Terms were satisfied, partially satisfied, or not satisfied.

A Fulfillment Claim is not automatically authoritative.

### 17.2 Acceptance Claim

An **Acceptance Claim** is an attributable Claim that a Participant accepted, rejected, conditionally accepted, or otherwise evaluated asserted fulfillment.

Delivery does not automatically equal acceptance.

---

## 18. Settlement

**Settlement** is a process or Event through which agreed economic consideration, assets, balances, rights, or other exchange obligations are discharged or transferred according to a selected mechanism.

Settlement may use:

- bank transfer;
- card networks;
- escrow;
- digital assets;
- blockchain systems;
- internal ledgers;
- barter;
- vouchers;
- credits;
- physical exchange;
- no monetary consideration; or
- other profile-defined mechanisms.

Marketplace core MUST remain settlement-neutral.

Settlement success does not by itself prove fulfillment, acceptance, ownership, legality, or absence of dispute.

### 18.1 Settlement Evidence

**Settlement Evidence** is Evidence concerning attempted, pending, completed, reversed, failed, or disputed settlement.

The marketplace may reference settlement evidence without becoming the settlement system.

---

## 19. Outcome

**Outcome** retains the OLP concept of a represented result associated with an Event or Interaction.

In marketplace contexts, outcomes may concern:

- completion;
- partial completion;
- cancellation;
- expiration;
- rejection;
- dispute;
- settlement;
- reversal;
- refund;
- delivery;
- non-performance; or
- another profile-defined result.

Different Participants may assert different Outcomes concerning the same market interaction.

The marketplace MUST permit disagreement to remain explicit evidence rather than requiring one universally authoritative outcome.

---

## 20. Dispute

A **Dispute** is an attributable challenge to a Claim, Intent interpretation, Agreement interpretation, Fulfillment Claim, Acceptance Claim, Settlement claim, Outcome, authority assertion, or other market evidence.

A Dispute does not automatically prove the challenged statement false.

A Dispute does not automatically suspend an Agreement or reverse Settlement unless an applicable policy/profile says so.

Dispute-resolution procedures are application- and profile-specific and are not defined by this foundational vocabulary.

---

## 21. Market View

A **Market View** is an application-specific selected and interpreted view over discoverable Intents, Listings, Evidence, Matches, and related marketplace information.

A Market View may apply:

- search criteria;
- ranking;
- moderation;
- policy;
- jurisdiction filters;
- trust models;
- personalization;
- privacy constraints; or
- availability rules.

There is no universal canonical Market View.

Two implementations may legitimately expose different views over the same portable evidence.

---

## 22. Marketplace Implementation

A **Marketplace Implementation** is software that implements some defined marketplace capabilities.

Examples may include:

- a marketplace user interface;
- a federation node;
- a search/index service;
- an autonomous agent;
- a matching engine;
- an agreement service;
- a fulfillment verifier; or
- an integration gateway.

Conformance to marketplace specifications does not make an implementation trustworthy, lawful, secure, or universally authoritative.

---

## 23. Profile

A **Marketplace Profile** is a named set of additional semantic and/or behavioral rules for a particular domain or capability.

Profiles may define concepts such as:

```text
software work
physical goods
logistics
compute
energy
licensing
research
construction
insurance
space-related observation or coordination
```

Profiles MAY define specialized Actions, Terms, roles, evidence requirements, state transitions, and validation rules.

A Profile MUST NOT silently redefine foundational terms incompatibly.

The core should remain smaller than the sum of all market domains.

---

## 24. Policy Decision

A **Policy Decision** is an application-specific conclusion about whether and how marketplace information may be accepted, displayed, ranked, matched, executed, disclosed, or acted upon.

Examples include:

```text
allow
reject
hide
quarantine
require additional evidence
require human review
restrict by jurisdiction
restrict by participant capability
```

Policy Decisions are not universal protocol truth.

Marketplace implementations MUST retain the ability to enforce safety, authorization, legal, and operational constraints independently of protocol expressibility.

---

## 25. Foundational invariants

All later marketplace specifications MUST preserve the following unless a future version explicitly changes the foundation:

### 25.1 Subject representation does not establish rights

```text
subject representation != ownership
listing                != transfer right
claim of ownership     != ownership
```

### 25.2 Evidence and verification do not create truth or endorsement

```text
evidence      != truth
verification  != endorsement
discovery     != endorsement
```

### 25.3 Coordination stages remain distinct

```text
intent       != match
match        != proposal
proposal     != agreement
agreement    != settlement
settlement   != fulfillment
payment      != completion
delivery     != acceptance
```

### 25.4 Identity, authority, legality, and trust remain distinct

```text
identity            != authority
authority evidence  != legal sufficiency
legal sufficiency   != trust
reputation          != universal trust
```

### 25.5 Market expression does not create universal value

```text
price       != value
bid         != value
valuation   != truth
```

### 25.6 Expressibility does not create permission

```text
protocol expressibility != permission
market visibility       != legitimacy
```

---

## 26. Scale neutrality examples

The vocabulary should survive the following cases without changing its foundational grammar.

### 26.1 Software bug

```text
Subject:      issue #481
Intent:       request repair
Action:       fix
Terms:        reward + deadline + acceptance criteria
Evidence:     commits + CI + review
Outcome:      completion claims / acceptance claims
```

### 26.2 Physical object

```text
Subject:      bicycle
Intent:       proposed transfer
Action:       transfer
Terms:        price + pickup conditions
Evidence:     provenance / inspection / authority claims
Outcome:      delivery + acceptance + settlement evidence
```

### 26.3 Compute capacity

```text
Subject:      compute-capacity allocation
Intent:       provide
Action:       compute
Terms:        capacity + duration + service constraints
Evidence:     capability + telemetry + settlement evidence
Outcome:      usage / fulfillment claims
```

### 26.4 Infrastructure project

```text
Subject:      proposed bridge project
Intent:       seek construction provider
Action:       build
Terms:        specification + milestones + evidence requirements
Evidence:     authority + certifications + inspections
Outcome:      milestone and completion evidence
```

### 26.5 Astronomical subject

```text
Subject:      Andromeda Galaxy
Intent:       seek observational campaign
Action:       observe
Terms:        telescope allocation + dataset requirements
Evidence:     facility authority + observations + provenance
Outcome:      dataset delivery / acceptance evidence
```

The galaxy example does not require or imply ownership of the galaxy. The market relationship concerns a defined Action involving a referenced Subject.

---

## 27. Concepts deliberately not universalized

Milestone 1 deliberately does not make the following universal primitives:

- one global `Product` type;
- one global `Service` type;
- one global ownership model;
- one global legal contract model;
- one global currency;
- one global settlement rail;
- one global escrow service;
- one global identity provider;
- one global reputation score;
- one global trust algorithm;
- one global matching algorithm;
- one global pricing algorithm;
- one global moderation policy;
- one global jurisdiction; or
- one canonical worldwide marketplace database.

These choices preserve interoperability without centralizing interpretation or infrastructure.

---

## 28. Deferred to later milestones

This vocabulary intentionally does not yet define:

- exact marketplace Record types;
- canonical serialization;
- marketplace object identity;
- intent lifecycle representation;
- agreement formation protocol;
- amendment/cancellation protocol;
- discovery and federation wire protocols;
- matching APIs;
- privacy/disclosure profiles;
- settlement adapters;
- dispute-resolution profiles;
- domain taxonomies;
- conformance suites; or
- production implementation architecture.

Those should be designed incrementally after the foundational semantics are stable.

---

## 29. Milestone 1 foundation

The smallest universal conceptual set established by this milestone is:

```text
Participant
Subject
Intent
Action
Role
Terms
Constraint
Evidence
Listing
Proposal
Match
Agreement
Commitment
Fulfillment
Settlement
Outcome
Dispute
Market View
Profile
Policy Decision
```

Not every concept above must become a distinct wire-level object.

Later representation work MUST determine which concepts require independent identity, proof, lifecycle, portability, and conformance semantics rather than prematurely turning every vocabulary term into a protocol object.

This distinction is deliberate.
