# Marketplace M17.6D — Unselected Web Ed25519 enrollment-proposal handoff boundary

Profile: `MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1`

Baseline: exact merged-green Marketplace `main`
`a44b318634bfe77b1067f3b426c57448c2a0ab57`.

Authority: owner-authorized **HIGH security/privacy / identity-trust handoff** source capability recorded in Issue #324, limited to the exact four additive files listed below.

## Purpose

M17.6C creates one fresh memory-only WebCrypto Ed25519 keypair, retains the non-extractable private key only as an in-memory handle, and exports exactly the 32-byte public key as canonical Web enrollment material using the `mkpk1_` carrier.

The reviewed server trust chain uses a separate semantic boundary. M17.5K stores explicit verification-method/controller/public-key evidence, M17.5L accepts only authority-attested evidence, and M17.5M verifies those attestations against independently provisioned public trust anchors.

M17.6D therefore introduces only a deterministic, source-only proposal handoff. It does **not** turn client-created key material into trusted evidence.

The boundary accepts exact caller-provisioned identity metadata plus canonical M17.6C public enrollment material and returns one frozen **non-authoritative** proposal suitable only for a later separately governed enrollment authority.

## Exact request

`createMarketplaceWebAuthEd25519EnrollmentProposal(request)` accepts an object with exactly:

- `profile` — exact `MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1`;
- `principal` — exact caller-provisioned absolute URI, valid UTF-8, at most 2048 UTF-8 bytes;
- `verificationMethod` — exact caller-provisioned absolute URI, valid UTF-8, at most 2048 UTF-8 bytes;
- `publicKeyValue` — exact canonical M17.6C `mkpk1_<43 base64url-no-padding chars>` value encoding exactly 32 bytes.

Unknown, missing, alternate, malformed, oversized, or non-canonical fields fail closed through one stable non-reflective error.

The principal and verification-method values are retained exactly. There is **no identity/controller inference**, lowercasing, percent decoding, DID canonicalization, fragment inference, aliasing, prefix matching, ownership inference, role or membership inference, delegation traversal, or relationship test between the two identifiers.

## Public-key carrier bridge

The only transformation is a representation handoff for the same exact 32 public bytes:

`mkpk1_<payload>` -> `mkp1_<same payload>`

The input payload is decoded and then canonically re-encoded before the `mkp1_` prefix is applied. The bytes must therefore round-trip exactly.

Frozen vector:

- Web enrollment material: `mkpk1_AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8`
- server-compatible proposal carrier: `mkp1_AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8`

The `mkp1_` result is proposal data only. Prefix conversion is not trust, identity proof, controller binding, verification-method assignment, evidence acceptance, or authority attestation.

## Exact result

A successful call returns one frozen object containing exactly:

- `profile` — `MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1`;
- `type` — `MarketplaceAuthenticationEd25519EnrollmentProposal`;
- exact caller-supplied `principal`;
- exact caller-supplied `verificationMethod`;
- `publicKey` — canonical `mkp1_` representation of the exact same 32 public bytes.

The result contains no authority, issue/expiry lease, validity interval, attestation, acceptance/trust state, session data, private-key material, or claim that enrollment has been accepted.

## Failure boundary

All M17.6D-owned failures use one stable public error:

`Marketplace Web authentication enrollment proposal failed`

with code:

`AUTH_ENROLLMENT_PROPOSAL_UNAVAILABLE`

Failures do not reflect the principal, verification method, public key, malformed input, provider details, or exception text.

## Capability boundary

M17.6D has **no private-key capability**. It performs no WebCrypto operation and contains no key generation, private/public key import, private/public key export, wrapping, unwrapping, derivation, signing, verification, seed handling, mnemonic handling, passphrase handling, or ambient `window.crypto` / `globalThis.crypto` selection.

There is **no network** capability: no fetch, XHR, WebSocket, EventSource, HTTP registration, server enrollment endpoint, resolver, provider, DNS, socket, redirect, or remote retrieval.

There is no persistence or background behavior: no localStorage, sessionStorage, IndexedDB, cookies, Cache API, service worker, filesystem picker, worker, timer, broadcast channel, retry, refresh, polling, or cache.

