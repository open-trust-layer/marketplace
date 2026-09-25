# Authenticated Proposal acceptance resolution HTTP

## Purpose

Expose the deterministic Proposal-acceptance resolver to authenticated Proposal
parties without allowing the caller to choose an acceptance identity.

The reviewed route is:

    GET /api/intents/{proposal_record_id}/acceptance

This is the read counterpart to the existing seller-only acceptance publication:

    POST /api/intents/{proposal_record_id}/acceptance

The method distinguishes the authority. GET never publishes acceptance; POST
never performs discovery.

## Request contract

The GET request has:

- no query parameters;
- no request body;
- no Content-Type;
- one active application bearer session.

Malformed request shape fails before the resolver is called.

The session is validated without extending its idle lifetime. The resolver
receives only the non-secret authenticated principal plus the Proposal Record
Identity from the path.

## Resolution authority

The injected
`MarketplaceProposalAcceptanceResolutionService` remains authoritative for:

- exact Proposal validation;
- exact parent Listing validation;
- buyer/seller party derivation;
- non-party rejection;
- deterministic acceptance identity derivation;
- proof that the derived acceptance is actually present in retained state;
- exact acceptance identity/Proposal/seller revalidation.

The HTTP adapter does not accept an acceptance identity from query/body input
and does not enumerate candidate events.

## Response

Success is HTTP 200 with exactly:

    {
      "proposal_record_id": "...",
      "record_id": "..."
    }

No acceptance record body, seller/buyer profile data, proof bytes, credentials,
session token, or key material is returned.

## Error boundary

Stable mappings include:

- unauthenticated/invalid session -> 401;
- authenticated non-party -> 403;
- missing Proposal/Listing/published acceptance -> 404;
- unavailable application state or unselected resolver -> 503;
- invalid deterministic resolution preconditions -> 409.

Errors remain non-reflective.

## Composition

The authenticated HTTP and startup composition functions accept the exact
resolver as an optional injected capability.

When absent, GET resolution fails closed with
`PROPOSAL_ACCEPTANCE_RESOLUTION_UNAVAILABLE`.

This slice does not construct the resolver from ambient configuration and does
not select it from environment/filesystem/database metadata.

## Authority boundary

This is a read-only authenticated discovery seam.

It does not:

- publish Proposal acceptance;
- create or sign Agreement assent;
- publish an Agreement;
- mutate coordination evidence;
- authorize payment, settlement, escrow, transfer, fulfillment, or ownership;
- refresh application-record retention;
- add a database index or migration;
- add network origins, background work, retries, timers, or workers;
- deploy or activate a production runtime.

Browser selection remains a later reviewed slice.

## Rollback

Rollback is source-only: remove the GET route/composition injection and restore
the prior authenticated adapter. No external state is created by the read.
