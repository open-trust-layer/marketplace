# M17.6H — In-memory atomic authentication enrollment nonce authority

Profile: `MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_NONCE_V1`

Exact implementation baseline: `7e50aa7a01acea28d4e2997416acb36512686fd4`

Risk classification: **HIGH security/privacy / one-time authentication-enrollment authorization material**.

M17.6H provides the first concrete implementation of the M17.6G replay-guard contract. It is a bounded, process-memory, digest-only nonce authority with lock-protected atomic one-use consumption. It remains unselected by HTTP, ASGI, Web, Android, startup, and runtime composition.

## Exact scope

Added:

1. `src/marketplace/application/auth_enrollment_nonce.py`
2. `tests/test_m17_6h_auth_enrollment_nonce.py`
3. `tests/test_m17_6h_auth_enrollment_nonce_artifacts.py`
4. `docs/m17-6h-auth-enrollment-nonce.md`

Modified only for package membership:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No dependency, workflow, HTTP, ASGI, Web, Android, PostgreSQL, configuration, service, or deployment source is changed.

## Material source

The authority accepts one injected purpose-specific material source:

`enrollment_nonce_bytes() -> bytes`

The source must return exact 32-byte material. M17.6H does not select `secrets`, `os.urandom`, a hardware RNG, filesystem material, network material, or any other concrete generator.

Malformed material or source failure collapses to one stable non-reflective issuance error.

## Issuance binding

Before requesting material, issuance validates the exact:

- principal;
- verification method;
- canonical `mkp1_` public key;
- authority URI;
- evidence lease duration;
- non-negative issuance time.

Validation reuses existing M17.5L evidence semantics.

The issued nonce is bound to those exact identity/authority values and the exact evidence lease duration.

## Lifetime and capacity

Each nonce is valid for exactly **120 seconds**.

Tracked state is bounded to:

- at most 128 active/recent nonce slots globally;
- at most 4 active/recent nonce slots per exact enrollment binding.

Recently consumed digests stay tracked only until their original nonce expiry. This prevents a broken material source from immediately reissuing the same raw nonce while keeping retention finite.

Expired outstanding and spent state is purged on issuance and consumption.

## Digest-only retention

The raw nonce is returned only in the immediate immutable issuance view.

Internal process-memory state retains:

- SHA-256 nonce digest;
- principal;
- verification method;
- public-key carrier;
- authority;
- evidence lease duration;
- issuance time;
- expiry time.

The raw nonce itself is not retained in authority state.

## Atomic one-use consumption

Consumption implements the exact M17.6G operation:

`consume_authentication_enrollment_nonce(...) -> bool`

After validating the consumption shape, the authority computes the nonce digest and enters one lock-protected critical section.

Within that section it:

1. purges expired state;
2. atomically removes the digest from outstanding state;
3. records the removed state as spent until its original expiry.

Only the caller that successfully removes the outstanding state can continue to a successful binding check. Concurrent or repeated callers receive exact `False`.

A valid-shape request with a wrong binding burns the nonce. This is fail-closed: possession of one nonce cannot be used for iterative binding guesses.

## Consumption checks

A first consumption returns exact `True` only when:

- the digest names one unexpired outstanding nonce;
- principal matches exactly;
- verification method matches exactly;
- public-key carrier matches exactly;
- authority matches exactly;
- evidence lease duration matches exactly;
- enrollment `issued_at` is at or after nonce issuance and strictly before nonce expiry.

Malformed, unavailable, expired, reused, or mismatched consumption returns exact `False` without reflecting a cause.

## Explicit non-authority

M17.6H adds no:

- HTTP request/response or carrier encoding;
- ASGI route or runtime selection;
- network/filesystem/environment/database persistence;
- cross-process/shared nonce coordination;
- concrete randomness source;
- concrete approval policy;
- signer or private-key custody;
- trust-anchor mutation;
- browser activation or WebCrypto selection;
- Android action;
- PostgreSQL/config/service mutation;
- background worker or retry;
- deployment, publishing, distribution, or public-network activity.

The authority is deliberately **unselected** and process-local. A multi-process or distributed deployment must later select a separately reviewed shared atomic authority rather than treating this process-memory implementation as cross-process truth.

## Failure behavior

Issuance-owned failures collapse to:

`AuthenticationEnrollmentNonceError("authentication enrollment nonce operation failed")`

No nonce bytes, nonce digest, principal, verification method, public key, authority, material-source details, or nested exception text is reflected.

Normal invalid/replayed/mismatched consumption returns exact `False`.

## Qualification

Qualification freezes:

- exact profile and constants;
- injected-only exact 32-byte material source;
- static binding validation before material acquisition;
- 120-second nonce lifetime;
- global/per-binding capacity;
- digest-only retained secret state;
- duplicate-material rejection while tracked;
- lock-protected atomic one-use removal;
- exact binding and evidence-lease match;
- issuance-window enforcement;
- mismatch burns valid-shape nonce;
- concurrent reuse yields exactly one success;
- stable non-reflective issuance failure;
- continued HTTP/ASGI/Web/Android non-selection;
- package membership coverage;
- FULL Marketplace conformance.

## Rollback and later gates

Rollback is **source-only rollback**: revert the exact M17.6H merge. Because the authority remains unselected, rollback requires no database migration, service restart, key revocation, or external cleanup.

Later separately governed work may define the exact authenticated HTTP nonce issuance/enrollment carrier, compose nonce/enrollment adapters into authenticated HTTP/ASGI, select a deployment-appropriate shared atomic nonce authority, activate browser enrollment, select concrete policy/provider/signer custody, or perform bounded localhost acceptance.
