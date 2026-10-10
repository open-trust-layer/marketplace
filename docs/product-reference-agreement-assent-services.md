# Reference Agreement assent service graph

## Purpose

This source-only slice composes the reviewed Agreement candidate, proof,
coordination, formation, and workflow services over one exact Marketplace
application/authentication graph.

Profile:

    MARKETPLACE_REFERENCE_AGREEMENT_ASSENT_SERVICES_V1

It deliberately leaves the injected coordination store uninitialized.

## Exact inputs

The builder requires:

- one exact MarketplaceApplicationComposition;
- one exact MarketplaceAuthenticatedStartupComposition whose HTTP application
  is that same application object;
- one injected AgreementAssentCoordinationStore with the reviewed retention
  class, bounded retention window, and required store methods.

No PostgreSQL provider is selected here.

## Exact reference semantics

The graph pins:

- build_product_agreement_candidate;
- agreement_candidate_record_id;
- build_product_agreement_assent_signing_input;
- build_verified_product_agreement_assent_proof;
- build_prepared_product_agreement_assent;
- reverify_prepared_product_agreement_assent;
- build_product_agreement_formation_evidence_from_verified_assent;
- evaluate_product_agreement_formation.

Candidate resolution reads the exact existing application state and delegates
candidate construction to the exact candidate-authoring service.

Proof and formation re-verification both reuse the exact immutable verification
method snapshot from the authenticated startup.

## Coordination boundary

The injected coordination store is retained by a
MarketplaceAgreementAssentCoordinationService, but this composition does not
call initialize(), put(), peek(), list_for_agreement(), or expire_due().

The resulting coordination service remains explicitly uninitialized.

This means constructing the graph does not apply PostgreSQL migrations, consume
the coordination clock, expire evidence, create assent evidence, or mutate
durable state.

## Runtime boundary

This slice does not compose HTTP/ASGI, build a launch plan, invoke the
Agreement-assent runtime seam, initialize the application, start a socket, or
execute localhost.

A later source slice may select this exact service graph into the already
reviewed Agreement startup overlay. Coordination initialization remains a
separate explicit lifecycle step.

## Non-scope

No runtime activation, deployment, database migration, provider administration,
trust/key mutation, browser/WebCrypto execution, Agreement signing/publication,
payment, settlement, escrow, fulfillment, ownership transfer, or public-network
activity is performed or authorized.

## Rollback

Rollback is source-only: remove this additive reference composition module,
tests, and documentation. No external or durable state is created by
composition.
