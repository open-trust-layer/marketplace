
# M17.7P - Authenticated Web structured-authoring session binding

Profile: `MARKETPLACE_AUTHENTICATED_WEB_AUTHORING_SESSION_V1`

Risk: **bounded Web/session composition correction**.

## Live finding

The first live PostgreSQL-backed browser acceptance on merged M17.7N successfully
established an authenticated seller session, but the visible **Create product
listing** action failed with `AUTH_REQUIRED`.

The runtime was enforcing the reviewed authenticated write boundary correctly.
The defect was in the active Web composition: `web/app.js` still sent listing
and Proposal POSTs through its anonymous `apiFetch` helper even though
`web/client_session.js` already contained the reviewed Bearer-scoped structured
authoring client.

## Correction

M17.7P keeps one authority source: the browser authentication bootstrap's same
established in-memory session.

- `createMarketplaceSessionClient` may now bind an exact existing
  `MarketplaceMemorySession`; omitting that parameter preserves the previous
  standalone-client behavior.
- `auth_bootstrap.js` exposes a structured-authoring view containing only
  `createProductListing` and `createProposal`.
- the returned structured view does not expose the session object, request helper,
  bearer token, or private key.
- when authentication is active, `app.js` requires the visible seller/buyer
  principal to equal the authenticated principal, removes that editable principal
  from the structured fields, and lets the reviewed session client derive it.
- when authentication is inactive, the existing anonymous database-free fallback
  remains unchanged.

This keeps seller/buyer attribution bound to authentication rather than trusting
an editable form field.

## Security and runtime boundary

Bearer material remains private to `MarketplaceMemorySession`. M17.7P adds no
credential persistence, local/session storage, cookies, IndexedDB, service worker,
background retry, private-key export, new route, server capability, PostgreSQL
initialization path, socket bind, or runtime-selection authority.

The change adds no public-network exposure, deployment authority, Android action,
no payment or settlement authority, and no production credential handling.

## Acceptance

Focused acceptance proves that:

1. the reviewed session client can reuse the exact established memory session;
2. auth bootstrap exposes only the two structured-authoring operations;
3. authenticated listing and Proposal submissions use that client;
4. visible seller/buyer principal mismatches fail before dispatch;
5. anonymous database-free authoring remains available when no session is active;
6. bearer/session-token text remains absent from `app.js` and
   `auth_bootstrap.js`.

The live PostgreSQL/browser flight must be repeated after this source change and
the prerequisite whole-second clock correction are merged green.

## Rollback

**source-only rollback:** revert the exact M17.7P merge.

No database, credential, session, network, payment, settlement, deployment, or
external-system rollback is introduced by this source correction.
