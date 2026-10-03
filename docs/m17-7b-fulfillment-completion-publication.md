# M17.7B — Application fulfillment evidence publication service

Profile: MARKETPLACE_APPLICATION_FULFILLMENT_COMPLETION_PUBLICATION_V1

Risk: **MODERATE application-state write capability**. The source remains
unselected; qualification uses synthetic initialized in-memory state only.

## Purpose

M17.7A authors three exact immutable happy-path fulfillment evidence records but
never publishes them.

M17.7B adds the smallest transport-neutral application publication boundary over
reviewed injected builders.

The service resolves the exact Agreement already present in application state,
builds one requested evidence record, re-verifies the exact Agreement/commitment
target, derives the exact evidence Record Identity, and then performs exactly one application-state publication.

## Exact operations

The service exposes exactly three operations:

1. publish_claimed_complete_performance;
2. publish_commitment_acceptance;
3. publish_commitment_completion.

Each accepts one Agreement Record Identity, one commitment local id, and one
issuer principal.

Request fields are bounded and validated before the Agreement state read.

## Resolution and re-binding

For one valid request, B calls state.peek exactly once with the exact Agreement
Record Identity.

A missing Agreement fails before any builder or publication.

The selected injected builder is called exactly once with the exact resolved
Agreement object, reviewed commitment id, and reviewed issuer.

Before publication, the injected target extractor must return exactly:

(Agreement Record Identity, commitment id)

and both values must match the original reviewed request exactly.

A target mismatch fails before identity derivation or publication.

## Identity and publication

Only after exact target re-binding does B derive the evidence Record Identity.

The state service is then called once with the exact built event. The return
value must be exact ApplicationStatePutResult.

The immutable result records only:

- event Record Identity;
- Agreement Record Identity;
- commitment id;
- one reviewed evidence-kind label;
- store disposition;
- optional change sequence.

## Authentication and authority boundary

M17.7B **does not authenticate callers** and **does not decide issuer authority**.

Performance-party equality remains a builder-level M17.7A semantic.

Acceptance and completion issuer role, delegation, organizational authority,
and policy remain future authenticated application gates.

B therefore must not be selected by a transport until that separate boundary is
reviewed.

## Semantic boundary

Publication stores immutable attributable evidence. It does not mutate the
Agreement, declare universal state, evaluate fulfillment, establish objective
performance, prove universal acceptance/completion, or imply payment or
settlement.

## Side-effect boundary

When explicitly invoked, B has one possible side effect: **exactly one
application-state publication** of the already-built and re-bound evidence
event.

It performs no HTTP/network action, proof creation, signing/private-key work,
filesystem/environment intake, database connection construction, direct store
bypass, clock acquisition, fulfillment evaluation, retry/fallback, background
work, runtime/provider/listener selection, Web/Android action, payment, or
settlement.

## Non-selection

M17.7B is **unselected**.

There is **no HTTP endpoint** and **no Web control** for B.

Generic application HTTP, authenticated localhost composition, Web bootstrap,
Web app/page, Android, runtime/provider/startup entry points, and the
deterministic MVP flight do not import or invoke this module.

Qualification publishes synthetic events only into disposable in-memory state.

## Next boundary

A later reviewed slice may compose exact M17.7A builders into B and then define
an authenticated issuer/role policy before an HTTP transport is exposed.

That later work must not infer acceptance authority merely from a caller-
provided principal.

## Rollback

**source-only rollback:** revert the exact M17.7B merge.

No production data, database, service, browser/device, provider, or deployment
cleanup is required because B remains unselected and qualification is
in-memory-only.
