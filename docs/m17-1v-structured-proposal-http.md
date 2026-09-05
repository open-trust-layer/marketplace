# M17.1V — Structured Proposal HTTP authoring

M17.1V adds one framework-neutral structured HTTP authoring path on top of the reviewed M17.1T Proposal draft and the M17.1U application authoring service.

## Baseline

This slice is stacked on pending M17.1U PR #224 at exact head `b19470f371a91bd782fa93b08fde1f0761719eec`, while merged `main` is `6def2cc52051237b5068fa77166701e6a881ed2f`.

It must not merge before M17.1U. A changed U head or applicable base requires revalidation.

## Structured route

`POST /api/intents/{parent_record_id}/proposals`

The request content type must be exactly `application/json`. The JSON object must contain exactly three string members:

- `buyer_principal`
- `subject_uri`
- `action_uri`

`parent_record_id` comes only from the reviewed path grammar and is not accepted in the body.

The adapter constructs the existing `BuyerRequestProposalDraft` and delegates through the injected M17.1U `MarketplaceProposalAuthoringService.create_buyer_request_proposal(...)` callable. The M17.1U service remains responsible for draft revalidation, record building, and publication only through `MarketplaceApplicationApiService.respond_to_intent(...)`.

A successful write returns the existing bounded `{change_seq, disposition}` application result with HTTP 201.

## Fail-closed transport behavior

The structured route accepts POST only, no query parameters, and the existing reviewed request-size bound. Duplicate JSON members, malformed JSON, unknown or missing members, non-string structured members, and invalid structured Proposal values are rejected before the Proposal creator is called.

Transport/body-shape failures use `INVALID_JSON_BODY` or `PROPOSAL_REQUEST_INVALID`. Reviewed M17.1U failures remain non-reflective: `PROPOSAL_DRAFT_INVALID` is a client error and `PROPOSAL_BUILD_FAILED` is an internal error. Existing application API parent/presence/type/binding errors keep the existing HTTP mapping.

## Raw authoring remains separate

`POST /api/intents/{parent_record_id}/responses` remains the low-level raw Record response route. M17.1V does not reinterpret, replace, or remove that surface.

The existing low-level `marketplace-application-http-v1` contract is not broadened here, matching the prior structured product-listing extension pattern.

## Semantic boundary

The caller supplies `action_uri`. No universal `ACTION_BUY` is introduced.

This slice introduces no agreement, acceptance, assent, order, pricing derivation, payment, settlement, fulfillment, inventory mutation, ownership transfer, ranking, trust, or authority semantics.

## Authority / runtime boundary

M17.1V is source-only application HTTP and inert composition work. No live PostgreSQL connection is required or authorized. No server/socket activation, browser action, Android build/runtime, filesystem asset loading, deployment, service/configuration mutation, secrets/provider administration, or other runtime/external mutation is part of this slice.

The application HTTP adapter still owns no socket or server lifecycle. Composition and launch-plan changes only carry the injected Proposal builder through the existing inert object graph; they do not initialize or execute it.
