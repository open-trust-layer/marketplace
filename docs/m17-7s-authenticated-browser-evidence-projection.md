# M17.7S — Authenticated browser evidence projection

Profile: `MARKETPLACE_AUTHENTICATED_BROWSER_EVIDENCE_PROJECTION_V1`

Evidence profile: `MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1`

Issue: #504.

## Purpose

M17.7R makes the final authenticated local-flight evidence machine-checkable.
M17.7S adds the matching pure Web projection so a browser-side evaluator can
turn already-observed lifecycle results into the exact R document shape.

The projection performs no live flight and does not infer missing observations.
Seller and buyer authentication booleans are explicit observed inputs; the
projector rejects either value unless it is exactly `true`.

## Inputs

The projector accepts only explicit, already-observed values:

- exact merged main commit;
- positive CI run number;
- runtime host, which must be exact `127.0.0.1`;
- seller/buyer authentication observations;
- listing, Proposal, and acceptance Record Identities;
- reviewed Agreement formation result;
- reviewed Agreement publication result;
- reviewed fulfillment completion result.

The Web result objects use the already-reviewed camelCase client shapes. The
output is normalized to the exact snake_case M17.7R JSON contract.

## Exact semantics

The projector requires:

- formation `EVIDENCE_SUFFICIENT_FOR_PROFILE`;
- no missing principals;
- one exact Agreement identity across formation/publication/completion;
- publication disposition `STORED` or `DUPLICATE`;
- commitment `seller-delivery`;
- evidence kind `CLAIMED_COMPLETE_PERFORMANCE`;
- completion disposition `STORED` or `DUPLICATE`;
- positive or null local change sequences.

It hard-codes the reviewed false boundaries for universal truth, payment or
settlement evaluation, public-network exposure, and public deployment.

## Security/runtime boundary

The module is pure synchronous value projection. It performs no fetch, network
request, storage, clipboard write, file write, browser automation, signing,
credential handling, database access, server execution, timers, workers, or
background activity.

It is delivered by the existing reviewed localhost static-module allow-list but
is not itself a runtime-selection or execution mechanism.

## Acceptance handoff

The resulting object is intended to be serialized by the evaluator and checked
offline with:

`python tools/marketplace_authenticated_local_flight_evidence.py <evidence.json>`

Passing projection alone is not live-flight acceptance. The input observations
must come from the separately authorized post-P loopback browser flight.

## Rollback

Source-only rollback: revert the M17.7S merge.
