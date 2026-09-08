# Marketplace M17.5P — Static authenticated HTTP composition bundle

Profile: `MARKETPLACE_APPLICATION_AUTH_HTTP_COMPOSITION_V1`

Baseline: exact merged-green Marketplace `main`
`ec49c0e9a951c7abf0e22c9735b46e9150d7ca6d`.

Authority: owner-authorized **HIGH** authentication-routing capability recorded
on Issue #290. The implementation is restricted to the exact six-file scope
listed below.

## Purpose

M17.5O freezes one coherent in-memory authentication trust graph:

`N -> M -> L -> one K snapshot -> J proof verifier + MarketplaceApplicationAuthService`

The existing application layer already exposes one inert
`MarketplaceApplicationComposition`, while the existing M17.5C/D HTTP adapters
already define protected Marketplace writes and challenge/session establishment.

M17.5P freezes the HTTP-level wiring between those already-reviewed objects
without selecting ASGI, launch, runtime, a clock, or an operational credential
source.

## Exact composition

`compose_marketplace_authenticated_http(...)` accepts only:

- one exact existing `MarketplaceApplicationComposition`;
- one exact existing M17.5O `MarketplaceStaticAuthenticationComposition`;
- one caller-supplied credential-material source exposing the reviewed
  `challenge_bytes()` and `session_token_bytes()` callables;
- caller-supplied record JSON decoding and record-principal extraction
  callables.

It then constructs exactly:

1. one `AuthenticatedProductListingAuthoringService` over the exact M17.5O
   auth service and existing application product-listing authoring service;
2. one `AuthenticatedProposalAuthoringService` over that same exact auth
   service and existing application proposal-authoring service;
3. one `MarketplaceAuthenticatedApplicationHttpAdapter` reusing the existing
   application HTTP adapter and exact application API write callables;
4. one `MarketplaceAuthenticationSessionHttpAdapter` using the same exact
   auth-service instance and the exact M17.5O proof verifier;
5. one frozen/slotted `MarketplaceAuthenticatedHttpComposition` containing
   the exact input compositions, authenticated authoring wrappers, and HTTP
   adapters.

The same exact auth-service instance therefore owns challenge/session state and
all protected-write authorization state. No second auth service, alternate
proof verifier, alternate verification-method snapshot, fallback key source, or
parallel application graph is constructed.

## Credential-material boundary

Composition performs **zero credential-material calls**.

The supplied material source is capability-checked only by obtaining its
callable methods. `challenge_bytes()` and `session_token_bytes()` are invoked
only later by an explicit request handled by the already-reviewed
`MarketplaceAuthenticationSessionHttpAdapter`.

M17.5P does not select or instantiate `MarketplaceCredentialMaterialSource`,
does not select a clock, and creates no challenge or session token merely by
composing the graph.

## Failure boundary

All construction/wiring failures become one stable non-reflective
`MarketplaceAuthenticatedHttpCompositionError`.

The public error does not include trust-manifest bytes, verification-method
evidence, proof documents, challenges, session tokens, principals, verification
methods, public keys, record bodies, provider details, paths, or raw exception
text.

Composition is atomic: failure returns no partially usable authenticated HTTP
composition.

## Activation and external-I/O boundary

M17.5P performs no filesystem access, no environment lookup, no database
provisioning, no socket/HTTP/DNS/network activity, no subprocess, no
resolver/provider acquisition, no configuration loading, no persistence
creation, no cache/background work, no refresh/retry, no ASGI selection, no
launch-plan mutation, and no runtime/server execution.

There is **no ASGI** activation and **no runtime** activation in this profile.
`MarketplaceSessionEstablishmentAsgiHttpAdapter`, `MarketplaceApplicationLaunchPlan`,
the runtime server seam, and concrete server providers remain unchanged and do
not select M17.5P.

Production source adds no private-key generation/import/export/storage/custody,
no signing capability, no deterministic credential generator, and no new
dependency.

## exact six-file scope

Added:

1. `src/marketplace/application/auth_http_composition.py`
2. `tests/test_m17_5p_auth_http_composition.py`
3. `tests/test_m17_5p_auth_http_composition_artifacts.py`
4. `docs/m17-5p-auth-http-composition.md`

Modified only:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No auth predecessor source, application composition, ASGI, launch, runtime,
provider, dependency metadata, workflow, repository audit, Web, Android,
PostgreSQL, configuration, or service/runtime file is changed.

## Qualification

Tests prove:

- exact profile and exact composition input types;
- same exact auth-service instance across session establishment, protected HTTP
  routing, listing authorization, and proposal authorization;
- exact M17.5O proof verifier reuse;
- exact existing application HTTP/API object reuse;
- zero material-source calls during composition;
- deterministic in-process challenge/session establishment after composition;
- a valid fixed synthetic proof creates a session;
- that exact session authorizes a matching-principal protected raw intent write;
- a different principal is rejected before downstream write;
- invalid proof and credential-material failures remain fail closed;
- unauthenticated reviewed reads continue delegating to the existing base HTTP
  adapter;
- ASGI/launch/runtime entry points remain non-selecting;
- package artifacts require the new module.

Synthetic private keys/signatures and deterministic credential material are
test-only.

## Threat boundary

M17.5P addresses:

- split auth-service state between session establishment and protected writes;
- accidental proof-verifier substitution;
- bypass of authenticated authoring wrappers;
- parallel application graph construction;
- hidden credential generation during composition;
- accidental ASGI/runtime activation inside a convenience factory.

It deliberately defers operational N/L provisioning, credential-material source
selection, clock selection, authenticated ASGI/launch selection, trust/evidence
replacement and rotation/revocation policy, network acquisition, client
private-key custody/signing, and live authentication.

## Rollback

Rollback is **source-only rollback**: revert the exact eventual M17.5P merge.

Because M17.5P remains caller-supplied, process-local, unselected by ASGI,
launch, and runtime, and performs zero credential-material calls during
composition, rollback requires no session cleanup, key revocation, trust-store
administration, provider action, database migration, service restart, Android
cleanup, configuration rollback, or external-data mutation.

## Later gates

Only after M17.5P is merged-green may separately authorized milestones decide:

1. bounded startup provisioning for canonical N/L bytes;
2. explicit credential-material and clock selection;
3. authenticated ASGI/launch-plan composition selection;
4. immutable runtime replacement/rollback and trust/evidence
   rotation/revocation/freshness policy;
5. bounded evidence acquisition with explicit network policy;
6. bounded live authentication acceptance.
