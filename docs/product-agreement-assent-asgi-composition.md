# Agreement assent authenticated ASGI composition

## Purpose

This source-only slice selects the already-reviewed Agreement-assent HTTP
overlay into one authenticated ASGI object graph.

Profile:

    MARKETPLACE_AGREEMENT_ASSENT_ASGI_COMPOSITION_V1

The composition remains inert. It creates Python objects only and does not
activate localhost or any server provider.

## Exact graph

The composer requires three exact reviewed objects:

- one MarketplaceAuthenticatedHttpComposition;
- one MarketplaceAgreementAssentHttpComposition built over that exact HTTP graph;
- one MarketplaceAuthenticationRuntimeInputs object whose material source is
  already bound to the authenticated session HTTP composition.

It then creates one MarketplaceSessionEstablishmentAsgiHttpAdapter with:

- the exact existing site host;
- the exact Agreement-assent HTTP overlay as marketplace_http;
- the exact existing authentication-session HTTP adapter;
- the exact reviewed runtime clock.

The Agreement overlay itself delegates non-Agreement Marketplace API routes to
the exact authenticated application HTTP adapter it already wraps.

## Session ASGI type boundary

MarketplaceSessionEstablishmentAsgiHttpAdapter now accepts exactly either:

- MarketplaceAuthenticatedApplicationHttpAdapter; or
- MarketplaceAuthenticatedAgreementAssentHttpAdapter.

Arbitrary duck-typed HTTP handlers remain rejected.

This is a nominal widening only for the reviewed Agreement overlay.

## Identity / material invariants

Composition fails closed unless:

- agreement_http.authenticated_http is the exact supplied authenticated_http;
- challenge generation is bound to runtime_inputs.material_source;
- session-token generation is bound to the same material source;
- the resulting ASGI clock is bound to runtime_inputs.clock;
- the resulting ASGI Marketplace handler is the exact Agreement overlay.

## No activation

This slice does not modify authenticated startup composition, launch plans,
runtime-server validation, or the localhost bootstrap.

Therefore normal authenticated localhost continues to select the pre-existing
authenticated application HTTP adapter until a later explicitly reviewed source
slice selects this Agreement ASGI composition.

No request is handled during composition.

## Capability boundary

This source change performs no:

- Agreement preparation, signing, submission, or publication;
- credential/challenge/session generation;
- browser/WebCrypto operation;
- database connection or migration;
- filesystem/environment access;
- socket/server execution;
- deployment;
- payment, settlement, escrow, fulfillment, or ownership transfer.

## Rollback

Rollback is source-only: remove the Agreement ASGI composition and restore the
session ASGI constructor to its prior single reviewed Marketplace HTTP type.
No persistent or external state is created by this composition.
