# M17.6K — Enrollment-aware authenticated ASGI selection

Profile: `MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_ASGI_COMPOSITION_V1`

Exact implementation baseline: `cc40a1ca3aeadc2312a3e6db66b96935b1aca3d3`

Risk classification: **HIGH security/privacy / authenticated routing selection capability**.

M17.6K selects the reviewed M17.6J enrollment HTTP graph into the existing authenticated ASGI parser/bearer/time boundary. It is source-only and remains **unselected** by startup, launch, runtime server, Web, and Android entry points.

## Exact eight-file scope

Added:

1. `src/marketplace/application/auth_enrollment_asgi_composition.py`
2. `tests/test_m17_6k_auth_enrollment_asgi_composition.py`
3. `tests/test_m17_6k_auth_enrollment_asgi_composition_artifacts.py`
4. `docs/m17-6k-auth-enrollment-asgi-composition.md`

Modified:

5. `src/marketplace/application/auth_session_asgi.py`
6. `tests/test_m17_5d_session_establishment_hardening.py`
7. `tools/package_artifact_gate.py`
8. `tests/test_package_artifact_gate.py`

No M17.6I/J source, M17.5P HTTP composition, authentication service/session source, startup composition, launch/runtime server, Web, Android, PostgreSQL/configuration/service source, dependency metadata, workflow, repository audit, or governance file is modified.

## Optional exact enrollment slot

`MarketplaceSessionEstablishmentAsgiHttpAdapter` now accepts one optional exact:

`MarketplaceAuthenticationEnrollmentHttpAdapter | None`

The default is `None`, preserving existing M17.5R and Agreement-assent call sites and behavior.

When supplied, enrollment selection is **exact-route** only:

- `/api/authentication-enrollment/nonces`
- `/api/authentication-enrollment/evidence`

No broad `/api/authentication-enrollment/` prefix is selected. Unknown or future enrollment-like paths retain the existing ordinary authenticated Marketplace HTTP fallthrough.

## Request bound

Exact enrollment routes use the existing M17.6I:

`AUTH_ENROLLMENT_HTTP_REQUEST_MAX_BYTES`

The existing M17.5D auth-session bound remains unchanged for `/api/auth/*`, and the existing ordinary Marketplace/API bound remains unchanged for other traffic.

An oversized enrollment request fails before body receive or enrollment handler invocation with the stable enrollment request error.

## Single bearer and clock boundary

M17.6K does not add a second parser.

The existing ASGI implementation still contains a **single bearer** parsing path and a single request-lifetime auth clock sample. For enrollment routes it passes the resulting exact request, session token/session-invalid flag, and clock value to the reviewed M17.6I adapter.

There is no second session validator, bearer decoder, authentication service, or clock source.

## Inert composition

`compose_marketplace_authentication_enrollment_asgi(...)` accepts exactly:

- one M17.6J `MarketplaceAuthenticationEnrollmentHttpComposition`;
- one M17.5Q `MarketplaceAuthenticationRuntimeInputs`.

It proves:

- J application HTTP and session HTTP use the same exact auth service;
- J enrollment HTTP uses that same exact auth service;
- session challenge/session-token callables belong to the exact runtime material source;
- the ASGI clock callable belongs to the exact runtime clock;
- the ASGI adapter retains exact site, ordinary Marketplace HTTP, session HTTP, enrollment HTTP, and clock identities.

Composition performs zero material generation, zero clock reads, zero request handling, zero policy/attestor calls, zero nonce operations, and zero provider/runtime actions.

## Routing ownership

With the optional enrollment slot supplied:

- `/api/auth/*` remains owned by the existing session HTTP adapter;
- the two exact enrollment routes are owned by M17.6I;
- other `/api/*` and bearer-present traffic remain owned by the existing authenticated Marketplace HTTP adapter;
- site traffic remains owned by the existing site host.

Without the optional slot, behavior remains the legacy M17.5D/M17.5R behavior.

## Explicit non-authority

M17.6K adds no startup composition selection, launch-plan replacement, socket/server execution, concrete nonce randomness/provider, persistent/shared nonce authority, concrete approval policy, signer/private-key custody, trust mutation, browser enrollment activation, Android action, database/configuration/service mutation, dependency/workflow widening, production/public-network activity, deployment, publishing, or distribution.

It also does not combine the enrollment overlay with the separately reviewed Agreement-assent overlay.

## Moon Company boundary

Moon Company may later discover Moon Commerce enrollment capability through a separate manifest/capability surface. M17.6K adds no Moon Company control-plane, registry, event-bus, or agent runtime dependency to Marketplace and does not grant Moon orchestration authentication authority.

Marketplace remains independently deployable.

## Qualification

Qualification freezes:

- exact profile and eight-file scope;
- optional enrollment slot defaulting to none;
- exact-route enrollment selection only;
- M17.6I request byte limit;
- one existing bearer parser;
- one existing request-lifetime clock path;
- same exact auth-service identity across application/session/enrollment HTTP;
- exact runtime material-source and clock ownership;
- zero composition consumption;
- deterministic in-process route selection for enrollment/auth/API/site traffic;
- future enrollment-like path fallthrough;
- oversized enrollment fail-before-receive behavior;
- continued startup/launch/runtime/Web/Android non-selection;
- package membership;
- FULL Marketplace conformance.

## Rollback

Rollback is **source-only rollback**: revert the exact M17.6K merge.

Because K remains unselected by startup/launch/runtime and introduces no provider or persistence, rollback requires no listener shutdown, session cleanup, nonce cleanup, key revocation, database rollback, service restart, provider administration, browser/device cleanup, or deployment rollback.
