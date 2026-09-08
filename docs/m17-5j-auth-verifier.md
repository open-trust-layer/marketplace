# Marketplace M17.5J â€” Production Ed25519 authentication verifier

Profile: `MARKETPLACE_APPLICATION_AUTH_ED25519_VERIFIER_V1`

Baseline: exact merged-green Marketplace `main` `3764afd27a4ff8263ff502a6f4c86cabd7349d8f`.

Authority: owner-authorized HIGH-risk source scope recorded in Issue #278. This milestone introduces only an unselected production-source public-key verifier and its exact optional dependency/package/CI boundary.

## Purpose

M17.5H froze the Marketplace-specific authentication proof carrier and deterministic `MARKETPLACE-AUTH` transcript. M17.5I qualified that frozen transcript against deterministic synthetic Ed25519 vectors. M17.5J introduces the smallest production verifier that can validate the same proof with an injected public verification key while preserving the existing M17.5D session and failure contracts.

Marketplace authentication remains distinct from `OLPProof`; the verifier does not import `olp.crypto.ed25519` or reuse OLP record-proof semantics.

## Dependency boundary

The base package remains dependency-free:

```toml
dependencies = []
```

One reviewed optional provider extra is added:

```toml
auth-verify = ["cryptography==50.0.1"]
```

The conformance workflow explicitly installs exact `cryptography==50.0.1` in its disposable virtual environment before installing the pinned OLP reference checkout. This proves the Marketplace-owned verifier dependency independently of OLP's transitive dependency range while preserving the existing self-hosted runner, permissions, checkout pin, acceptance gate, and cleanup controls.

## Verifier boundary

`src/marketplace/application/auth_verifier_ed25519.py` provides:

- profile `MARKETPLACE_APPLICATION_AUTH_ED25519_VERIFIER_V1`;
- purpose-specific `AuthenticationVerificationKeySource` with only `verification_key_bytes(verification_method)`;
- `MarketplaceEd25519AuthenticationProofVerifier`, implementing the existing `AuthenticationProofVerifier` shape;
- exact 32-byte raw Ed25519 public-key validation;
- direct `cryptography` `Ed25519PublicKey.from_public_bytes` construction;
- exact frozen M17.5H proof parsing and transcript reconstruction;
- exact 64-byte proof signature verification;
- existing `VerifiedAuthenticationProof` facts only.

The verifier catches only `cryptography.exceptions.InvalidSignature`. A structurally valid proof with an invalid signature returns `cryptographically_valid=False`, which the existing session service maps to `AUTH_PROOF_INVALID`. Verification-key-source exceptions, malformed key-source output, backend/provider failures, and other verifier infrastructure failures propagate to the existing session adapter, which maps them to `AUTH_PROOF_VERIFIER_UNAVAILABLE` without reflecting provider details.

`PrincipalBindingVerifier` remains a separate policy boundary. Successful Ed25519 verification does not establish verification-method ownership, DID/controller resolution, identity, trust, authority, permission, payment, settlement, or legal effect.

## Public-key source contract

`AuthenticationVerificationKeySource` is injected only. M17.5J provides no concrete resolver/provider or discovery implementation.

The port accepts the exact proof `verificationMethod` and returns only exact 32-byte raw Ed25519 public-key material. There is no retry or fallback in the verifier. A lookup occurs once per verification attempt.

The milestone provides no filesystem, environment, database, browser, Android, HSM, keyring, wallet, HTTP, DNS, DID-resolution, provider, or network lookup.

## Threat and abuse boundary

M17.5J intentionally provides no private-key capability. Production source contains no `Ed25519PrivateKey`, no private-key generation/import/export/storage/custody/rotation/deletion/use, no seed/mnemonic/passphrase handling, no signer, and no generic crypto or signing oracle.

It also provides no concrete resolver/provider, no principal-binding policy change, no runtime activation, no localhost/ASGI/client selection, no WebCrypto/browser-wallet activation, no Android build or Keystore action, no credential/session/key persistence, no PostgreSQL access, and no configuration/service mutation.

The verifier is deliberately unselected by the application package entry surface, authentication ASGI composition, localhost tool, Web client, and Android client.

## Qualification

The M17.5J tests use only the frozen public M17.5I Ed25519 public key and 64-byte signature. They contain no private seed and perform no signing operation.

Qualification covers:

1. exact frozen public vector verification;
2. exact challenge/domain/purpose/method facts;
3. exactly one verification-key lookup per attempt;
4. a corrupted well-formed signature returning invalid facts and the existing `AUTH_PROOF_INVALID` response;
5. changed transcript-bound challenge failing verification against the original signature;
6. key-source exceptions retaining `AUTH_PROOF_VERIFIER_UNAVAILABLE` without detail reflection;
7. wrong key type/length failing closed without retry/fallback;
8. direct public-key-only `cryptography` imports and no production OLP crypto helper;
9. exact optional dependency/package metadata and explicit CI installation;
10. runtime/Web/Android/auth-composition non-selection;
11. predecessor M17.5B-I conformance remaining green.

## Rollback and blast radius

Rollback is source-only rollback: revert the exact M17.5J merge if later separately authorized.

Because this verifier remains unselected and has no concrete key source, private-key custody, network path, persistence, database, configuration, service, device, or deployment effect, rollback requires no credential/key revocation, session cleanup, provider administration, database migration, service restart, Android cleanup, configuration rollback, or external-data mutation.

Blast radius is limited to the verifier module, exact optional dependency/package/CI governance metadata, tests, and this documentation.

## Non-authority

This milestone authorizes no private-key or signing capability; no concrete resolver/provider/key-source implementation; no principal-binding change; no runtime activation; no public-network authentication; no deployment, publishing, or distribution; no WebCrypto/browser-wallet integration; no Android build/device action; no PostgreSQL/config/service mutation; and no merge.

Any later verification-method resolution, private-key custody/signing provider, runtime selection, or live authentication acceptance requires a separate milestone and explicit authority.
