# Marketplace M17.5M — Static Ed25519 authentication-evidence trust verifier

Profile: `MARKETPLACE_APPLICATION_AUTH_EVIDENCE_ED25519_TRUST_V1`

Baseline: exact merged-green Marketplace `main` `c140e1f27824e59dc4c623f739d8f398fd5ab9f0`.

Authority: owner-authorized **HIGH** authentication-trust source capability recorded on Issue #284. During implementation, authority was explicitly renewed from six files to the exact seven-file scope below after a predecessor M17.5I crypto allowlist was found to require narrow supersession.

## Purpose

M17.5L accepts canonical verification-method evidence only after an injected trust verifier binds acceptance to the exact claims digest and exact authority. M17.5M supplies one concrete trust verifier without adding evidence acquisition, persistence, dynamic trust-store administration, or runtime selection.

The verifier uses an immutable, constructor-injected public trust-anchor snapshot and direct Ed25519 public-key verification. It does not provision trust anchors or decide where they come from.

## Trust-anchor snapshot

`AuthenticationEvidenceTrustAnchor` contains exactly:

- `authority`: exact non-normalized absolute URI, UTF-8, at most 2048 bytes;
- `public_key`: exact 32-byte Ed25519 public key.

`MarketplaceAuthenticationEvidenceTrustAnchorSnapshot` contains **1..64** anchors. It rejects duplicate exact authority URIs and copies the caller-supplied sequence into a frozen mapping.

Lookup is purpose-specific:

`authentication_evidence_trust_key_bytes(authority)`

There is no normalization, aliasing, prefix matching, DID fragment inference, role or membership inference, graph traversal, multi-key iteration, alternate-authority fallback, dynamic replacement, or remote lookup.

Unknown authority fails closed through the stable M17.5M trust error.

## Attestation

For M17.5M, the M17.5L opaque attestation must be exactly **64 raw bytes** and is interpreted only as an Ed25519 signature.

No JSON, JWS, COSE, VC, X.509, DID proof wrapper, alternate algorithm, alternate encoding, or fallback is accepted.

M17.5L itself remains unchanged and continues to treat attestation bytes as opaque.

## Frozen transcript

For canonical L claims bytes:

`claims_sha256 = SHA-256(envelope.claims_json)`

The signature transcript is exactly:

```text
ASCII("MARKETPLACE-AUTH-EVIDENCE") || 0x00 ||
0x01 ||
u16be(len(authority_utf8)) || authority_utf8 ||
claims_sha256
```

Authority bytes are the exact canonical claims authority encoded as UTF-8. No normalization or implicit context is permitted.

The prefix and version domain-separate evidence trust from the M17.5H authentication proof transcript and from OLP record proofs.

## Verification contract

`MarketplaceEd25519AuthenticationEvidenceTrustVerifier` implements M17.5L's existing purpose-specific trust-verifier contract.

For one verification attempt it:

1. requires the exact M17.5L envelope type and exact 64-byte attestation;
2. decodes the exact canonical L claims using the existing L decoder;
3. computes SHA-256 of the exact claims bytes;
4. performs one exact authority lookup in the immutable trust-anchor snapshot;
5. constructs the frozen transcript;
6. constructs `Ed25519PublicKey` from the exact 32-byte public anchor;
7. verifies the raw signature;
8. returns L's existing `VerifiedAuthenticationVerificationMethodEvidence`.

A valid signature returns the exact digest, exact authority and `accepted=True`. `InvalidSignature` returns the same exact facts with `accepted=False`, allowing L to reject through its existing fail-closed trust result path.

Unknown authority, malformed anchor material, malformed envelope, malformed signature length, decoder failure, or malformed verifier construction fails closed with a stable non-reflective M17.5M error.

No error includes authority, public key, raw claims, attestation/signature bytes, provider detail, or exception text.

## Cryptographic boundary

Production code uses only the already-reviewed optional dependency:

`auth-verify = ["cryptography==50.0.1"]`

Base `dependencies = []` remains unchanged. CI already installs exactly `cryptography==50.0.1`; no dependency or workflow change is part of M17.5M.

Production M17.5M contains `Ed25519PublicKey` verification only. It contains **no production private-key** generation, import, export, storage, custody, use, signing, seed handling, randomness, generic signing oracle, `Ed25519PrivateKey`, NaCl, or production `olp.crypto.ed25519`.

Synthetic private-key use is confined to tests using the published RFC 8032 non-secret seed fixture.

## Predecessor guard supersession

M17.5I originally froze production `cryptography` imports to M17.5J alone. That assertion became intentionally stale when M17.5M introduced a second separately reviewed public-only verifier.

The renewed authority permits modifying only `tests/test_m17_5i_auth_ed25519_artifacts.py` to change the allowlist from J-only to exactly:

- `src/marketplace/application/auth_verifier_ed25519.py`;
- `src/marketplace/application/auth_evidence_trust_ed25519.py`.

The superseded guard continues to reject production `olp.crypto.ed25519`, NaCl, `Ed25519PrivateKey`, private-key/signing/key-generation capability, and any `cryptography` import in every other production Python file.

This is a policy supersession only; it creates no new runtime selection or dependency.

## External-I/O and runtime boundary

M17.5M performs **no network** or evidence acquisition. It contains no HTTP, DNS, socket, redirect, remote retrieval, filesystem/environment/database/provider lookup, background refresh, retry, cache, or persistence.

Trust anchors are supplied only through constructor injection. M17.5M does not define provisioning, source-of-truth, rotation, expiry, revocation, replacement, or multi-key rollover.

It remains unselected by application authentication composition, localhost tooling, Web and Android. There is **no runtime activation**, live authentication, service restart, PostgreSQL/configuration mutation, production/public-network activity, deployment, publishing, or distribution.

## Exact seven-file implementation scope

Added:

1. `src/marketplace/application/auth_evidence_trust_ed25519.py`
2. `tests/test_m17_5m_auth_evidence_trust_ed25519.py`
3. `tests/test_m17_5m_auth_evidence_trust_artifacts.py`
4. `docs/m17-5m-auth-evidence-trust-ed25519.md`

Modified:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`
7. `tests/test_m17_5i_auth_ed25519_artifacts.py`

No eighth file is authorized.

## Qualification

Tests cover the exact profile/transcript bytes, RFC 8032 public key and deterministic fixed signature, immutable 1..64 anchor bounds, duplicate rejection, exact URI lookup, exact 64-byte attestation, valid verification, corrupted signature, claims substitution, authority substitution, unknown authority/no fallback, malformed inputs, full L→K materialization, package inclusion, predecessor crypto allowlist supersession, dependency/workflow stability, runtime non-selection, and forbidden production capabilities.

## Rollback and blast radius

Rollback is **source-only rollback**: revert the exact eventual M17.5M merge if separately authorized.

Because the verifier and anchors remain constructor-injected, process-local, public-key-only, unselected and external-I/O-negative, rollback requires no credential/key revocation, session cleanup, trust-store administration, database migration, service restart, device cleanup, configuration rollback, or external-data mutation.

Blast radius is limited to the M17.5M public trust-anchor/verifier module, tests/docs, wheel-member controls, and the narrow predecessor test supersession.

## Non-authority

M17.5M authorizes no trust-anchor provisioning/loading from filesystem, environment, database or network; no dynamic trust-store administration; no anchor rotation/revocation; no resolver/provider or network activity; no persistence/cache; no production private-key/signing capability; no runtime/client authentication selection; no live authentication; no WebCrypto/browser wallet; no Android action; no PostgreSQL/config/service mutation; no production/public-network activity; no deployment, publishing, distribution, or merge.
