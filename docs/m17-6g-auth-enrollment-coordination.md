# M17.6G — Authenticated enrollment coordination and one-time replay gate

Profile: `MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_COORDINATION_V1`

Exact implementation baseline: `8e191960af331c3b538685891686b9725ef52b29`

Risk classification: **HIGH security/privacy / authenticated identity-enrollment coordination capability**.

M17.6G adds one transport-neutral, unselected coordinator between the existing session service and the M17.6F approval/issuance path. It makes principal binding and replay ordering explicit without selecting HTTP, ASGI, nonce storage, policy implementation, signing custody, or runtime.

## Exact scope

Added:

1. `src/marketplace/application/auth_enrollment_coordination.py`
2. `tests/test_m17_6g_auth_enrollment_coordination.py`
3. `tests/test_m17_6g_auth_enrollment_coordination_artifacts.py`
4. `docs/m17-6g-auth-enrollment-coordination.md`

Modified only for package membership:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No dependency, workflow, HTTP, ASGI, Web, Android, PostgreSQL, configuration, service, or deployment source is changed.

## Inputs

The coordinator accepts exactly:

- an exact existing `MarketplaceApplicationAuthService`;
- an exact 32-byte active session token;
- an exact existing M17.6E `MarketplaceAuthenticationEnrollmentProposal`;
- an exact 32-byte enrollment nonce;
- explicit non-negative `now`;
- trusted-composition authority URI;
- explicit evidence lease duration from 1 second through the existing M17.5L maximum;
- one injected replay guard;
- one injected M17.6F approval policy;
- one injected M17.6E attestor.

The coordinator does not generate any of these values.

## Static validation

Before session authorization or replay consumption, M17.6G validates exact types, sizes, time, lease bounds, proposal public key, controller/verification-method claim shape, and authority/lease semantics using the existing M17.5L evidence types.

Invalid static inputs therefore cannot consume a nonce or reach policy/signing.

## Session-principal binding

The coordinator then calls the exact existing:

`MarketplaceApplicationAuthService.authorize_principal(...)`

The claimed principal is exactly the proposal principal. A missing, expired, invalid, or different-principal session fails before replay consumption.

M17.6G does not accept a caller-provided “authenticated principal” field and does not infer principal identity from the verification-method URI.

## One-time replay gate

The only replay operation is:

`consume_authentication_enrollment_nonce(...exact binding...) -> bool`

It receives:

- exact 32-byte nonce;
- exact proposal principal;
- exact proposal verification method;
- exact canonical `mkp1_` public key;
- exact authority;
- exact `issued_at = now`;
- exact `expires_at = now + lease_seconds`.

The operation is called exactly once and must return exact boolean `True`.

A missing operation, exception, `False`, integer, string, or other non-bool result fails closed before policy or attestor use.

## Burn-before-policy invariant

Once replay consumption returns exact `True`, the nonce is **consumed even if policy rejects or attestation later fails**.

That ordering deliberately prevents one authorization token from driving repeated policy or signing attempts.

M17.6G does not mint, serialize, transport, persist, replenish, recover, or garbage-collect nonces. A concrete nonce source/store and atomic implementation are later separately governed capabilities.

## Delegation

Only after successful session binding and replay consumption does M17.6G call M17.6F exactly once with:

- the exact same proposal;
- the exact same authority;
- `issued_at = now`;
- `expires_at = now + lease_seconds`;
- the exact injected policy;
- the exact injected attestor.

The result must remain the existing M17.5L `MarketplaceAuthenticationVerificationMethodEvidenceEnvelope`.

## Explicit non-authority

M17.6G adds no:

- HTTP request or response carrier;
- ASGI route or runtime selection;
- nonce generation or storage implementation;
- database, filesystem, environment, network, DNS, provider, queue, cache, or background activity;
- concrete approval policy;
- concrete signer or private-key custody;
- trust-anchor mutation, replacement, rotation, or revocation;
- browser activation or WebCrypto selection;
- Android action;
- PostgreSQL/config/service mutation;
- deployment, publishing, distribution, or public-network activity.

The coordinator remains deliberately **transport-neutral** and **unselected**.

## Failure behavior

All M17.6G-owned failures collapse to:

`AuthenticationEnrollmentCoordinationError("authentication enrollment coordination failed")`

No session token, nonce, principal, verification method, public key, authority, policy result, replay-provider detail, signer detail, or nested exception text is reflected.

## Qualification

Qualification freezes:

- exact profile;
- exact 32-byte session token and 32-byte enrollment nonce requirements;
- M17.5L-compatible static validation before session/replay;
- exact existing-session principal binding through `authorize_principal`;
- replay operation exactly once;
- exact replay binding fields;
- exact boolean `True` required;
- replay success before policy;
- nonce remains consumed after later rejection/failure;
- M17.6F called only after successful replay consumption;
- existing M17.5L envelope output;
- stable non-reflective failures;
- continued HTTP/ASGI/Web/Android non-selection;
- package membership coverage;
- FULL Marketplace conformance.

## Rollback and later gates

Rollback is **source-only rollback**: revert the exact M17.6G merge. No durable or external state is created by this unselected source slice.

Later separately governed work may add a concrete atomic nonce source/store, exact HTTP request/response transport, authenticated route composition, ASGI selection, browser activation, concrete policy/provider/signer custody, trust replacement/revocation, or bounded live localhost acceptance.
