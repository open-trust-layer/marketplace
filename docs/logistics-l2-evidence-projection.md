# L2-A — Read-only delivery lifecycle projection

**Status:** proposed, source-only application-domain evaluator (not activated)  
**Dependency:** [L1 exact purchase-to-delivery Agreement link](logistics-l1-architecture.md)  
**Risk:** MODERATE. No OLP protocol changes, runtime activation, shipping, payment, location access, or proof verification.

## Purpose and boundary

A delivery lifecycle is not a mutable universal record status. This initial evaluator accepts externally reviewed OLP `MarketEventV1` claims targeting exactly one delivery-service `MarketAgreementV1` and its transport commitment. It produces a **method-relative, identity-only application projection**. The separate purchased goods Agreement, seller delivery commitment and its eventual fulfillment evaluation remain unchanged.

This is a **post-agreement review projection**: the first three events (REQUESTED, QUOTED, ASSIGNED) are *claims examined retrospectively* after a proposed service agreement exists. It does **not** expose a job board or execute pre-agreement requests, quotations or assignment. Actual negotiation and explicit assent remain a separate L4 workstream.

## Inputs and evaluation

`project_delivery_events(purchase_agreement, delivery_agreement, buyer_principal, reviewed_events)` requires:
- L1 valid separate logistics Agreement linked to the exact original purchase Agreement and commitment.
- A purchase Agreement with exactly one non-seller principal identified as the buyer for this narrowed profile. More complex multiparty cases fail closed rather than silently selecting a recipient.
- Up to 256 `ReviewedDeliveryEvent` entries, each with one immutable `RecordV1`, distinct positive sequence, and explicit Boolean `attribution_accepted` and `authority_accepted` assessments from an external relying method.
- Events whose profile contains both core-v1 and logistics-delivery-v1, with exactly version, issuer, event, and an exact delivery-service CommitmentRefV1. No address, GPS track, photo, timestamp-based hidden precedence, or extra fields.

The evaluator does not verify OLP cryptographic proofs or determine external authority. It is the caller's separate obligation to establish attribution and policy permission before supplying accepted review flags. A positive flag from an untrusted caller is **not** sufficient runtime authorization, and the function must remain unselected from public transports until a reviewed admission boundary is in place.

The explicit integer sequence defines one local review ordering method, **not** authoritative event chronology. Different orderings may yield different provisional conclusions; that is intentional and must remain visible to clients.

## Milestones

The projection admits one non-skipping forward sequence:

`REQUESTED → QUOTED → ASSIGNED → PICKUP_READY → PICKED_UP → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED → CONFIRMED`

Expected event issuers are seller for REQUESTED, ASSIGNED, PICKUP_READY; courier/transport performer for QUOTED through DELIVERED; buyer for CONFIRMED. A seller may simultaneously be the transport performer in seller-managed delivery. No issuer can self-certify buyer receipt unless that issuer is the independently identified buyer.

Exception claims are tracked additively, never erased:
`CANCELLED`, `FAILED_PICKUP`, `FAILED_DELIVERY`, `RECIPIENT_UNAVAILABLE`, `DAMAGED`, `LOST`, `RETURN_TO_SENDER`, `DISPUTED`, `PARTIAL_DELIVERY`, `REFUND_REQUESTED`.

Exception actor roles and admissible stages are bounded. E.g., cancellation/refund requests originate from seller/buyer, delivery failure and return-to-sender reports from courier, and missing pickup confirmation cannot be invented from later assertions. All exception claims remain claims; they do not prove objective damage, a legal refund entitlement, or a completed dispute determination.

## Outputs and fail-closed conditions

`DeliveryProjection` holds `stage` (UNKNOWN or latest admitted ordered milestone), `status` (INSUFFICIENT, PROVISIONAL, EXCEPTION, CONFLICT), exception codes and exact OLP Record Identity references for admitted, excluded and conflicting events.

- No evidence → INSUFFICIENT / UNKNOWN.
- Reviewed but untrusted or unauthorized event → excluded, no status advance.
- Skipped/out-of-order positive milestone → CONFLICT, never silently fills in missing evidence.
- Delivered without later buyer-attributed, independently admitted CONFIRMED → **DELIVERED only**, not confirmed.
- Any admitted exception without later reviewed remedy evidence → EXCEPTION, not clean provisional success (including disputes after buyer receipt).
- Because this first profile has no accepted remedy/resumption event, subsequent progress after an admitted exception → CONFLICT; no implicit recovery from failed pickup, cancellation, loss, dispute or partial delivery.
- Wrong purchase/delivery/commitment target, nonconforming event, unexpected extension, duplicate identity or review sequence, invalid actor, ambiguous buyer or oversized input → fail closed with content-free error code.

**PROVISIONAL** is not a platform truth assertion. Even `CONFIRMED` remains method-relative admitted evidence and is not a payment-release trigger, a proof that goods physically arrived or an unconditional final fulfillment conclusion. Positive settlement still requires a separate reviewed authority and rail-specific execution policy.

## Not implemented

No live APIs, Web or Android UI, OLP evidence issuance, courier onboarding, dispatcher, carrier integration, user permissions, cryptographic attestation verification, trusted clocks, persistence, real shipping or payments. Real request/quote/assignment workflows, reconciliation of conflicting evidence from federation, cancellation rights and cross-border eligibility remain future reviewed work.

## Tests and rollback

`tests/test_logistics_l2_lifecycle_projection.py` covers the full synthetic progression, seller/courier/buyer actor separation, authority rejection, skipped steps, duplicated IDs/review sequence, wrong targets, invalid payloads, exception preservation and cancellation/receipt conflicts. It uses disposable synthetic OLP records only.

Validate on a **specific source head** with an exact pinned OLP source checkout:

`PYTHONPATH=src:<olp-root>/src python -m unittest tests.test_logistics_l1_agreement_link tests.test_logistics_l2_lifecycle_projection -v`

Full protected `acceptance` CI is required before merger. Undo the L2 source/tests/docs to roll back; no migration, live service or real-world side effects exist.
