# Product M17.6T — Reference Ed25519 authentication-enrollment attestor

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_ED25519_ATTESTOR_V1`

Risk: **HIGH security/privacy** source-only private-key signing capability.

## Purpose

M17.6E defines the narrow purpose-specific enrollment attestor operation. M17.6S composes the reviewed nonce authority and exact-binding policy into the inert enrollment launch but deliberately leaves attestation caller-supplied.

M17.6T adds one concrete, **unselected**, process-local Ed25519 implementation of that purpose-specific operation. It does not create a generic signing service and it does not select M17.6S, runtime execution, configuration, Web, Android, or production behavior.

## Key boundary

Construction accepts exactly one caller-supplied **32-byte** Ed25519 private-key seed.

The implementation creates one in-memory `Ed25519PrivateKey` and does not retain the raw seed separately. It exposes no private-key export operation and no generic `sign(data)` API.

M17.6T performs no key generation, filesystem/key-file read, environment lookup, keyring/HSM/vault/provider lookup, network access, persistence, cache, background work, rotation, revocation, or trust-anchor mutation.

Tests use only fixed synthetic key bytes.

## Purpose-specific transcript boundary

The only public signing operation is:

`attest_authentication_enrollment(transcript)`

Before signing, the source requires the exact frozen M17.5M authentication-evidence transcript shape and rebuilds it with the existing `build_marketplace_authentication_evidence_trust_transcript` function.

The accepted transcript is exactly:

`MARKETPLACE-AUTH-EVIDENCE || 0x00 || version || u16be(authority_len) || authority_utf8 || claims_sha256`

The authority is validated by the existing M17.5M builder, the claims digest is exactly 32 bytes, and no leading or trailing bytes are accepted.

A successful call performs exactly one Ed25519 signature operation and requires an exact 64-byte result. There is no retry, fallback, alternate key, or signer selection.

Any M17.6T-owned failure collapses to the stable non-reflective error:

`reference authentication enrollment Ed25519 attestor failed`

## Non-selection boundary

M17.6T remains **unselected**.

M17.6S/O/N, Uvicorn/provider paths, startup/CLI/services, environment/configuration, Web, Android, and Moon Company runtime/control-plane do not import or instantiate this module.

A later separately reviewed composition may supply this purpose-specific attestor into M17.6S. That composition and any runtime execution remain separately governed.

## Explicit non-authority

This source does not authorize or perform production key provisioning, secret retrieval, external signer/HSM/vault activation, trust mutation, runtime/server/provider execution, socket creation, browser/Android activation, PostgreSQL/config/service mutation, dependency/workflow widening, production/public-network activity, deployment, publishing, or distribution.

## Moon Company boundary

M17.6T is a replaceable Moon Commerce reference attestor only.

It grants Moon Company no key-provisioning, policy-administration, identity-administration, runtime, deployment, or production authority.

## Rollback

**source-only rollback:** revert the exact M17.6T merge.

Because T is unselected and has no external I/O or persistence, rollback requires no key revocation, trust-store mutation, nonce/session cleanup, database rollback, service restart, provider administration, browser/device cleanup, or deployment rollback.
