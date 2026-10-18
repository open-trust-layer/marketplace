# L1 — Logistics agreement linkage (source-only architecture decision)

**Date:** 2026-10-19  
**Status:** Initial L1 application-domain contract, unselected; not a production capability  
**Risk:** MODERATE — new domain profile and reference validator only  
**Decision:** Reuse existing OLP RecordV1 / Marketplace MarketIntent, MarketAgreement and MarketEvent. No fourth record type, global courier operator, payment rail, or mutable universal shipment state.

## Context and verified baseline

- Specifications 0002, 0003 and 0006 already define Marketplace agreement, commitment references, attributable performance/delivery evidence and method-relative fulfillment. 0007 defines payment-rail-neutral settlement *interfaces*, not payment execution.
- M17.7A–P introduced seller-attributed fulfillment completion flows. Authenticated live buyer/seller acceptance remains pending under issue #525; production attestation remains pending under #528.
- No dedicated courier marketplace, shipment job discovery, carrier adapter, shipping quotations, tracking lifecycle, or operational delivery pilot is proven by this L1 slice.
- Any seller, courier, and provider role is a policy/context distinction, not proof of real-world identity, licensing or authorization.

## Decision: independent delivery agreement linked to purchase

The purchase retains its original immutable MarketAgreement and the exact seller-performance CommitmentRefV1. A delivery service is **another** MarketAgreement, with explicit assent by its participants before relying on it. The courier service may have its own MarketIntent and negotiation terms; these are not required to be implicitly created by the L1 validator.

The L1 delivery Agreement uses existing Marketplace v1 fields:

| Field | Required L1 representation | Meaning |
| --- | --- | --- |
| OLP record type | MarketAgreementV1 | No new record type |
| Profile | `https://open-trust-layer.github.io/marketplace/semantics/v1/profile/logistics-delivery-v1` | Optional logistics-domain semantics |
| `source_records` | Contains exact OLP RecordRef to purchase Agreement | Discoverable provenance, not assent |
| `terms[.../term/logistics-purchase-commitment]` | Exactly `{record: RecordRef, id: LocalId}` | Exact purchase CommitmentRef, not bare local ID |
| `actions` | Contains `.../action/logistics-transport` | Describes service without authorizing it |
| `commitments` | Exactly one transport-action commitment in L1 | Names the proposed performing principal |
| `parties` | Includes principal named in the targeted purchase commitment | Keeps original seller in the service agreement |
| Personal delivery details | No extra L1 terms accepted | Do not publish recipient addresses or tracking in durable public agreement |

All URIs above share the existing Marketplace semantic base:
`https://open-trust-layer.github.io/marketplace/semantics/v1`.

A seller may also be the transport performer (seller-managed). An independent courier or transport company may be the performing party instead. L1 does **not** automatically assume the courier has agreed to the proposed agreement. A future authority/assent gate must establish this separately.

The optional `marketplace.logistics.agreement_link_v1.inspect_delivery_agreement_link` function is a pure, read-only, exact-record/commitment validator. It returns an identity-only projection for local applications. It accepts only validated immutable OLP MarketAgreements, requires an exact parent source record and CommitmentRef, rejects self-reference, mismatches, ambiguity, missing seller role and missing transport performer. It never writes an event, assigns a courier or authorizes a shipment. It does not prove ownership, pickup, delivery, buyer receipt, agreement formation, settlement, or legal compliance.

**Compatibility:** The profile is not imported by Marketplace Core, runtime composition, API routes, Web or Android. Older records and clients remain unchanged. Domains may add new profile versions later; L1 rejects unknown additional *link terms* rather than silently interpreting them.

## Proposed future delivery lifecycle (L2, not implemented by L1)

The local application projection will represent:

`REQUESTED → QUOTED → ASSIGNED → PICKUP_READY → PICKED_UP → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED → CONFIRMED`

Each operational status is a method-relative projection over attributable MarketEvents and policy-admitted external observations. Events must identify exact agreement/commitment targets when asserting commitment performance. Conflicting, unavailable, untrusted or unauthorized evidence must not turn into a positive conclusion. `DELIVERED` is not `CONFIRMED`; carrier assertion is not buyer acceptance; neither is settlement.

Exceptions to model explicitly in L2: cancellation, failed pickup, failed delivery, recipient unavailable, damaged/lost goods, return to sender, disputes, partial delivery, refunds and compensation requests. They do not silently alter a purchase or a payment ledger.

## Privacy and authorization boundary

- No public immutable payload containing recipient address, telephone, detailed GPS history, delivery photograph or private handling instructions.
- Future address/contact disclosure must be purpose-scoped to authorized delivery participants with bounded lifetime and revocation/retention procedures. Consent-based GPS collection is optional, not assumed.
- Independent participants require appropriate identity/evidence, permission and jurisdictional eligibility checks before accepting or fulfilling a shipment.
- Shipment events and carrier tracking data must distinguish observation/claim, accepted attribution and method-relative outcome.
- No payment execution or automatic escrow release. Shipping compensation is separate from the product consideration; Moon Coin is merely a future optional integration, not a required or active rail.

## Gap classification and roadmap

| Capability | 2026-10-19 assessment |
| --- | --- |
| MarketAgreement / CommitmentRef / event identity and evidence | **Already implemented/tested** in existing protocol/reference scope |
| Seller claim of completion for existing seller-delivery commitment | **Supported in source/CI**, authenticated live acceptance pending |
| Separate courier service Agreement referencing purchase | **L1 source-only contract/validator introduced here**; no UI or publication |
| Seller-managed operational delivery | **Missing application workflow**, L3 |
| Courier discovery/quotes/matching/assignment | **Missing**, L4 |
| Tracking, confirmation, returns, disputes | **Partially supported by generic evidence semantics**; logistics workflow missing, L2/L5 |
| Third-party carrier adapters | **Missing**, L6; real provider needs separate approval |
| Shipping prices, settlement adapters | **Generic interfaces exist**; shipping-specific contracts missing, L7; no money movement |
| International compliance and customs | **External/legal dependency and application work**, L8 |
| EN/RU Web and Android logistics UX | **Missing**, L9; Android acceptance separate |
| Real operational pilot | **Not authorized or demonstrated**, L10 |

## Incremental execution and validation

1. **L1 (this work unit):** optional exact agreement-link profile, pure validator, positive/negative tests, architecture decision, roadmap entry. No new dependencies, no runtime selection.
2. **L2:** event vocabulary and deterministic reducer with explicit unknown/conflict/exception handling. Add adversarial/authorization tests and evaluate against existing fulfillment evaluator.
3. **L3:** authorized seller-managed delivery flow in the application; preserve offline and authenticated buyer/seller gates.
4. **L4–L9:** add replaceable courier/provider systems and bilingual clients by separate coherent PRs, with privacy and payment controls.
5. **L10:** require separately approved and geographically scoped real-world pilot after operational/legal/security evidence.

**Rollback:** Revert the L1 code, tests and this document/roadmap update. Because the module is unselected, no data, network, deployment, Android build, active payment or running service needs migration or cleanup.

**Stop conditions:** Any need to alter OLP identity/proof semantics, expose private delivery data publicly, automatically perform protected side effects, change deployed runtime or bypass acceptance policy requires a new review and corresponding authority.
