# Marketplace

**An open-source economic coordination layer built on Open Layer Protocol (OLP).**

> Coordinate exchange around anything that can be referenced, without making ownership, legality, truth, value, or trust centrally owned.

**Project status:** experimental / pre-implementation
**Foundation status:** Milestone 1 — Foundations — COMPLETE
**Object model status:** Milestone 2 — Marketplace Object Model & Representation — COMPLETE
**Record representation status:** Milestone 3 — Marketplace Record Representation & Identity — COMPLETE
**Lifecycle status:** Milestone 4 — Lifecycle & Negotiation Semantics — COMPLETE
**Matching/discovery status:** Milestone 5 — Matching & Discovery Semantics — COMPLETE
**Fulfillment/performance status:** Milestone 6 — Fulfillment & Performance Semantics — COMPLETE
**Settlement status:** Milestone 7 — Settlement Interfaces & Economic Exchange Semantics — COMPLETE

This project explores a global, interoperable marketplace architecture whose subject scale ranges from very small objects and tasks to arbitrarily large structures: a software bug, a physical item, a service, a company, infrastructure, an asteroid, a planet, or a galaxy may all be *subjects of market intent*.

Representation is not ownership. Discovery is not legitimacy. A listing is not proof of rights. The marketplace carries and connects attributable intentions and evidence; applications and participants decide what those mean in context.

---

## Relationship to Open Layer Protocol

