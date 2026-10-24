# L3-B — Third-party proposal and logistics Agreement coherence review

**Status:** Source-only / unselected; no execution authority.
**Dependency:** Merged L3-A purchase selection, L1 courier Agreement linkage, and immutable OLP/Marketplace RecordV1 semantics.
**Scope:** An independent courier or partner-carrier *proposal* referencing one goods purchase must match the named performing principal in a **distinct** delivery-service MarketAgreement, including the exact original purchase commitment.

## Decision

The existing L3-A `review_purchase_delivery_selection` examines a proposed seller/buyer/performer arrangement against the immutable goods purchase Agreement. The existing L1 `inspect_delivery_agreement_link` checks the delivery Agreement's exact purchase source reference and target commitment and identifies the carrier's transport commitment.

L3-B adds one **unselected** pure application-domain helper, `marketplace.logistics.purchase_selection_link_review_v1.review_delivery_selection_link`, to require *both* reviews to agree:

1. The proposal is either `independent_courier` or `partner_carrier`; a seller-managed proposal does not silently require or select an additional courier Agreement.
2. The purchase Agreement is an immutable validated OLP MarketAgreement with exactly the expected buyer/seller parties and seller-owned `seller-delivery` commitment (L3-A).
3. The separate delivery Agreement is valid under the existing L1 exact purchase Agreement/commitment link and transport-commitment profile, with the purchase seller included as a party.
4. The linked purchase identity and original commitment **match the L3-A review**, rather than merely pointing to another commitment in the same purchase.
5. The delivery-service transport principal equals the **explicitly proposed** third-party provider. Neither a different courier nor the seller can be substituted for the selected third party.

Any mismatch or invalid input fails closed with a stable bounded error code, without echoing agreement terms, personal address data or user-controlled strings. A positive result contains only record identities, commitment IDs, the proposed mode, seller/provider principals, and **`status=CONSISTENT_PROPOSAL_ONLY`**.

## Strictly absent authority

The projection permanently reports `assent_verified=False`, `dispatch_authorized=False`, `settlement_authorized=False` and `goods_fulfilled=False`. It does **not**:

- verify OLP cryptographic proofs, parties' signatures, courier qualifications, business jurisdiction or the legal enforceability of an agreement;
- negotiate or publish a delivery agreement, contact a courier, schedule pickup, create a shipment, select a route, or trigger a provider adapter;
- access recipient addresses, persist tracking/GPS, collect customer data, charge a shipping fee, release goods payments, or infer buyer acceptance.

The owner or runtime must separately establish approved identity/authority, assent, retention, jurisdictional permissions and proof evaluation before considering any live flow. Product acceptance blockers #525 (authenticated buyer/seller flight) and #528 (authoritative service-host classification) remain open.

## Regression and stop criteria

Focused tests exercise exact courier and partner matches, wrong performer (including a seller masquerading as an external carrier), wrong immutable purchase identity, a different valid purchase commitment, invalid draft and record types, missing delivery profile, seller-managed mode exclusion, sensitive-term non-disclosure, and immutable deterministic output. The existing L1/L2/L3-A and reference-architecture regression tests run alongside the new cases.

Rollback is a narrow revert of this unselected helper, tests and document; there is no runtime state, database schema, network process, API route, financial or OLP protocol mutation.

**Follow-up:** separately designed consent/assent gates and private shipping-address handling for seller-managed handoff; independent courier job discovery and quotation belong to L4. No real pilot or dispatch is authorized by this review contract.
