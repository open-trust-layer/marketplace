# Agreement assent loopback launch plan

## Purpose

This source-only slice binds exact loopback launch metadata to the already
reviewed inert Agreement-assent startup overlay.

Profile:

    MARKETPLACE_AGREEMENT_ASSENT_LOOPBACK_LAUNCH_PLAN_V1

It does not run a server.

## Exact graph

The launch plan requires:

- host exactly `127.0.0.1`;
- a port inside the existing reviewed Marketplace loopback range;
- one exact `MarketplaceAgreementAssentStartupComposition`.

The plan selects exactly:

    startup.agreement_asgi.asgi

as its ASGI application.

## Identity invariants

Construction fails closed unless:

- Agreement HTTP is still bound to the authenticated startup HTTP graph;
- Agreement ASGI is still bound to that same authenticated HTTP graph;
- Agreement ASGI is still bound to the exact Agreement HTTP composition;
- the selected ASGI adapter is the exact reviewed session-establishment adapter;
- its Marketplace handler is the exact Agreement-assent HTTP adapter;
- its auth handler is the exact authenticated session HTTP adapter.

Direct construction cannot substitute another ASGI object.

## Inert boundary

Creating the plan does not:

- sample a clock;
- generate credential material;
- handle a request;
- initialize the application;
- open a socket;
- start a server;
- connect to PostgreSQL;
- resolve Agreement candidates;
- create or verify assent proofs.

## Selection boundary

This plan is additive. It does not modify the existing authenticated launch
plan or foreground runtime seam.

A later source slice may add a dedicated Agreement-assent foreground execution
seam that accepts only this exact plan. Even that source seam would remain
inactive until separately invoked with the existing explicit runtime authority.

## Non-scope

No runtime activation, localhost execution, deployment, database migration,
provider administration, trust-anchor/key mutation, browser/WebCrypto
execution, Agreement signing/publication, payment, settlement, escrow,
fulfillment, ownership transfer, or public-network activity is performed or
authorized.

## Rollback

Rollback is source-only: remove this additive launch-plan module, tests, and
documentation. No external or durable state is created by plan construction.
