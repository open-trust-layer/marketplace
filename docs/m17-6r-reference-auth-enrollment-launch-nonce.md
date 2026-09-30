# M17.6R — Reference enrollment launch with reference nonce authority

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_NONCE_V1`

Exact implementation baseline: `52c15a43ff0b7184508cf573192c866b27819d86`

Risk classification: **HIGH security/privacy / reference authenticated-enrollment composition capability**.

M17.6R adds one tiny, **unselected** reference composition that supplies the exact M17.6Q reference nonce-authority graph to the existing M17.6O reference authentication-enrollment launch.

The exact new graph is:

`Q → O`

M17.6O continues to compose the already-reviewed enrollment startup and launch layers. M17.6R does not alter those layers and does not invoke M17.6N runtime execution.

## Exact six-file scope

Added:

1. `src/marketplace/reference/auth_enrollment_launch_nonce_v1.py`
2. `tests/test_m17_6r_reference_auth_enrollment_launch_nonce.py`
3. `tests/test_m17_6r_reference_auth_enrollment_launch_nonce_artifacts.py`
4. `docs/m17-6r-reference-auth-enrollment-launch-nonce.md`

Modified only for wheel membership:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No existing Q/O/N, startup, launch, runtime, HTTP/ASGI, Web, Android, provider, dependency, workflow, PostgreSQL, configuration, service, audit, or governance source is modified.

## Exact inputs

The builder accepts:

- one exact existing authenticated loopback launch plan;
- one caller-supplied purpose-specific enrollment approval policy;
- one caller-supplied purpose-specific enrollment attestor;
- one explicit authority value;
- one finite evidence lease.

M17.6R does not create the policy, attestor, authority, or lease.

## Exact composition

The builder constructs exactly:

1. one M17.6Q `MarketplaceReferenceAuthenticationEnrollmentNonceAuthority`;
2. one M17.6O `MarketplaceReferenceAuthenticationEnrollmentLaunch` using the exact nonce authority retained by that Q graph.

The frozen result retains the exact authenticated plan, caller collaborators/values, Q graph, and O graph.

Identity checks fail closed unless the O launch retains the exact authenticated plan, exact Q nonce authority, exact caller policy, exact caller attestor, exact authority value, and exact evidence lease.

## Zero-consumption boundary

M17.6R construction consumes **zero entropy**.

M17.6Q construction is already frozen to construct its P material source and H process-memory nonce authority without calling the CSPRNG. M17.6R performs no nonce issuance or consumption.

Construction also performs zero:

- approval-policy decisions;
- attestation or signing;
- wall-clock sampling;
- authentication/session material generation;
- HTTP/ASGI request handling;
- provider inspection;
- runtime invocation;
- socket creation/bind/listen/accept;
- filesystem, network, or database access.

The Q nonce authority begins with empty outstanding and spent replay state and remains empty after M17.6R composition.

## Explicit authority boundary

M17.6R does not create or select:

- a concrete enrollment approval policy;
- a concrete enrollment attestor;
- a signer or private key;
- trust anchors;
- persistent/shared nonce or replay storage;
- evidence persistence;
- runtime/server execution;
- Uvicorn/provider selection;
- configuration/environment authority;
- Web or Android enrollment activation.

The caller-supplied policy and attestor remain independent authority-bearing boundaries.

## Runtime non-selection

The result is inert launch metadata.

M17.6R does not invoke M17.6N, does not import/select Uvicorn, does not call a provider, and does not open a socket.

No existing CLI, Web, Android, service, startup, runtime, or Moon Company path selects this reference module.

## Moon Company boundary

M17.6R gives Moon Commerce a replaceable reference composition for attaching a reviewed ephemeral anti-replay nonce authority to the existing enrollment launch graph while preserving Marketplace independence and authority separation.

It adds no Moon Company control-plane/runtime dependency and grants Moon Company no approval-policy, signing, identity, session, enrollment, runtime, or production authority.

## Rollback

Rollback is **source-only rollback**: revert the exact M17.6R merge.

Because the composition is inert, unselected, and consumes zero entropy, rollback requires no listener shutdown, nonce cleanup, session cleanup, key revocation, trust-store mutation, database rollback, service restart, provider administration, browser/device cleanup, or deployment rollback.
