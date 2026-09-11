# M17.6C — Unselected WebCrypto Ed25519 key-creation boundary

Profile: `MARKETPLACE_WEB_AUTH_ED25519_KEY_CREATION_V1`

Exact implementation baseline: `910e27ad608e108270a305b83d343418f18cee1e`

Risk classification: **HIGH security/privacy** source capability.

M17.6C adds one source-only, unselected WebCrypto Ed25519 key-creation adapter. It is the first Marketplace Web source capability permitted to create fresh private authentication authority. The private signing key is created as non-extractable and remains memory-only; this milestone performs public-key export only.

## Exact scope

The milestone is additive-only and consists of exactly:

- `web/auth_ed25519_key_creation.js`
- `tests/test_m17_6c_web_auth_ed25519_key_creation_contract.py`
- `tests/test_m17_6c_web_auth_ed25519_key_creation_artifacts.py`
- `docs/m17-6c-web-auth-ed25519-key-creation.md`

No existing Web entry point, authentication establishment source, proof-provider source, client-session source, Android source, Python authentication/runtime source, dependency manifest, workflow, repository-audit control, PostgreSQL/configuration/service path, or runtime state is modified.

## Purpose-specific creation boundary

The factory accepts only one injected `SubtleCrypto`-compatible surface with `generateKey` and `exportKey`. It exposes only `createAuthenticationKey(request)`.

The request shape is exactly:

```text
{ profile: "MARKETPLACE_WEB_AUTH_ED25519_KEY_CREATION_V1" }
```

For one valid request the adapter performs exactly one Ed25519 generation operation:

```text
subtle.generateKey({ name: "Ed25519" }, false, ["sign", "verify"])
```

The generated private key must report:

- `type === "private"`;
- `extractable === false`;
- `algorithm.name === "Ed25519"`;
- exactly one usage, `"sign"`.

The generated public key must report:

- `type === "public"`;
- `extractable === true` so its public material can be exported;
- `algorithm.name === "Ed25519"`;
- exactly one usage, `"verify"`.

Any malformed request, crypto surface, keypair, key metadata, export result or crypto exception fails with one stable non-reflective local error.

## Frozen public enrollment carrier

The only export operation is:

```text
subtle.exportKey("raw", publicKey)
```

The result must be exactly 32 raw Ed25519 public-key bytes. Those public bytes are encoded as canonical base64url without padding and transported as:

```text
mkpk1_<43 base64url-no-padding characters>
```

For bytes `00..1f`, the frozen carrier is:

```text
mkpk1_AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8
```

The adapter returns exactly:

```text
{
  profile: "MARKETPLACE_WEB_AUTH_ED25519_KEY_CREATION_V1",
  privateKey: <non-extractable in-memory CryptoKey handle>,
  publicKeyValue: "mkpk1_..."
}
```

It does not return the public `CryptoKey`, raw public bytes, any private bytes, seed, mnemonic, passphrase or serialized key material.

## Explicit non-authority

M17.6C grants fresh key creation and public-key export only. It grants:

- no private-key export;
- no private-key import;
- no wrapping/unwrapping, seed, mnemonic, passphrase, raw-private-key or PKCS#8 path;
- no persistence in localStorage, sessionStorage, IndexedDB, cookies, Cache API, service workers, filesystem or any other store;
- no key restoration, recovery, backup, migration, rotation, revocation or multi-key selection;
- no signing operation and no generic signing oracle;
- no server enrollment, registration, identity binding, trust-evidence mutation or verification-method assignment;
- no ambient `window.crypto` / `globalThis.crypto` selection;
- no active Web authentication selection or session establishment;
- no browser execution or real-browser secure-context acceptance;
- no Android action;
- no network, database, service, configuration or runtime mutation;
- no dependency, package or workflow widening;
- no production/public-network activity;
- no deployment, publishing or distribution.

The adapter remains deliberately unselected. No shipped page or application entry point imports or instantiates it.

## Failure and key-material handling

All local validation and WebCrypto failures collapse to `AUTH_KEY_CREATION_UNAVAILABLE` with stable non-reflective text. No key material is logged, serialized, persisted, transmitted or incorporated into an error.

The source contains no fetch, socket, timer, worker, service-worker, storage, retry or background behavior.

## Qualification

Qualification freezes:

- exact profile and one-member request shape;
- exactly one Ed25519 key-generation call on the valid path;
- non-extractable private signing-only authority;
- Ed25519 verification-only public-key shape;
- exactly one raw public-key export and zero private-key export;
- exact 32-byte public-key requirement;
- exact `mkpk1_` carrier and 43-character canonical base64url payload;
- exact three-field result shape;
- stable non-reflective failures;
- zero private-key import, wrapping, persistence, signing, networking or background behavior;
- continued non-selection by Web and Android entry points;
- existing M17.5H/I, M17.6A and M17.6B guards remaining green.

Repository audit and Marketplace conformance remain authoritative without dependency or workflow widening.

## Rollback and later gates

Rollback is **source-only rollback**: revert the exact M17.6C merge if later separately authorized. Because the boundary is unselected, memory-only and non-persisting, rollback requires no key revocation, storage cleanup, database migration, service restart or deployment action.

Later capabilities remain separately governed: server enrollment/binding of `mkpk1_` public material to one identity and verification method; composition with M17.6B proof creation and M17.6A establishment; bounded real-browser secure-context acceptance; active Web login and session-derived actor identity; any custody persistence/recovery lifecycle; Android custody/auth; and production key administration, service hosting, public-network exposure or deployment.

Until those gates are separately reviewed, M17.6C creates no active Marketplace authentication session and assigns no verification method.
