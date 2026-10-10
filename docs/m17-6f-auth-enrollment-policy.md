# M17.6F — Unselected authentication enrollment approval-policy gate

Profile: `MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_POLICY_V1`

Exact implementation baseline: `ee12e3a9e2b2de615287c320cb1fea88092adfe8`

Risk classification: **HIGH security/privacy / identity-enrollment authorization source capability**.

M17.6F inserts one explicit fail-closed approval decision between a validated M17.6E enrollment request and the existing M17.6E authority-attestation seam. It selects no concrete policy, signer, provider, HTTP route, runtime, or persistence.

## Exact scope

The implementation adds:

1. `src/marketplace/application/auth_enrollment_policy.py`
2. `tests/test_m17_6f_auth_enrollment_policy.py`
3. `tests/test_m17_6f_auth_enrollment_policy_artifacts.py`
4. `docs/m17-6f-auth-enrollment-policy.md`

Package membership is updated only in:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No dependency metadata, workflow, runtime selection, Web source, Android source, PostgreSQL path, configuration source, service definition, or deployment path is changed.

## Input boundary

The gate accepts exactly:

- one existing M17.6E `MarketplaceAuthenticationEnrollmentProposal`;
- trusted-composition `authority`;
- explicit `issued_at`;
- explicit `expires_at`;
- one injected purpose-specific approval policy;
- one injected existing M17.6E purpose-specific attestor.

Before consulting policy, M17.6F reuses the existing M17.5L public-key, verification-method/controller, authority, and finite lease validation semantics.

Invalid proposal, authority, or lease fails before policy is called and before the attestor can be reached.

## Purpose-specific policy

The only policy operation is:

`approve_authentication_enrollment(...exact request fields...) -> bool`

The operation receives the exact proposal fields plus the exact authority and lease already validated by the gate.

Approval requires an exact boolean `True`. `False`, integers, strings, truthy objects, missing operations, and exceptions all fail closed.

There is no implicit approval, default approval, alternate policy, retry, fallback, or caller-provided “trusted” flag.

## Ordering

The successful path is:

1. validate exact proposal type and M17.5L-compatible request semantics;
2. resolve one purpose-specific policy operation;
3. call policy exactly once with the exact validated request values;
4. require exact boolean `True`;
5. delegate exactly once to the existing M17.6E authority issuance function;
6. return the existing canonical M17.5L evidence envelope.

A policy rejection or policy failure means the attestor is not called.

If the approved M17.6E authority operation later fails, M17.6F returns one stable non-reflective policy-gate error.

## Explicit non-authority

M17.6F does not define who should be approved.

It adds no:

- allowlist, denylist, role, membership, entitlement, DID-resolution, ownership, KYC, organization, or account policy;
- user lookup or identity directory;
- HTTP endpoint or anti-replay protocol;
- filesystem, environment, database, network, DNS, or provider acquisition;
- persistence, cache, background activity, queue, or retry;
- concrete attestor or private-key custody;
- trust-anchor loading, rotation, revocation, or mutation;
- browser execution or WebCrypto selection;
- authentication-session mutation;
- runtime/server selection;
- PostgreSQL/configuration/service mutation;
- deployment, publishing, distribution, or public-network activity.

The module remains deliberately **unselected**.

## Failure behavior

All M17.6F-owned validation, policy, and delegated authority failures collapse to:

`AuthenticationEnrollmentPolicyError("authentication enrollment policy operation failed")`

The failure does not reflect proposal values, authority, lease, policy output, provider details, attestor details, or nested exception text.

## Qualification

Qualification freezes:

- exact profile;
- exact existing M17.6E proposal input type;
- exact M17.5L-compatible request validation before policy;
- one purpose-specific policy operation;
- policy exactly once;
- exact request values preserved into policy;
- exact boolean `True` required;
- rejection/malformed result/exception => attestor not called;
- approved path delegates to M17.6E exactly once;
- existing M17.5L envelope remains the output type;
- stable non-reflective failure;
- no concrete policy or provider implementation;
- continued runtime/Web/Android non-selection;
- package membership coverage;
- FULL Marketplace conformance.

## Rollback and later gates

Rollback is **source-only rollback**: revert the exact M17.6F merge. The module creates no durable or external state and remains unselected.

Later separately governed capabilities may select a concrete approval policy, add authenticated enrollment HTTP and anti-replay semantics, select concrete authority custody/provider, implement trust-anchor or signer rotation/revocation, select browser enrollment workflow, or perform bounded live localhost acceptance.
