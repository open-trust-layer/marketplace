# Physical delivery responsibility — Marketplace proposal V1

**Status:** source-only application planning, **NOT** a shipment, carrier integration, Agreement, dispatch, price quotation, payment, OLP semantic extension, or public product activation. [Issue #601](https://github.com/open-trust-layer/marketplace/issues/601) tracks incremental logistics execution.

## Who delivers when a buyer accepts a product offer?

The actual physical executor must be chosen explicitly. No one is automatically hired or paid simply because a buyer accepts a Marketplace listing:

| Mode | Proposed physical executor | Product seller's existing `seller-delivery` commitment | Additional service Agreement |
| --- | --- | --- | --- |
| `seller_delivery` | The seller/performer | Still seller-attributed under current product profile | No, absent separately negotiated services |
| `independent_courier` | A distinct courier Marketplace participant | **Still** seller-attributed; courier evidence cannot impersonate the seller | **Required** before any courier is authorized to carry goods |
| `partner_carrier` | A distinct carrier/provider | **Still** seller-attributed; partner evidence does not prove fulfillment | **Required**, with explicit provider-side authorization |

The first private-alpha path is seller delivery. Independent couriers are a **separate Marketplace service**, not automatically an extension of buyer/seller consent. Existing carrier APIs are a later opt-in integration. This same model can be localized for city-level and international markets only after reviewing actual routes, capacity, prices and jurisdiction-specific obligations.

## Source-only interface

`marketplace.application.delivery_selection_v1` exposes `DeliverySelectionDraft`, `plan_delivery_selection`, and immutable `DeliverySelectionPlan`. The input requires an explicit mode plus distinct seller and buyer principal URIs. External modes require an additional, distinct proposed provider principal URI. Seller mode rejects a hidden third-party principal.

The output only identifies a **proposed** executor and the remaining seller commitment; it carries:

- `state=PROPOSAL_ONLY`
- `dispatch_authorized=False`
- `payment_authorized=False`
- `seller_delivery_fulfilled=False`
- `quote_and_consent_required=True`
- `distinct_delivery_service_agreement_required=True` for external providers

No silent mode default, provider selection, shipment record, authorization, settlement or OLP Record is created. Principal URI shape and byte length are reviewed syntactically; this does **not** authenticate the principal, credential or role.

## Proposed future workflow, not implemented by this patch

1. Buyer and seller negotiate a goods Agreement, with explicit scope for who is responsible for transport, handoff, loss, returns and inspection. Any change to the product commitment requires correct immutable Agreement revision and renewed consent; never silently rewrite the existing `seller-delivery` commitment.
2. For an independent courier or carrier, a separate delivery-service listing/quote and Agreement binds the actual paying party and courier, with pickup, route/service area, timing, cargo restrictions, handoff evidence, exceptions and remedies. Each party separately assents before dispatch.
3. A dispatch adapter may reserve work only after verified identity, authority, provider acceptance, policy checks, pricing/quote approval, and provider availability. Fail closed on missing consent, mismatched principal or duplicate dispatch.
4. Delivery, inspection, acceptance/rejection, claimed completion and disputes remain separate attributable immutable evidence. A courier event targets the courier's exact service Commitment, **not** the seller's product Commitment. Seller completion must be attributed to the actual seller under `specification/0006`; carrier handoff evidence may support their assertion but cannot forge it.
5. Payment/settlement is separately authorized and independently evidenced; a delivery record does not release escrow or transfer title. Partner API updates are untrusted until source and authorization are checked.

## Safety, privacy and release boundary

This step stores **no addresses, live positions, delivery instructions, recipient contact data, route histories, prices, bank details, API secrets, credentials or Moon Coin activity**. Later collection must specify purpose, receiver access, retention deadline, disclosure minimization, opt-in location scope and user removal/withdrawal behavior. Marketplace does not guarantee legality, physical shipment, carrier performance or objective truth.

External dispatch, web/mobile user journeys, provider eligibility/insurance, regional/international regulation, agreement formation, actual fulfillment, payments, shipment tracking and disputes are future work. Current real authenticated browser acceptance [#525](https://github.com/open-trust-layer/marketplace/issues/525) and production-host/TLS acceptance [#528](https://github.com/open-trust-layer/marketplace/issues/528) are separate release blockers.

## Test

Run the pure in-process review cases without network, OLP or third-party packages:

```sh
PYTHONPATH=src python3 -m unittest tests.test_delivery_selection_v1 -v
```

No automatic production rollout is authorized by merging this source-only milestone.