[Open Layer Protocol (OLP)](https://github.com/open-trust-layer/protocol) is the evidence substrate.

OLP provides portable, independently verifiable records, proofs, relationships, identity/authority evidence, lifecycle evidence, bundles, resolution, privacy boundaries, and conformance mechanisms. OLP deliberately does not define a marketplace, payment system, universal trust score, or central authority.

This repository builds marketplace semantics **above** that boundary.

```text
Open Layer Protocol (OLP)
    portable evidence / proofs / history
                    |
                    v
Marketplace semantic layer
    intents / terms / agreements / outcomes
                    |
          +---------+---------+
          |         |         |
          v         v         v
     App / UI   AI agent   Federation node
          |         |         |
          +---------+---------+
                    v
       external settlement / delivery /
       legal / identity / policy systems
```

The marketplace should depend on OLP's evidence capabilities, not fork or duplicate them.

---

## Foundational model

The smallest useful mental model is:

```text
PARTICIPANT
    |
    | expresses
    v
INTENT
    |
    +-- concerns ------> SUBJECT
    |
    +-- proposes ------> ACTION
    |
    +-- under ---------> TERMS
    |
    +-- may reference -> EVIDENCE (OLP)
```

An intent can describe selling, buying, hiring, providing, requesting, funding, licensing, exchanging, reserving, bidding, donating, coordinating, or other domain-defined actions.

The universal layer does not need a closed taxonomy of `Product`, `Job`, `Vehicle`, `RealEstate`, `Patent`, and thousands of other object classes. Domain profiles may define rich semantics while the core remains small.

### Marketplace object model

Milestone 2 keeps the universal first-class record set deliberately small:

    MarketIntent
    MarketAgreement
    MarketEvent

All three use ordinary immutable OLP Records or OLP Event profiling; the Marketplace does not create a second identity-bearing record envelope. Proposal, Offer, Request, Bid, Ask, and similar negotiation forms specialize MarketIntent.

Reusable structures such as SubjectBinding, ActionDescriptor, Terms, Constraint, Commitment, ValueExpression, quantities, time/location conditions, and evidence requirements are embedded by default.

Listing, Match, MarketView, current status, trust, reputation, risk, ranking, recommendation, fair value, and PolicyDecision remain derived/application-specific unless a participant intentionally publishes an attributable OLP claim about them.

### Exact record representation

Milestone 3 makes the three first-class profiles independently constructible and verifiable without creating a second identity system. Exact v1 content shapes, required/optional fields, cardinalities, semantic identifiers, set ordering, references, decimals, quantities, time/location conditions, extensions, and validation boundaries are defined in the record-representation specification.

```text
Marketplace Record Identity = OLP Record Identity
Marketplace canonical identity encoding = OLP-CIE-1
Marketplace record envelope = OLP RecordV1
```

The core semantic namespace is `https://open-trust-layer.github.io/marketplace/semantics/v1`. Executable conformance coverage currently contains 33 positive/negative record and structure vectors. Positive identities are derived exclusively through the OLP reference implementation pinned by the vector set to source commit `41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c`.

Milestone 3 does not freeze a mandatory Marketplace JSON/CBOR wire format or transport API; those remain separate from identity.

### Lifecycle and negotiation

Milestone 4 defines negotiation and lifecycle as additive evidence rather than mutable marketplace state. Proposals form immutable `response_to` graphs; acceptance and decline are `MarketEvent` evidence; Intent withdrawal reuses scoped OLP lifecycle `retire`; natural expiration is derived from authenticated validity bounds; Agreement formation is evaluated from detached OLP assent proofs; and Agreement amendment uses a new immutable Agreement plus OLP `supersedes`.

```text
response_to          != supersedes
acceptance event     != agreement formation
withdrawal           != expiration
amendment            != mutation
conflict             != canonical winner
```

The protocol does not select a universal current proposal, current Agreement, latest-wins branch, or winner when concurrent/conflicting evidence exists. The Milestone 4 executable set contains 26 positive/negative lifecycle and negotiation vectors.

### Matching and discovery

Milestone 5 defines source-scoped discovery, exact verified index projections, method-relative matching, ranking plurality, federated result merging, and cursor binding without turning search visibility or compatibility into protocol truth.

```text
search result              != resolved evidence
source completeness        != global completeness
match                      != protocol truth
compatibility under method != agreement
ranking                    != canonical ordering
```

The core exact-query profile operates only over authenticated Intent fields. Mandatory constraints that are unsatisfied block compatibility under the selected method; mandatory semantics that are missing, unknown, or unsupported keep the result indeterminate. Different matching and ranking methods may legitimately disagree. The Milestone 5 executable set contains 31 positive/evaluation and negative matching/discovery vectors.

### Fulfillment and performance

Milestone 6 defines commitment-targeted performance, delivery, inspection, acceptance/rejection, completion/failure, and dispute evidence without introducing mutable Agreement state or a fourth Marketplace record type.

```text
performance assertion      != objective performance
delivery                   != acceptance
completion assertion       != fulfillment truth
settlement/payment         != fulfillment
conflict                   != canonical winner
```

Every core fulfillment event targets an exact `{Agreement RecordRef, Commitment id}` pair. Positive fulfillment remains method-relative and requires accepted evidence for the selected method; missing evidence remains incomplete rather than automatic non-performance. The Milestone 6 executable set contains 47 positive/evaluation and negative vectors.

### Settlement interfaces and economic exchange

Milestone 7 defines rail-neutral settlement attempts, completion/failure, reversals/refunds, escrow hold/release, and asset-transfer evidence as ordinary immutable `MarketEvent` records targeted to exact Agreement Commitments.

```text
settlement evidence         != objective transfer
settlement                  != fulfillment
asset-transfer evidence     != ownership or legal title
rail verification           != legal finality
multi-rail evidence         != canonical rail
```

Attribution, authority, and rail verification are separate relying-party inputs. `SettlementPreferenceV1` constrains rail admissibility only where its semantics are understood; parameterized requirements are never guessed. Core preserves multi-rail evidence without exchange-rate invention or cross-rail arithmetic. The Milestone 7 executable set contains 57 positive/evaluation and negative vectors.

---

## What this project is

This project is intended to become:

- an open marketplace and economic-coordination semantic layer built on OLP;
- subject-scale neutral, from tiny digital tasks to arbitrarily large referenced structures;
- participant-type neutral across humans, organizations, software agents, services, devices, and other actors recognized by applications;
- intent-centric rather than product-taxonomy-centric;
- evidence-aware, with claims about identity, authority, history, fulfillment, and outcomes carried as inspectable evidence rather than hidden platform state;
- settlement-neutral and capable of interoperating with multiple payment, asset-transfer, escrow, barter, or non-monetary mechanisms;
- implementation-plural, allowing multiple applications, indexes, agents, and federation nodes to participate without one mandatory operator;
- jurisdiction-aware at application and policy layers without making one jurisdiction universal at the protocol layer; and
- open source, independently implementable, and designed for interoperability.

---

## What this project is not

The marketplace is **not**:

- Open Layer Protocol itself;
- a universal ownership or title registry;
- proof that a listed subject is ownable, transferable, legal to exchange, or controlled by the lister;
- a truth oracle;
- a legal authority, court, regulator, or universal contract-enforcement system;
- a universal identity provider;
- a universal trust or reputation score;
- a mandatory cryptocurrency, token, blockchain, or distributed ledger;
- a mandatory payment processor, bank, escrow provider, or settlement rail;
- a requirement that all market activity live in one global database;
- a guarantee that discovered content is safe, lawful, authentic, valuable, or permitted by a particular application; or
- a replacement for application-level authorization, moderation, safety, compliance, fraud controls, taxation, or dispute processes.

Protocol expressibility does not create permission or legitimacy.

---

## Foundational separations

The architecture must preserve these distinctions:

```text
subject representation      != ownership
listing                     != right to transfer
claim of ownership          != ownership
identity                    != authority
authority evidence          != legal sufficiency
market visibility           != legitimacy
discovery                   != endorsement
intent                      != agreement
agreement                   != legal enforceability
agreement                   != settlement
settlement evidence          != objective transfer
rail reference               != universal transaction proof
payment                     != fulfillment
performance evidence        != fulfillment truth
delivery                    != acceptance
completion assertion        != fulfillment truth
fulfillment evidence        != acceptance
price                       != value
evidence                    != truth
verification                != endorsement
reputation                  != universal trust
protocol expressibility     != permission
```

These separations are constraints, not merely documentation language.

---

## Example scale

The same conceptual model can describe very different domains:

```text
software bug
  intent: fix
  terms: reward + acceptance criteria

bicycle
  intent: transfer
  terms: requested consideration + delivery conditions

compute capacity
  intent: provide
  terms: capacity + duration + constraints

bridge project
  intent: construct / fund / insure / inspect
  terms: role-specific conditions

asteroid
  intent: research / observe / fund / claim a proposed right
  terms: domain-specific conditions

galaxy
  intent: fund observational campaign
  terms: telescope allocation + data-delivery conditions
```

The marketplace can represent an intent concerning a subject without asserting that every conceivable action involving that subject is possible, lawful, ownable, or enforceable.

---

## Specification

- [`PRINCIPLES.md`](PRINCIPLES.md) — constitutional constraints for the project.
- [`specification/0001-market-vocabulary.md`](specification/0001-market-vocabulary.md) — foundational marketplace vocabulary and semantic separations.
- [`specification/0002-market-object-model.md`](specification/0002-market-object-model.md) - first-class record profiles, embedded structures, derived concepts, and OLP representation boundaries.
- [`specification/0003-market-record-representation.md`](specification/0003-market-record-representation.md) - exact v1 abstract representation, semantic identifiers, deterministic structures, and OLP identity inheritance.
- [`specification/0004-market-lifecycle-negotiation.md`](specification/0004-market-lifecycle-negotiation.md) - additive negotiation history, withdrawal/expiration, formation evidence, amendments, concurrency, and lifecycle boundaries.
- [`specification/0005-market-matching-discovery.md`](specification/0005-market-matching-discovery.md) - source-scoped discovery, matching aggregation, ranking plurality, federation, and cursor boundaries.
- [`specification/0006-market-fulfillment-performance.md`](specification/0006-market-fulfillment-performance.md) - commitment-targeted performance, delivery, inspection, acceptance, disputes, and method-relative fulfillment.
- [`specification/0007-market-settlement-interfaces.md`](specification/0007-market-settlement-interfaces.md) - rail-neutral settlement evidence, reversals/refunds, escrow, asset transfer, preference constraints, and finality boundaries.
- [`conformance/README.md`](conformance/README.md) - executable representation vectors and reproducibility workflow.
- [`docs/standards-landscape.md`](docs/standards-landscape.md) - initial prior-art and interoperability targets.

Future specifications will define federation transports, privacy profiles, safety/policy boundaries, dispute-resolution profiles, and further conformance incrementally.

---

## Development principles

Development follows a maintenance-first engineering standard: small coherent changes, explicit boundaries, replaceable infrastructure, validated configuration, isolated side effects, deterministic tests, regression coverage, and green acceptance gates before completion.

The project should prefer established open standards and OLP capabilities over unnecessary invention.

---

## License

Licensed under the [Apache License 2.0](LICENSE).
