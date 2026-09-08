# Marketplace M17.5L ? Canonical authentication verification-method evidence intake

Profile: `MARKETPLACE_APPLICATION_AUTH_VERIFICATION_METHOD_EVIDENCE_BUNDLE_V1`

Baseline: exact merged-green Marketplace `main` `8edd7c0d2e199e2a3d27de24f2946620b078406c`.

Authority: owner-authorized HIGH-risk six-file source scope recorded in Issue #282.

## Purpose

M17.5K introduced one immutable process-local snapshot that supplies both the M17.5J public verification-key lookup and M17.5D principal-binding decision from the same evidence set. K intentionally does not decide where real evidence comes from or whether externally supplied evidence should be trusted.

M17.5L adds only the intake boundary between externally supplied bytes and that immutable snapshot. It does not acquire evidence itself.

The key rule is: **parsing is not trust**. Canonical claims may be projected into a K snapshot only after one injected, purpose-specific trust verifier accepts those exact claims and returns a matching SHA-256 digest and exact authority identifier.

## Canonical claims

Claims are exact canonical UTF-8 JSON bytes, at most **512 KiB**.

The decoder rejects:

- non-byte input;
- empty or oversized input;
- UTF-8 BOM;
- invalid UTF-8;
- duplicate object keys;
- NaN or Infinity;
- unknown keys;
- alternate whitespace, ordering, escaping, or other non-canonical serialization.

Canonicality is checked by strict parsing followed by re-encoding with the frozen encoder and exact byte equality.

The top-level object contains exactly:

- `type = MarketplaceAuthenticationVerificationMethodEvidenceBundle`;
- `version = 1`;
- `authority`;
- `issuedAt`;
- `expiresAt`;
- `entries`.

`authority` is an exact, non-normalized absolute URI of at most 2048 UTF-8 bytes. It is provenance metadata only; it never becomes an entry controller.

`issuedAt` and `expiresAt` are exact non-boolean, non-negative Unix seconds. The lease is `[issuedAt, expiresAt)`, must be non-empty, and must not exceed **24-hour** duration.

`entries` contains 1..256 complete entries. Duplicate exact verification methods reject the whole document; there is no partial acceptance.

## Entry profile

Each entry contains exactly:

- `verificationMethod`;
- `controllerPrincipal`;
- `publicKey`;
- `validFrom`;
- `validUntil`.

Principal and verification-method values are exact non-normalized absolute URIs, each at most 2048 UTF-8 bytes. No lowercasing, percent decoding, DID canonicalization, fragment/controller inference, aliases, roles, membership, delegation, prefix matching, or graph traversal is performed.

The public key uses exact carrier `mkp1_<43 base64url-no-padding chars>` and decodes to exactly 32 bytes. Re-encoding must reproduce the input carrier exactly.

Entry validity uses exact non-boolean, non-negative Unix seconds or `null`. If both bounds exist, `validFrom < validUntil` is required.

## Opaque attestation envelope

`MarketplaceAuthenticationVerificationMethodEvidenceEnvelope` contains only:

- `claims_json: bytes` ? exact canonical claims bytes;
- `attestation: bytes` ? opaque, non-empty, at most **16 KiB**.

The attestation is not parsed, logged, interpreted, signed, verified, resolved, fetched, persisted, or transformed by M17.5L.

The frozen envelope prevents caller rebinding after construction.

## Trust verifier seam

M17.5L defines `AuthenticationVerificationMethodEvidenceTrustVerifier` with one purpose-specific operation:

`verify_authentication_verification_method_evidence(envelope)`

A verifier returns frozen `VerifiedAuthenticationVerificationMethodEvidence` containing only:

- exact 32-byte `claims_sha256`;
- exact accepted `authority` URI;
- exact boolean `accepted`.

For each syntactically valid materialization attempt, the verifier is called exactly once with the exact envelope object. Materialization rejects unless:

1. `accepted is True`;
2. `claims_sha256 == SHA-256(envelope.claims_json)`;
3. the returned authority exactly equals the canonical claims authority.

Verifier exceptions, malformed results, rejection, digest mismatch, and authority mismatch fail closed through one stable non-reflective source error.

M17.5L provides **no concrete trust verifier**, no trust store, no cryptographic attestation algorithm, and no trust-anchor format.

