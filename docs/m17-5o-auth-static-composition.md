# Marketplace M17.5O â€” Static in-memory authentication composition bundle

Profile: `MARKETPLACE_APPLICATION_AUTH_STATIC_COMPOSITION_V1`

Baseline: exact merged-green Marketplace `main`
`bf37ce6a1392944a8e1fa31a4d28c3c36449695c`.

Authority: owner-authorized **HIGH** authentication-composition capability
recorded on Issue #288. The implementation is restricted to the exact six-file
scope below.

## Purpose

M17.5J/K/L/M/N already define the production-source public-key verification,
immutable verification-method/principal-binding snapshot, canonical evidence
intake, evidence trust verification, and canonical trust-anchor manifest intake.
They deliberately remain individually constructor-driven and unselected.

M17.5O freezes one source-only coherent composition path:

`N â†’ M â†’ L â†’ one K snapshot â†’ J + application-auth`

The exact same K snapshot instance is supplied to J for proof-key lookup and to
`MarketplaceApplicationAuthService` for principal binding. This prevents a
split-snapshot authentication decision inside this profile.

## Inputs

`compose_marketplace_static_authentication(...)` accepts only:

- exact caller-supplied M17.5N canonical trust-anchor manifest `bytes`;
- one exact M17.5L
  `MarketplaceAuthenticationVerificationMethodEvidenceEnvelope`;
- one exact non-boolean, non-negative integer `at_time`.

The function performs no source discovery and has no defaults for trust data.

## Exact composition

The implementation performs exactly:

1. materialize N manifest bytes into one immutable M trust-anchor snapshot;
2. construct one M Ed25519 evidence trust verifier from that snapshot;
3. materialize the supplied L envelope at `at_time` into one immutable K
   verification-method snapshot;
4. construct one J Ed25519 authentication proof verifier using that K snapshot;
5. construct one Marketplace application-auth service using that same K
   snapshot as principal-binding verifier;
6. return one frozen/slotted composition value containing the auth service,
   proof verifier, and exact immutable K/N snapshots for deterministic
   inspection.

There is no alternate key source, permissive trust verifier, second K snapshot,
fallback, URI ownership inference, aliasing, role/membership/delegation
inference, or graph traversal.

## Failure boundary

All composition failures become one stable non-reflective
`MarketplaceStaticAuthenticationCompositionError`. No manifest bytes, evidence
claims, attestation bytes, authorities, verification methods, controller
principals, public keys, paths, provider details, or raw exception text are
included in the public error.

Composition is atomic: a failure returns no partially usable composition.

## Capability and activation boundary

M17.5O performs **no filesystem** access, no environment lookup, no database
access, **no network** access, no HTTP/DNS/socket activity, no subprocess, no
resolver/provider acquisition, no configuration loading, **no persistence**, no
cache, no background task, no refresh, no retry, and **no runtime activation**.

It creates no challenge or session token during composition and does not
instantiate `MarketplaceCredentialMaterialSource`, HTTP/ASGI adapters, a
localhost application, or runtime/server composition.

Production source adds no private-key generation/import/export/storage/custody,
no signing capability, and no new dependency. It uses only the existing
reviewed public-key verification chain and the already-reviewed optional
`cryptography==50.0.1` dependency.

## Exact six-file scope

Added:

1. `src/marketplace/application/auth_static_composition.py`
2. `tests/test_m17_5o_auth_static_composition.py`
3. `tests/test_m17_5o_auth_static_composition_artifacts.py`
4. `docs/m17-5o-auth-static-composition.md`

Modified:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No M17.5J/K/L/M/N source, auth HTTP/ASGI source, runtime composition,
`auth_material.py`, dependency metadata, workflow, repository audit, Web,
Android, configuration, or service/runtime file is changed.

## Qualification

Tests cover the exact profile/input types, exact N/M/L/K/J chain, canonical
manifest failure, stale evidence failure, unknown authority and invalid evidence
signature rejection, wrong proof-key rejection, explicit controller mismatch,
valid in-process synthetic authentication, and exact same-snapshot wiring.
Artifact tests prove the module is not selected by HTTP/ASGI/localhost/runtime,
Web or Android entry points and adds no provisioning/I/O/private-key/dependency
surface.

Synthetic fixed private keys/signatures are test-only. Production source has no
private-key or signing surface.

## Threat boundary

M17.5O addresses split-snapshot key/binding decisions, accidental bypass of
L/M/N trust processing, hidden fallback, partial composition, and accidental
runtime/provisioning behavior hidden inside a convenience factory.

It does not decide operational trust/evidence sources, replacement/rollback,
rotation/revocation/freshness administration, network acquisition policy,
service startup configuration, client private-key custody, or live
authentication.

## Rollback

Rollback is **source-only rollback**: revert the exact eventual M17.5O merge.
Because the composition remains unselected, caller-supplied, process-local,
public-key-only and external-I/O-negative, rollback requires no key revocation,
trust-store administration, session cleanup, provider action, database
migration, service restart, Android cleanup, configuration rollback, or
external-data mutation.

## Later gates

Only after M17.5O is merged-green may separately authorized milestones decide:

1. one bounded startup provisioning source for canonical N/L bytes;
2. immutable composition replacement/rollback and rotation/revocation policy;
3. any bounded evidence acquisition provider and network policy;
4. runtime/ASGI composition selection;
5. bounded live authentication acceptance.
