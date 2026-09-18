# Product Agreement assent proof - first source slice

## Purpose

This slice adds the smallest transport-neutral bridge from an exact unpublished
Agreement candidate to one cryptographically verified party-assent observation.

It deliberately does not persist assent evidence, publish an Agreement, expose
an HTTP route, activate browser signing, select a client key, or claim legal
effect.

## Architecture

The application layer remains OLP-neutral.

    AgreementCandidateBuildResult
            |
            v
    MarketplaceAgreementAssentProofService
            |
            +-- trusted principal <-> verification-method snapshot
            +-- injected signing-input builder
            +-- injected verified-evidence builder

The reference layer owns the pinned OLP integration.

    exact Agreement candidate
    -> SHA-256 RecordCommitment
    -> minimal ProofInputV1
    -> deterministic CBOR bytes
    -> external Ed25519 signature
    -> standard OLPProof
    -> verify_proof()
    -> exact AssentEvidence

No direct olp import is added under src/marketplace/application.

## First proof profile

The source slice freezes:

    cryptosuite        eddsa-ed25519-v1
    proofPurpose       assertion
    verificationMethod exact trusted method URI
    recordCommitment   SHA-256 / COSE -16
    created            absent
    expires            absent
    domain             absent
    challenge          absent
    nonce              absent
    extensions         {}
    critical           []

The application service never accepts a caller-supplied public key or
attribution decision. Public key material and principal/method binding come only
from the already reviewed immutable verification-method snapshot.

## Preparation

Preparation is read-only.

It requires an exact AgreementCandidateBuildResult, re-derives the Agreement
Record Identity, requires that identity to match the candidate result, validates
the requested principal/method, verifies trusted principal/method binding at the
supplied evaluation time, builds exact signing bytes through the injected
reference seam, and limits signing input to 4096 bytes.

The returned immutable value contains only the exact Agreement Record Identity,
exact principal, exact verification method, and exact signing bytes.

## Finalization

Finalization accepts only an exact 64-byte Ed25519 signature.

It rebuilds the complete preparation from the candidate and current trusted
method evidence. A caller-modified preparation is rejected.

The public key is obtained only from the same trusted snapshot. The reference
builder reconstructs a standard OLP proof and requires:

    conformance                       CONFORMING
    record_binding                    VALID
    version_support                   SUPPORTED
    cryptosuite_support               SUPPORTED
    commitment_algorithm_support      SUPPORTED
    critical_extension_status         UNDERSTOOD
    verification_method_resolution    RESOLVED
    verification_method_compatibility COMPATIBLE
    cryptographic_validity            VALID
    purpose_status                    MATCH

Only then is AssentEvidence with accepted attribution produced. Attribution is
therefore derived from trusted application evidence, not caller input.

## Frozen cross-runtime vector

The tests freeze one Marketplace product vector built from a seller, buyer,
EUR 125 bicycle listing, buyer Proposal, seller Proposal acceptance, and method
urn:example:olp:test-key-1.

Expected Agreement identity:

    r1_grS0_HlLNS2A1VqdELEa_daC4IJl_SBGzxcAO6esM5A

Expected ProofInput length:

    106 bytes

The expected 64-byte signature has already been independently reproduced by
Node WebCrypto Ed25519 over those exact bytes and is verified by pinned OLP in
the reference test.

The private conformance seed used to derive the public test vector is not
present in this source slice.

## Security and authority boundary

This source slice performs no private-key generation/import/export, browser
CryptoKey handling, authentication-proof conversion, persistence or schema
migration, trust-anchor mutation, network I/O, Agreement publication, payment,
settlement, escrow, fulfillment, ownership transfer, runtime activation, or
deployment.

The verified evidence returned here is one input to the existing Agreement
formation evaluator. It does not by itself establish formation sufficiency,
legal enforceability, identity, or universal truth.

## Rollback

Rollback is source-only: revert this additive change set. No runtime or
persistent state is created by this slice.
