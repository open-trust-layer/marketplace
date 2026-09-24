# Product Agreement assent Web client

## Purpose

This source-only slice adds the browser-side transport/orchestration module for
the already-reviewed Agreement assent preparation, submission, and formation-status HTTP routes.

Profile:

    MARKETPLACE_WEB_AGREEMENT_ASSENT_CLIENT_V1

The module is delivered as a reviewed same-origin asset and remains imported
only by auth_bootstrap.js so the existing authenticated memory-only session/key
custody can be reused. app.js and index.html do not import the module directly.
A later browser slice may call the bootstrap composition factory only for the
read-only formation-status operation.

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

## Browser selection and non-scope

The source is delivered and selected only by the reviewed auth bootstrap
composition factory. It is not imported by app.js or index.html.

A later product slice provides read-only browser activation by invoking only
`agreementAssentClient().formationStatus(...)` after an explicit user click and
an exact in-memory Proposal acceptance Record Identity. Status never calls the
signer.

There is no signing activation: the active page does not call `prepare`,
`signAndSubmit`, or `createAgreementAssentSignature`, and the visible signing
control remains disabled.

There is no automatic user action, key creation/import/export, persistent
storage, timer/worker/background work, or ambient crypto selection. There is
no Agreement publication, payment, settlement, fulfillment, or deployment.

## Rollback

Rollback is source-only rollback: revert this client/delivery/route-scope slice.
There is no credential persistence, runtime state, Agreement publication, or
external data mutation to repair.
