# Marketplace — Principles

**Status:** Project principles
**Applies to:** marketplace semantics, specifications, implementations, discovery, matching, agents, federation, and project governance

The marketplace exists to make economic coordination open and interoperable without making ownership, legality, value, reputation, or trust centrally owned.

These principles are architectural constraints, not marketing slogans. When a proposed feature conflicts with them, the conflict must be explicit and the burden of proof lies with the proposal.

## 1. Intent over product taxonomy

The universal marketplace model should describe what participants want to do rather than require every possible subject to fit a closed product taxonomy.

A software bug, a physical object, a service opportunity, a company, infrastructure, an asteroid, or a galaxy may all be referenced as subjects of market intent.

Domain profiles may specialize semantics. The universal layer should remain small.

## 2. Subject-scale neutrality

Physical size, monetary value, complexity, and domain must not determine whether something can be referenced as a marketplace subject.

Being representable does not imply that the subject is ownable, transferable, lawful to exchange, physically reachable, or economically meaningful.

## 3. Representation is not ownership

A marketplace reference, listing, intent, claim, or agreement must never become protocol-level proof of ownership merely because it exists.

Claims of ownership, custody, authority, title, licensing power, or transfer rights require separate evidence and remain subject to contextual evaluation.

## 4. Evidence over platform reputation

Where trust-relevant claims matter, participants should be able to inspect portable evidence rather than depend exclusively on a proprietary platform score or hidden moderation history.

Applications may derive reputation or risk assessments, but those judgments remain application-specific and separable from the underlying evidence.

## 5. OLP is the evidence substrate

Open Layer Protocol (OLP) provides the portable evidence layer.

The marketplace must not duplicate OLP's record, proof, identity, authority, lifecycle, bundle, resolution, privacy, or conformance mechanisms without a demonstrated need.

Marketplace semantics should reference and compose OLP evidence rather than create a parallel trust protocol.

## 6. Evidence is not truth

A valid record, proof, listing, claim, or observation does not make its content true.

Cryptographic verification establishes defined integrity or attribution properties. It does not establish ownership, legal validity, quality, safety, fulfillment, or factual accuracy by itself.

## 7. Participant neutrality

Humans, organizations, software agents, services, devices, and other actors recognized by an application may participate without receiving automatic marketplace privilege solely because of actor type.

Applications and law may legitimately distinguish actor types. The universal semantic layer should not invent a single global hierarchy among them.

## 8. No mandatory central marketplace operator

The architecture must not require one company, server, database, ranking engine, or marketplace UI to remain globally authoritative.

Multiple applications, indexes, agents, and federation nodes should be able to discover and interpret compatible market evidence according to their own policies.

## 9. Discovery is not endorsement

Finding, indexing, matching, ranking, or displaying an intent does not mean the protocol or an implementation endorses it.

Applications must remain free to filter, reject, quarantine, moderate, or require additional evidence according to law, safety, policy, and risk.

## 10. Protocol expressibility is not permission

The ability to represent a subject, intent, action, or term does not make that activity lawful, safe, ethical, authorized, or permitted by a deployment.

The protocol must not be treated as a mechanism for bypassing application authorization, moderation, compliance, or jurisdiction-specific rules.

## 11. Intent is not agreement

An intent is an attributable expression of willingness, need, availability, or desired coordination.

It does not become an agreement merely because another compatible intent exists or a matching engine associates them.

Agreement requires explicit evidence of assent according to a defined profile.

## 12. Agreement is not legal enforceability

A marketplace agreement records or references evidence that participants assented to defined terms.

Whether that agreement forms an enforceable contract, what law applies, and what remedies exist are contextual legal questions outside the universal marketplace semantic layer.

## 13. Settlement neutrality

The marketplace must not require one payment processor, bank, currency, token, escrow system, barter mechanism, asset registry, or settlement network.

Settlement systems are replaceable external capabilities or profiles.

The marketplace should make settlement evidence portable where useful without turning settlement infrastructure into the source of universal trust.

