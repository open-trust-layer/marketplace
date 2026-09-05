# M17.1W — Structured Proposal Web + Android authoring

M17.1W migrates the product-facing buyer Proposal form in both source clients onto the reviewed M17.1V structured HTTP route.

## Stacked baseline

This source slice is stacked on M17.1V PR #226 at exact head `b43a812ce1eff01394cb9e09723d1ac583f6f5a7`.

M17.1V is itself stacked on pending M17.1U PR #224. M17.1W must not merge ahead of either dependency; changed stack heads require revalidation.

## Shared structured route

`POST /api/intents/{parent_record_id}/proposals`

The product-facing clients submit exactly:

- `buyer_principal`
- `subject_uri`
- `action_uri`

The selected `parent_record_id` is path state only and is never duplicated in the JSON body.
## Client validation

Each Proposal field is caller-supplied exact text and is reviewed as a non-empty absolute URI with a 2048-byte UTF-8 bound before the structured body is sent. The complete JSON body remains subject to the existing 256 KiB client request bound.

The clients do not infer a buyer action. In particular, no universal `ACTION_BUY` is introduced; caller-supplied `action_uri` remains authoritative.

## Raw response boundary

The shared raw `/responses` route remains available and response browsing is unchanged. Android retains `MarketplaceApiClient.respondToIntent(...)` as a low-level compatibility/raw authoring surface.

The Web and Compose product-facing forms no longer require callers to materialize a complete response Record JSON themselves.

## Semantic exclusions

This slice does not introduce agreement, acceptance, assent, order, pricing derivation, payment, settlement, fulfillment, inventory mutation, ownership transfer, ranking, trust, legitimacy, or authority semantics.
## Authority boundary

M17.1W is source-only client work. There is **no browser launch**, **no Android build**, no Android runtime/sign/install, no live PostgreSQL connection, no HTTP server/socket activation, no dependency installation/download, no deployment, and no service/configuration/secrets/provider mutation.

No runtime activation is authorized or required by this milestone.

Validation is limited to source/artifact tests, JavaScript syntax checking, dependency-free repository gates, and the repository's existing disposable CI conformance workflow after publication.
