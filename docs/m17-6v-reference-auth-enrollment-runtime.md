# Product M17.6V — Reference enrollment foreground execution seam

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_FOREGROUND_RUNTIME_V1`

Risk: **HIGH security/privacy** source-only runtime-execution capability.

## Purpose

M17.6U now provides the exact inert reference enrollment graph containing the
reviewed T Ed25519 attestor, S nonce/policy composition, O enrollment launch,
and M enrollment-aware loopback plan.

M17.6N already defines the explicit application-layer foreground execution seam.

M17.6V introduces the smallest reference bridge:

`U → N`

It accepts one exact U reference graph, validates its identity continuity, derives
the exact nested M launch plan, and delegates exactly once to N.

## Exact execution token

M17.6V defines no new token. It reuses the exact execution token exported by N:

`EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER`

Wrong type or value fails before N delegation.

The exact caller token is passed unchanged to N.

## Graph boundary

Before delegation, V revalidates that:

- the input is exact M17.6U;
- the U attestor is exact M17.6T;
- the U launch is exact M17.6S;
- U authenticated-plan, bindings, attestor, authority, and lease remain identical
  through S and O;
- O retains S's exact nonce authority and policy;
- the nested plan is exact M17.6M;
- the M plan retains O's exact startup and enrollment-aware ASGI;
- M host and port remain the exact inherited authenticated-plan values.

Forged or cross-bound graphs fail before N/provider inspection.

## Provider boundary

M17.6V accepts only a caller-injected `MarketplaceAsgiServerProvider` surface.

It does not import, construct, discover, or select
`UvicornLoopbackServerProvider` or another concrete provider.

Tests use a **deterministic provider probe** only. They do not open a socket or
run a real server.

## Side-effect boundary

Before N delegation, validation consumes no signing/attestation, nonce issuance
or consumption, approval decision, entropy, clock sample, HTTP/ASGI request,
filesystem/environment/database/network access, socket operation, persistence,
or background work.

The only possible side effect of a valid explicit call is the one provider
delegation already governed by M17.6N.

## Failure boundary

M17.6V-owned failure collapses to:

`reference authentication enrollment foreground runtime failed`

Provider errors and nested details are not reflected.

## Non-selection boundary

M17.6V remains **unselected**.

Startup, existing launch paths, Uvicorn/provider selection, CLI/services, Web,
Android, configuration, and Moon Company runtime/control-plane do not import or
invoke V.

No real runtime activation, listener creation, public-network activity, external
key custody, HSM/vault/keyring activation, trust mutation, deployment,
publishing, or distribution is authorized by this milestone.

## Moon Company boundary

M17.6V is a replaceable Moon Commerce reference execution seam only.

It grants Moon Company no runtime execution authority, provider ownership,
identity or policy administration, key custody, deployment authority, or
production control.

## Rollback

**source-only rollback:** revert the exact M17.6V merge.

Because V remains unselected and qualification uses only deterministic provider
probes, rollback requires no listener shutdown, key revocation, nonce/session
cleanup, trust-store change, database rollback, service restart, provider
administration, browser/device cleanup, or deployment rollback.
