# M17.7M — Authenticated completion flight acceptance

Profile: `MARKETPLACE_AUTHENTICATED_COMPLETION_FLIGHT_ACCEPTANCE_V1`

Risk: **acceptance-only**. This slice adds tests and documentation, not product
runtime or authority.

## Purpose

M17.7H-L made the reviewed fulfillment-completion path reachable from the
explicit localhost runtime and active authenticated Web surface.

M17.7M adds one integrated acceptance checkpoint over that merged path.

## What the acceptance proves

The acceptance test constructs the final reviewed
`MarketplaceSessionEstablishmentAsgiHttpAdapter` with the exact authenticated
fulfillment HTTP adapter beneath it and sends a canonical Bearer-authenticated
request through the ASGI boundary.

For the exact route:

`POST /api/agreements/{agreement_record_id}/commitments/seller-delivery/completion-evidence`

with exact body:

```json
{"evidence_kind":"CLAIMED_COMPLETE_PERFORMANCE"}
```

the acceptance requires:

- the Bearer token to resolve through the reviewed session transport;
- the authenticated principal to be the only fulfillment issuer;
- the Agreement Record Identity and commitment id to remain request-bound;
- exactly one claimed-complete publication call;
- a bounded immutable-style response containing only publication metadata;
- HTTP 201 for a newly stored event.

## Zero-publication failure cases

The same final ASGI path must produce zero fulfillment publication when:

- authentication is absent; or
- the caller attempts to inject an issuer/authority field into the request.

## Agreement publication continuity

The final fulfillment adapter overlays the existing Agreement-publication
adapter.

M17.7M proves a non-completion Agreement-publication path still delegates
unchanged through that same final adapter with the parsed session token, invalid
flag, and reviewed clock value.

This guards against completion support accidentally shadowing or replacing the
existing Agreement path.

## Active Web contract

The acceptance also locks the merged page behavior:

- **Publish Agreement** is an explicit button;
- **Claim delivery complete** is a separate explicit button;
- rendering never calls either write client;
- each click path invokes its reviewed client exactly once;
- completion remains fixed to commitment `seller-delivery`;
- completion remains fixed to evidence kind
  `CLAIMED_COMPLETE_PERFORMANCE`;
- the exact listing seller must match the authenticated principal before the
  completion button becomes actionable.

## Runtime/module delivery contract

The acceptance locks:

- reviewed Agreement-publication and fulfillment-completion Web modules in the
  authenticated bootstrap;
- the exact authenticated session route allowlist for both paths;
- static delivery of both modules through the reviewed site host;
- explicit localhost fulfillment runtime selection through
  `--execute-fulfillment-completion-localhost`;
- the exact execution opt-in
  `EXECUTE_FULFILLMENT_COMPLETION_AUTHENTICATED_MARKETPLACE_LOCALHOST_V1`.

## Semantic boundary

Completion remains **seller-attributed evidence only**.

It does not establish universal truth, buyer acceptance, payment, settlement,
legal effect, or absence of dispute.

## Non-authority

M17.7M adds:

- no new HTTP route;
- no runtime selection;
- no browser automation dependency;
- no socket execution;
- no database initialization;
- no credential or signing authority;
- no background or automatic completion;
- no public-network exposure;
- no deployment;
- no payment or settlement authority;
- no production-health claim.

## Rollback

**acceptance-only rollback:** revert the exact M17.7M merge.

No runtime state, database schema, external system, payment, settlement, or
deployment rollback is involved.
