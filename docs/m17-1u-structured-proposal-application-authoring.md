# M17.1U — Structured Proposal application authoring service

## Baseline and purpose

M17.1U starts from exact merged-green `main`
`6def2cc52051237b5068fa77166701e6a881ed2f` after M17.1T and merged-main
Marketplace conformance #426 succeeded on its first attempt.

M17.1T introduced the transport-neutral `BuyerRequestProposalDraft` and the explicit
OLP-dependent reference builder, while deliberately leaving publication at the existing raw
response boundary. M17.1U composes that reviewed draft through the existing application API
only. It does not change HTTP, Web, Android, persistence, or runtime behavior.

## Application composition

`marketplace.application.proposal_authoring.MarketplaceProposalAuthoringService` accepts an
exact `BuyerRequestProposalDraft` and an injected Proposal record builder. Before invoking the
builder, it reconstructs the draft through `review_buyer_request_proposal_draft(...)`, so a
frozen instance deliberately rebound after construction cannot bypass M17.1T validation.

The application authoring layer imports no Marketplace reference adapter and no OLP type. The
builder result is intentionally opaque at this layer. Builder exceptions are mapped to the
stable non-reflective `PROPOSAL_BUILD_FAILED` application-authoring error.

After construction, publication delegates only to
`MarketplaceApplicationApiService.respond_to_intent(reviewed.parent_record_id, record)`.
M17.1U therefore does not duplicate or weaken the existing authoritative checks for:

- initialized application state;
- response record being a Marketplace intent;
- exact response-to-parent binding;
- parent presence in local application state;
- parent resolving to a Marketplace intent;
- final publication through the shared application state service.

A mismatched builder result, missing parent, wrong parent type, or uninitialized API remains an
existing `ApplicationApiError`, not a new parallel policy path.

## Structured field boundary

No second transport field DTO is added. The M17.1T `BuyerRequestProposalDraft` already is the
reviewed transport-neutral four-primitive contract:

- buyer principal;
- subject URI;
- caller-supplied action URI;
- exact parent record identity.

Avoiding a duplicate field structure keeps one validation source for this semantic slice. A
future HTTP/client milestone may construct this exact draft from its bounded transport shape.

## Non-authority boundary

A structured Proposal is still only an immutable response intent. This milestone does not
infer subject/action from parent content and does not create acceptance, assent, agreement,
price, order, reservation, inventory mutation, ownership transfer, payment, settlement,
fulfillment, ranking, trust, legitimacy, or authorization.

The existing raw `POST /api/intents/{id}/responses` route and raw Web/Android response forms
remain unchanged. HTTP/Web/Android structured Proposal authoring is deferred to a later
reviewed slice.

## Capability and execution boundary

M17.1U is MODERATE source-only work under issue #223. Minimum capabilities are READ_PROJECT,
WRITE_PROJECT, and EXECUTE_LOCAL. No merge authority is implied.

This milestone authorizes no live PostgreSQL/Psycopg execution, dependency installation or
download, server/socket activation, browser action, Android build/runtime/sign/install,
filesystem asset loading, secrets/environment loading, deployment, service/configuration
mutation, provider administration, payment, settlement, fulfillment, inventory mutation,
ownership transfer, or other runtime/external mutation.
