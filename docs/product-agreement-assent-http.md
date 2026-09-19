# Product authenticated Agreement assent HTTP seam

## Purpose

This source-only slice exposes the already-reviewed Agreement assent workflow
through two authenticated application HTTP routes without activating any server,
browser signer, database migration, or Agreement publication.

Routes:

    POST /api/agreements/{proposal_record_id}/assent/preparation
    POST /api/agreements/{proposal_record_id}/assent

## Preparation

The preparation request body contains exactly:

    acceptance_record_id

The Proposal identity comes only from the route. The Listing identity is
derived only from that Proposal's single parent by the candidate resolver.

The active application session supplies both principal and verification method.
Neither may be supplied by the request.

Preparation validates the session without refreshing its idle lifetime, builds
the exact candidate, and returns only:

- Agreement Record Identity;
- session verification method;
- exact signing input encoded as canonical OJVE bytes.

Preparation performs no coordination write.

## Submission

The submission body contains exactly:

- acceptance_record_id;
- signature as canonical OJVE bytes.

The server does not accept a caller-supplied preparation or signing input.
After authenticating the session, it resolves the exact candidate and runs
workflow preparation again from the current session principal/method. It then
passes the exact decoded 64-byte signature to workflow submission.

A stored result reports bounded retention metadata and keeps
publishes_agreement and authorizes_side_effects permanently false.

## Transport

The byte carrier reuses pinned OLP OJVE-1:

    {"$olp":"bytes","v":"<canonical-base64url-no-padding>"}

No new mk-style carrier or alternate base64 profile is introduced.

## Composition

The new adapter wraps the existing authenticated Marketplace HTTP adapter.
Non-matching routes delegate to the existing adapter unchanged.

This source slice does not add the routes to an ASGI/server composition or
activate them on localhost/public network. Runtime selection remains separate.

## Security boundary

The request cannot supply:

- acting principal;
- verification method;
- Listing Record Identity;
- public key;
- attribution decision;
- signing input;
- trust evidence.

There is no automatic latest-acceptance selection. The exact acceptance Record
Identity is required for every preparation/submission.

No Agreement publication, payment, settlement, escrow, fulfillment, ownership
transfer, key generation/import/export, browser delivery/selection, deployment,
or production database action is performed.

## Rollback

Rollback is source-only: revert this additive adapter/codec/test/doc slice.
