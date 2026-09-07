# M17.5H — Authentication proof transcript and private-key custody contract

Profile: `MARKETPLACE_APPLICATION_AUTH_PROOF_TRANSCRIPT_V1`

Exact implementation baseline: `69f339386fe7889e1c1a4ab27985125ddec2ef8f`

Risk classification: **HIGH security/privacy source contract**. This milestone freezes future Marketplace authentication signature meaning and the private-key custody seam, while performing no cryptographic operation and selecting no runtime/client authentication path.

## Scope

M17.5H is additive-only and consists of exactly:

- `src/marketplace/application/auth_proof_profile.py`
- `tests/test_m17_5h_auth_proof_profile.py`
- `tests/test_m17_5h_auth_proof_profile_artifacts.py`
- `docs/m17-5h-auth-proof-profile.md`

No existing Marketplace source, dependency manifest, workflow, configuration, Web source, Android source, runtime entry point, database path, or service definition is modified.

## Why this is not an `OLPProof`

The pinned Open Layer Protocol proof layer defines a genuine `OLPProof` as a proof over one immutable OLP record and requires a `recordCommitment`. Its compact `eddsa-ed25519-v1` identifier names the OLP ProofInputV1 signing/verification procedure.

Marketplace login does not currently create or authenticate a dedicated immutable OLP authentication record. It proves control for one application challenge/session transcript. M17.5H therefore does **not** pretend that a login challenge is an `OLPProof`, does not omit a mandatory OLP `recordCommitment`, and does not reuse the compact OLP `eddsa-ed25519-v1` identifier for non-OLP bytes.

The application profile instead owns a distinct absolute cryptosuite identifier:

```text
https://open-trust-layer.github.io/marketplace/application-auth/eddsa-ed25519-v1
```

That identifier means Ed25519 over the exact Marketplace authentication transcript defined below. M17.5H itself provides no concrete Ed25519 signer or verifier.

## Exact proof carrier

`MarketplaceAuthenticationProof` contains exactly eight mandatory fields and no extension surface:

- `type` = exact `MarketplaceAuthenticationProof`;
- `version` = exact integer `1`;
- `cryptosuite` = exact Marketplace-owned absolute URI above;
- `proofPurpose` = exact `assertion`;
- `verificationMethod` = one bounded absolute URI;
- `domain` = exact `https://open-trust-layer.github.io/marketplace/application-auth/v1`;
- `challenge` = exact canonical existing `mkc1_<43 base64url-no-padding chars>` carrier for 32 challenge bytes;
- `proofValue` = exact canonical `mks1_<86 base64url-no-padding chars>` carrier for a 64-byte signature.

Unknown fields, missing fields, alternate type/version/suite/purpose/domain, malformed or oversized verification-method URI, malformed challenge/signature carrier, noncanonical base64url, padding, wrong prefix, wrong raw length, duplicate JSON members, BOM, invalid UTF-8 and oversized proof JSON all fail closed with one non-reflective local profile error.

There are no timestamps, nonce, principal, public key, private key, key identifier other than `verificationMethod`, bearer/session token, redirect/callback, algorithm negotiation, extension map, DID document, provider metadata or hidden alternate carrier.

## Canonical signature carrier

A signature is exactly 64 raw bytes.

Text transport is exactly:

```text
mks1_<86 base64url-no-padding characters>
```

The decoder requires the exact `mks1_` prefix, exact character count, base64url alphabet only, exact 64-byte decoded length, and canonical round-trip re-encoding. It rejects padding and alternate spellings.

The carrier is transport only. `mks1_` text is never signed and `proofValue` is never part of the signed transcript.

## Exact deterministic transcript

`MarketplaceAuthTranscriptV1` is:

```text
ASCII("MARKETPLACE-AUTH") || 0x00 ||
0x01 ||
u16be(len(cryptosuite_utf8)) || cryptosuite_utf8 ||
u16be(len(proofPurpose_utf8)) || proofPurpose_utf8 ||
u16be(len(verificationMethod_utf8)) || verificationMethod_utf8 ||
u16be(len(domain_utf8)) || domain_utf8 ||
challenge_32_bytes
```

Rules:

- `MARKETPLACE-AUTH` is the fixed application-auth domain separator corresponding to the exact proof type/profile;
- version is one literal octet `0x01`;
- each text value is exact UTF-8 with no Unicode normalization, URI rewriting, alias substitution or case folding;
- each `u16be` value is an unsigned two-byte big-endian octet length for the immediately following UTF-8 field;
- all accepted text is bounded below 65536 octets; `verificationMethod` has the existing 2048-byte URI ceiling;
- challenge is exact raw 32-byte challenge material, not its textual `mkc1_` carrier;
- `proofValue` / signature bytes are excluded;
- there is no timestamp, nonce, principal, session token, record commitment, mutable client state or hidden context.

Changing the domain separator/type profile, version, cryptosuite, proof purpose, verification method, domain or challenge changes the transcript bytes. Tests freeze one exact cross-language byte vector and mutation behavior.

