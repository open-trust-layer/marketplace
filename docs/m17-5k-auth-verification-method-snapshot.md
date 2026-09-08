# Marketplace M17.5K â€” Immutable authentication verification-method evidence snapshot

Profile: `MARKETPLACE_APPLICATION_AUTH_VERIFICATION_METHOD_SNAPSHOT_V1`

Baseline: exact merged-green Marketplace `main` `9721f352d3cb4a065e72ed01d8bc968aa17330ac`.

Authority: owner-authorized HIGH-risk six-file source scope recorded in Issue #280. This milestone introduces only an unselected, constructor-injected, process-local public verification-method/control evidence snapshot and the package controls needed to ensure the new module ships in reviewed wheels.

## Purpose

M17.5J added a production Ed25519 authentication proof verifier whose public-key lookup is injected through `verification_key_bytes(verification_method)`. M17.5D separately asks `PrincipalBindingVerifier.verify(principal, verification_method, at_time)` whether the challenged principal is bound to the proof verification method.

If those two decisions use independently mutable or independently resolved evidence, a proof can be verified against one key view while principal binding is evaluated against another. M17.5K closes that local split-resolution / TOCTOU seam by supplying both structural ports from one immutable evidence snapshot.

A coherent future composition MUST pass the same snapshot instance to the M17.5J verifier as its key source and to the M17.5D authentication service as its principal-binding verifier. M17.5K itself performs no composition or runtime activation.

## Identity separation

The snapshot does not infer controller ownership from URI spelling.

`verification_method = did:example:alice#key-1` does not imply that `did:example:alice` controls that method. Only the exact `controller_principal` stored in the injected evidence entry governs the local binding decision.

Principal and verification-method identifiers are treated as exact bounded absolute-URI strings. M17.5K performs no lowercasing, percent decoding, fragment inference, DID canonicalization, alias substitution, redirect following, prefix matching, relation traversal, role inference, membership inference, or graph reachability.

Cryptographic validity remains distinct from principal binding. A mathematically valid signature can still be rejected because the exact controller differs or because the local validity interval does not authorize the challenged time.

## Evidence entry

`AuthenticationVerificationMethodEvidence` is a frozen, slotted value with exactly these security-relevant fields:

- `verification_method: str`
- `controller_principal: str`
- `public_key: bytes`
- `valid_from: int | None`
- `valid_until: int | None`

Both URI fields must be non-empty absolute URIs encoded as valid UTF-8 and must be at most 2048 UTF-8 bytes. Their exact string values are retained unchanged.

`public_key` must be exact `bytes` of length 32. Mutable byte containers and other sizes are rejected.

Optional validity times must be exact non-boolean, non-negative integer Unix seconds. When both are present, `valid_from < valid_until` is required.

The policy interval is half-open: `[valid_from, valid_until)`. The lower bound is inclusive and the upper bound is exclusive.

## Snapshot boundary

`MarketplaceAuthenticationVerificationMethodSnapshot` accepts only constructor-supplied entries.

The reviewed ceiling is 256 entries.

The constructor:

1. rejects more than 256 entries;
2. rejects duplicate exact `verification_method` identifiers;
3. copies the caller-supplied collection;
4. retains only frozen entry values;
5. stores the copied mapping behind a read-only mapping proxy.

Caller mutation of the original list after construction cannot alter the snapshot.

The class exposes only:

- construction;
- `verification_key_bytes(verification_method)`;
- `verify(principal=..., verification_method=..., at_time=...)`.

It provides no add, update, delete, refresh, reload, retry, fallback, resolver, provider, persistence, or background synchronization capability.

## Public-key lookup semantics

`verification_key_bytes(verification_method)` performs one exact identifier lookup in the frozen snapshot.

A matching entry returns its exact 32-byte public Ed25519 key.

A missing method, malformed identifier, malformed internal evidence, or unavailable lookup fails closed by raising a stable non-reflective snapshot exception. M17.5J and the existing HTTP session boundary preserve this as the existing `AUTH_PROOF_VERIFIER_UNAVAILABLE` path when failure occurs during proof verification.

The lookup performs no principal or time inference because the existing M17.5J key-source port carries only the verification-method identifier.

## Principal-binding semantics

`verify(principal, verification_method, at_time)` performs exact lookup against the same frozen entry set.

A missing method or unavailable/malformed evidence raises, preserving the existing `AUTH_PRINCIPAL_BINDING_UNAVAILABLE` behavior when used through M17.5D.

A present entry returns `False` when:

- its exact `controller_principal` differs from the challenged `principal`;
- `valid_from` exists and `at_time < valid_from`;
- `valid_until` exists and `at_time >= valid_until`.

Otherwise it returns exact `True`.

A `False` decision preserves the existing `AUTH_PRINCIPAL_BINDING_REJECTED` path.

## No controller inference

M17.5K deliberately has no controller inference.

It does not interpret:

