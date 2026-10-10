# Reference Agreement assent launch selection

## Purpose

This source-only slice selects the reviewed reference Agreement service graph
into the already-reviewed Agreement HTTP/ASGI/startup/loopback launch layers.

Profile:

    MARKETPLACE_REFERENCE_AGREEMENT_ASSENT_LAUNCH_V1

The result is still inert launch metadata. It does not execute a server.

## Exact input

The builder requires:

- one exact MarketplaceAuthenticatedLoopbackLaunchPlan;
- one injected reviewed AgreementAssentCoordinationStore.

It derives the exact existing:

- authenticated startup;
- Marketplace application object;
- authentication runtime-input object.

No replacement auth graph is created.

## Service selection

The builder first creates
MarketplaceReferenceAgreementAssentServices over the exact authenticated
application/startup graph.

That pins the reviewed candidate, proof, coordination, retained-proof
re-verification, and formation semantics.

The coordination service remains uninitialized.

## HTTP and ASGI selection

The exact reference OJVE carriers are selected:

- encode_agreement_assent_signing_input;
- decode_agreement_assent_signature.

The service graph is then passed into
compose_marketplace_agreement_assent_startup using the exact runtime-input
object already bound to authenticated startup.

Finally the exact authenticated host/port are copied into
build_marketplace_agreement_assent_loopback_launch_plan.

## Identity invariants

The result fails closed unless:

- all Agreement services are bound to the exact authenticated startup;
- Agreement HTTP uses the exact reference candidate resolver/workflow;
- the Agreement launch plan uses the exact Agreement startup;
- host and port match the authenticated launch plan exactly;
- the selected ASGI object is the exact Agreement ASGI object;
- coordination remains uninitialized.

## Inert boundary

Construction does not initialize the coordination store, consume its clock,
apply PostgreSQL migrations, handle HTTP, initialize the Marketplace
application, open a socket, inspect a server provider, or invoke the Agreement
foreground runtime seam.

## Next boundary

A later source slice may choose a concrete reviewed coordination store, such as
the existing PostgreSQL store, and define an explicit initialization lifecycle.

Actual database migration/initialization and foreground server invocation remain
separate runtime authorities.

## Non-scope

No runtime activation, localhost execution, deployment, database migration,
provider administration, trust/key mutation, browser/WebCrypto execution,
Agreement signing/publication, payment, settlement, escrow, fulfillment,
ownership transfer, or public-network activity is performed or authorized.

## Rollback

Rollback is source-only: remove this additive reference launch selection module,
tests, and documentation. No external or durable state is created.
