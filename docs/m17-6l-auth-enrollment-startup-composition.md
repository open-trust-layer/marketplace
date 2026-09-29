# M17.6L — Authenticated enrollment startup overlay composition

Profile: `MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_STARTUP_COMPOSITION_V1`

Exact implementation baseline: `058f48459a62435c7c5bb3222249ab6f235ab1dc`

Risk classification: **HIGH security/privacy / authenticated enrollment startup-selection source capability**.

M17.6L overlays the reviewed M17.6J enrollment HTTP composition and M17.6K enrollment-aware ASGI composition onto one already-built M17.5T authenticated startup. It does not modify, rebuild, or replace that startup.

## Exact six-file scope

Added:

1. `src/marketplace/application/auth_enrollment_startup_composition.py`
2. `tests/test_m17_6l_auth_enrollment_startup_composition.py`
3. `tests/test_m17_6l_auth_enrollment_startup_composition_artifacts.py`
4. `docs/m17-6l-auth-enrollment-startup-composition.md`

Modified only for wheel membership:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No existing startup, launch, runtime, ASGI, HTTP, Web, Android, PostgreSQL, configuration, service, dependency, workflow, audit, or governance source is modified.

## Overlay inputs

`compose_marketplace_authentication_enrollment_startup(...)` accepts exactly:

- one existing M17.5T `MarketplaceAuthenticatedStartupComposition`;
- one exact M17.5Q `MarketplaceAuthenticationRuntimeInputs`;
- one exact M17.6H nonce authority;
- one injected M17.6F approval policy;
- one injected M17.6E authority attestor;
- one trusted authority URI;
- one finite evidence lease.

The **same exact runtime-input object** must already be retained by the base startup's M17.5R ASGI composition.

## Composition order

L composes only:

1. M17.6J from `authenticated_startup.http`;
2. M17.6K from that exact J object plus the exact retained runtime inputs.

The returned frozen overlay retains:

- exact base authenticated startup;
- exact runtime inputs;
- exact J enrollment HTTP composition;
- exact K enrollment ASGI composition.

No second authentication graph, HTTP graph, credential-material source, clock, application composition, provisioning bundle, or base startup is created.

## Zero consumption

M17.6L performs **zero new clock** reads and zero:

- credential-material generation;
- enrollment-nonce material generation;
- nonce issuance or consumption;
- policy calls;
- attestor calls;
- HTTP/ASGI request handling;
- provisioning loads;
- application initialization;
- provider/network/filesystem/database operations.

The M17.5T startup may already have consumed its one reviewed startup clock sample before being supplied to L. L itself consumes nothing.

## Identity and failure boundary

The overlay fails closed unless:

- the base object is exact M17.5T startup;
- the supplied runtime inputs are the same exact object retained by the base startup ASGI composition;
- the base startup's HTTP/authentication/ASGI identity graph is coherent;
- J retains the exact base HTTP graph;
- K retains the exact J object and exact runtime inputs;
- K's ASGI retains the exact J enrollment HTTP adapter.

All L-owned failures collapse to:

`MarketplaceAuthenticationEnrollmentStartupCompositionError("authentication enrollment startup composition failed")`

Raw nested exception text and sensitive enrollment/session material are not reflected.

## Explicit non-authority

M17.6L adds no:

- M17.5T mutation or replacement;
- launch-plan selection or replacement;
- runtime-server selection or execution;
- host/port/socket binding;
- concrete nonce randomness/provider;
- persistent/shared nonce authority;
- concrete approval policy;
- signer/private-key custody/provider;
- trust-anchor/evidence mutation;
- browser enrollment activation;
- WebCrypto client selection;
- Android action;
- PostgreSQL/configuration/service mutation;
- dependency/workflow/repository-audit widening;
- production/public-network activity;
- deployment, publishing, or distribution.

The existing M17.5U launch path remains unchanged and therefore does not automatically select the L overlay.

## Moon Company boundary

M17.6L advances Moon Commerce toward a complete authenticated enrollment flow while preserving Marketplace as an independently deployable product.

It introduces no Moon Company runtime/control-plane, registry, event-bus, or agent dependency. Moon Company orchestration does not become the Marketplace enrollment authority, signer, session authority, or runtime owner.

## Qualification

Qualification freezes:

- exact profile and six-file scope;
- exact base M17.5T identity;
- exact runtime-input object identity;
- J then K reuse;
- exact nonce-authority/policy/attestor/authority/lease retention;
- exact enrollment-aware ASGI retention;
- zero new clock/material/nonce/policy/attestor/request/provider consumption;
- mismatch/corruption fail-before-overlay construction;
- stable non-reflective failures;
- unchanged base startup;
- unchanged M17.5U launch selection;
- continued runtime/Web/Android non-selection;
- package membership;
- FULL Marketplace conformance.

## Rollback

Rollback is **source-only rollback**: revert the exact M17.6L merge.

Because the overlay remains unselected by launch/runtime and introduces no provider or persistence, rollback requires no listener shutdown, session cleanup, nonce cleanup, key revocation, trust-store change, database rollback, service restart, provider administration, browser/device cleanup, or deployment rollback.