## 14. Blockchain neutrality

The marketplace does not require a blockchain, cryptocurrency, token, distributed ledger, or consensus network.

Such systems may be used for settlement, anchoring, asset representation, transparency, or other purposes when selected by participants or profiles, but they remain optional infrastructure.

## 15. Price is not value

A quoted price, bid, valuation, exchange ratio, or consideration term is an attributed market expression, not a universal measure of value.

Different participants and applications may value the same subject differently.

## 16. Fulfillment is evidence-based and disputable

Claims that an obligation was performed, delivered, accepted, rejected, partially completed, or breached should remain attributable evidence.

Payment does not automatically prove fulfillment. Delivery does not automatically prove acceptance. One participant's outcome claim must not silently overwrite another's.

## 17. Additive history

Published historical evidence should not be silently rewritten.

Corrections, withdrawals, supersession, disputes, cancellation, completion, revocation, and other lifecycle changes should be represented through additive evidence and explicit relationships.

## 18. Privacy by architecture

Marketplace discovery can create severe correlation and surveillance risks.

Implementations and specifications must consider data minimization, selective disclosure, identifier reuse, discoverability, indexing, retention, and graph correlation from the beginning.

Public-by-default is not a universal requirement.

## 19. Jurisdictional plurality

The universal semantic layer must not encode one jurisdiction as the global authority for ownership, contract formation, taxation, licensing, consumer protection, employment, securities, sanctions, or other legal questions.

Applications may enforce jurisdiction-specific policies and may require evidence relevant to them.

## 20. Algorithm plurality

Matching, search, ranking, pricing, recommendation, risk assessment, fraud detection, reputation, and trust algorithms must remain replaceable.

The protocol may define interoperability requirements but must not canonize one universal market algorithm.

## 21. Open interoperability before invention

Where established open standards adequately solve identity, payment, transport, schema, geospatial, units, legal-document, or other domain problems, the marketplace should interoperate with them rather than create unnecessary replacements.

New mechanisms should exist because a genuine semantic or interoperability gap requires them.

## 22. Explicit lifecycle and state

Marketplace objects with lifecycle semantics must use explicit, interpretable state transitions or evidence relationships.

Ambiguous combinations of mutable flags should not become the foundation of agreement, fulfillment, dispute, or settlement logic.

## 23. Profiles enrich; core stays small

The universal core should define only concepts necessary across domains.

Domain-specific detail belongs in composable profiles such as software work, physical goods, logistics, compute, energy, licensing, research, infrastructure, or future space-related coordination.

A profile must not silently redefine foundational core semantics.

## 24. Independent implementation

Core marketplace semantics should be implementable and interpretable independently from explicit inputs and published specifications.

No hidden proprietary database, privileged resolver, secret ranking model, or central operator should be required to understand normative marketplace objects.

## 25. Safety by architecture

Implementations must treat market input as untrusted and should support explicit authorization, validation, moderation, abuse controls, bounded resource use, and policy enforcement.

Open coordination is not an excuse for unbounded execution, arbitrary code or network access, unsafe automation, or silent policy bypass.

## Architectural consequence

These principles imply recurring separations throughout the project:

```text
subject representation      != ownership
listing                     != transfer right
claim of ownership          != ownership
identity                    != authority
authority evidence          != legal sufficiency
market visibility           != legitimacy
discovery                   != endorsement
intent                      != match
match                       != agreement
agreement                   != legal enforceability
agreement                   != settlement
settlement                  != fulfillment
payment                     != completion
fulfillment evidence        != acceptance
price                       != value
evidence                    != truth
verification                != endorsement
reputation                  != universal trust
protocol expressibility     != permission
```

## Changing these principles

These principles may evolve as the project matures, but changes should be deliberate, documented, and reviewed against the long-term goal:

> **Enable open, interoperable economic coordination around arbitrary subjects while keeping evidence portable and ownership, legality, value, policy, and trust contextual rather than centrally dictated.**
