# M17.6E — Unselected trusted enrollment authority evidence issuance boundary

Profile: `MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_AUTHORITY_V1`

Exact implementation baseline: `4c8de670d1a9c024f811184df740d0c4f4fc6ba1`

Risk classification: **HIGH security/privacy / identity-trust authority source capability**.

M17.6E adds one source-only, unselected authority seam that can transform one exact caller-reviewed enrollment proposal into one canonical M17.5L evidence envelope through one injected purpose-specific attestor. It does not select or implement private-key custody.

## Exact scope

The implementation touches exactly six files.

Added:

1. `src/marketplace/application/auth_enrollment_authority.py`
2. `tests/test_m17_6e_auth_enrollment_authority.py`
3. `tests/test_m17_6e_auth_enrollment_authority_artifacts.py`
4. `docs/m17-6e-auth-enrollment-authority.md`

Modified only for package membership:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No M17.5L/M source, M17.6A/B/C/D source, active authentication/runtime composition, Web/Android source, dependency metadata, workflow, repository audit, PostgreSQL/configuration/service path, or deployment path is modified.

## Enrollment proposal input

`MarketplaceAuthenticationEnrollmentProposal` contains exactly:

- `principal`: exact non-normalized absolute URI;
- `verification_method`: exact non-normalized absolute URI;
- `public_key`: exact canonical M17.5L `mkp1_` public-key carrier.

Validation reuses M17.5L's existing canonical public-key parser and evidence-claim constructor. The proposal remains non-authoritative: it contains no authority decision, lease, attestation, trust status, acceptance state, session state, private-key material, role, membership, or delegation.

## Authority issuance

`issue_marketplace_authentication_enrollment_evidence(...)` receives the proposal plus trusted-composition inputs:

- exact authority URI;
- explicit `issued_at`;
- explicit `expires_at`;
- one injected purpose-specific attestor.

The function constructs exactly one existing `AuthenticationVerificationMethodEvidenceClaim` with:

- `controller_principal = proposal.principal`;
- `verification_method = proposal.verification_method`;
- exact 32 public-key bytes decoded from `proposal.public_key`.

It then constructs one existing `MarketplaceAuthenticationVerificationMethodEvidenceClaims`. Existing M17.5L validation therefore enforces exact URI semantics and the finite maximum 24-hour evidence lease. Entry validity is left unextended so the enclosing lease remains authoritative.

Canonical claims bytes are produced only by:

`encode_marketplace_authentication_verification_method_evidence_claims(...)`

No second evidence JSON representation or alternate canonicalizer is introduced.

## Attestation binding

The source computes SHA-256 over the exact canonical claims bytes and builds the exact existing M17.5M transcript only with:

`build_marketplace_authentication_evidence_trust_transcript(...)`

The authority URI comes from trusted composition, never from the enrollment proposal and never by inference from the principal or verification method.

Only after proposal, authority, lease, claims and transcript validation succeeds does the source resolve one injected operation:

`attest_authentication_enrollment(transcript: bytes) -> bytes`

The operation is called exactly once with the exact M17.5M transcript. It must return exactly 64 raw bytes. Provider exceptions and malformed results collapse to one stable non-reflective M17.6E error.

The resulting object is the existing M17.5L `MarketplaceAuthenticationVerificationMethodEvidenceEnvelope`.

## Purpose-specific attestor

The attestor seam is deliberately narrower than a signing API. Production M17.6E has:

- no `Ed25519PrivateKey`;
- no key generation/import/export;
- no private-key file, environment, keyring, HSM, vault or provider access;
- no seed, mnemonic or passphrase;
- no arbitrary caller-supplied transcript;
- no generic `sign(data)` operation;
- no retry, fallback or multi-signer iteration.

Tests may use deterministic synthetic private material only to prove the full issuance -> M17.5M verification -> M17.5L materialization path.

Concrete production custody/provider selection is a later separately governed capability.

## Explicit non-authority

M17.6E establishes only one finite authority attestation over one exact verification-method/controller/public-key binding.

It provides:

- no legal identity or ownership claim;
- no automatic verification-method allocation;
- no principal/controller inference or normalization;
- no DID resolution, role, membership, delegation or authorization logic;
- no trust-anchor provisioning/loading/mutation;
- **no production private-key custody**;
- **no generic signing oracle**;
- no network, DNS, HTTP or remote signer/provider access;
- no filesystem/environment/database/configuration acquisition;
- no persistence or revocation registry;
- no runtime, Web or Android selection;
- no live authentication/session establishment;
- no PostgreSQL mutation;
- no dependency/workflow/repository-audit widening;
- no production/public-network activity, deployment, publishing or distribution.

The module remains deliberately **unselected**.

## Failure behavior

All M17.6E-owned validation, attestor, and envelope-construction failures collapse to:

`AuthenticationEnrollmentAuthorityError("authentication enrollment authority operation failed")`

The error does not reflect principal, verification method, public key, authority, claims, attestation, provider details, or exception text.

## Qualification

Qualification freezes:

- exact profile and typed proposal shape;
- existing M17.5L URI/public-key validation reuse;
- canonical `mkp1_` parsing to exact 32 bytes;
- authority supplied separately from proposal;
- finite explicit evidence lease under M17.5L's existing 24-hour maximum;
- exactly one canonical evidence claim;
- exact preservation of principal, verification method and public-key bytes;
- canonical claims via existing M17.5L encoder only;
- SHA-256 over exact canonical claims bytes;
- transcript via existing M17.5M builder only;
- one purpose-specific attestor call only after validation;
- exact 64-byte attestation;
- existing M17.5L envelope result type;
- deterministic synthetic end-to-end issuance -> trust verification -> snapshot materialization;
- prior-attestation rejection after proposal substitution;
- stable non-reflective failures;
- zero concrete production private-key/custody/network/persistence/runtime capability;
- continued runtime/Web/Android non-selection;
- package membership coverage;
- FULL Marketplace conformance.

## Rollback and later gates

Rollback is **source-only rollback**: revert the exact M17.6E merge. Because this module is unselected, no-persistence, external-I/O-negative and has no concrete signer, rollback requires no key revocation, trust-store cleanup, session cleanup, database rollback, service restart, provider administration, browser cleanup, or device cleanup.

Later separately governed capabilities include: concrete authority custody/provider selection, policy deciding whether a proposal should be approved, authenticated enrollment HTTP and anti-replay semantics, trust-anchor/signer rotation and revocation, dynamic trusted snapshot replacement, browser enrollment workflow selection, bounded live localhost acceptance, production identity administration, public hosting and deployment.