## Freshness and projection

Materialization receives an explicit `at_time` Unix second. It requires:

`issuedAt <= at_time < expiresAt`.

Only after canonical parsing and successful trust verification are entries projected into `AuthenticationVerificationMethodEvidence` values for the existing K snapshot.

Each entry receives finite effective validity:

- `effective_valid_from = max(issuedAt, validFrom or issuedAt)`;
- `effective_valid_until = min(expiresAt, validUntil or expiresAt)`.

An empty intersection rejects the whole bundle.

This guarantees that no projected key/controller binding outlives the verified bundle lease, even when the entry omitted its own validity bounds.

The resulting `MarketplaceAuthenticationVerificationMethodSnapshot` retains K's exact key-source and principal-binding semantics. The authority identifier never replaces `controllerPrincipal` and never implies identity, ownership, role, membership, delegation, or authorization.

## Failure disclosure

All L failures use a stable non-reflective error. Failures do not include:

- authority identifiers;
- verification methods;
- controller principals;
- public keys;
- raw claims;
- attestation bytes;
- verifier internals;
- exception text.

M17.5L is unselected, so it does not alter the existing HTTP authentication error vocabulary.

## External-I/O boundary

M17.5L performs **no network** or other evidence acquisition.

It contains no:

- HTTP, DNS, socket, redirect, or remote retrieval;
- DID, Controlled Identifier, VC, X.509, or OLP resolver;
- filesystem or environment lookup;
- database/provider lookup;
- wallet, HSM, keyring, browser, or Android lookup;
- background refresh, retry, fallback, or cache;
- persistence.

Any later acquisition provider requires its own explicit HTTPS/DNS/redirect/SSRF/private-address/TLS/size/time policy and separate authorization.

## Cryptographic and custody boundary

The only cryptographic primitive performed by L is stdlib SHA-256 to bind verifier acceptance to the exact canonical claims bytes.

There is no private-key generation, import, export, storage, custody, use, signing, rotation, deletion, WebCrypto, browser-wallet, Android Keystore, or generic cryptographic oracle.

## Runtime boundary

The new module remains unselected by application package entry surfaces, `auth.py`, the Ed25519 verifier, K snapshot source, authentication ASGI composition, localhost tooling, Web, Android, and client-session composition.

There is **no runtime activation**, live authentication, service restart, production/public-network activity, PostgreSQL/configuration/secret mutation, deployment, publishing, or distribution.

## Exact source scope

The authorized implementation touches exactly six files.

Added:

1. `src/marketplace/application/auth_verification_method_evidence.py`
2. `tests/test_m17_5l_auth_verification_method_evidence.py`
3. `tests/test_m17_5l_auth_verification_method_evidence_artifacts.py`
4. `docs/m17-5l-auth-verification-method-evidence.md`

Modified:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No dependency, workflow, repository-audit, auth/runtime, Web, or Android change is part of L.

## Qualification

Tests cover canonical JSON and duplicate-key rejection; exact public-key carrier; entry/capacity/lease bounds; immutable envelope/result values; one-call verifier semantics; verifier rejection/exception/malformed-result behavior; digest and authority substitution; stale leases; authority/controller separation; finite validity intersection; atomic whole-bundle rejection; non-reflective errors; package inclusion; predecessor dependency/workflow/OLP controls; and runtime non-selection.

## Rollback and blast radius

Rollback is **source-only rollback**: revert the exact M17.5L merge if a later separately authorized merge occurs.

Because L remains caller-injected, process-local, public-key-only, unselected, and external-I/O-negative, rollback requires no credential/key revocation, session cleanup, provider administration, database migration, service restart, device cleanup, configuration rollback, or external-data mutation.

Blast radius is limited to the evidence claims/envelope/trust-verifier intake module, tests/documentation, and the wheel required-member controls.

## Non-authority

M17.5L authorizes no concrete trust verifier or trust store; no DID/Controlled Identifier/VC/X.509/OLP resolver; no network, redirects, provider administration, remote retrieval, filesystem/environment/database access, refresh/background activity, cache/persistence, private-key/signing capability, runtime/client authentication selection, live authentication, WebCrypto/browser wallet, Android action, PostgreSQL/config/service mutation, production/public-network activity, deployment, publishing, distribution, or merge.
