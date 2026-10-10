# Product M17.6U — Reference enrollment launch with exact Ed25519 attestor

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_POLICY_NONCE_ED25519_V1`

Risk: **HIGH security/privacy** source-only private-key composition capability.

## Purpose

M17.6S composes the reviewed Q process-local nonce authority and R exact-binding
approval policy into the inert O enrollment launch, while leaving attestation
caller-supplied. M17.6T provides one concrete unselected purpose-specific
Ed25519 enrollment attestor.

M17.6U joins those exact reviewed pieces as:

`caller 32-byte seed → T → S(Q + R → O)`

It does not select the enrollment foreground runtime, a server provider, Web,
Android, configuration, or production behavior.

## Private-key boundary

The builder accepts exactly one caller-supplied **32-byte** Ed25519 private-key
seed and passes that exact value directly to the reviewed M17.6T constructor.

M17.6U itself does not import a cryptography implementation. It does not inspect,
transform, derive, serialize, export, log, persist, cache, or return the raw
seed. The result **must not retain** the raw seed separately.

All cryptographic behavior remains inside M17.6T. Construction creates the
process-local T attestor but performs **zero signing**.

There is no key generation, filesystem or environment lookup, keyring/HSM/vault
selection, provider discovery, retry, fallback, rotation, or revocation.

## Exact composition boundary

Construction creates exactly:

1. one `MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor`;
2. one M17.6S
   `MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce`.

The exact T attestor is passed by object identity into S and remains the exact
attestor retained by S and its O launch.

The exact authenticated launch plan, immutable R binding tuple, authority URI,
and finite evidence lease are preserved unchanged through the U → S → O graph.

The S/Q nonce replay maps remain empty after construction.

## Zero-consumption boundary

M17.6U composition performs no attestation, nonce issuance or consumption,
approval-policy decision, entropy consumption, clock sampling, HTTP/ASGI
handling, runtime/provider invocation, socket activity, persistence, or
external I/O.

## Failure boundary

M17.6U-owned failure collapses to the stable non-reflective error:

`reference authentication enrollment launch policy nonce Ed25519 composition failed`

Private-key bytes, authority values, nested exceptions, provider details,
filesystem paths, and configuration text are not reflected.

## Non-selection boundary

M17.6U remains **unselected**.

M17.6N foreground runtime, Uvicorn/provider paths, startup/CLI/services,
environment/configuration, Web, Android, and Moon Company runtime/control-plane
do not import or instantiate this composition.

A later separately reviewed milestone may decide how external production key
custody or runtime selection works. Neither is authorized here.

## Explicit non-authority

This source does not authorize production key provisioning or retrieval,
HSM/vault/keyring/provider activation, key export or rotation, trust-anchor
mutation, persistent/shared nonce or policy storage, runtime/server execution,
network activity, browser/Android activation, PostgreSQL/config/service
mutation, dependency/workflow widening, deployment, publishing, or
distribution.

## Moon Company boundary

M17.6U is a replaceable Moon Commerce reference composition only.

It grants Moon Company no identity-administration, key-provisioning, signing-key
retrieval, approval-administration, session, runtime, deployment, or production
authority.

## Rollback

**source-only rollback:** revert the exact M17.6U merge.

Because U is inert, unselected, process-local and zero-signing at construction,
rollback requires no key revocation, nonce/session cleanup, trust-store change,
database rollback, service restart, provider administration, browser/device
cleanup, or deployment rollback.
