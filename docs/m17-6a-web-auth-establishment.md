# M17.6A — Web authentication session-establishment seam

## Profile

`MARKETPLACE_WEB_AUTH_SESSION_ESTABLISHMENT_V1` is a **HIGH security/privacy** source capability.

It adds one **unselected** Web seam for the already-reviewed Marketplace authentication protocol. It does not activate login in `web/index.html` or `web/app.js`.

The seam performs exactly this bounded flow:

1. validate one explicit principal URI and verification-method URI;
2. send one bearer-negative same-origin `POST /api/auth/challenges`;
3. validate the canonical `mkc1_...` challenge, domain, purpose and 120-second challenge lifetime;
4. delegate proof construction to one purpose-specific injected proof provider;
5. validate the exact frozen Marketplace authentication-proof profile;
6. send one bearer-negative same-origin `POST /api/auth/sessions`;
7. validate exact principal/method echo, canonical `mkt1_...` token and reviewed session lifetimes;
8. adopt the bearer only through the existing memory-session boundary;
9. return only non-secret session facts.

## Proof-provider boundary

The proof provider exposes only the exact Marketplace authentication operation required by this seam. M17.6A adds no concrete signer or private-key custody implementation.

There is **no WebCrypto**, **no browser wallet**, no extension/passkey substitution, no raw private-key input, no key enrollment, and no credential persistence.
## Security boundaries

Challenge/session requests use only exact relative same-origin paths, `credentials: "omit"`, no redirects, no referrer and no Authorization header.

The module has no retry, refresh, timer, callback, redirect, worker, service worker, background task, storage or logging capability. A page/process restart therefore has no session recovery by design.

Server `AUTH_*` error codes are preserved when present, while local failures use stable non-reflective errors. Challenge, proof and bearer values are never included in error text or returned separately after adoption.

## Deliberate non-selection

M17.6A does not modify or select:

- `web/index.html` or active `web/app.js`;
- the existing `web/client_session.js` behavior;
- Android entry points or offline cache;
- Python authentication/ASGI/launch/runtime source;
- PostgreSQL, configuration, services, dependencies or workflows.

A later capability must separately select one concrete Web signer/private-key custody model before any active Web login UX is wired.

## Rollback

Rollback is **source-only rollback**: revert the M17.6A source merge. Because this milestone performs no active Web UI selection, browser execution, key operation, credential persistence or runtime/database mutation, rollback requires no credential revocation, storage cleanup, service restart, database migration or deployment action.
