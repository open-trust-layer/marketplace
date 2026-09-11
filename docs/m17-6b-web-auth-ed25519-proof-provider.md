# M17.6B — Unselected WebCrypto Ed25519 authentication proof provider

Profile: `MARKETPLACE_WEB_AUTH_ED25519_PROOF_PROVIDER_V1`

Exact implementation baseline: `d2a16fa4b26f6e489118ca1679ce2dd288b757e7`

Risk classification: **HIGH security/privacy** source capability.

M17.6B adds one source-only, unselected Web proof-provider adapter for the already-reviewed Marketplace authentication protocol. It is the first Web source capability permitted to use private signing authority, but only through an already-supplied non-extractable Ed25519 private CryptoKey.

## Exact scope

The milestone is additive-only and consists of exactly:

- `web/auth_ed25519_proof_provider.js`
- `tests/test_m17_6b_web_auth_ed25519_proof_provider_contract.py`
- `tests/test_m17_6b_web_auth_ed25519_proof_provider_artifacts.py`
- `docs/m17-6b-web-auth-ed25519-proof-provider.md`

No existing Web entry point, Android source, Python authentication/runtime source, dependency manifest, workflow, repository-audit control, PostgreSQL/configuration/service path, or runtime state is modified.

## Purpose-specific provider boundary

The factory accepts only:

- one injected `SubtleCrypto`-compatible signing surface;
- one already-supplied non-extractable Ed25519 private CryptoKey;
- one pinned verification-method URI.
The provider object exposes only `createAuthenticationProof(request)`. It does not expose a generic arbitrary-message signing oracle.

Before every signing attempt, the supplied key must still report:

- `type === "private"`;
- `extractable === false`;
- `algorithm.name === "Ed25519"`;
- exactly one usage, `"sign"`.

M17.6B performs no key acquisition. There is **no key generation**, **no key import**, **no key export**, no wrapping/unwrapping, no enrollment, registration, rotation, revocation, recovery or backup.

## Request binding

The provider requires the exact M17.6A establishment request shape and exact reviewed values:

- profile `MARKETPLACE_WEB_AUTH_SESSION_ESTABLISHMENT_V1`;
- one bounded principal URI;
- the exact pinned verification-method URI;
- canonical `mkc1_...` challenge;
- authentication domain `https://open-trust-layer.github.io/marketplace/application-auth/v1`;
- proof purpose `assertion`.

Any alternate profile/domain/purpose/method, malformed URI, malformed/noncanonical challenge, unexpected request member, or invalid key shape fails before signing with one stable non-reflective local error.

## Frozen transcript

The canonical challenge carrier is decoded to exactly 32 raw bytes. The signed transcript is exactly the M17.5H profile:
```text
ASCII("MARKETPLACE-AUTH") || 0x00 || 0x01 ||
u16be(len(cryptosuite_utf8)) || cryptosuite_utf8 ||
u16be(len(proofPurpose_utf8)) || proofPurpose_utf8 ||
u16be(len(verificationMethod_utf8)) || verificationMethod_utf8 ||
u16be(len(domain_utf8)) || domain_utf8 ||
challenge_32_bytes
```

The provider signs raw transcript bytes, not JSON, not the textual challenge carrier, and not `proofValue`. The M17.5H qualification vector remains exactly 236 bytes for `did:example:alice#key-1` with challenge bytes `00..1f`.

## Signing and proof carrier

For one valid request the provider performs exactly one purpose-specific operation:

```text
subtle.sign({ name: "Ed25519" }, privateKey, transcript)
```

The returned value must be exactly 64 signature bytes. It is encoded canonically as:

```text
mks1_<86 base64url-no-padding characters>
```

The provider returns exactly the existing eight-field `MarketplaceAuthenticationProof`: type, version, cryptosuite, proof purpose, verification method, domain, original canonical challenge carrier, and proof value.

M17.6B does not change M17.5H/M17.5I signature meaning, session semantics, principal-binding policy, trust evidence, or OLP proof semantics.
## Explicit non-authority

This milestone grants:

- no key generation, import, export, persistence, enrollment, registration, rotation, revocation, recovery or backup;
- no raw private-key, seed, mnemonic or passphrase input;
- no browser wallet, extension, WebAuthn/passkey or external-signer integration;
- no localStorage, sessionStorage, IndexedDB, cookies, Cache API or service-worker credential persistence;
- no ambient `window.crypto` / `globalThis.crypto` selection;
- no active Web authentication selection in `web/index.html` or `web/app.js`;
- no browser execution or real-browser secure-context acceptance;
- no Android action;
- no network, database, service, configuration or runtime mutation;
- no dependency, package or workflow widening;
- no production/public-network activity;
- no deployment, publishing or distribution.

The adapter is deliberately unselected source. A page cannot reach it unless a later reviewed composition explicitly supplies both the signer surface and the already-provisioned non-extractable key.

## Failure and secret handling

All local validation, signer exceptions and malformed signer results collapse to one stable non-reflective proof error. Error text does not include the private key, transcript, challenge or signature.

The source contains no console logging, telemetry, URL propagation, storage, retry, refresh, timer, worker or background behavior. There is **no credential persistence**.
## Qualification

Qualification must preserve:

- exact M17.5H constants and 236-byte transcript vector;
- exact M17.5I RFC 8032 signature/carrier compatibility;
- canonical challenge decoding and signature encoding;
- exact verification-method binding;
- exactly one Ed25519 signing call on the valid path;
- zero signing before all request/key checks pass;
- rejection of non-64-byte signer results;
- stable non-reflective failures;
- no generic signing surface;
- no key lifecycle, persistence or active-client selection;
- existing M17.5H/I and M17.6A guards remain green.

Repository audit and Marketplace conformance remain authoritative without workflow or dependency widening.

## Rollback and later gates

Rollback is **source-only rollback**: revert the exact M17.6B merge if later separately authorized. Because the provider is unselected and performs no key provisioning or persistence, rollback requires no key revocation, storage cleanup, database migration, service restart or deployment action.

Later capabilities remain separately governed: concrete Web key creation/enrollment/custody lifecycle; binding provisioned verification material to server evidence; active Web login/session-derived identity; bounded **real-browser secure-context acceptance**; Android custody/auth; and production key administration, service hosting, public-network exposure and deployment.

Until those gates are separately reviewed, M17.6B provides **no active Web authentication selection** and no production authentication authority.
