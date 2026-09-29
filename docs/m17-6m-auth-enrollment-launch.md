# M17.6M — Enrollment-aware inert loopback launch plan

Profile: `MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_LOOPBACK_LAUNCH_PLAN_V1`

Exact implementation baseline: `1cfca662a6297bbaad5bd9f11d57d34c309d08e2`

Risk classification: **HIGH security/privacy / authenticated enrollment launch-selection source capability**.

M17.6M adds inert loopback launch metadata for the already-reviewed M17.6L authenticated enrollment startup overlay. It selects an exact ASGI object for a possible later runtime seam but **does not run a server**.

## Exact six-file scope

Added:

1. `src/marketplace/application/auth_enrollment_launch.py`
2. `tests/test_m17_6m_auth_enrollment_launch.py`
3. `tests/test_m17_6m_auth_enrollment_launch_artifacts.py`
4. `docs/m17-6m-auth-enrollment-launch.md`

Modified only for wheel membership:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No existing startup, launch, runtime, ASGI, HTTP, Web, Android, PostgreSQL, configuration, service, dependency, workflow, audit, or governance source is modified.

## Exact launch metadata

The builder accepts only:

- host exactly `127.0.0.1` through the existing `LOOPBACK_LAUNCH_HOST`;
- an exact integer port inside the existing reviewed Marketplace loopback range;
- one exact M17.6L `MarketplaceAuthenticationEnrollmentStartupComposition`.

The returned frozen plan retains exactly:

- host;
- port;
- startup overlay;
- `startup.enrollment_asgi.asgi`.

No hostname alias, wildcard interface, public address, automatic port discovery, socket probing, or alternate ASGI object is accepted.

## Identity gate

Construction fails closed unless:

- the M17.6L overlay is exact;
- enrollment HTTP remains bound to the base authenticated startup HTTP graph;
- enrollment ASGI remains bound to that exact enrollment HTTP composition;
- the overlay and base authenticated startup retain the same exact runtime-input object;
- selected ASGI is the exact reviewed session-establishment ASGI adapter;
- its site is the exact base application site;
- its ordinary Marketplace HTTP handler is the exact base authenticated application HTTP adapter;
- its auth handler is the exact base authenticated session HTTP adapter;
- its enrollment handler is the exact M17.6J enrollment HTTP adapter;
- its clock callable is bound to the exact runtime clock.

Direct plan construction cannot substitute another ASGI object.

## Inert boundary

Plan creation performs zero:

- clock reads;
- credential-material generation;
- nonce generation, issue, or consumption;
- policy or attestor calls;
- HTTP/ASGI request handling;
- provider calls;
- socket creation, bind, listen, or accept;
- application initialization;
- provisioning loads;
- filesystem/network/database access.

The plan is immutable process-local metadata only.

## Explicit non-authority

M17.6M adds no:

- modification or replacement of M17.5U authenticated launch;
- mutation or selection of M17.5V runtime execution;
- foreground server execution;
- provider `.run(...)`;
- socket binding;
- public-network host;
- concrete nonce provider;
- persistent/shared nonce authority;
- concrete approval policy;
- signer/private-key custody/provider;
- trust-anchor/evidence mutation;
- browser enrollment activation;
- WebCrypto client selection;
- Android action;
- PostgreSQL/configuration/service mutation;
- dependency/workflow/audit widening;
- production/public-network activity;
- deployment, publishing, or distribution.

## Moon Company boundary

M17.6M advances Moon Commerce to a precise, inspectable enrollment-aware launch-plan capability while preserving independent Marketplace deployment.

It introduces no Moon Company runtime/control-plane, registry, event-bus, or agent dependency. Moon Company orchestration does not become the Marketplace runtime owner, enrollment authority, signer, or session authority.

## Qualification

Qualification freezes:

- exact profile and six-file scope;
- loopback-only host;
- exact reviewed port range;
- exact M17.6L startup identity;
- exact K ASGI selection;
- exact base site/application/session identities;
- exact enrollment HTTP identity;
- exact runtime-input and clock ownership;
- direct-construction substitution rejection;
- zero clock/material/nonce/policy/attestor/request/provider/socket activity;
- corrupted graph fail-closed behavior;
- unchanged M17.5U/M17.5V source and selection;
- continued Web/Android non-selection;
- package membership;
- FULL Marketplace conformance.

## Rollback

Rollback is **source-only rollback**: revert the exact M17.6M merge.

Because M remains inert and creates no external or durable state, rollback requires no listener shutdown, session cleanup, nonce cleanup, key revocation, trust-store change, database rollback, service restart, provider administration, browser/device cleanup, or deployment rollback.
