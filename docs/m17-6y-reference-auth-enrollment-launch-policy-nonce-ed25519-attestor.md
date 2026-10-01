# Product M17.6Y — Compose existing Ed25519 enrollment attestor into U graph

Profile:
`MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_POLICY_NONCE_ED25519_ATTESTOR_V1`

Risk: **HIGH security/privacy** source-only private-key-handle composition.

## Purpose

M17.6U creates an exact M17.6T Ed25519 enrollment attestor from raw 32-byte
private-key input and supplies it into the existing M17.6S reference enrollment
graph.

M17.6X now defines a separately governed local intake that returns an already
constructed exact T attestor without returning raw key bytes.

M17.6Y adds the smallest composition seam:

`existing T → S → existing U`

Y accepts an already-constructed exact T object, supplies that exact object to S,
and returns the existing U result dataclass with the same attestor identity.

Y defines no new graph type and does not alter T, S, U, X, V, or W.

## Exact composition contract

The function accepts:

- one exact `MarketplaceAuthenticatedLoopbackLaunchPlan`;
- one exact tuple of reviewed R approval bindings;
- one exact existing
  `MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor`;
- authority;
- evidence lease seconds.

Any non-exact attestor type fails before S is called.

For a valid exact attestor, Y calls the existing S builder exactly once, passing
the exact caller plan, bindings, attestor, authority, and lease. Y then
constructs the existing U result exactly once with those same values and the
exact returned S graph.

Identity continuity is therefore inherited and revalidated by existing U/S
constructors.

## Raw-key boundary

M17.6Y has no `private_key_bytes` parameter.

It does not construct T, import cryptography, acquire key material, read a
keyfile, generate/import/export/derive a key, or serialize key material.

The caller-provided attestor reference is the only private-key-bearing authority
visible to Y.

## Side-effect boundary

Construction performs **zero signing**, attestation, nonce issuance/consumption,
entropy use, approval decisions, HTTP/ASGI request handling, filesystem access,
environment/config lookup, database/network activity, provider/runtime/socket
execution, persistence, retry, fallback, or background work.

## Failure boundary

All Y-owned failures collapse to:

`reference authentication enrollment existing Ed25519 attestor composition failed`

Nested errors, authority values, bindings, key material, paths, provider details,
and runtime details are not reflected.

## Non-selection boundary

M17.6Y remains **unselected**.

Existing U, X, V, W, startup/launch/runtime entry points, localhost tooling,
Web, Android, configuration/services, and Moon Company runtime/control-plane do
not import or invoke Y.

Therefore Y does not acquire a secret or activate a runtime/provider/listener.

## Explicit non-authority

M17.6Y does not authorize private-key acquisition, generation, import/export,
keyfile access, HSM/vault/keyring/cloud-secret integration, runtime/provider
activation, listener/socket execution, Web/Android activation,
production/public-network activity, PostgreSQL/config/service mutation,
publishing, or deployment.

## Moon Company boundary

Y is a replaceable Moon Commerce composition seam only.

It grants Moon Company no secret access, key administration, runtime execution,
provider administration, identity/policy control, deployment authority, or
production control.

## Rollback

**source-only rollback:** revert the exact M17.6Y merge.

Because Y remains unselected and accepts only an already-constructed attestor
reference, rollback requires no key revocation, secret cleanup, listener
shutdown, database rollback, service restart, browser/device cleanup, provider
action, or deployment rollback.
