# M17.5D — authentication challenge/session establishment

## Profile

`MARKETPLACE_APPLICATION_SESSION_ESTABLISHMENT_V1` defines the source-only prerequisite for a truthful later client login flow. It does not select a running auth composition.

The public challenge carrier is exactly:

```text
mkc1_<43 base64url-no-padding characters>
```

It decodes canonically to 32 challenge bytes. Established sessions are returned once using the already-reviewed `mkt1_<43-character>` opaque bearer token form from M17.5C.

## Exact HTTP routes

The source contract exposes exactly four auth routes:

- `POST /api/auth/challenges` — register one exact principal + verification-method challenge;
- `POST /api/auth/sessions` — submit one bounded proof attempt and establish one session;
- `GET /api/auth/session` — inspect non-secret session facts without refreshing idle lifetime;
- `POST /api/auth/logout` — revoke the supplied session exactly once.
Challenge and session creation routes admit no bearer. Session inspection/logout require the exact M17.5C bearer. Query/body session tokens, cookies, Proxy-Authorization, Set-Cookie, redirects, callbacks, JWTs and alternate credential schemes remain forbidden.

## Injected-only authority

M17.5D defines narrow ports and no permissive default:

- `CredentialMaterialSource.challenge_bytes()` supplies exactly 32 challenge bytes;
- `CredentialMaterialSource.session_token_bytes()` supplies exactly 32 session-token bytes;
- `AuthenticationProofVerifier.verify()` returns an exact `VerifiedAuthenticationProof` fact value.

There is no concrete generator, CSPRNG selection, signing implementation, cryptographic verifier, resolver, provider or network client in this slice. Injected calls are attempted at most once; failures and collisions fail closed with no hidden retry.

M17.5B `PrincipalBindingVerifier` remains mandatory. Authentication proves only the reviewed application-session binding and does not establish real-world identity, ownership, legitimacy, trust, agreement, payment, settlement or fulfillment.

## One-use and retention semantics

A structurally accepted session-establishment attempt atomically removes its challenge from outstanding state before injected proof verification. Verifier failure, invalid proof, binding failure, material failure and session-capacity failure therefore cannot make the challenge reusable.

Challenges remain process-memory only with the approved 2-minute ceiling. Consumed challenges are removed immediately. Session state remains digest-only in process memory with the approved 30-minute idle and 8-hour absolute ceilings.

Raw challenge, proof and session-token payloads are not written to PostgreSQL, files, telemetry or durable logs by this slice. There is **no credential persistence**.
## Deterministic abuse/resource ceilings

The source contract enforces these approved bounds:

- auth request body: **64 KiB**;
- proof canonical JSON: **48 KiB**;
- JSON structural depth: 8;
- object keys at any object: 64;
- array items: 64;
- individual JSON string UTF-8 bytes: 8192;
- outstanding unexpired challenges globally: 128;
- outstanding challenges per exact principal/verification-method pair: 4;
- active unexpired sessions globally: 256;
- active sessions per exact principal: 8.

Expired state is purged before capacity decisions. Reaching either a global or narrower capacity ceiling produces the same `AUTH_CAPACITY_EXCEEDED`; this slice introduces no IP/device identity and no timer-based request-rate limiter.

## Stable public failures

- malformed request/challenge/proof envelope: `400 AUTH_REQUEST_INVALID`;
- absent/reused/expired challenge: `401 AUTH_CHALLENGE_INVALID`;
- invalid or mismatched verified proof facts: `401 AUTH_PROOF_INVALID`;
- proof verifier unavailable/noncanonical: `503 AUTH_PROOF_VERIFIER_UNAVAILABLE`;
- principal binding rejected: `403 AUTH_PRINCIPAL_BINDING_REJECTED`;
- principal binding unavailable/noncanonical: `503 AUTH_PRINCIPAL_BINDING_UNAVAILABLE`;
- material unavailable/noncanonical/collision: `503 AUTH_MATERIAL_UNAVAILABLE`;
- state ceiling reached: `503 AUTH_CAPACITY_EXCEEDED`;
- missing bearer on inspection/logout: `401 AUTH_REQUIRED`;
- malformed/unknown/expired/revoked bearer: `401 AUTH_SESSION_INVALID`.

Failures use the existing bounded JSON/security-header response shape and never reflect raw challenge, proof, bearer token, provider/verifier detail or injected exception text.

## ASGI and runtime boundary

`MarketplaceSessionEstablishmentAsgiHttpAdapter` is a separately constructed explicit source seam. It composes the four auth routes with the existing M17.5C protected-write adapter while preserving anonymous Marketplace reads. The pre-existing M17.5C adapter does not begin serving M17.5D routes merely because this source exists.

There is **no runtime activation** in M17.5D. This change does not select the new adapter in localhost/server composition, generate live credentials, execute real proof verification/signing, perform resolver/provider/network activity, mutate PostgreSQL/config/services, or add Web/Android authentication code.

Web/Android clients remain credential-negative for this milestone. Later M17.5E may use memory-only client tokens only after separate authorization; offline cached Android browse/detail/map remains credential-free and read-only.

## Rollback / blast radius

Rollback is source-only: revert the exact M17.5D merge commit. No token invalidation, database migration, provider administration, service restart or device cleanup is required because runtime composition remains inactive.

Blast radius is limited to transport-neutral auth state hardening, challenge/session wire parsing, explicit auth HTTP/ASGI source adapters, deterministic tests and this documentation. No dependency, workflow, database schema, Web, Android, runtime composition or deployment surface is intentionally changed.
