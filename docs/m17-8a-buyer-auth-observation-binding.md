# M17.8A — Transaction-bound buyer-auth observation

Profile: `MARKETPLACE_BUYER_AUTH_OBSERVATION_BINDING_V1`

## Why

The authenticated local-flight evidence preview has a separately observed buyer
authentication checkbox. Previously, the browser only checked whether that
checkbox was checked. Selecting a different Proposal could leave an old
confirmation checked and make the new transaction appear buyer-observed.

## Narrow behavior

When the evaluator explicitly checks the buyer observation, the Marketplace
records **in memory only** the currently selected Proposal Record Identity,
parent Listing Record Identity, exact record-derived buyer principal, and
active seller session's principal. The context is accepted only if the buyer
differs from the seller and the currently established seller session matches
the parent Listing.

Before preview readiness, after the asynchronous projector import, and before
any explicit evidence download, the browser re-evaluates those four values
against current selected records and the same seller session. A different Proposal,
parent Listing, buyer/seller principal, or inactive/changed seller session
invalidates the manual observation: the checkbox is unchecked and any
prepared evidence is cleared. Returning to a previously selected Proposal
still requires a fresh explicit observation; a prior checkbox value does
not automatically carry over.

If the checkbox is selected without a complete and valid current context,
it reverts to unchecked. An operator may observe buyer authentication in a
separate browser and then explicitly confirm it in the seller browser for
the exact selected Proposal.

## Strict boundary

This remains a **manual observation**, not cryptographic evidence of a buyer
session. It does not infer, impersonate or establish buyer authentication.
A source-only preview is **not live-runtime acceptance**.

The observation exists only in the current page's memory. The implementation
adds no server call, network action, database access, credential collection,
storage, clipboard, signing, background worker, automatic export, payment,
settlement or public deployment. The offline M17.7R evidence JSON contract
does not change. Existing seller attribution and formation sufficiency rules
remain authoritative.

## Verification / rollback

M17.8A tests verify the transaction/context binding, fail-closed checkbox
invalidation, rechecks on preview / asynchronous preparation / export, and
the lack of extra runtime capabilities. Source-only rollback reverts the
M17.8A PR; no runtime/database rollback is involved.
