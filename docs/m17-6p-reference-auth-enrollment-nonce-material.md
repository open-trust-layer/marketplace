# M17.6P — Reference authentication-enrollment nonce material source

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_NONCE_MATERIAL_V1`

Exact implementation baseline: `477a6e703650b7bd4f21f9ba1b2c144060562e64`

Risk classification: **HIGH security/privacy / ephemeral CSPRNG enrollment-nonce material source capability**.

M17.6P adds one tiny, stateless, **unselected** reference adapter for the existing M17.6H `AuthenticationEnrollmentNonceMaterialSource` protocol.

## Exact six-file scope

Added:

1. `src/marketplace/reference/auth_enrollment_nonce_material_v1.py`
2. `tests/test_m17_6p_reference_auth_enrollment_nonce_material.py`
3. `tests/test_m17_6p_reference_auth_enrollment_nonce_material_artifacts.py`
4. `docs/m17-6p-reference-auth-enrollment-nonce-material.md`

Modified only for wheel membership:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No existing nonce authority, reference enrollment launch, runtime, ASGI, HTTP, Web, Android, provider, configuration, dependency, workflow, persistence, or governance source is modified.

## Exact material boundary

The source reuses the existing reviewed bound:

`AUTH_ENROLLMENT_NONCE_BYTES == 32`

Each explicit `enrollment_nonce_bytes()` call performs exactly one standard-library OS CSPRNG call:

`secrets.token_bytes(AUTH_ENROLLMENT_NONCE_BYTES)`

The exact returned value must be `bytes` and exactly 32 bytes long.

Import and construction consume zero entropy.

There is no cache, pool, prefetch, retry, fallback PRNG, state, environment lookup, file access, network access, or persistence.

## Stable failure

CSPRNG provider failure or malformed provider output collapses to:

`reference authentication enrollment nonce material failed`

Provider detail and material bytes are never reflected.

## Purpose restriction

This adapter produces enrollment anti-replay nonce material only.

It does not produce or manage authentication/session tokens, API keys, passwords, encryption keys, private keys, signing keys, trust anchors, attestation signatures, recovery secrets, payment credentials, user identifiers, or device identifiers.

## Non-selection boundary

M17.6P remains **unselected**.

It is not instantiated by:

- M17.6H nonce authority;
- M17.6O reference enrollment launch selection;
- M17.6N foreground runtime seam;
- authenticated startup/launch/runtime;
- Uvicorn/provider paths;
- Web;
- Android;
- CLI or service definitions;
- environment/configuration;
- Moon Company runtime/control-plane.

A later separately reviewed slice may choose to supply this adapter to an M17.6H nonce authority.

## Explicit non-authority

M17.6P authorizes no automatic nonce issuance, nonce-authority construction, persistence, concrete enrollment policy, attestor/signer/private-key custody, trust mutation, HTTP/ASGI/runtime selection, socket/server execution, Web/Android activation, database/config/service mutation, production activity, deployment, publishing, or distribution.

## Moon Company boundary

M17.6P is only a replaceable Moon Commerce adapter for ephemeral enrollment anti-replay material.

It adds no Moon Company runtime/control-plane dependency and grants Moon Company no policy, signing, identity, session, enrollment, runtime, or production authority.

## Rollback

Rollback is **source-only rollback**: revert the exact M17.6P merge.

Because the adapter is stateless and unselected, rollback requires no nonce cleanup, session cleanup, key revocation, trust-store mutation, database rollback, service restart, provider administration, browser/device cleanup, or deployment rollback.
