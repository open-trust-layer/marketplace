# M17.5C — bounded bearer-session transport

## Profile

`MARKETPLACE_APPLICATION_BEARER_V1` is the only admitted session carrier in this source slice:

```text
Authorization: Bearer mkt1_<43 base64url-no-padding characters>
```

The payload decodes canonically to exactly 32 opaque session-token bytes. Scheme, one-space separator, `mkt1_` prefix, alphabet, payload length and no-padding form are exact. Alternate schemes, duplicate Authorization, whitespace variants, padding, unknown versions and malformed values fail closed.

Raw Authorization and token bytes are **request-lifetime only**. They are not added to `ApplicationHttpRequest`, returned in response values, logged by this source slice, or persisted.

## Admission boundary

The approved anonymous reads remain credential-free and otherwise unchanged. A bearer on an anonymous or other non-protected route fails closed instead of being ignored.

All existing publication/write surfaces require a valid M17.5B session:

- `POST /api/product-listings`;
- `POST /api/intents/{parent}/proposals`;
- raw `POST /api/intents`;
- raw `POST /api/intents/{parent}/responses`.

## Principal binding and failures

Structured writes route through the M17.5B authenticated Product Listing and Proposal authoring services. Raw intent/response writes decode the exact record first, extract its validated issuer principal, and require exact equality with the session-bound principal before publication.

Authentication does not imply record truth, ownership, legitimacy, trust, agreement, payment, settlement or fulfillment.

Stable public failures are:

- missing bearer on a protected write: `401 AUTH_REQUIRED`;
- malformed, unknown, expired or revoked bearer/session: `401 AUTH_SESSION_INVALID`;
- valid session with a different seller, buyer or raw issuer: `403 AUTH_PRINCIPAL_MISMATCH`.

Errors do not reflect credential bytes or provider/verifier detail.

## Security and retention boundary

Cookie, Proxy-Authorization and Set-Cookie remain forbidden. There is no query/body token, JWT, refresh token, redirect/callback, CORS widening, hidden refresh loop or retry/background polling introduced here.

This slice performs **no credential persistence**. M17.5B session state remains digest-only in process memory under the approved 30-minute idle and 8-hour absolute ceilings. Web/Android persistent storage and the Android content cache remain outside this credential boundary.

## Source-only authority boundary

The legacy `MarketplaceAsgiHttpAdapter` stays credential-negative. Bearer admission exists only through the separately constructed explicit bearer-capable adapter; merging source does not select or start that adapter in any running service.

There is **no runtime activation** in M17.5C: no server start/restart, socket/network-origin change, localhost activation, credential issuance, challenge generation, proof execution, provider/resolver administration, PostgreSQL mutation, Web/Android credential persistence, Android build/device action, production access, publishing or deployment.

Rollback is source-only: revert the M17.5C source commit to restore the prior credential-negative transport surface. No token invalidation, database migration or service mutation is required by this slice itself.
