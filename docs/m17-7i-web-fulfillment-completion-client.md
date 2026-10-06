# M17.7I — Unselected Web fulfillment completion client

Profile: `MARKETPLACE_WEB_FULFILLMENT_COMPLETION_CLIENT_V1`

Risk: **MODERATE authenticated Web transport**, source-only and unselected.

## Purpose

M17.7C defines the authenticated fulfillment-completion HTTP route and M17.7H
makes that route reachable only through an explicitly authorized loopback
runtime. M17.7I adds the browser transport client for that exact route without
selecting it in the active page.

## Exact request

The client accepts only:

- one Agreement Record Identity;
- one local commitment id;
- one reviewed evidence kind.

The reviewed evidence kinds are exactly:

- `CLAIMED_COMPLETE_PERFORMANCE`;
- `COMMITMENT_ACCEPTANCE`;
- `COMMITMENT_COMPLETION`.

It sends one authenticated:

`POST /api/agreements/{agreement_record_id}/commitments/{commitment_id}/completion-evidence`

with exact JSON:

```json
{"evidence_kind":"COMMITMENT_COMPLETION"}
```

No issuer, principal, verification method, public key, trust statement,
authorization claim, outcome, target identity, disposition, or change sequence
is supplied by the browser.

## Session authority

Bearer material is obtained only through the existing in-memory
`MarketplaceMemorySession.authorizationFor("POST", path)` boundary.

The client does not receive or expose the raw session token.

The current session route policy is **not widened by M17.7I**. This module is
therefore intentionally unusable from the active browser until a later reviewed
selection slice admits this exact route and composes the client into the
bootstrap.

## Exact response

A successful response must contain exactly:

- `record_id`;
- `agreement_record_id`;
- `commitment_id`;
- `evidence_kind`;
- `disposition`;
- `change_seq`.

The Agreement identity, commitment id, and evidence kind must exactly re-bind to
the request.

`STORED` requires HTTP 201. `DUPLICATE` requires HTTP 200.

No other success status or disposition is accepted.

## Failure boundary

Transport failure, oversized/malformed JSON, unexpected members, identity
mismatch, unsupported evidence kind, invalid disposition/change sequence, or
status/disposition mismatch fails closed.

Bounded server error codes are passed through the existing session invalidation
hook.

## Non-selection

M17.7I does not modify:

- `web/auth_bootstrap.js`;
- `web/client_session.js`;
- `web/index.html`;
- `web/app.js`;
- authenticated localhost asset serving;
- application/runtime/startup code;
- Android;
- deployment.

## Semantic boundary

The client publishes attributable evidence only when a later UI explicitly
selects it.

It does not establish universal completion, payment, settlement, legal effect,
or absence of dispute. It does not evaluate fulfillment.

## Rollback

**source-only rollback:** revert the exact M17.7I merge.
