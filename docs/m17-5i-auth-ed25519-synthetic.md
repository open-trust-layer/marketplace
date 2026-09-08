# M17.5I — Synthetic Ed25519 authentication-proof interoperability qualification

Profile: `MARKETPLACE_APPLICATION_AUTH_ED25519_SYNTHETIC_V1`

Exact implementation baseline: `8bab6c83f09e299f392cf6f994f1fa73406ae379`

Tracking: Issue #276.

Risk classification: **HIGH security/privacy test qualification**. This milestone performs real Ed25519 signing and verification only inside deterministic test code using one fixed synthetic non-secret public test key fixture. It introduces no production signer/verifier capability, real key custody, runtime/client authentication selection, provider authority, or deployment.

## Scope

M17.5I is additive-only and consists of exactly:

- `tests/test_m17_5i_auth_ed25519_synthetic.py`
- `tests/test_m17_5i_auth_ed25519_artifacts.py`
- `docs/m17-5i-auth-ed25519-synthetic.md`

No existing Marketplace production source, dependency manifest, workflow, configuration, Web source, Android source, runtime entry point, database path, or service definition is modified.

## Dependency boundary

Marketplace continues to declare an empty base runtime dependency set (`dependencies = []`). M17.5I does not add `cryptography`, PyNaCl, or another crypto package to Marketplace.

The existing Marketplace conformance workflow already checks out the Open Layer Protocol reference at exact source commit:

`41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c`

and installs that pinned OLP checkout into the disposable CI environment before Marketplace tests run. That pinned OLP package already declares `cryptography>=41.0` and exposes the reviewed helper module `olp.crypto.ed25519`.

M17.5I imports the pinned OLP helper **only from the additive test module**. Marketplace production source does not import `olp.crypto.ed25519` or `cryptography`, and no production code relies on OLP's transitive crypto dependency. This is deliberately **no dependency widening**.

A later production verifier/dependency decision must explicitly decide whether Marketplace should declare and own a production crypto dependency. M17.5I does not make that decision implicitly.

## Fixed synthetic key fixture

The qualification uses RFC 8032 Ed25519 test vector 1.

The exact fixed synthetic non-secret 32-byte test seed is:

```text
9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60
```

Its expected public key is:

```text
d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a
```

These bytes are published test material, deliberately non-secret, and suitable only for deterministic interoperability qualification. They must never be treated as a production identity key, custody secret, wallet key, authentication secret, signing authority, funds key, or reusable private credential.

M17.5I performs no randomized key generation and reads no key material from the operating system, environment, filesystem, database, provider, keyring, wallet, browser extension, Android Keystore, network, or device.

## Frozen Marketplace transcript qualification

M17.5H froze `MarketplaceAuthTranscriptV1`, the `MarketplaceAuthenticationProof` carrier, the Marketplace-owned Ed25519 cryptosuite identifier, and the exact `mks1_` 64-byte signature carrier.

For the frozen M17.5H test request:

- verification method: `did:example:alice#key-1`
- challenge: bytes `00..1f`

the exact transcript remains 236 bytes.

Using the fixed RFC 8032 seed above, the pinned OLP Ed25519 implementation must produce this deterministic 64-byte signature:

```text
85fb0e24d5b1bf54ae397e1028a6e2db690e67d8eaa279fcd2e39cfe17240030206b3eda21574888fde8b0b6d331cba53438e660b3e17bb9d481ce06179ed505
```

The test freezes that cross-boundary vector, verifies it with the expected public key, and verifies exact `mks1_` encode/decode round-trip behavior.

This qualification is not an `OLPProof`, does not create an OLP `recordCommitment`, and does not reuse OLP record-proof semantics for application login.

## Purpose-specific test signer

`SyntheticEd25519AuthenticationProofSigner` exists only in the M17.5I test module.

It structurally follows the frozen M17.5H `AuthenticationProofSigner` custody seam:

```text
sign_authentication_proof(AuthenticationProofSigningRequest) -> 64 signature bytes
```

The fixture:

- accepts only the typed Marketplace authentication signing request;
- constructs exactly the frozen Marketplace authentication transcript;
- signs only that transcript using the fixed public test seed;
- returns exactly the Ed25519 signature bytes consumed by the frozen proof carrier;
- exposes no generic `sign(bytes)` method;
- accepts no caller-supplied seed, private key, mnemonic, passphrase, key handle, provider handle, or arbitrary message bytes.

The fixed seed is embedded only because this is deterministic test-only qualification. No equivalent production custody implementation is introduced or authorized.

## Test verifier and existing failure semantics

`SyntheticEd25519AuthenticationProofVerifier` also exists only in the M17.5I test module.

It:

