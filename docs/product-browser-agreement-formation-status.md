# Browser Agreement formation status

Risk classification: LOW read-only authenticated product selection.

## Purpose

This source slice activates only the existing read-only Agreement formation
status seam in the browser product.

It consumes the exact acceptance Record Identity already returned by the
explicit seller Proposal-acceptance flow and retains that identity only in
current page memory.

The browser operation is:

    agreementAssentClient().formationStatus(proposalRecordId, acceptanceRecordId)

The request is initiated only after an explicit user click on **Check Agreement
formation**.

## Preconditions

The status control remains disabled unless:

- the selected record is an exact Proposal in the reviewed response flow;
- the same page has an exact published seller acceptance result for that
  Proposal;
- the authentication bootstrap still has an active memory-only session/key;
- no formation-status request for that Proposal is already pending.

The server independently resolves the exact Proposal, listing, acceptance, and
Agreement candidate and independently requires the authenticated principal to
be an Agreement party.

## Returned view

The page retains only the reviewed bounded formation result:

- Agreement candidate Record Identity;
- formation evidence;
- required/covered/missing principal sets;
- fixed legal-enforceability / truth / publication / side-effect claims already
  enforced by the Web client.

The UI shows the Agreement Record Identity, formation evidence, covered parties,
and missing parties.

## Signing boundary

The formation-status operation itself remains read-only. Its explicit
**Check Agreement formation** handler does not call:

- prepare();
- signAndSubmit();
- createAgreementAssentSignature().

A separate browser signing slice may consume the reviewed result after this
status operation. No signing occurs inside the formation-status request or
handler.

## Authority / activity boundary

Formation status does not publish an Agreement and does not authorize payment,
settlement, escrow, fulfillment, transfer, ownership, or legal enforceability.

There is no Agreement publication.

No new persistent storage, cookie, localStorage, sessionStorage, IndexedDB,
worker, timer, background polling, retry loop, external origin, or credential
persistence is added. Status metadata is memory-only for the current page.

## Rollback

Rollback is source-only rollback: remove the formation-status card and explicit
status handler. No durable browser state or signed evidence exists to repair.
