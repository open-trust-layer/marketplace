# Product M17.6R — Reference enrollment launch with reference nonce authority

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_NONCE_AUTHORITY_V1`

Risk: **HIGH security/privacy** reference composition.

## Purpose

M17.6O already provides the inert reference authentication-enrollment launch selection, but deliberately requires a caller-supplied nonce authority, approval policy, attestor, authority URI, and evidence lease.

M17.6Q now provides the reviewed process-local reference nonce-authority composition: one M17.6P OS-CSPRNG material source bound to one M17.6H in-memory one-use nonce authority.

M17.6R connects those two existing capabilities only:

`Q → O`

It constructs exactly one Q composition and supplies that exact Q nonce authority to exactly one O launch composition. The approval policy and attestor remain caller-supplied. The authenticated launch plan, authority URI, and evidence lease remain caller-selected inputs under the existing O validation boundary.

## Frozen behavior

The M17.6R result retains exactly:

- one `MarketplaceReferenceAuthenticationEnrollmentNonceAuthority`;
- one `MarketplaceReferenceAuthenticationEnrollmentLaunch`.

The O launch must retain the exact `nonce.nonce_authority` object produced by Q. The Q nonce authority must remain bound to the exact Q material source.

Construction consumes **zero entropy** because Q constructs the material source and H authority without requesting nonce bytes. No nonce is issued or consumed. No policy decision occurs. No attestation or signing operation occurs. No request is handled.

Any dependency failure collapses to the stable non-reflective error:

`reference authentication enrollment launch nonce authority composition failed`

## Authority boundary

M17.6R chooses a reviewed process-local anti-replay implementation for the inert reference enrollment launch, and nothing more.

It does not choose a concrete approval policy. It does not choose an attestor, signer, private key, key provider, or trust anchor. It does not issue enrollment evidence. It does not make the Q authority persistent, shared, distributed, or globally authoritative.

The process-memory replay semantics and bounds defined by M17.6H remain unchanged.

## Runtime boundary

M17.6R remains **unselected** by the M17.6N foreground runtime seam, Uvicorn provider, Web client, Android client, CLI, services, configuration, and Moon Company runtime/control-plane.

There is no provider invocation, socket creation, bind/listen/accept, localhost smoke run, public-network action, background task, or service activation.

## Data and platform boundary

No filesystem, environment, database, PostgreSQL, SQLite, or network acquisition is introduced. No production credentials or private-key custody are introduced. No dependency or workflow widening is required.

## Moon Company boundary

This is a replaceable Moon Commerce reference composition. It does not grant Moon Company identity authority, approval authority, signing authority, session authority, runtime authority, or production authority. Moon Company may later discover or orchestrate a separately reviewed capability, but this source slice adds no Moon runtime dependency.

## Rollback

**source-only rollback:** revert the exact M17.6R merge.

Because the composition is inert and unselected, rollback requires no nonce cleanup, key revocation, trust-store change, database rollback, service restart, browser/device cleanup, provider administration, or deployment rollback.
