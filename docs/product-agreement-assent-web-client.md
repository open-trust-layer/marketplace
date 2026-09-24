# Product Agreement assent Web client

## Purpose

This source-only slice adds the browser-side transport/orchestration module for
the already-reviewed Agreement assent preparation, submission, and formation-status HTTP routes.

Profile:

    MARKETPLACE_WEB_AGREEMENT_ASSENT_CLIENT_V1

The module is delivered as a reviewed same-origin asset and remains imported
only by auth_bootstrap.js so the existing authenticated memory-only session/key
custody can be reused. app.js and index.html do not import the module directly.
The active page reaches the client only through the reviewed bootstrap
composition factory for explicit formation-status inspection and explicit
Agreement-assent signing.

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
composition factory. It is not imported directly by app.js or index.html.

Formation status remains an explicit read-only user action and never calls the
signer.

The signing path is a separate explicit browser action. The page calls
`signAndSubmit(proposalRecordId, acceptanceRecordId, expectedAgreementRecordId)`
only after a reviewed formation result proves that the authenticated principal
is a required missing party for the exact in-memory Proposal acceptance.

Before the signer is called, the client independently re-prepares the exact
candidate and requires its Agreement Record Identity to match the exact
`expectedAgreementRecordId` supplied from the reviewed formation-status
result. A mismatch fails with `AGREEMENT_ASSENT_AGREEMENT_MISMATCH` before any
signature is created.

There is no automatic signing, key creation/import/export, persistent storage,
timer/worker/background work, or ambient crypto selection. Signing and assent
submission do not publish an Agreement and do not authorize payment,
settlement, fulfillment, transfer, or deployment.

## Rollback

Rollback is source-only rollback: revert this client/delivery/route-scope slice.
There is no credential persistence, runtime state, Agreement publication, or
external data mutation to repair.
