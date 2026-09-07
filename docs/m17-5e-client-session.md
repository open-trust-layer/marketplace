# M17.5E — memory-only Web/Android client session seam

## Profile

`MARKETPLACE_APPLICATION_CLIENT_SESSION_V1` is a HIGH security/privacy, source-only client capability.

It adds unselected Web and Android seams that can carry the already-reviewed M17.5C opaque bearer token form:

```text
Authorization: Bearer mkt1_<43 base64url-no-padding characters>
```

The bearer exists only in page/process memory. There is **no credential persistence** and **No runtime activation** in this milestone.

## Composition boundary

The active Web entry point does not import `web/client_session.js`.

The active Android `MainActivity` continues to construct the existing credential-negative `MarketplaceApiClient` with `LoopbackMarketplaceTransport()` directly. It does not construct `MarketplaceMemorySession` or `MarketplaceSessionClient`.

Therefore anonymous reads and the currently selected localhost client composition remain unchanged until a separately authorized activation milestone.
## Route-scoped bearer admission

The M17.5E seams attach Authorization only to reviewed authenticated routes:

- `GET /api/auth/session`;
- `POST /api/auth/logout`;
- `POST /api/product-listings`;
- `POST /api/intents`;
- `POST /api/intents/{parent}/responses`;
- `POST /api/intents/{parent}/proposals`.

All ordinary anonymous reads remain bearer-negative, including intent browse/detail, response listing and sync.

Challenge/session creation remains bearer-negative. No cookie, query/body token, Basic, JWT, refresh token, redirect/callback propagation or cross-origin credential forwarding is introduced.

Android keeps the raw bearer out of ordinary `ApiRequest` values. `EphemeralAuthorizationTransport` admits the credential only immediately before dispatch and only after exact bearer and route review.

Web keeps the token in a private class field and adds Authorization only immediately before the reviewed request.
## Authenticated principal derivation

For the new authenticated structured authoring seam, the seller principal and buyer principal are derived only from the active memory session.

The new authenticated input types do not accept independently editable `seller_principal` or `buyer_principal` values.

Raw publication helpers require an injected issuer extractor and reject a record before dispatch when its exact issuer principal does not equal the active session principal.

Application authentication still does not prove ownership, legitimacy, trust, agreement, payment, settlement, fulfillment or real-world identity.

## Logout and invalidation

Logout is local-first logout:

1. obtain the transient Authorization value;
2. clear local principal/token state immediately;
3. make at most one `POST /api/auth/logout` attempt;
4. never restore the token after transport or server failure;
5. never retry in background.

A stable `AUTH_SESSION_INVALID` server failure clears the local memory session. Other stable server error codes are propagated without reflecting bearer material.
## Offline and persistence boundary

Android offline cache remains credential-negative and read-only. No bearer, challenge, proof, principal-binding material or reauthentication metadata is added to the offline snapshot/cache format.

Protected writes remain unavailable in cached offline mode through the existing `OFFLINE_WRITE_UNAVAILABLE` boundary.

M17.5E adds no `SharedPreferences`, DataStore, Room/SQLite, files, saved state, WorkManager, AlarmManager, service, notification, clipboard, keystore, browser storage, IndexedDB, Cache API, cookies, service worker, timer, websocket or background refresh/retry capability.

Page reload, browser restart, Android process death or app restart loses the local session by design.

## Source-only rollback and exclusions

Rollback is source-only rollback: revert the exact M17.5E merge commit if one is later authorized.

No database migration, token-file cleanup, provider administration, cache migration or service restart is required because this milestone has no credential persistence and no runtime selection.

This milestone performs no concrete credential/challenge/session generation, private-key handling, signing, proof verification, resolver/provider activity, OAuth/OIDC/password/JWT/cookie flow, dependency widening, PostgreSQL/config/service mutation, production/public-network access, publishing or deployment.

There is no Android build, install, device action or live login acceptance in M17.5E.
