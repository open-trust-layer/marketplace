# M17.6Q — Reference authentication-enrollment nonce authority composition

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_NONCE_AUTHORITY_V1`

Exact implementation baseline: `c67e54d1e66b70c9254707697950da9194607f0b`

Risk classification: **HIGH security/privacy / in-memory enrollment nonce-authority reference composition**.

M17.6Q adds one tiny, **unselected** reference composition joining the reviewed M17.6P material source to the reviewed M17.6H process-memory nonce authority.

The exact graph is:

`P → H`

Nothing else is selected.

## Exact six-file scope

Added:

1. `src/marketplace/reference/auth_enrollment_nonce_authority_v1.py`
2. `tests/test_m17_6q_reference_auth_enrollment_nonce_authority.py`
3. `tests/test_m17_6q_reference_auth_enrollment_nonce_authority_artifacts.py`
4. `docs/m17-6q-reference-auth-enrollment-nonce-authority.md`

Modified only for wheel membership:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No existing M17.6H/P/O/N source, runtime, HTTP/ASGI, Web, Android, provider, configuration, dependency, workflow, persistence, or governance source is modified.

## Construction boundary

The no-argument builder constructs exactly:

1. one `MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource`;
2. one `MarketplaceAuthenticationEnrollmentNonceAuthority` using that exact source.

The frozen result retains both exact objects.

The authority's captured `_nonce_bytes` bound method must belong to the exact retained P source.

The new authority must begin with empty `_outstanding` and `_spent` maps.

## Zero-consumption boundary

M17.6Q composition consumes **zero entropy**.

The P constructor is stateless and does not call its CSPRNG. The H constructor captures only the source method and initializes empty process-memory replay state.

Therefore importing, building, inspecting, or packaging Q creates no nonce and consumes no random material.

Nonce material can exist only after a later explicit H `issue_authentication_enrollment_nonce(...)` call, which M17.6Q does not perform.

## Stable failure

Malformed or cross-bound composition collapses to:

`reference authentication enrollment nonce authority composition failed`

No entropy-provider detail, nonce bytes, principal, verification method, public key, authority URI, lease, path, configuration, platform, or nested exception text is reflected.

## Authority boundary

M17.6Q creates only the existing bounded process-local nonce authority.

It does not create or select:

- approval policy;
- attestor;
- signer;
- private key;
- trust anchor;
- evidence store;
- authenticated startup;
- enrollment HTTP/ASGI;
- M17.6O reference enrollment launch;
- M17.6N foreground runtime;
- Uvicorn/provider;
- persistent/shared replay storage;
- Web or Android client.

The existing H capacity, expiry, one-use, digest-only retention, and process-memory semantics are unchanged.

## Non-selection boundary

M17.6Q remains **unselected**.

No M17.6O/N, authenticated startup/launch/runtime, Uvicorn/provider, Web, Android, CLI, service, environment/configuration, or Moon Company runtime/control-plane path instantiates it.

A later separately reviewed composition may choose to supply the Q authority into O together with separately reviewed policy and attestor collaborators.

## Moon Company boundary

M17.6Q is only a replaceable Moon Commerce reference composition for local enrollment anti-replay authority.

It adds no Moon Company runtime/control-plane dependency and grants Moon Company no approval-policy, signing, identity, session, enrollment, runtime, or production authority.

## Rollback

Rollback is **source-only rollback**: revert the exact M17.6Q merge.

Because Q is construction-only, unselected, and consumes zero entropy, rollback requires no nonce cleanup, session cleanup, key revocation, trust-store mutation, database rollback, service restart, provider administration, browser/device cleanup, or deployment rollback.
