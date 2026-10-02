# Product M17.6Z — Compose local Ed25519 keyfile intake into U graph

Profile:
`MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_POLICY_NONCE_ED25519_KEYFILE_V1`

Risk: **HIGH security/privacy** source-only local private-key acquisition plus
inert enrollment-launch composition.

## Purpose

M17.6X defines a bounded local keyfile intake:

`canonical local key directory → exact T attestor`

M17.6Y defines the raw-key-free composition:

`existing T → S → existing U`

M17.6Z composes only those reviewed boundaries:

`X → Y → existing U`

Z does not define a new graph/result type. It returns the existing exact U
result.

## Exact composition contract

The caller supplies one authenticated loopback launch plan, one exact tuple of
reviewed R bindings, one local key directory string, authority, and evidence
lease seconds.

Z calls X exactly once with the exact directory. It then calls Y exactly once
with the exact caller plan/bindings/authority/lease and the exact T attestor
returned by X.

The returned value must be the exact existing U type or Z fails closed.

## Raw-key and local-file boundary

M17.6Z contains no `private_key_bytes` parameter or raw private-key handling.

Z does not construct T and performs no direct file open, stat, path traversal,
environment/config lookup, key generation/import/export, cryptographic signing,
or key serialization.

Its only local-file authority is the already-reviewed X boundary.

Qualification uses only **synthetic non-secret** 32-byte private-key fixtures in
temporary directories.

## Side-effect boundary

The composition performs zero attestation, nonce issuance/consumption, entropy
use, approval decisions, HTTP/ASGI request handling, database/network access,
provider/runtime/socket execution, persistence, retries, fallback, or
background work.

## Failure boundary

All Z-owned failures collapse to:

`reference authentication enrollment Ed25519 keyfile composition failed`

Paths, OS errors, raw key material, authority values, bindings, nested X/Y
errors, provider details, and runtime details are not reflected.

## Non-selection boundary

M17.6Z remains **unselected**.

Existing X, Y, U, V, W, startup/launch/runtime entry points, localhost tooling,
Web, Android, configuration/services, and Moon Company runtime/control-plane do
not import or invoke Z.

Therefore Z acquires no production secret and activates no runtime, provider,
listener, browser path, Android path, or public-network surface.

## Explicit non-authority

M17.6Z does not authorize production key provisioning, creating/writing/
modifying/deleting a keyfile, selecting a production key directory, HSM/vault/
keyring/cloud-secret integration, runtime/provider/listener activation,
Web/Android activation, production/public-network activity,
PostgreSQL/config/service mutation, publishing, or deployment.

## Moon Company boundary

Z is a replaceable Moon Commerce reference composition seam only.

It grants Moon Company no secret administration, identity/policy control,
runtime execution, provider administration, deployment authority, or production
control.

## Rollback

**source-only rollback:** revert the exact M17.6Z merge.

Because Z remains unselected and qualification uses synthetic temporary bytes
only, rollback requires no key revocation, secret cleanup, listener shutdown,
database rollback, service restart, browser/device cleanup, provider action, or
deployment rollback.
