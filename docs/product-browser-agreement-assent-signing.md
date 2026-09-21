# Browser Agreement assent signing

Risk classification: HIGH source capability selection — explicit cryptographic
Agreement-assent creation and protected assent submission. This source slice
does not itself deploy or activate a production runtime.

## Purpose

This slice activates the already-reviewed Agreement-assent signer/client through
the browser product only after an explicit human click.

The selected operation is:

    agreementAssentClient().signAndSubmit(
        proposalRecordId,
        acceptanceRecordId,
        expectedAgreementRecordId,
    )

The page never receives the private key, bearer token, raw signature, proof
input, or trusted public-key authority.

## Required exact state

The **Sign Agreement assent** control starts disabled.

It may become enabled only when all of these are true for the selected Proposal:

1. the page holds one exact published Proposal-acceptance Record Identity from
   either the reviewed seller-publication result or the explicit authenticated
   party-gated resolution flow;
2. authentication is active;
3. an explicit formation-status request has returned a reviewed result;
4. that status result is still bound in page memory to the same exact acceptance
   Record Identity;
5. the authenticated principal is in the reviewed required-principal set;
6. the authenticated principal is in the reviewed missing-principal set;
7. the authenticated principal is not already in the reviewed covered-principal
   set;
8. no signing operation for that Proposal is pending.

Only the authenticated principal that is a required missing party for the same exact acceptance Record Identity may trigger signing.

Formation being incomplete for some *other* party is not signing authority.

A non-party, already-covered party, stale acceptance/status binding, missing
status result, inactive session, or pending operation keeps signing disabled.

## Candidate-identity guard

The formation-status result supplies the exact expected Agreement candidate
Record Identity.

The browser passes that identity to the reviewed Web client. The client
re-prepares the exact Proposal + acceptance pair and compares the freshly
prepared Agreement Record Identity with the expected status identity **before**
calling the signer.

Mismatch fails closed with:

    AGREEMENT_ASSENT_AGREEMENT_MISMATCH

No signature is created on that mismatch.

The server remains authoritative and independently re-prepares/re-verifies the
candidate, proof, trusted verification method, principal attribution, party
membership, and coordination-store rules.

## Explicit user action

There is exactly one visible signing event handler:

    signAgreementAssentButton.addEventListener("click", ...)

Page load, authentication, Proposal navigation, acceptance publication,
formation-status rendering, language changes, and ordinary re-rendering never
invoke `signAndSubmit`.

The status request itself remains read-only and never invokes the signer.

## Result handling

The client accepts only the reviewed bounded submission result:

- exact Agreement Record Identity;
- `STORED` or `DUPLICATE`;
- accepted-at value;
- expiry value;
- `publishesAgreement = false`;
- `authorizesSideEffects = false`.

Only that bounded result/error metadata is retained in page memory.

No proof bytes, signature bytes, private key, bearer token, or credential
material is copied into application state.

After a successful submission the sign control remains disabled. The user may
explicitly run **Check Agreement formation** again to refresh party coverage;
there is no automatic polling or background refresh.

## Authentication and acceptance invalidation

Authentication reset or establishment clears formation/signing page-memory
state.

Publishing/re-publishing an exact Proposal acceptance invalidates prior
formation/signing page state for that Proposal, requiring a fresh explicit
formation-status check before signing.

## Authority boundary

Agreement assent evidence is not Agreement publication.

This slice does not:

- publish the Agreement record;
- establish legal enforceability;
- claim universal truth/currentness;
- authorize payment, settlement, escrow, transfer, fulfillment, or ownership;
- invalidate competing Proposals;
- mutate trust anchors;
- generate/import/export/wrap private keys;
- persist credentials or assent evidence in browser storage;
- add workers, timers, polling, retries, WebSockets, or external origins;
- perform database migration, service mutation, deployment, or public-network
  activation.

## Rollback

Rollback is source-only: remove the signing handler/status UI and restore the
prior read-only formation-status selection.

Browser key/session/result state is memory-only. Server-side assent evidence
created by an explicitly completed user signing action is immutable reviewed
application evidence and is not silently deleted or rewritten by source
rollback.