- DID fragments;
- URI prefixes;
- path hierarchy;
- host ownership;
- aliases;
- `sameSubjectAs`;
- roles;
- memberships;
- delegation;
- graph reachability;
- verification-method identifier resemblance.

Only explicit exact constructor-injected evidence is considered.

## External authority boundary

M17.5K provides no external resolver and no evidence-acquisition authority.

There is no:

- DID or Controlled Identifier resolution;
- VC or X.509 processing;
- OLP identity-evidence resolution;
- HTTP or DNS access;
- filesystem or environment lookup;
- database access;
- wallet, HSM, keyring, browser, or Android lookup;
- remote public-key retrieval;
- refresh feed;
- background task;
- retry or fallback.

The milestone does not define where real-world evidence comes from or how freshness, revocation, trust anchors, provenance, redirects, private-address policy, multi-controller policy, aliases, or shared-key semantics should be handled. Those remain later gates.

## Cryptographic and custody boundary

This module performs no cryptography and imports no cryptographic backend.

It contains no private-key generation, import, export, storage, custody, rotation, deletion, use, or signing surface. It contains no `Ed25519PrivateKey`, WebCrypto, browser-wallet, Android Keystore, seed, mnemonic, passphrase, signer, or generic crypto oracle.

Only exact public verification-key bytes are retained.

## Runtime boundary

The new snapshot module remains unselected by:

- application package entry surfaces;
- `auth.py`;
- `auth_verifier_ed25519.py`;
- authentication ASGI composition;
- localhost tooling;
- Web;
- Android;
- client-session composition.

There is no runtime activation, live authentication, public-network authentication, service restart, deployment, publishing, distribution, PostgreSQL access, configuration mutation, secret mutation, or credential/session/private-key persistence.

## Exact source scope

The authorized M17.5K implementation touches exactly six files.

Added:

1. `src/marketplace/application/auth_verification_method_snapshot.py`
2. `tests/test_m17_5k_auth_verification_method_snapshot.py`
3. `tests/test_m17_5k_auth_verification_method_snapshot_artifacts.py`
4. `docs/m17-5k-auth-verification-method-snapshot.md`

Modified:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No change is made to `auth.py`, `auth_verifier_ed25519.py`, `pyproject.toml`, `.github/workflows/conformance.yml`, `tools/repository_audit.py`, localhost/runtime/ASGI composition, Web, or Android.

The base package remains `dependencies = []`. The already reviewed optional `auth-verify = ["cryptography==50.0.1"]` dependency remains unchanged.

## Qualification

Qualification covers:

1. exact profile, 256-entry ceiling, 2048-byte URI ceiling, and 32-byte key size;
2. exact bounded URI syntax without normalization;
3. exact immutable `bytes` public-key handling;
4. exact non-boolean non-negative validity times and ordered bounds;
5. duplicate-method and capacity rejection;
6. copied constructor input and no mutable refresh/update surface;
7. exact controller match and `[valid_from, valid_until)` semantics;
8. explicit proof that DID-like URI spelling does not establish controller ownership;
9. missing lookup fail-closed behavior without identifier reflection or fallback;
10. one same snapshot instance completing the frozen M17.5J Ed25519 vector through the in-process M17.5D session path;
11. cryptographically valid proofs rejected by explicit controller mismatch, pre-validity, or expiration policy;
12. missing key evidence preserving `AUTH_PROOF_VERIFIER_UNAVAILABLE`;
13. missing binding evidence preserving `AUTH_PRINCIPAL_BINDING_UNAVAILABLE`;
14. source artifact checks proving no cryptography/private-key/resolver/provider/I/O/refresh authority;
15. runtime/Web/Android/auth source non-selection;
16. unchanged dependency, workflow, repository-audit, OLP-pin, and runner controls;
17. wheel required-member enforcement for the new module;
18. predecessor conformance remaining green through the existing Marketplace acceptance workflow.

## Rollback and blast radius

Rollback is source-only rollback: revert the exact M17.5K merge if a later separately authorized merge occurs.

Because the snapshot remains unselected, constructor-only, public-key-only, process-local, and free of external I/O or persistence, rollback requires no credential or key revocation, session cleanup, provider administration, database migration, service restart, Android cleanup, configuration rollback, or external-data mutation.

Blast radius is limited to the new immutable snapshot/binding module, its tests and documentation, and the two wheel required-member controls.

## Non-authority

This milestone authorizes no external DID/identity resolver or provider; no HTTP/DNS/network access; no remote key retrieval; no refresh/background activity; no filesystem/environment/database/wallet/HSM/keyring/browser/Android lookup; no private-key or signing capability; no controller inference, aliasing, identity merge, roles, membership, delegation, or authority policy; no runtime/localhost/ASGI/client authentication selection; no live authentication; no credential/session/private-key persistence; no PostgreSQL/config/service mutation; no deployment, publishing, distribution, production/public-network activity; and no merge.

Any real evidence acquisition provider, private-key custody/signing path, runtime selection, or live authentication requires a separate milestone and explicit authority.
