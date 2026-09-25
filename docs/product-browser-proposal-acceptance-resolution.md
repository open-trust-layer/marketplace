# Browser Proposal acceptance resolution

Risk classification: LOW authenticated read-only product selection.

## Purpose

A seller that explicitly publishes Proposal acceptance receives the acceptance
Record Identity in that browser session. A buyer uses a different authenticated
session and cannot rely on the seller's page memory.

This slice gives either exact Proposal party one explicit browser action to
resolve the canonical published acceptance identity before Agreement formation
inspection or Agreement assent.

## Explicit user action

The Agreement card contains:

    Resolve Proposal acceptance

The control starts disabled.

It becomes available only for an exact selected Proposal with an active
authenticated session when no acceptance identity is already present in the
current page state and no resolution request is pending.

Resolution occurs only from the button click. Page load, authentication,
navigation, rendering, Proposal publication, formation checks, and signing do
not automatically invoke the resolution GET.

## Exact client operation

The page calls:

    proposalAcceptanceClient().resolveAcceptance(proposalRecordId)

The client performs only:

    GET /api/intents/{proposal_record_id}/acceptance

with bearer authorization from the existing memory-only session, no query and no body, and no Content-Type.

A successful response must be HTTP 200 with exactly:

- `proposal_record_id`;
- `record_id`.

The returned Proposal identity must exactly equal the requested Proposal.

## Party / authority boundary

The browser does not decide whether the session is a Proposal party.

The server-side resolver independently derives buyer + seller from the exact
Proposal and parent Listing and rejects non-parties before acceptance
disclosure.

The browser never supplies an acceptance identity to the resolver.

## Handoff into Agreement flow

Published seller acceptance metadata remains preferred when it already exists
in page memory.

Otherwise the exact resolved acceptance Record Identity becomes the page-memory
evidence input for:

- explicit Agreement formation-status inspection;
- the later explicit Agreement-assent signing action.

Both operations still send the exact acceptance Record Identity to their
independently reviewed server-side candidate resolver.

Resolution does not imply formation sufficiency or assent.

## Authentication lifecycle

Resolved acceptance identities/errors/pending state are cleared whenever a new
authenticated session is established or the current authentication is reset.

Seller publication of acceptance for the same Proposal also invalidates any
resolved copy and downstream formation/assent page state.

## Activity / retention boundary

Resolution metadata is page-memory-only.

This slice adds no persistent browser storage, worker, timer, retry loop,
background request, polling, service worker, WebSocket, or external origin.

The GET does not refresh server-side application-record retention.

## Non-scope

This slice does not:

- publish Proposal acceptance;
- automatically sign Agreement assent;
- publish an Agreement;
- create payment/settlement/escrow/fulfillment authority;
- mutate trust evidence or keys;
- migrate a database;
- deploy or activate a production runtime.

## Rollback

Rollback is source-only: remove the resolution control/client selection and
restore the prior seller-session-only acceptance handoff.
