# Marketplace logistics L3-A — purchase-to-delivery selection review

**Status:** unselected source-only review contract, not a seller dispatch flow or a live shipment.
**Depends on:** PR #603's merged `delivery_selection_v1` proposal module, not on L1/L2 branch heads.

## What this changes

A seller-managed goods order must not silently become a courier job. The existing `DeliverySelectionDraft` proposes one explicit performer for an existing goods purchase Agreement. The reference-layer adapter `review_purchase_delivery_selection` now checks that the choice is consistent with the immutable original `MarketAgreementV1`:

- Requires the valid Marketplace/OLP purchase Agreement, exactly two known participants (one seller, one buyer), and a uniquely identified `seller-delivery` commitment attributed to that same seller.
- For `seller_delivery`, keeps the seller as proposed physical executor. The seller's original goods-delivery obligation remains unchanged.
- For `independent_courier` or `partner_carrier`, keeps the original seller responsible for its own goods commitment but marks a **distinct, separately negotiated and consented logistics Agreement required**. It never creates one, consents on another actor's behalf, or makes a courier a party to the goods purchase.
- A mismatch in buyer/seller, wrong commitment actor, missing required commitment, unsupported or tampered input fails closed with a bounded, content-free error.
- Output includes only purchase Record Identity, original commitment ID, selected mode, seller and proposed performer principals, separate-agreement-needed flag, and permanent nonauthorization fields.

The projection always reports `PROPOSAL_ONLY`, `consent_verified=False`, `dispatch_authorized=False`, `settlement_authorized=False`, and `goods_fulfilled=False`.

**Important:** The existence or validity of a RecordV1 does not prove actual assent, signature authorization, delivery, purchase fulfillment or a legal right to charge. Even this matched proposal cannot release payments, allocate routes, send offers to real couriers, collect private addresses, persist geolocation, send notifications, or use carrier APIs.

## Boundary and pending scope

This milestone is an **identity/commitment preflight**, not a solution for L3's remaining seller-side logistics operations. It does not provide shipping quotes, localized address handling, recipient availability, seller dispatch UX, multi-party purchases, returns, pickup handoffs, buyer notifications, acceptance, proof verification or L2 exceptional-case resolution. Later additions require independently reviewed authority, privacy/retention, legal eligibility and evidence-policy checks.

It intentionally does **not** import L1's unmerged agreement-link helper. Once L1 lands, a separate testable method can verify the selected courier and exact purchase-to-logistics Agreement links without claiming that selection forms an Agreement.

## Validation and rollback

Run in a disposable source checkout with pinned OLP:
`PYTHONPATH=src:<pinned-olp-root>/src python -m unittest tests.test_delivery_selection_v1 tests.test_purchase_delivery_selection_review_v1 -v`

The separate GitHub `acceptance` check on this exact PR head and protected-main governance remain mandatory. Revert only these source, test and docs changes to roll back. No database schema, service, process, wire protocol, custody, finances or production configuration has been changed.
