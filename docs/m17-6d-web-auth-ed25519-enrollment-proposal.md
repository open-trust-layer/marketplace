# M17.6D — Unselected Web Ed25519 enrollment-proposal handoff boundary

Profile: `MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1`

Exact implementation baseline: `e5be62390315183786033366af42778011bf80b5`

Risk classification: **HIGH security/privacy / identity-trust handoff source capability**.

M17.6D adds one source-only, unselected handoff boundary between M17.6C public enrollment material and a later separately governed trusted enrollment authority. The output is deliberately **non-authoritative** proposal data.

## Exact scope

The milestone is additive-only and consists of exactly:

- `web/auth_ed25519_enrollment_proposal.js`
- `tests/test_m17_6d_web_auth_ed25519_enrollment_proposal_contract.py`
- `tests/test_m17_6d_web_auth_ed25519_enrollment_proposal_artifacts.py`
- `docs/m17-6d-web-auth-ed25519-enrollment-proposal.md`

No M17.6A/B/C source, active Web entry point, M17.5K/L/M/N/S trust source, Python authentication/runtime source, dependency manifest, workflow, repository-audit control, PostgreSQL/configuration/service path, Android source, or runtime state is modified.

## Request

The pure function accepts exactly:

```text
{
  profile: "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1",
  principal: "<caller-provisioned absolute URI>",
  verificationMethod: "<caller-provisioned absolute URI>",
  publicKeyValue: "mkpk1_<43 canonical base64url-no-padding characters>"
}
```

Both URI fields are preserved exactly, must be non-empty absolute URIs, and must encode to at most 2048 UTF-8 bytes. There is no normalization, DID resolution, controller inference, aliasing, ownership proof, role logic, or relationship inference between them.

## Public-key handoff

The `mkpk1_` value must decode canonically to exactly 32 bytes. Those exact bytes are re-encoded as the existing M17.5L public-key carrier:

```text
mkp1_<43 canonical base64url-no-padding characters>
```

Frozen vector:

```text
mkpk1_AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8
->
mkp1_AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8
```

Prefix translation alone is not trust. Canonical decoding and same-byte re-encoding are required.

## Result

The frozen result contains exactly:

```text
{
  profile: "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1",
  type: "MarketplaceAuthenticationEnrollmentProposal",
  principal: "<exact caller value>",
  verificationMethod: "<exact caller value>",
  publicKey: "mkp1_..."
}
```

This is proposal data only. It is not an M17.5L evidence bundle and carries no authority decision.

## Explicit non-authority

M17.6D provides:

- no verification-method assignment;
- no principal/controller inference or normalization;
- no evidence bundle or envelope creation;
- no authority, validity lease, attestation, signature, trust status, acceptance status, or session data;
- no evidence signing or trust verification;
- no server enrollment/registration or HTTP request;
- no trust mutation, provisioning, loading, or persistence;
- no private-key access, generation, import, export, wrapping, serialization, signing, or custody behavior;
- no ambient WebCrypto selection;
- no active Web authentication/session establishment;
- no browser secure-context acceptance;
- no Android action;
- no network, database, service, configuration, runtime, dependency, package, workflow, or repository-audit widening;
- no production/public-network action, deployment, publishing, or distribution.

The source is deliberately **unselected** by active Web and Android entry points.

## Failure behavior

Malformed request shape, profile, URI, prefix, alphabet, length, non-canonical base64url, or non-32-byte material fails with one stable non-reflective local error:

`AUTH_ENROLLMENT_PROPOSAL_UNAVAILABLE`

Input values are not reflected in errors or logs.

## Qualification

Qualification freezes:

- exact profile and request/result shapes;
- exact <=2048-byte URI boundary matching M17.6B;
- no URI normalization or relationship inference;
- exact canonical `mkpk1_` decoding to 32 bytes;
- exact same-byte `mkp1_` re-encoding;
- frozen bytes `00..1f` bridge vector;
- malformed/non-canonical carrier rejection;
- exact preservation of principal and verification method;
- no authority/validity/attestation/trust/acceptance fields;
- zero private-key, signing, WebCrypto generation, persistence, networking, server registration, evidence creation, or background capability;
- continued non-selection by Web and Android entry points;
- existing M17.5K/L/M/N/S and M17.6A/B/C guards remaining green;
- repository audit and Marketplace conformance remaining green without dependency/workflow widening.

## Rollback and later gates

Rollback is **source-only rollback**: revert the exact M17.6D merge. Because the boundary is pure, unselected, non-persisting, and non-authoritative, rollback requires no key revocation, trust cleanup, database migration, service restart, or deployment action.

A later trusted enrollment authority must independently decide whether and how to bind one exact proposal to M17.5L/M trusted verification-method evidence. Composition with proof creation/session establishment, real-browser acceptance, active authenticated UI, custody persistence/recovery/rotation, Android custody/auth, production trust administration, service hosting, public-network exposure, and deployment remain separately governed.
