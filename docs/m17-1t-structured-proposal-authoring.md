# M17.1T — Structured core Proposal response builder

## Baseline and purpose

M17.1T starts from exact merged-green `main`
`fcbf0f70167047019592e4486aabdce27845db7c` after M17.1S and merged-main
Marketplace conformance #423 attempt 2 succeeded.

M17.1Q/R/S deliberately left response authoring at the reviewed raw-record boundary because
there was no shared structured Proposal builder. M17.1T fills only that missing construction
primitive. It does not change HTTP, Web, Android, persistence, or runtime behavior.

## Reused semantics

Marketplace Specification 0003 remains authoritative: a Proposal is an ordinary immutable
`MarketIntentV1` whose profile set includes `proposal-v1` and whose content contains a
non-empty set-like `response_to` array of OLP RecordRefs. Proposal compatibility does not
create acceptance, assent, agreement, authority, or a protected side effect.

The human product listing profile currently defines only the seller `action/sell` semantic.
M17.1T therefore does **not** invent `ACTION_BUY` or another universal buyer taxonomy. It
reuses the already-reviewed M74 buyer/request primitive: buyer principal, explicit subject,
caller-supplied absolute action URI, and empty core terms.

## Layering

`marketplace.application.proposal.BuyerRequestProposalDraft` is protocol/transport neutral.
It validates four primitive fields only:

- `buyer_principal` — bounded absolute URI;
- `subject_uri` — bounded absolute URI;
- `action_uri` — bounded caller-supplied absolute URI;
- `parent_record_id` — non-empty exact UTF-8 text within the existing 512-character
  application path bound.

The application layer does not parse OLP Record Identity text and imports no OLP/reference,
database, network, filesystem, process, browser, or mobile stack. A fresh exact draft is
reconstructed before reference materialization so deliberate rebinding of a frozen instance
cannot bypass validation.

`marketplace.reference.proposal_v1.build_buyer_request_proposal_record(...)` is the explicit
OLP-dependent adapter. It authoritatively decodes the parent as canonical `record` identity,
constructs exactly one `EvidenceRefV1`, creates one `MarketIntentV1` with exact core/proposal
profiles and singleton `response_to`, and runs the existing Marketplace validator before
returning the Record.

Invalid draft, parent identity, or record materialization produces bounded non-reflective
errors. No input/provider exception text is surfaced by the adapter.

## Non-authority boundary

The structured record is a buyer/request Proposal only. This milestone does not establish a
price, order, inventory reservation, acceptance, agreement, ownership transfer, payment,
settlement, fulfillment, ranking, legitimacy, or authorization. It does not infer the
subject from the parent or fetch parent content; exact parent/subject consistency remains a
higher application/UI concern for a later reviewed slice.

The existing raw `POST /api/intents/{id}/responses` route and raw Web/Android response forms
remain unchanged. A later milestone may compose this builder through the existing
`respond_to_intent(...)` API after separate review.

## Capability and execution boundary

M17.1T is MODERATE source-only work under issue #221. It adds no live PostgreSQL/Psycopg
execution, dependency installation, server/socket activation, browser action, Android
build/runtime/sign/install, asset loading, secrets/environment loading, deployment,
service/configuration mutation, provider administration, payment, settlement, fulfillment,
or other runtime/external mutation.
