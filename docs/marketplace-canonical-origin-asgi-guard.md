# Marketplace canonical-origin ASGI guard (source only)

**Profile:** `MARKETPLACE_PRIVATE_ALPHA_CANONICAL_ORIGIN_ASGI_BOUNDARY_V1`
**Risk:** MODERATE security boundary, not activated or integrated.

## Intent

Before exposing the authenticated Marketplace product behind the owner's selected **open-trust-layer.org VPS** and **https://marketplace.open-trust-layer.org/** origin, an explicit production composition must verify that requests arriving from a separately approved TLS reverse proxy belong to the correct browser origin.

The new `MarketplaceCanonicalOriginAsgiGuard` is a dependency-free, **inert-until-injected** ASGI wrapper. Construction only retains a caller-provided callable; no local database, secrets, network, server, TLS certificate, browser, provider or installed VPS service is accessed. It is **not wired into** `tools/marketplace_localhost.py`, Caddy, Moon heartbeat, CI deployment or any production entry point. Source, tests and documentation do not prove the operator's live traffic path.

## Scope and rejection policy

The wrapper accepts only ASGI HTTP 3 requests with an explicit reviewed `https` scheme and root path `""`. The scheme is trusted only from a **separately reviewed** ASGI/proxy composition; it does not infer TLS from user-supplied headers.

- Require a single `Host` header with **exact** `marketplace.open-trust-layer.org`, optionally `:443`. Reject duplicate or noncanonical host headers with a stable fixed response.
- For `POST`, `PUT`, `PATCH` and `DELETE`, require a single `Origin` header exactly `https://marketplace.open-trust-layer.org` without slash/port/aliases. A supplied `Origin` is checked on safe methods too. This is an *additional* anti-cross-origin policy, not an authentication/session authority or substitute for CSRF defenses.
- Reject `Forwarded`, `X-Forwarded-*`, `X-Real-IP`, `X-Original-*` and other explicitly enumerated proxy metadata to avoid trusting client-supplied forwarding. A future production proxy/server adapter must **remove or neutralize these headers before this boundary** and separately establish trusted TLS scheme and peer authenticity. Do **not** simply disable Caddy's protections or trust unreviewed proxy-protocol headers.
- Only allow known `GET`, `HEAD`, `OPTIONS`, `POST`, `PUT`, `PATCH`, `DELETE` methods. Reject malformed/duplicate headers, CR/LF/NUL bytes, overlarge values and headers exceeding count/size caps.
- Reject before consuming the ASGI request body or invoking the injected application. One fixed two-event ASGI denial response is emitted with redacted code, `no-store` and `nosniff`. No user-supplied host, origin, token or exception text is echoed.
- Accepted scopes are passed through unchanged to the injected ASGI application, including the existing authenticated Marketplace handlers; the guard itself cannot issue sessions, assign principal identity or create records.

**This is a narrowly scoped source primitive, not a comprehensive production proxy integration.** In particular, the application will require a reviewed concrete ASGI provider, canonical scheme provenance, stable `Host` preservation, forwarding-header stripping, rate limits, upstream network isolation, sensible timeout/backpressure settings, user invitation/revocation, isolated PostgreSQL, backup/restore and real signed seller/buyer browser evidence. This guard intentionally fails closed when those assumptions are not met. It is not an authorization to reconfigure Caddy or run the localhost evaluator publicly.

## Offline validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_canonical_origin_guard -v
```

The synthetic tests include accepted safe methods and same-origin mutation, fake Host/Origin values, port variants, duplicates, unsafe missing Origin, HTTP downgrade, forwarding spoofing, unsupported ASGI scopes/methods, malformed bytes and bounded denial responses. Tests invoke no external server or network and create no customers or secrets.

Any future runtime wiring **requires a new distinct PR, threat-model review, full conformance/security CI and separate operator deployment authority**. No live VPS service, DNS, public TLS, PostgreSQL, Moon runtime or payment capability is changed by this source-only slice. Rollback is a source revert; there is no live configuration to undo.

For the actual selected destination, transport checks and pending prerequisites see [the private Web alpha deployment plan](private-web-alpha-deployment-plan.md), [the Caddy review candidate](marketplace-caddy-review-candidate.md), and [hosting tracker #528](https://github.com/open-trust-layer/marketplace/issues/528).
