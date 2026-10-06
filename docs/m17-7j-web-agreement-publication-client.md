# M17.7J — Unselected Web Agreement publication client

Profile: `MARKETPLACE_WEB_AGREEMENT_PUBLICATION_CLIENT_V1`

Risk: **MODERATE authenticated Web transport**, source-only and unselected.

## Purpose

The active browser can author Proposal acceptance and Agreement assent, but it
does not yet publish the formed Agreement record. Fulfillment evidence must
target an exact published Agreement Record Identity, so Agreement publication is
a required explicit step before a later Web completion control can be reviewed.

M17.7J adds only the browser transport client for the existing authenticated
Agreement publication seam.

## Exact request

The client accepts exactly:

- one Proposal Record Identity;
- one Proposal-acceptance Record Identity; and
- the exact expected Agreement candidate Record Identity already reviewed by
  the browser's Agreement-formation flow.

It sends:

`POST /api/agreements/{proposal_record_id}`

with exact JSON:

```json
{"acceptance_record_id":"<exact Proposal-acceptance Record Identity>"}
```

No principal, issuer, verification method, public key, trust claim, formation
claim, legal claim, publication authority, disposition, or change sequence is
supplied by the browser.

## Session authority

Bearer authorization is obtained only through the existing in-memory
`MarketplaceMemorySession.authorizationFor("POST", path)` boundary.

M17.7J does **not** widen the current session route policy. The client therefore
remains intentionally unusable from the active page until a later reviewed
selection slice admits the exact route.

## Exact response

A successful response contains exactly:

- `agreement_record_id`;
- `disposition`;
- `change_seq`.

The returned Agreement Record Identity must equal the exact expected Agreement
candidate identity supplied by the caller.

`STORED` requires HTTP 201. `DUPLICATE` requires HTTP 200.

No other success status or disposition is accepted.

## Server authority remains authoritative

The existing server route independently:

- resolves the exact Proposal and acceptance;
- reevaluates retained Agreement formation evidence;
- checks the authenticated actor is an Agreement party;
- requires that actor's assent to be covered;
- runs the reviewed publication preflight; and
- publishes through the reviewed Agreement publication service.

The Web client does not reproduce or weaken those checks.

## Failure boundary

Transport failure, oversized or malformed JSON, unexpected response members,
Agreement identity mismatch, invalid disposition/change sequence,
status/disposition mismatch, or bounded server failure fails closed.

Bounded server error codes pass through the existing session invalidation hook.

## Non-selection

M17.7J does not modify:

- `web/auth_bootstrap.js`;
- `web/client_session.js`;
- `web/index.html`;
- `web/app.js`;
- authenticated localhost asset serving;
- application/runtime/startup code;
- Android;
- deployment.

## Semantic boundary

Publishing a reviewed Agreement record does not itself establish performance,
completion, payment, settlement, legal enforceability, universal truth, or
absence of dispute.

No signing or private-key operation occurs inside this client.

## Rollback

**source-only rollback:** revert the exact M17.7J merge.