For the qualification vector using verification method `did:example:alice#key-1` and challenge bytes `00..1f`, the transcript is exactly 236 bytes. The tests freeze the complete expected hex representation; no signing operation is required to validate the vector.

## Purpose-specific signer custody boundary

`AuthenticationProofSigningRequest` contains only:

- one validated `verification_method` URI;
- one exact 32-byte challenge.

`AuthenticationProofSigner` exposes only a purpose-specific signer method:

```text
sign_authentication_proof(AuthenticationProofSigningRequest) -> 64 signature bytes
```

It is **not a generic signing oracle**. It accepts no arbitrary caller-supplied message bytes and no private-key bytes, seed, mnemonic, passphrase, exportable key material, browser-wallet secret, Android Keystore secret or generic provider handle string.

The signer port provides no key generation/import/export/list/rotate/delete operation, no persistence policy and no provider administration. The port is a custody seam only. This milestone contains **no concrete signing** and **no concrete verification** and never invokes the signer port.

Future signer implementations must construct/sign exactly this profile transcript from the typed request rather than expose a generic `sign(bytes)` operation for convenience.

## Relationship to M17.5D session establishment

The existing `/api/auth/sessions` state machine remains unchanged and continues to consume one challenge before the injected verifier runs. The outer request still carries the challenge independently.

A future concrete `AuthenticationProofVerifier` must decode this profile, verify the future signature, and return exact `VerifiedAuthenticationProof` facts so the already-reviewed M17.5D service can compare:

- `challenge_sha256` to the consumed challenge;
- exact domain;
- exact proof purpose;
- exact verification method;
- cryptographic validity.

M17.5H does not connect this profile to that verifier port and performs no signing or verification.

## Threat / abuse boundary

This slice fixes only **what future authentication signatures mean** and **where private-key custody must stop**.

The purpose-specific signer seam reduces confused-deputy and generic signing-oracle risk by preventing application code from handing arbitrary bytes to a future key holder. The profile also prevents algorithm/profile confusion with OLP record proofs by using a Marketplace-owned absolute cryptosuite URI and a distinct transcript domain separator.

This source does not establish that a verification method belongs to a principal. Existing `PrincipalBindingVerifier` remains the separately injected application policy/evidence boundary.

Successful future authentication must not be represented as proving real-world identity, ownership, legitimacy, authority, reputation, trust, payment, agreement, settlement, fulfillment or OLP-record proof semantics.

## Explicit non-authority

M17.5H grants:

- no private-key generation, import, export, storage, custody, rotation, deletion or use;
- no concrete signing and no concrete verification;
- no synthetic or real cryptographic operation in production source;
- no concrete `AuthenticationProofVerifier` implementation;
- no DID/resolver/provider lookup, policy change or network activity;
- no resolver/provider/network activity of any kind;
- no WebCrypto, browser-wallet or extension activation;
- no Android Keystore/provider use and no Android build, Gradle, install, emulator, adb or device action;
- no OAuth, OIDC, password, JWT, cookie, callback or redirect capability;
- no runtime activation and no runtime/client auth selection;
- no localhost live authentication;
- no credential/session/key persistence;
- no dependency widening;
- no PostgreSQL access, schema/data mutation, environment/config/secret mutation or service restart;
- no production/public-network activity;
- no deployment, publishing or distribution.

Merely importing the module creates no challenge, session, proof, signature or key operation.

## Validation

Focused qualification:

```text
python -m unittest \
  tests.test_m17_5h_auth_proof_profile \
  tests.test_m17_5h_auth_proof_profile_artifacts
```

The tests verify exact constants, canonical `mkc1_` and `mks1_` carriers, the 236-byte transcript vector, deterministic mutation behavior, strict proof/JSON shape, duplicate-member rejection, no material reflection, typed custody boundaries, no generic signer, no OLPProof impersonation, no crypto/provider/network/database imports, no runtime/client selection and no dependency widening.

The repository's existing `Marketplace conformance` workflow remains the authoritative exact-head acceptance gate and already discovers all `test_*.py` tests. No workflow modification is required.

Existing M17.5B-G security/conformance suites must remain green.

## Rollback and blast radius

Rollback is a **source-only rollback**: revert the exact M17.5H merge if a later merge is separately authorized.

Because this milestone adds one unselected profile/custody contract plus tests/documentation and performs no cryptographic or key operation, rollback requires no key revocation, credential/session cleanup, database migration, provider administration, service restart, Android cleanup, configuration rollback, deployment action or external data mutation.

Blast radius is limited to the new unselected authentication-proof profile module and its qualification artifacts.

## Later decision gates

Only after M17.5H is merged-green should later milestones separately review and authorize, in order:

1. a concrete **synthetic/local Ed25519 signer + verifier adapter** against the frozen transcript/carrier vectors, still unselected by runtime/client composition;
2. principal-binding/resolver policy and verification-material sourcing;
3. concrete Web and/or Android key custody/provider path with platform-specific user-presence/exportability constraints;
4. localhost auth-capable composition selection and bounded live acceptance.

These capabilities remain separate review, authorization and rollback decisions.
