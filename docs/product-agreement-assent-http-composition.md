# Product Agreement assent HTTP composition

## Purpose

This source-only slice composes the reviewed authenticated Agreement-assent HTTP
adapter over the exact existing authenticated Marketplace HTTP object graph.

Profile:

    MARKETPLACE_AGREEMENT_ASSENT_HTTP_COMPOSITION_V1

The composition is inert. It creates Python objects only.

## Shared authentication invariant

The Agreement-assent adapter receives the same exact authentication graph used
by MarketplaceAuthenticatedHttpComposition.

In particular:

- its base adapter is the exact existing authenticated application HTTP adapter;
- its auth service is the exact existing authentication.auth_service instance;
- candidate resolution is the exact reviewed injected resolver;
- workflow is the exact reviewed injected Agreement-assent workflow;
- signing-input encoder and signature decoder are injected callables only.

The composition does not create, clone, replace, or independently configure an
authentication service.

## No activation

This slice performs no ASGI selection, no site-host selection, no static asset
delivery, and no runtime selection. There is no browser activation.

The new composition is not referenced by launch/runtime entry points or active
Web entry points.

## Capability boundary

Composition performs no:

- HTTP or network I/O;
- credential generation;
- challenge/session material generation;
- filesystem/environment configuration;
- PostgreSQL connection or schema mutation;
- Agreement proof signing;
- Agreement publication;
- payment, settlement, escrow, fulfillment, or ownership transfer;
- background task creation;
- deployment.

The existing HTTP adapter still owns all request-time authentication, exact
candidate binding, signature verification, and coordination behavior.

## Rollback

Rollback is source-only rollback: revert this additive slice. There is no
persistent state, runtime selection, or external side effect to undo.
