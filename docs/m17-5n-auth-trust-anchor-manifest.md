# Marketplace M17.5N — Canonical static authentication trust-anchor manifest intake

Profile: `MARKETPLACE_APPLICATION_AUTH_TRUST_ANCHOR_MANIFEST_V1`

Baseline: exact merged-green Marketplace `main`
`88450b90efe8869c5d697b66c880117ee315982d`.

Authority: owner-authorized **HIGH** trust-root intake capability recorded on
Issue #286. The implementation is restricted to the exact six-file scope below.

## Purpose

M17.5M introduced an immutable, constructor-injected mapping from an exact
authority URI to one exact 32-byte Ed25519 public trust anchor. It intentionally
did not decide where those anchors come from.

M17.5N freezes only a representation boundary: exact caller-supplied canonical
manifest bytes can be validated and materialized into the existing M17.5M
snapshot. It adds no provisioning source, mutable trust store, replacement
policy, runtime selection, or acquisition mechanism.

## Canonical manifest

The exact top-level JSON object contains:

- `type`: `MarketplaceAuthenticationEvidenceTrustAnchorManifest`;
- `version`: integer `1`;
- `anchors`: exactly **1..64** anchor objects.

Each anchor contains exactly:

- `authority`: exact, non-normalized absolute URI accepted by M17.5M, UTF-8,
  at most 2048 bytes;
- `publicKey`: the existing canonical M17.5L `mkp1_` carrier encoding exactly
  32 public-key bytes.

The complete manifest is limited to **256 KiB** and must be exact canonical
UTF-8 JSON. BOMs, invalid UTF-8, duplicate JSON keys, NaN/Infinity, unknown
keys, alternate whitespace/order/escaping, non-byte input, duplicate exact
authorities, malformed key carriers, and partial manifests fail closed.

No lowercasing, percent decoding, DID canonicalization, aliasing, prefix
matching, graph traversal, ownership inference, multi-key iteration, fallback,
or partial acceptance is performed.

## Materialization

`materialize_marketplace_authentication_evidence_trust_anchor_snapshot(raw)`

performs exactly:

1. canonical manifest decoding;
2. canonical `mkp1_` decoding;
3. construction of existing `AuthenticationEvidenceTrustAnchor` values;
4. construction of one existing immutable
   `MarketplaceAuthenticationEvidenceTrustAnchorSnapshot`.

The result remains process-local and immutable. There is no add/update/delete,
reload, refresh, retry, replacement, rotation, revocation, cache, persistence,
background task, or clock behavior.

## Failure boundary

All intake/materialization failures use one stable non-reflective
`AuthenticationTrustAnchorManifestError`. Errors do not contain authority URIs,
public keys, raw manifest content, paths, environment names, provider details,
or exception text.

## External-I/O and capability boundary

M17.5N performs **no filesystem** access, **no network** access, no environment
lookup, no database access, no provider/resolver activity, no subprocess, and
no configuration loading.

It introduces no private-key generation/import/export/storage/custody/use,
signing, randomness, WebCrypto, browser-wallet, Android Keystore, or new
cryptographic dependency. It reuses only the already-reviewed M17.5L public-key
carrier and the existing M17.5M public-anchor snapshot.

There is **no persistence**, no cache, no refresh/background activity, and
**no runtime activation**. Localhost/ASGI/Web/Android composition remains
unchanged and non-selecting.

## Exact six-file scope

Added:

1. `src/marketplace/application/auth_trust_anchor_manifest.py`
2. `tests/test_m17_5n_auth_trust_anchor_manifest.py`
3. `tests/test_m17_5n_auth_trust_anchor_manifest_artifacts.py`
4. `docs/m17-5n-auth-trust-anchor-manifest.md`

Modified:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No dependency, workflow, repository-audit, runtime, configuration, Web,
Android, M17.5M, M17.5L, or M17.5K source file is changed.

## Qualification

Tests cover the exact profile/type/version, 256 KiB bound, canonical JSON
rules, 1..64 anchor bound, duplicate exact-authority rejection, exact
non-normalized URI behavior, canonical `mkp1_` decoding, atomic failure,
stable non-reflective errors, immutable materialization, exact no-fallback
lookup, package inclusion, and source guards excluding acquisition,
persistence, refresh, private-key/signing, and runtime-selection authority.

## Threat boundary

This slice reduces ambiguity around static trust-root representation and
prevents malformed, duplicate, non-canonical, partially accepted, or mutable
caller data from silently becoming M17.5M trust state.

It does not establish authenticity of manifest bytes, operational ownership of
a trust-root source, rotation/revocation/expiry/rollback policy, DID/Controlled
Identifier/VC/X.509/OLP resolution, network/TLS/SSRF policy, private-key custody,
runtime readiness, or live authentication.

## Rollback

Rollback is **source-only rollback**: revert the exact eventual M17.5N merge.

Because M17.5N remains unselected, caller-supplied-bytes only, immutable,
public-key-only, external-I/O-negative, and non-persistent, rollback requires no
key revocation, trust-store administration, session cleanup, provider action,
database migration, service restart, Android cleanup, configuration rollback,
or external-data mutation.

## Later gates

Only after M17.5N is merged-green may later separately authorized milestones
decide:

1. one bounded startup provisioning source for canonical manifest bytes;
2. immutable snapshot replacement/rollback and rotation/revocation semantics;
3. any bounded evidence acquisition provider with explicit network policy;
4. runtime composition using the reviewed J/K/L/M/N chain;
5. bounded live authentication acceptance.