# M17.5B — Application authentication/session contracts

Status: source-only contract; no HTTP/runtime activation.

Approved profile: `MARKETPLACE_APPLICATION_AUTH_MVP` from #261 comment `5567223831`.

## Boundary

M17.5B defines a passwordless, challenge-bound application authentication contract without creating a second identity system:

```text
caller-supplied 256-bit challenge
  -> separately verified OLP proof facts
  -> injected PrincipalBindingVerifier
  -> caller-supplied opaque 256-bit session token
  -> SHA-256 token digest retained in process memory
```

The module does not generate challenge/token material, handle private keys, resolve identifiers, select an identity provider, bind HTTP headers/cookies, persist auth state, or start network/runtime capability.

## Reviewed limits

- challenge: exactly 32 bytes; one proof attempt; absolute lifetime <= 120 seconds;
- proof: exact application domain, `assertion` purpose, challenge digest and verification-method match;
- principal binding: explicit injected verifier; unavailable/non-boolean/rejected decisions fail closed;
- session token: exactly 32 bytes; raw value is never retained or exposed by session views;
- session idle ceiling: 30 minutes;
- session absolute ceiling: 8 hours, never extended by activity;
- revocation: removes the in-memory session immediately;
- stable, non-reflective error codes only.

## Semantic separation

```text
valid OLP proof            != identity
verification-method control != authority for every action
application session        != OLP principal authority
principal URI text         != proof of control
authenticated write        != truth / ownership / legitimacy / trust
```

The `PrincipalBindingVerifier` is where an application may evaluate acceptable evidence such as OLP `controlsVerificationMethod` plus resolver/external policy. There is deliberately no permissive default.

## Write guard

The source-only guarded authoring wrappers authenticate the opaque session and require exact equality:

- listing `seller_principal == session.principal`;
- proposal `buyer_principal == session.principal`.

Mismatch fails before invoking downstream authoring. Existing unguarded authoring remains unchanged in M17.5B because HTTP/runtime activation is outside this slice; a later transport milestone must route authenticated write endpoints only through the guarded boundary.

## Retention/privacy

- raw challenges and raw session tokens are caller-supplied transient values and are not retained by the service;
- challenge/session lookup state retains only SHA-256 digests plus bounded principal/verification-method/time metadata in process memory;
- consumed challenges are retained only through their 120-second replay window and then are eligible for purge;
- active sessions live no longer than 8 hours and expire after 30 minutes idle;
- revocation removes session state immediately;
- no credential, token, proof body, key material, or session secret belongs in logs, PostgreSQL, the Marketplace record store, or Android offline content cache.

## Explicit exclusions

No live credential/token issuance, randomness provider, key generation, proof generation, resolver/provider administration, password handling, OAuth/OIDC, JWT, cookie, `Authorization` header acceptance, CORS change, HTTP route, PostgreSQL schema/data, filesystem credential store, Android token storage, build/device action, server/config/service mutation, production activation, publishing/distribution, deployment, or merge.
