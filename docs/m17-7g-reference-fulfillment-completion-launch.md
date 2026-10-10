# M17.7G — Reference fulfillment completion launch composition

Profile: `MARKETPLACE_REFERENCE_FULFILLMENT_COMPLETION_LAUNCH_V1`

Risk: **MODERATE reference composition**, source-only and inert.

## Purpose

M17.7B-F define the reviewed fulfillment-completion publication, authenticated
HTTP, session-aware ASGI, startup, and loopback launch boundaries.

M17.7G composes those exact boundaries from one existing reference
Agreement-assent PostgreSQL graph. It prevents the localhost bootstrap from
reconstructing fulfillment services ad hoc.

## Exact input

The builder accepts one exact
`MarketplaceReferenceAgreementAssentPostgres`.

From that graph it reuses only:

- the exact Marketplace application-state service;
- the exact Agreement-assent startup;
- the exact authentication runtime inputs;
- the exact Agreement-assent loopback host and port.

It performs no environment, filesystem, database, socket, provider, or clock
selection.

## Exact service graph

M17.7G constructs:

1. one Agreement publication preflight service using the reviewed
   `agreement_candidate_record_id`;
2. one Agreement publication service over the exact existing application state;
3. one M17.7B fulfillment publication service over that same state using only
   the M17.7A reference builders, target extractor, and pinned OLP
   `record_identity_text`;
4. one exact M17.7E startup composition;
5. one exact M17.7F loopback launch plan.

The returned value freezes object identity across the Agreement graph,
application state, publication services, startup, loopback host/port, and final
session-aware ASGI value.

## Inert boundary

Construction performs:

- zero database initialization;
- zero Agreement-assent coordination initialization;
- zero request handling;
- zero Agreement or fulfillment publication;
- zero provider/server execution;
- zero socket creation or binding;
- zero filesystem/environment intake;
- zero credential generation or signing;
- zero clock reads.

## Non-selection

Existing localhost execution, runtime-server, Web, Android, and deterministic
MVP entry points remain unchanged and do not select M17.7G.

The fulfillment route remains unreachable from an executing process solely
because this reference composition exists.

## Explicit non-authority

No production PostgreSQL activation, public-network exposure, browser/Web
activation, Android action, fulfillment evaluation, payment, settlement,
deployment, publishing/distribution, or production-health claim is added.

## Next boundary

A later reviewed slice may let the explicit localhost bootstrap build this exact
reference object and execute its loopback-only plan behind a new exact
mode-specific opt-in.

## Rollback

**source-only rollback:** revert the exact M17.7G merge.