1. parses the exact frozen `MarketplaceAuthenticationProof`;
2. reconstructs the exact M17.5H transcript;
3. verifies its 64-byte Ed25519 signature with the fixed synthetic public key through the pinned OLP helper;
4. returns only the existing M17.5D `VerifiedAuthenticationProof` facts:
   - challenge SHA-256;
   - exact domain;
   - exact proof purpose;
   - exact verification method;
   - cryptographic validity.

A well-formed proof whose signature bytes are corrupted remains structurally parseable but returns `cryptographically_valid=False`. The existing M17.5D service then rejects it with stable `AUTH_PROOF_INVALID`.

An infrastructure exception raised by the injected verifier remains the already-reviewed distinct `AUTH_PROOF_VERIFIER_UNAVAILABLE` path. M17.5I changes no HTTP code and invents no new production exception taxonomy.

`PrincipalBindingVerifier` remains the separate policy boundary that determines whether a verification method may authenticate the requested principal. Successful Ed25519 verification alone does not establish identity, authority, ownership, legitimacy, trust, or permission.

## In-process session qualification

The focused tests compose the existing M17.5D session adapter with:

- the existing deterministic fixed challenge/session material source fixture;
- the existing synthetic `AllowBinding` principal-binding fixture;
- the M17.5I test-only signer/verifier.

They exercise one complete in-process sequence:

```text
POST /api/auth/challenges
        ->
frozen Marketplace transcript
        ->
fixed-seed Ed25519 signature
        ->
MarketplaceAuthenticationProof
        ->
POST /api/auth/sessions
        ->
existing M17.5D session issuance
```

No socket, listener, public network, localhost runtime, server process, browser, Android process, provider, database, or external service is used.

Negative qualification also proves that:

- corrupting otherwise well-formed signature material yields `AUTH_PROOF_INVALID`;
- changing challenge-bound transcript material while retaining a cryptographically valid signature for the changed transcript cannot authenticate the separately registered challenge;
- verifier infrastructure failure remains `AUTH_PROOF_VERIFIER_UNAVAILABLE`.

## Threat and authority boundary

M17.5I proves only that the frozen Marketplace application-auth transcript and proof carrier interoperate correctly with real Ed25519 mechanics in deterministic synthetic tests.

It does **not** prove or establish:

- that `did:example:alice#key-1` belongs to any real principal;
- DID/controller resolution or trust policy;
- real-world identity, ownership, authority, legitimacy, agreement, payment, settlement, or legal effect;
- safe production private-key custody;
- production signer/verifier availability;
- browser-wallet, WebCrypto, extension, Android Keystore, HSM, wallet, keyring, or provider compatibility;
- production runtime authentication readiness;
- OLP-record proof semantics.

## Explicit non-authority

M17.5I grants:

- no production source change;
- no Marketplace dependency-manifest or workflow change;
- no production private-key generation, import, export, storage, custody, rotation, deletion, or use;
- no randomized key generation;
- no production signer or verifier implementation or selection;
- no generic signing oracle;
- no resolver/provider/network activity: no DID resolver, provider lookup, provider administration, or network activity;
- no WebCrypto, browser-wallet, extension, or active Web authentication capability;
- no Android Keystore/provider capability and no Android build, Gradle execution, install, emulator, adb, or device action;
- no OAuth, OIDC, password, JWT, cookie, callback, redirect, or cross-origin credential capability;
- no credential/session/key persistence;
- no PostgreSQL access, schema change, data mutation, environment/config/secret mutation, or service restart;
- no runtime activation and no localhost live authentication;
- no production/public-network activity;
- no deployment, publishing, or distribution.

All crypto operations and the fixed synthetic key bytes remain test-only and unselected.

## Validation

Focused qualification:

```text
python -m unittest \
  tests.test_m17_5i_auth_ed25519_synthetic \
  tests.test_m17_5i_auth_ed25519_artifacts
```

The repository's existing `Marketplace conformance` workflow remains the authoritative exact-head FULL acceptance gate and already discovers every `tests/test_*.py` module. No workflow modification is necessary.

Predecessor M17.5B-H security/conformance behavior must remain green.

## Rollback and blast radius

Rollback is a **source-only rollback**: revert the exact M17.5I merge if a merge is later separately authorized.

Because the change consists only of two additive test modules and this documentation file, with fixed public synthetic test material and no runtime selection, rollback requires no key revocation, credential/session cleanup, provider administration, database migration, service restart, configuration rollback, Android cleanup, external data mutation, or deployment action.

The blast radius is limited to the three additive M17.5I artifacts.

## Later decision gates

Only after M17.5I is merged-green should the next authentication milestone make the separate **production verifier/dependency decision**: whether Marketplace should add a production-source Ed25519 verifier adapter and an explicit declared crypto dependency boundary.

Subsequent authority remains separate for:

1. principal-binding and resolver/provider policy;
2. concrete Web and/or Android private-key custody/provider integration;
3. auth-capable localhost/runtime composition selection;
4. bounded live authentication acceptance.

M17.5I does not authorize any of those later capabilities.