There is no evidence or trust authority. M17.6D creates no M17.5L evidence bundle or envelope, no `authority`, `issuedAt`, `expiresAt`, `validFrom`, `validUntil`, attestation/signature, trust-anchor value, or `accepted` state. It performs no trust verification and no trust-anchor provisioning, loading, rotation, revocation, replacement, or mutation.

There is **no verification-method allocation** or assignment, controller registration, server-side enrollment, identity binding, ownership proof, role/membership/delegation decision, or DID/Controlled-Identifier resolution.

## Runtime boundary

The new module is deliberately **unselected** by active Web entry points, Web authentication/session composition, M17.6A/B/C modules, and Android.

It adds no active authentication, browser execution, real-browser secure-context acceptance, session establishment, authenticated UI identity, runtime/server selection, PostgreSQL access, configuration mutation, service mutation, production/public-network activity, deployment, publishing, or distribution.

## Exact four-file scope

Added only:

1. `web/auth_ed25519_enrollment_proposal.js`
2. `tests/test_m17_6d_web_auth_ed25519_enrollment_proposal_contract.py`
3. `tests/test_m17_6d_web_auth_ed25519_enrollment_proposal_artifacts.py`
4. `docs/m17-6d-web-auth-ed25519-enrollment-proposal.md`

No predecessor source, package/dependency metadata, workflow, repository-audit control, Python authentication/runtime source, PostgreSQL/configuration/service path, Web entry point, or Android file is modified.

## Qualification

Qualification freezes:

1. exact profile/type and exact request/result shapes;
2. exact <=2048-byte absolute-URI validation with no normalization or inference;
3. exact canonical `mkpk1_` decoding to 32 bytes;
4. exact same-byte `mkp1_` re-encoding and the frozen `00..1f` vector;
5. malformed/non-canonical carrier rejection;
6. exact preservation of principal and verification method;
7. no authority/lease/validity/attestation/trust/acceptance fields;
8. no private-key, signing, WebCrypto, persistence, network, evidence creation, registration, or background capability;
9. continued non-selection by active Web and Android entry points;
10. predecessor M17.6A/B/C boundaries remaining unchanged;
11. repository and Marketplace conformance without dependency/workflow widening.

## Threat boundary

This slice prevents a client-created public key from being silently conflated with already-trusted server evidence. It freezes one canonical, bounded proposal representation while preserving the separation between public-key possession material and server-side identity/trust authority.

It does not establish that the caller controls the claimed principal, that the verification method is allocated to that principal, that an authority has accepted the proposal, or that any trusted M17.5L evidence exists.

## Rollback

Rollback is **source-only rollback**: revert the exact eventual M17.6D merge if separately authorized.

Because the module is unselected, deterministic, public-data-only, external-I/O-negative, non-persistent, and non-authoritative, rollback requires no credential/key revocation, trust-store administration, session cleanup, database migration, service restart, browser cleanup, Android cleanup, configuration rollback, or external-data mutation.

## Later gates

Only separately authorized later milestones may decide:

1. a trusted enrollment authority that consumes one exact proposal and independently validates/attests a principal + verification-method + public-key relationship into the reviewed M17.5L/M trust path;
2. unselected composition of that trusted binding with M17.6B proof creation and M17.6A session establishment;
3. bounded real-browser secure-context localhost acceptance;
4. only then active authenticated Web UI/session-derived identity;
5. custody persistence, recovery and rotation;
6. Android custody/authentication;
7. production trust administration, service hosting, public-network exposure and deployment.

## Explicit non-authority

M17.6D authorizes no merge and no identity/controller inference; no verification-method allocation or assignment; no authority or attestation creation; no evidence bundle/envelope creation; no trust verification or mutation; no server enrollment/registration; no private-key access/export/import/wrapping/signing/generation; no persistence; no filesystem/environment/database/configuration intake; no network; no active Web authentication selection; no browser execution; no Android action; no dependency/workflow/repository-audit widening; no runtime/service mutation; no production/public-network activity; and no deployment, publishing, or distribution.
