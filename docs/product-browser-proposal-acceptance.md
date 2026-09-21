# Product browser Proposal acceptance

Risk classification: HIGH authenticated protected-write selection.

Profile:

    MARKETPLACE_WEB_PROPOSAL_ACCEPTANCE_CLIENT_V1

## Purpose

This source slice selects the already-reviewed authenticated Proposal-acceptance
HTTP write through the memory-only browser session and the existing seller
acceptance handoff. It adds no new server authority.

The operation remains one exact empty POST:

    POST /api/intents/{proposal_record_id}/acceptance

with no query, no body, and no Content-Type.

## Explicit user action and seller binding

The initial HTML control remains disabled.

The page enables **Accept Proposal** only when all of the following are true:

- the selected record is an exact Proposal in the reviewed response flow;
- its exact parent listing is present in the current reviewed application view;
- an authenticated memory-only session is active;
- the session principal exactly equals the parent listing seller principal;
- no acceptance request for that Proposal is already pending;
- no acceptance result for that Proposal is already retained in page memory.

Publication occurs only after the explicit user click by the exact authenticated seller.

The browser check is defense in depth. The server independently derives the
seller from the authenticated session and independently rechecks ownership of
the exact parent listing before it can publish.

## Browser client boundary

The dedicated client receives only:

- injected same-origin fetch;
- the existing MarketplaceMemorySession;
- the exact Proposal Record Identity supplied at call time.

It obtains bearer authorization only through session.authorizationFor for the
exact acceptance route. The bearer token is never returned to app.js, rendered,
logged, persisted, or copied into page state.

The request has no editable seller principal and no request body.

A successful 201 response is accepted only with the exact fields:

- record_id;
- disposition = STORED or DUPLICATE;
- change_seq = null or a positive integer.

Only that bounded public publication metadata is retained in page memory, keyed
by the exact Proposal identity.

## Read-only acceptance resolution

The same purpose-specific client now also exposes an exact authenticated read:

    GET /api/intents/{proposal_record_id}/acceptance

This operation has no query, body, or Content-Type. It accepts HTTP 200 only
when the response has exactly `proposal_record_id` and `record_id`, and the
returned Proposal identity exactly matches the requested Proposal.

GET does not publish acceptance and does not return acceptance record content.
It exists so another authenticated Proposal party can converge on the exact
immutable acceptance identity without sharing the seller's browser memory.

Browser selection of this read remains a separate explicit user action from the
seller-only empty POST publication action.

## Semantic boundary

A Proposal-acceptance record is one immutable seller-attributed acceptance event.

It does not form an Agreement, prove complete Agreement assent, establish legal
enforceability or ownership, invalidate competing Proposals, or authorize
payment, settlement, escrow, fulfillment, or transfer. There is no payment
capability in this slice.

Agreement assent/signing remains a separate later explicit user action. This
slice does not call the Agreement assent client or signer.

## Retention / activity boundary

The client and UI add no persistent browser storage, worker, timer, retry loop,
background request, service worker, credential persistence, or external network
origin. Result metadata is memory-only in the current page.

## Rollback

Rollback is source-only rollback: revert this browser selection/client slice.
Published immutable acceptance records, if this source is later deployed and a
user explicitly invokes it, are application records and are not silently
deleted by a source rollback. No deployment or live acceptance operation is
performed by this PR.
