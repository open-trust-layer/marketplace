# M17.7K — Select Agreement and fulfillment Web clients

Profile: `MARKETPLACE_WEB_PUBLICATION_FULFILLMENT_CLIENT_SELECTION_V1`

Risk: **MODERATE authenticated browser capability selection**.

## Purpose

M17.7I and M17.7J add strict browser clients for fulfillment evidence and
Agreement publication but intentionally leave them unusable from the active
browser. M17.7K selects only those reviewed transport clients into the existing
authenticated localhost Web module graph.

It does not add an active page button and it does not call either client
automatically.

## Exact session routes

The existing memory-only session admits exactly two additional POST shapes.

Agreement publication:

`/api/agreements/{proposal_record_id}`

The path contains exactly one non-empty bounded Record Identity segment after
`/api/agreements/`, with no query or fragment marker.

Fulfillment completion evidence:

`/api/agreements/{agreement_record_id}/commitments/{commitment_id}/completion-evidence`

The Agreement identity is non-empty and bounded. The commitment id must match
the reviewed local-id grammar `[A-Za-z][A-Za-z0-9._-]{0,63}`. No query or
fragment marker is admitted.

No new GET route is admitted.

## Same-origin module selection

The existing reviewed authenticated module bundle adds exactly:

- `/agreement_publication_client.js`;
- `/fulfillment_completion_client.js`.

The localhost bootstrap reads them only through the existing bounded asset
reader, and the site host serves them only as reviewed same-origin JavaScript
assets.

The normal unauthenticated static page still does not expose those modules.

## Authentication bootstrap

`auth_bootstrap.js` imports both reviewed clients and exposes two factory
methods:

- `agreementPublicationClient()`;
- `fulfillmentCompletionClient()`.

Both require an already-active memory-only authenticated session.

They receive only the existing reviewed fetch transport and session object.
Neither method publishes anything merely by being called; publication still
requires an explicit later client method call.

Bearer material remains private to the session boundary.

## Active page non-selection

M17.7K does not modify `web/index.html` or `web/app.js`.

There is therefore:

- no Agreement publication button;
- no fulfillment evidence button;
- no automatic publication after assent;
- no background completion action.

## Semantic boundary

Agreement publication does not establish performance, completion, payment,
settlement, legal effect, or universal truth.

Fulfillment client availability does not establish fulfillment. Later explicit
role-specific actions must still publish attributable evidence through the
reviewed server route.

## Network and runtime boundary

M17.7K adds no new application/runtime HTTP route. The server-side routes are
the already-reviewed M17.7C Agreement/fulfillment overlay reached only through
the explicitly selected loopback runtime.

No public-network exposure, deployment, daemonization, Android action, payment,
settlement, or production-health claim is added.

## Rollback

Revert the exact M17.7K merge. Because no active page control is selected,
rollback requires no record cleanup or runtime migration.
