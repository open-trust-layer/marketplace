# M17.7C — Authenticated fulfillment completion HTTP seam

Profile: `MARKETPLACE_AUTHENTICATED_FULFILLMENT_COMPLETION_HTTP_V1`

Risk: **MODERATE application-state write**, source-only and unselected.

## Purpose

M17.7A authors three exact immutable fulfillment-completion evidence records.
M17.7B resolves one exact Agreement, builds one of those records, re-binds it to
the requested Agreement and commitment, derives its Record Identity, and
publishes it through the shared application-state service.

M17.7C adds only the authenticated HTTP seam over that reviewed M17.7B service.

It does **not** activate the route in any runtime, startup graph, Web bootstrap,
Android client, provider, or public listener.

## Exact route

`POST /api/agreements/{agreement_record_id}/commitments/{commitment_id}/completion-evidence`

The JSON body is exact and contains only:

```json
{"evidence_kind":"CLAIMED_COMPLETE_PERFORMANCE"}
```

The exact reviewed `evidence_kind` values are:

- `CLAIMED_COMPLETE_PERFORMANCE`
- `COMMITMENT_ACCEPTANCE`
- `COMMITMENT_COMPLETION`

No caller-supplied issuer, principal, verification method, public key,
authorization claim, trust claim, outcome, target, Record Identity, disposition,
or change sequence is accepted.

## Authority flow

The adapter:

1. validates the exact route, method, query absence, content type, and request shape;
2. requires the existing Marketplace application session;
3. validates that session without deriving authority from request data;
4. derives the evidence issuer only from the validated session principal;
5. touches the same session before the application-state write;
6. invokes exactly one reviewed M17.7B publication method selected by the exact evidence kind;
7. requires the returned Agreement identity, commitment id, and evidence kind to re-bind to the exact request;
8. returns only immutable publication metadata already produced by M17.7B.

The transport layer does not create a second issuer or authorization system.

For claimed-complete performance, the M17.7A builder still requires the issuer
to equal the targeted commitment party principal. M17.7C does not weaken that
rule.

For acceptance and completion assertions, M17.7C preserves M17.7A semantics:
the authenticated principal authors attributable evidence. The route does not
claim that the statement is universally true, legally authoritative, undisputed,
or sufficient for payment or settlement.

## Response

A successful response contains only:

- `record_id`
- `agreement_record_id`
- `commitment_id`
- `evidence_kind`
- `disposition`
- `change_seq`

`201 Created` is used for `STORED`; an idempotent/non-new disposition uses
`200 OK`.

## Fail-closed boundary

Malformed requests, unsupported evidence kinds, invalid sessions, missing or
unavailable Agreements, evidence-builder failure, target re-binding failure,
identity derivation failure, invalid service result, and state-write failure do
not produce a successful HTTP response.

The adapter delegates all non-M17.7C paths unchanged to the existing
authenticated Agreement-publication adapter.

## Explicit non-authority

This slice performs no runtime/startup/provider selection, socket binding,
public-network exposure, production PostgreSQL activation, filesystem/environment
configuration intake, key generation/import/export, signing, browser WebCrypto,
Android action, fulfillment evaluation, payment, settlement, deployment,
publishing/distribution, or production-health claim.

It does not change the deterministic MVP flight.

## Next product boundary

After M17.7C is merged green, a later reviewed slice may select this exact seam
inside the local authenticated composition and then expose an explicit Web
completion control. Runtime selection and Web UX remain separate gates.

## Rollback

Revert the exact M17.7C merge.

Because the adapter and composition remain unselected, rollback requires no
runtime restart, data cleanup, database migration, credential rollback,
browser/device cleanup, or deployment rollback.
