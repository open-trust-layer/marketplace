# Marketplace

**An open-source economic coordination layer built on Open Layer Protocol (OLP).**

> Coordinate exchange around anything that can be referenced, without making ownership, legality, truth, value, or trust centrally owned.

**Project status:** experimental / pre-implementation  
**Current milestone:** Milestone 1 — Foundations

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
payment                     != fulfillment
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

Future specifications will define representation, identity, lifecycle, matching/discovery, agreements, fulfillment, settlement interfaces, federation, privacy, safety/policy boundaries, and conformance incrementally.

---

## Development principles

Development follows a maintenance-first engineering standard: small coherent changes, explicit boundaries, replaceable infrastructure, validated configuration, isolated side effects, deterministic tests, regression coverage, and green acceptance gates before completion.

The project should prefer established open standards and OLP capabilities over unnecessary invention.

---

## License

Licensed under the [Apache License 2.0](LICENSE).
