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
**Federation/interoperability status:** Milestone 8 — Federation Transport & Marketplace Interoperability APIs — COMPLETE
**Trust evaluation status:** Milestone 9 — Trust Evaluation & Evidence Query Semantics — COMPLETE
**Privacy/disclosure status:** Milestone 10 — Privacy, Selective Disclosure & Data Minimization Profiles — COMPLETE
**Safety/policy status:** Milestone 11 — Safety, Policy & Authorization Boundaries — COMPLETE
**Conformance/CI status:** Milestone 12 — Unified Conformance & Continuous Integration Quality Gate — COMPLETE
**Dispute-resolution status:** Milestone 13 — Dispute Resolution Profiles & Resolution Evidence — COMPLETE
**Deployment status:** Milestone 14 — Deployment Profiles & Runtime Boundaries — COMPLETE
**Domain evaluator status:** Milestone 15 — Domain Evaluator Method Profiles & Criterion Aggregation — COMPLETE

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

### Federation transport and interoperability

Milestone 8 profiles OLP transport/capability primitives for source-scoped Marketplace federation without introducing a second wire envelope, global marketplace server, canonical peer graph, or mutable shared state.

```text
transport delivery       != evidence identity
source completeness      != global completeness
sync absence             != deletion
replay/idempotency       != exactly-once delivery
receiver policy          != protocol validity
```

Snapshot and incremental-sync requests carry explicit normalized scopes and optional opaque cursors bound to source + operation + scope. Exchange results carry canonical scope fingerprints, sorted unique OLP Record identities, source-relative completeness, and explicit truncation/cursor state. Exact Record Identity is recomputed on receipt; duplicate immutable evidence is replay-safe; receiver accept/reject/defer/ignore outcomes remain source-local. The Milestone 8 executable set contains 93 positive/evaluation and negative vectors.

### Trust evaluation and evidence queries

Milestone 9 defines method-relative, explainable evidence evaluation without introducing a universal trust score, reputation object, canonical ranking, or trust authority. Queries bind a method URI, purpose, target, context, evidence scope, source scope, and explicit resource limits.

```text
selected evidence            != supporting evidence
supporting evidence          != truth
proof verification           != authority acceptance
method-relative sufficiency  != universal trust
missing evidence             != negative evidence
```

The reference method preserves proof, identity, authority, lifecycle, source policy, critical-semantics and domain-direction observations as separate dimensions. Results remain `SUFFICIENT/INSUFFICIENT UNDER METHOD`, conflicting, disputed, or indeterminate, with exact Record identities, provenance, exclusion reasons and explainable traces. The Milestone 9 executable set contains 56 positive/evaluation and negative/adversarial vectors.
### Privacy, selective disclosure, and data minimization

Milestone 10 profiles OLP 0010 for Marketplace workflows instead of creating a second privacy envelope or redactable Marketplace record format. Disclosure remains whole-object and graph-subset selection over exact immutable evidence, with explicit task purpose and dependency closure.

```text
selective disclosure       != field deletion
withheld evidence           != nonexistent evidence
task-scoped minimized       != globally minimal
privacy warning             != invalid evidence
privacy planning            != authorization / consent / trust
```

The core profile recognizes discovery, negotiation, fulfillment-verification, settlement-verification, federation-exchange, and trust-evaluation tasks. It preserves OLP disclosure results, adds deterministic Marketplace correlation warnings, requires explicit network/privacy context, and bounds roots, inventories, resources, capabilities, dependencies, and warning lists. The Milestone 10 executable set contains 52 positive/evaluation and negative/adversarial vectors.


### Safety, policy, and authorization boundaries

Milestone 11 defines a local, method-relative PolicyDecision process for protected Marketplace operations without creating a global censor, regulator, moderation authority, allow/deny registry, or protocol-level permission oracle.

```text
valid record             != permitted action
authority evidence       != final authorization
policy ALLOW             != universal permission
policy DENY              != universal prohibition
result fingerprint       != result authentication
```

The reference method binds policy observations to an exact method, local decision scope, operation, actor, target, context, and required-dimension set. It preserves evidence validity, proof validity, authentication, attribution, identity, authority, delegation, lifecycle, authorization, trust, legal/compliance, safety, business-policy, and moderation observations as separate dimensions. Protected side effects require explicit authorization, while stale, unsupported, unresolved, conflicting, or missing required dimensions fail closed without being silently converted into universal prohibition. The Milestone 11 executable set contains 77 positive/evaluation and negative/adversarial vectors.

### Unified conformance and CI quality gate

Milestone 12 established one bounded, reproducible acceptance workflow around the then-nine Milestone 3–11 suites without changing Marketplace semantics. The manifest now also registers Milestones 13–15, so the provider-neutral gate verifies the exact OLP source pin, audits repository invariants, runs deterministic unit tests and all 745 semantic vectors, replays all twelve generators in an isolated temporary copy, and performs working-tree, staged-index, and committed-delta whitespace checks.

```text
python tools/conformance_gate.py --olp-root <path-to-pinned-olp-checkout>
```

GitHub Actions is only an infrastructure adapter around that same local command. Every subprocess has a finite timeout, suite order is deterministic, generator replay cannot rewrite the developer worktree, and CI requires no privileged secret for ordinary pull-request validation.

The Marketplace remains experimental/pre-implementation: M12 improves the reliability of the specification/conformance foundation; it does not introduce a hosted marketplace, application runtime, payment rail, trust authority, or new protocol truth.

