# Initial Standards Landscape

**Status:** Milestone 1 research note  
**Normative:** No

This note records established standards and vocabularies that later marketplace specifications should evaluate before inventing overlapping mechanisms.

It does **not** assert that any external term is semantically identical to a marketplace term. Formal mappings require explicit profile/version work in later milestones.

## 1. Open Layer Protocol (OLP)

Source: https://github.com/open-trust-layer/protocol

OLP is the marketplace evidence substrate. It already addresses immutable records, cryptographic proofs, evidence relationships, identity/authority evidence, lifecycle evidence, bundles, resolution, privacy boundaries, transport profiles, and conformance.

Marketplace work should compose these capabilities rather than create a parallel evidence or trust layer.

The marketplace must track explicit OLP profile/version compatibility once marketplace wire representations are defined. Milestone 1 deliberately does not pin a marketplace representation to a still-evolving OLP candidate profile.

## 2. Schema.org Offer and Demand

Sources:

- https://schema.org/Offer
- https://schema.org/Demand
- https://schema.org/itemOffered
- https://schema.org/Action

Schema.org defines widely deployed vocabulary for offers, demands, items, prices, eligible regions, availability, and actions.

Its `Offer` concept can describe transfer of rights or provision of a service, while `Demand` describes a public announcement seeking goods or services. Schema.org also separates the item offered from the transactional/business function applied to it.

Marketplace implication:

- `Intent` should be capable of mapping to compatible `Offer` and `Demand` cases without being restricted to them.
- `Subject` should remain distinct from the market action concerning the subject.
- domain profiles should reuse Schema.org identifiers/properties where their semantics are sufficient.

No one-to-one equivalence is declared in Milestone 1.

## 3. GoodRelations

Source: https://www.heppnetz.de/ontologies/goodrelations/v1.html

GoodRelations models offerings, business entities, products/services, business functions, prices, quantities, eligible counterparties, locations, and related commercial properties. Its business-function concept distinguishes actions such as sell, lease, repair, construction, and disposal from the underlying item.

Marketplace implication:

The separation:

```text
Subject != Action
```

has strong prior-art support. Marketplace `Action` profiles should evaluate reuse/mapping of GoodRelations business functions rather than inventing an incompatible transaction-function vocabulary unnecessarily.

GoodRelations is narrower than the marketplace's intended universal subject model, so it is an interoperability source rather than the entire foundation.

## 4. ActivityStreams 2.0

Source: https://www.w3.org/TR/activitystreams-vocabulary/

The W3C ActivityStreams vocabulary defines actors, objects, collections, and activities including `Offer`, `Accept`, `TentativeAccept`, `Reject`, `Invite`, `Create`, `Update`, `Delete`, and `Undo`.

Marketplace implication:

ActivityStreams provides useful prior art for expressing attributable activities and responses. Later agreement/lifecycle work should examine whether selected marketplace events can map to or reuse ActivityStreams semantics.

ActivityStreams does not replace OLP evidence identity, proof, authority, or verification semantics.

## 5. ActivityPub

Source: https://www.w3.org/TR/activitypub/

ActivityPub provides W3C-standard client-to-server and federated server-to-server delivery based on ActivityStreams 2.0.

Marketplace implication:

ActivityPub is a candidate transport/federation mechanism for some discovery and notification profiles.

It should not be assumed to be the only federation mechanism, and using ActivityPub would not by itself solve marketplace evidence verification, private discovery, agreement semantics, settlement, or authorization.

## 6. OASIS Universal Business Language (UBL)

Source: https://docs.oasis-open.org/ubl/UBL-2.4.html

UBL defines reusable business components and documents such as Order, Tender, Despatch Advice, Receipt Advice, Invoice, and many procurement/transport artifacts.

Marketplace implication:

Later domain profiles for procurement, orders, logistics, invoicing, and fulfillment should evaluate UBL interoperability instead of defining replacement document vocabularies without a concrete gap.

Marketplace core remains more abstract because it must also describe domains that are not conventional order-to-invoice commerce.

## 7. Open Contracting Data Standard (OCDS)

Source: https://standard.open-contracting.org/

OCDS models and publishes data across contracting stages including planning, tendering, award, contract, and implementation.

Marketplace implication:

The marketplace's separation of:

```text
Intent / Proposal
!= Agreement
!= Fulfillment / implementation evidence
```

is compatible with the general observation that procurement and contracting have distinct lifecycle stages. Public-procurement profiles should evaluate OCDS mappings rather than flattening those stages into a generic listing object.

OCDS is disclosure-focused and public-contracting-specific; it is not a universal marketplace protocol.

## 8. Standards posture

Milestone 1 adopts the following rule:

> Reuse or map to established standards when their semantics fit; create new marketplace semantics only for gaps required by the universal coordination model or OLP integration.

Later specifications should document, for each significant external mapping:

1. the exact external standard/version;
2. the marketplace concept being mapped;
3. whether the mapping is exact, narrower, broader, or lossy;
4. canonical transformation rules where interoperability requires them;
5. security and privacy consequences; and
6. behavior when the external standard cannot represent required marketplace semantics.

No normative external mappings are established by this research note.
