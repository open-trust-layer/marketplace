# L3-B — Inert selected transporter / logistics Agreement cross-check

**Status:** Source-only, unselected reference helper; does not activate any Marketplace workflow.  
**Parent work:** #601; builds upon L3-A purchase delivery review (#611) and L1 separate logistics Agreement link (#602).  
**Risk / capability:** MODERATE; READ_PROJECT / WRITE_PROJECT, offline focused tests. No runtime, external network, secrets, payment, dispatch, CI setting or OLP semantic change.

## Purpose

The L3-A delivery proposal is an explicit **suggestion**, not an agreement. The L1 logistics Agreement-link validator separately identifies the exact purchase Agreement, targeted purchase commitment and transport performer. Before an application can even consider a third-party transport proposal, these two independently reviewed identities must match.

`review_selected_logistics_agreement` is an *inert* composition that:

1. Revalidates the exact `DeliverySelectionDraft` against an existing two-party purchase Agreement and its seller-delivery commitment.
2. Requires one explicitly proposed `independent_courier` or `partner_carrier` mode. Seller-managed delivery is intentionally out of scope.
3. Calls L1's existing validator to read the exact separate delivery Agreement and transport commitment, including purchase source and commitment link.
4. Requires the reviewed purchase Agreement identity and purchase commitment ID to match, and the exact named transport performer to equal the proposed provider principal.
5. Returns immutable IDs and source mode only. Outputs `IDENTITY_MATCH_ONLY` and permanent false consent, attribution, eligibility, dispatch, settlement and goods-fulfillment fields. Errors are stable, content-free codes.

## Not proven by matching identifiers

A valid OLP RecordV1 or exact local match **does not** demonstrate signatures, consent, legal qualification, route availability, quotations accepted, insurance, pickup, buyer receipt, objective delivery, a lawful contract, or authority to pay or dispatch. The helper does not verify OLP proofs, query trust/eligibility systems, recruit couriers, contact carriers, load addresses/GPS, create an Agreement, choose a live route, persist data or call a network service.

The operator must establish these gates separately. This helper must not be registered in public HTTP/Web/Android composition until reviewed proof/assent, capability, authorization, privacy retention, legal jurisdiction and user-consent controls are implemented and accepted.

## Validation and rollback

- Test: `PYTHONPATH=src:<pinned-olp-root>/src python -m unittest tests.test_logistics_l1_agreement_link tests.test_purchase_delivery_selection_review_v1 tests.test_selected_logistics_agreement_review_v1 -v`.
- Test positive courier and carrier linkage, immutable/non-authoritative output, seller-mode rejection, provider substitution, wrong purchase source, tampering, malformed records and sensitive-data nonreflection.
- Final branch needs its own protected, exact-head GitHub `acceptance` and independent postmerge `main` acceptance. Earlier tests on component branches are not a substitute.
- Rollback: remove the new reference helper, tests and this document. No new dependencies, migrations, live processes, production data or wire-profile semantics.

M2/M3 operational courier onboarding, consent and real dispatch remain **OPEN** under #601. Real authenticated buyer/seller flight #525 and authoritative host #528 are separate blockers.
