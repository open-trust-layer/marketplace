# Product Agreement assent Web client

## Purpose

This source-only slice adds the browser-side transport/orchestration module for
the already-reviewed Agreement assent preparation, submission, and formation-status HTTP routes.

Profile:

    MARKETPLACE_WEB_AGREEMENT_ASSENT_CLIENT_V1

The module is delivered as a reviewed same-origin asset but is not imported by
app.js, index.html, or auth_bootstrap.js. There is no browser activation.

## Exact flow

The unselected client can perform preparation, strict OJVE signing-input decode,
one injected signer call, strict OJVE signature encode, submission, and a
separate read-only formation-status request. Status never calls the signer.

The server independently re-prepares and re-verifies all authority.

## Authorization boundary

MarketplaceMemorySession gains bearer authority only for the three exact POST
Agreement assent route shapes: preparation, submission, and status. This is the
exact bearer route scope.

Authorization still comes only from session.authorizationFor. The client does
not receive, expose, persist, or reconstruct the bearer token.

The caller cannot provide principal, verification method, public key, Listing
identity, Agreement identity, attribution, or trust decisions.

## Transport boundary

The client contains a bounded strict OJVE bytes codec for the exact HTTP carrier.

It accepts canonical base64url without padding, rejects invalid alphabet,
forbidden padding, invalid length, and non-zero trailing padding bits.

The signing input remains bounded to 4096 bytes. Signature output remains
exactly 64 bytes.

## Non-selection and non-scope

The source is delivered but not imported by app.js or other active Web entry
points. There is no browser activation.

This slice performs no automatic user action, no key creation/import/export,
no storage, no timer/worker/background work, and no ambient crypto selection.
There is no Agreement publication, no payment, no settlement, no fulfillment,
and no deployment.

## Rollback

Rollback is source-only rollback: revert this client/delivery/route-scope slice.
There is no credential persistence, runtime state, Agreement publication, or
external data mutation to repair.
