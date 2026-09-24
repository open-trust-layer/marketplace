# Product Agreement assent Web client

## Purpose

This source-only slice adds the browser-side transport/orchestration module for
the already-reviewed Agreement assent preparation, submission, and formation-status HTTP routes.

Profile:

    MARKETPLACE_WEB_AGREEMENT_ASSENT_CLIENT_V1

The module is delivered as a reviewed same-origin asset. A later composition
slice imports it only from auth_bootstrap.js so the existing authenticated
memory-only session/key custody can be reused. app.js and index.html still do
not import or call the module, and there is no active Agreement-assent user
action.

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

The source is delivered and selected only by the reviewed auth bootstrap
composition factory. It is still not imported by app.js or index.html, and the
active page exposes no Agreement-assent action. The bootstrap does not invoke
prepare, formationStatus, or signAndSubmit by itself.

This slice performs no automatic user action, no key creation/import/export,
no storage, no timer/worker/background work, and no ambient crypto selection.
There is no Agreement publication, no payment, no settlement, no fulfillment,
and no deployment. There is no browser activation of Agreement assent in this slice.

## Rollback

Rollback is source-only rollback: revert this client/delivery/route-scope slice.
There is no credential persistence, runtime state, Agreement publication, or
external data mutation to repair.