### Dispute resolution profiles

Milestone 13 defines method-relative dispute resolution over exact OLP `disputes` relationship evidence. Disputes, source acceptance, proof, attribution, authority, lifecycle, and resolution merits remain separate dimensions; competing admissible resolutions remain visible rather than being collapsed by timestamp, majority, or hidden policy.

```text
dispute                         != falsity
resolution under method         != universal truth
resolution                      != legal judgment
resolution                      != remedy
resolution                      != authorization
```

The reference M13 profile produces bounded, deterministic, explainable results such as uphold/reject under method, partial/mixed resolution, conflicting resolution evidence, additional-evidence/human-review requirements, indeterminate, or no admissible supplied dispute. Protected side effects still require the Milestone 11 authorization boundary.

### Deployment profiles

Milestone 14 defines portable deployment composition and local readiness without creating one mandatory Marketplace server, database, queue, cloud, container platform, or transport. Runtime components bind explicit roles to replaceable adapters; services declare the roles that back each capability.

```text
deployment descriptor          != Marketplace Record
configured endpoint            != reachable endpoint
component readiness            != operator authority
service capability             != authorization
READY                           != external availability
```

The reference M14 profile derives `READY`, `DEGRADED`, or `NOT_READY` from exact local observations, suppresses capability advertisement when deployment-critical semantics are unknown, rejects credential-like descriptor fields, and requires every side-effect service to depend on both policy/authorization and side-effect-executor roles. M11 authorization is still required for each protected operation.

### Domain evaluator method profiles

Milestone 15 defines portable domain-scoped criterion methods that derive the `domain_status` consumed by M9 without duplicating evidence selection or the broader trust lattice. Methods bind explicit domains, purposes, criteria, required/optional handling, local integer weights, thresholds, and critical semantics to an exact method profile.

```text
method-local weight            != confidence
method threshold               != universal quality bar
aggregate SUPPORTS             != universal trust
aggregate UNKNOWN              != adverse evidence
positive domain result         != authorization
```

The reference criterion-threshold profile preserves support/opposition conflict, fails closed on unresolved required or unknown critical semantics, treats missing optional criteria as non-adverse, and binds exact reuse to normalized method profile, request, Record Identity, context, and observations. M9 remains authoritative for proof, identity, authority, lifecycle, source, dispute, and overall trust treatment.

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
transport serialization     != Record Identity
source completeness         != global completeness
sync absence                != deletion/retirement
receiver policy             != protocol validity
selective disclosure        != field deletion
withheld evidence            != nonexistent evidence
privacy warning              != protocol invalidity
authority evidence          != final authorization
policy ALLOW                != universal permission
policy DENY                 != universal prohibition
result fingerprint          != result authentication
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
- [`specification/0008-market-federation-transport.md`](specification/0008-market-federation-transport.md) - OLP-based federation capabilities, snapshot/sync exchange, cursor/replay/idempotency boundaries, source provenance, and receiver outcomes.
- [`specification/0009-market-trust-evaluation.md`](specification/0009-market-trust-evaluation.md) - method-relative evidence queries, exact provenance, observation dimensions, explainable traces, conflict/dispute preservation, and non-universal trust evaluation.
- [`specification/0010-market-privacy-selective-disclosure.md`](specification/0010-market-privacy-selective-disclosure.md) - OLP-based Marketplace privacy tasks, selective disclosure, correlation warnings, open-world withholding, and bounded data minimization.
- [`specification/0011-market-safety-policy-authorization.md`](specification/0011-market-safety-policy-authorization.md) - local method-relative policy decisions, authorization gates, explainable outcomes, replay binding, and non-universal permission boundaries.
- [`specification/0012-market-dispute-resolution.md`](specification/0012-market-dispute-resolution.md) - method-relative OLP dispute admission, attributable resolution evidence, conflict preservation, exact reuse binding, and side-effect separation.
- [`specification/0013-market-deployment-profiles.md`](specification/0013-market-deployment-profiles.md) - portable runtime composition, replaceable adapter roles, deterministic readiness, capability backing, secret-safe descriptors, and side-effect authorization separation.
- [`specification/0014-market-domain-evaluator-methods.md`](specification/0014-market-domain-evaluator-methods.md) - domain-scoped criterion methods, method-local thresholds, exact profile/result binding, conflict preservation, and non-universal evaluation boundaries.
- [`conformance/README.md`](conformance/README.md) - executable representation vectors and reproducibility workflow.
- [`docs/conformance-quality-gate.md`](docs/conformance-quality-gate.md) - M12 unified local/CI acceptance architecture, dependency pinning, timeout, and isolated replay boundaries.
- [`conformance/olp-source-pin.txt`](conformance/olp-source-pin.txt) - exact draft OLP source compatibility pin verified by the acceptance gate.
- [`docs/standards-landscape.md`](docs/standards-landscape.md) - initial prior-art and interoperability targets.

Future specifications will define remedy/workflow profiles where appropriate, selected deployment adapters where interoperability benefits justify them, additional domain evaluator methods where interoperability benefits justify them, and further conformance incrementally.

---

## Development principles

Development follows a maintenance-first engineering standard: small coherent changes, explicit boundaries, replaceable infrastructure, validated configuration, isolated side effects, deterministic tests, regression coverage, and green acceptance gates before completion.

The project should prefer established open standards and OLP capabilities over unnecessary invention.

---

## License

Licensed under the [Apache License 2.0](LICENSE).
