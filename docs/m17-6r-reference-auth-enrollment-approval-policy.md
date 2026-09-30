# M17.6R — Reference authentication-enrollment exact-binding approval policy

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_APPROVAL_POLICY_V1`

Exact implementation baseline: `52c15a43ff0b7184508cf573192c866b27819d86`

Risk classification: **HIGH security/privacy / identity-enrollment approval-policy reference capability**.

M17.6R adds one deterministic, process-local, **unselected** exact-match implementation of the existing M17.6F `AuthenticationEnrollmentApprovalPolicy` seam.

It does not alter M17.6F, M17.6O, M17.6Q, M17.6N, or any runtime/client path.

## Exact six-file scope

Added:

1. `src/marketplace/reference/auth_enrollment_approval_policy_v1.py`
2. `tests/test_m17_6r_reference_auth_enrollment_approval_policy.py`
3. `tests/test_m17_6r_reference_auth_enrollment_approval_policy_artifacts.py`
4. `docs/m17-6r-reference-auth-enrollment-approval-policy.md`

Modified only for wheel membership:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No existing application, launch, nonce, runtime, HTTP/ASGI, Web, Android, provider, dependency, workflow, PostgreSQL, configuration, service, audit, or governance source is modified.

## Exact immutable binding

`MarketplaceReferenceAuthenticationEnrollmentApprovalBinding` freezes exactly:

- `principal`;
- `verification_method`;
- canonical `mkp1_` `public_key`;
- `authority`.

Construction reuses the already-reviewed M17.6E/M17.5L validation path. No URI or key normalization, inference, wildcarding, prefix matching, role/group lookup, controller resolution, or external lookup is added.

## Bounded policy

`MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy` stores one immutable tuple of exact bindings.

The tuple must contain between 1 and **256** entries inclusive, reusing the existing M17.5L evidence-entry ceiling.

Construction rejects:

- non-tuple containers;
- zero bindings;
- more than 256 bindings;
- non-binding entries;
- duplicate exact bindings;
- malformed binding fields.

Construction performs zero policy decisions and no external I/O.

## Exact-match decision semantics

The existing purpose-specific method:

`approve_authentication_enrollment(...)`

first validates the supplied principal, verification method, public key, authority, issued-at time, and expires-at time through the reviewed enrollment/evidence validation path.

For a well-formed request it returns exact boolean `True` iff one retained binding equals all four identity-selection fields exactly:

- principal;
- verification method;
- public key carrier;
- authority.

Otherwise it returns exact boolean `False`.

`issued_at` and `expires_at` must form a valid finite M17.5L lease but are not approval selectors.

A malformed policy call fails closed with the stable non-reflective error:

`reference authentication enrollment approval policy failed`

A normal well-formed non-match is `False`, not an exception.

## No ambient authority

The policy performs no:

- filesystem access;
- environment/configuration lookup;
- network/DNS access;
- database access;
- clock sampling;
- nonce/session/entropy consumption;
- policy cache or mutation;
- retry/fallback/background work;
- attestor or signer invocation;
- private-key operation;
- trust-anchor mutation.

The configured binding tuple is the complete decision input beyond the exact request fields.

## Non-selection boundary

M17.6R remains **unselected**.

It is not wired into:

- M17.6O reference enrollment launch;
- M17.6Q reference nonce authority;
- M17.6N foreground runtime;
- authenticated startup/launch/runtime;
- Uvicorn/provider paths;
- Web;
- Android;
- CLI/services;
- environment/configuration;
- Moon Company registry/runtime/control-plane.

A later separately reviewed composition may combine:

`Q nonce authority + R approval policy + separately governed attestor → O reference enrollment launch`.

## Explicit non-authority

M17.6R creates or selects no:

- enrollment evidence attestor;
- Ed25519 signer;
- private key or key custody;
- trust anchor;
- nonce authority/material source;
- persistent/shared policy store;
- identity directory;
- role/group/membership system;
- runtime/server/provider execution;
- browser/Android activation;
- PostgreSQL/config/service mutation;
- production/public-network activity;
- deployment, publishing, or distribution.

## Moon Company boundary

M17.6R is only a replaceable Moon Commerce reference policy for explicit pre-approved enrollment bindings.

It adds no Moon Company runtime/control-plane dependency and grants Moon Company no identity authority, policy-administration authority, signing authority, key custody, session authority, runtime authority, or production authority.

## Rollback

Rollback is **source-only rollback**: revert the exact M17.6R merge.

Because the policy is immutable, process-local, unselected, and external-I/O-negative, rollback requires no policy-store cleanup, nonce/session cleanup, key revocation, trust-store mutation, database rollback, service restart, provider administration, browser/device cleanup, or deployment rollback.
