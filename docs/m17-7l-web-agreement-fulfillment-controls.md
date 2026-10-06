# M17.7L — Explicit Web Agreement publication and fulfillment controls

Profile: `MARKETPLACE_WEB_AGREEMENT_FULFILLMENT_CONTROLS_V1`

Risk: **HIGH explicit authenticated application writes**, localhost-only.

## Purpose

The reviewed browser flow can already create Proposal acceptance, inspect
Agreement formation, and submit Agreement assent. M17.7J/K make exact Agreement
publication and fulfillment-evidence clients available through the existing
memory-only authenticated bootstrap.

M17.7L selects those clients through explicit page controls.

No write occurs automatically after acceptance, formation, assent,
authentication, navigation, language change, or page load.

## Agreement publication

For a selected Proposal, the page enables **Publish Agreement** only when:

- exact Proposal acceptance evidence is available;
- the current Agreement-formation result belongs to that exact acceptance;
- `formationEvidence` is exactly `EVIDENCE_SUFFICIENT_FOR_PROFILE`;
- no required principals remain missing;
- the active authenticated principal is a required Agreement party; and
- that principal is already covered by reviewed assent evidence.

The click calls the M17.7J client with exactly:

- Proposal Record Identity;
- acceptance Record Identity;
- expected Agreement candidate Record Identity.

The server remains authoritative for candidate resolution, formation
reevaluation, party/assent checks, preflight, and state publication.

A successful immutable Agreement publication result is retained only in page
memory.

## Exact fulfillment commitment

The active controls target only the reviewed product commitment id:

`seller-delivery`

There is no free-form commitment-id input in this slice.

## Role-specific evidence actions

After Agreement publication, three separate explicit actions are exposed.

### Seller — Claim delivery complete

The authenticated principal must equal the seller principal from the selected
parent product listing.

The page calls M17.7I with:

`CLAIMED_COMPLETE_PERFORMANCE`

This is an attributable seller performance claim. M17.7A/server validation still
requires the event issuer to equal the targeted commitment party.

### Buyer — Accept delivered commitment

The authenticated principal must equal the buyer principal from the selected
Proposal.

The page calls M17.7I with:

`COMMITMENT_ACCEPTANCE`

This is attributable buyer acceptance evidence.

### Seller — Assert commitment complete

The authenticated principal must equal the listing seller.

The page calls M17.7I with:

`COMMITMENT_COMPLETION`

This is an attributable completion assertion.

## Fulfillment semantics

Under the existing core acceptance evaluator, a reviewed claimed-complete
performance record plus reviewed acceptance evidence may support
`FULFILLED_UNDER_METHOD` when the method's other requirements are satisfied.

The browser does **not** run that evaluator and does not display a
`FULFILLED_UNDER_METHOD` conclusion merely because records were published.

The separate completion assertion is retained as audit evidence; it is not
presented as the fact that makes fulfillment universally true.

No single button establishes universal completion, payment, settlement, legal
effect, or absence of dispute.

## Authentication switching

Agreement publication and fulfillment publication results are immutable record
metadata kept in page memory. Resetting the in-memory authentication session
does not erase those already-returned publication identities.

This permits an operator to authenticate as the seller for seller evidence,
reset, then authenticate as the buyer for buyer acceptance without implying
shared private-key authority.

Private keys and bearer tokens remain inside the existing authentication
bootstrap/session boundaries.

## Retry boundary

There is no automatic retry, timer, worker, queue, or background publication.

After a bounded server/client failure, the same explicit button may become
available again only when the exact role and preconditions still hold. A retry
therefore requires another deliberate click.

## Localization

All new visible controls and status messages are provided in English and
Russian through the existing Marketplace localization surface.

## Network and deployment boundary

These controls are intended only for the explicitly selected authenticated
localhost fulfillment runtime.

M17.7L adds no public-network listener, CORS widening, production deployment,
Android action, payment/settlement capability, background worker, or
production-health claim.

## Rollback

Stop any explicitly started localhost process if necessary and revert the exact
M17.7L merge.

Already-published immutable Marketplace records are evidence and must not be
silently deleted or rewritten by UI rollback.
