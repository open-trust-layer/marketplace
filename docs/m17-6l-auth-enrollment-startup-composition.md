# M17.6L — Authenticated enrollment startup overlay composition

Profile: `MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_STARTUP_COMPOSITION_V1`

Exact implementation baseline: `058f48459a62435c7c5bb3222249ab6f235ab1dc`

Risk classification: **HIGH security/privacy / authenticated enrollment startup-selection source capability**.

M17.6L adds one source-only authenticated enrollment startup **overlay** over an already-composed M17.5T startup. It reuses M17.6J enrollment HTTP composition and M17.6K enrollment-aware ASGI composition without modifying or rebuilding the existing authenticated startup.

## Exact six-file scope

Added:

1. `src/marketplace/application/auth_enrollment_startup_composition.py`
2. `tests/test_m17_6l_auth_enrollment_startup_composition.py`
3. `tests/test_m17_6l_auth_enrollment_startup_composition_artifacts.py`
4. `docs/m17-6l-auth-enrollment-startup-composition.md`

Modified only for package membership:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No existing startup, launch, runtime, ASGI, HTTP, Web, Android, dependency, workflow, PostgreSQL, configuration, service, or governance file is modified.

## Exact inputs

`compose_marketplace_authentication_enrollment_startup(...)` accepts exactly:

- one existing `MarketplaceAuthenticatedStartupComposition`;
- one exact existing `MarketplaceAuthenticationRuntimeInputs`;
- one exact `MarketplaceAuthenticationEnrollmentNonceAuthority`;
- one injected enrollment approval policy;
- one injected enrollment authority attestor;
- one trusted authority URI;
- one finite evidence lease.

The base startup has already completed its separately reviewed M17.5T composition before L is called.

## Same runtime-input identity

The supplied runtime inputs must be the **same exact runtime-input object** already retained by:

`authenticated_startup.asgi.runtime_inputs`

M17.6L also verifies that:

- base startup authentication, HTTP and ASGI have their exact reviewed types;
- `authenticated_startup.http.authentication is authenticated_startup.authentication`;
- `authenticated_startup.asgi.http is authenticated_startup.http`.

A different runtime-input object fails before J or K construction, even if it contains otherwise valid material and clock instances.

## J then K reuse

After the base startup identity gate succeeds, L performs only these two composition steps:

1. `compose_marketplace_authentication_enrollment_http(...)` over the exact `authenticated_startup.http`;
2. `compose_marketplace_authentication_enrollment_asgi(...)` over that exact J result plus the exact retained runtime inputs.

The immutable L result retains:

- exact base authenticated startup;
- exact runtime inputs;
- exact J enrollment HTTP composition;
- exact K enrollment ASGI composition.

The K ASGI graph continues to retain the exact base site, ordinary authenticated Marketplace HTTP adapter, session HTTP adapter, enrollment HTTP adapter and runtime clock.

## Zero-consumption boundary

L performs **zero new clock** reads.

It also performs:

- zero credential-material generation;
- zero enrollment nonce material generation;
- zero nonce issuance or consumption;
- zero policy approval calls;
- zero attestor calls;
- zero HTTP or ASGI handler calls;
- zero application initialization;
- zero provisioning load;
- zero provider, filesystem, network or database access.

The one reviewed M17.5T startup clock sample happened before the base startup was passed to L. L does not resample it.

## Base startup remains unchanged

M17.6L does not mutate or replace M17.5T.

The original `authenticated_startup.asgi.asgi` remains the original non-enrollment M17.5R ASGI graph. The enrollment-aware ASGI graph is retained separately inside the L overlay.

That separation keeps selection explicit and reversible.

## Stable failure

Wrong exact types, corrupted base-startup identity, runtime-input mismatch, invalid collaborator shape, invalid authority/lease, or J/K construction failure collapses to:

`MarketplaceAuthenticationEnrollmentStartupCompositionError("authentication enrollment startup composition failed")`

No principal, verification method, session token, proposal, nonce, authority, attestation, provider detail, path or raw nested exception is reflected.

## Explicit non-authority

M17.6L adds no:

- modification of `auth_startup_composition.py`;
- launch-plan replacement;
- runtime-server selection or execution;
- socket/host/port binding;
- concrete nonce randomness provider;
- persistent/shared nonce authority;
- concrete approval policy;
- signer/private-key custody or provider;
- trust-anchor/evidence mutation;
- browser enrollment activation;
- WebCrypto client selection;
- Android action;
- PostgreSQL/config/service mutation;
- dependency/workflow/repository-audit widening;
- production/public-network activity;
- deployment, publishing, or distribution.

It remains **unselected by launch** and runtime.

## Moon Company boundary

This milestone moves Moon Commerce toward a usable authenticated enrollment flow while preserving Marketplace as an independently deployable product.

Moon Company may later discover this capability through a separately reviewed manifest/capability surface. M17.6L adds no Moon control-plane, registry, event-bus, agent-runtime, enrollment-authority, signer, session-authority, or runtime-owner dependency.

## Qualification

Qualification freezes:

- exact profile and six-file scope;
- exact base startup and runtime-input types;
- same exact runtime-input object;
- exact base startup identity graph;
- J composition from exact base HTTP;
- K composition from exact J and runtime inputs;
- exact nonce-authority/policy/attestor/authority/lease retention;
- zero L-time consumption;
- base startup remains unchanged;
- launch/runtime/Web/Android non-selection;
- package membership;
- FULL Marketplace conformance.

## Rollback and later gates

Rollback is **source-only rollback**: revert the exact M17.6L merge.

Because L creates only inert process-local overlay objects and remains unselected by launch/runtime, rollback requires no listener shutdown, session cleanup, nonce cleanup, key revocation, trust-store change, database rollback, service restart, provider administration, browser/device cleanup, or deployment rollback.

Later separately governed gates may define an enrollment-aware loopback launch plan, runtime-server selection, concrete nonce/provider/persistence choices, concrete policy/signer custody, browser enrollment workflow, bounded localhost acceptance, and Moon Company capability exposure.
