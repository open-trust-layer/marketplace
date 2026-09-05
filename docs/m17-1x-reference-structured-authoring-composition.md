# M17.1X reference structured authoring composition

M17.1X closes the source-composition gap left after M17.1W by adding one **reference-layer inert factory** that binds the existing structured application authoring services to the **genuine OLP reference builders** already reviewed for Product Listings and Proposals.

## Composition boundary

`build_reference_marketplace_application_launch_plan(...)` delegates to the existing application-layer `build_marketplace_application_launch_plan(...)` and fixes only two dependencies:

- Product Listing materialization uses `build_product_listing_record`;
- Proposal materialization uses `build_buyer_request_proposal_record`.

Persistence, intent querying, canonical record preparation/decoding, raw-record JSON codecs, loopback host/port metadata, and Web asset bytes remain explicit caller-supplied dependencies. The reference factory does not invent configuration, persistence, transport, identity, or business semantics.

The dependency direction remains one-way: the reference layer may compose application contracts, while application modules do not import `marketplace.reference`.

## Semantic boundary

The existing reviewed semantics remain unchanged:

- Product Listings remain genuine `MarketIntentV1` records under the reviewed `product-listing-v1` profile and sell action;
- Proposals remain genuine `MarketIntentV1` records under `proposal-v1` with exact `response_to` binding and a caller-supplied action URI;
- raw `/api/intents` and `/api/intents/{parent}/responses` compatibility surfaces remain unchanged;
- Proposal compatibility is not acceptance, assent, agreement formation, payment authority, fulfillment, ownership transfer, ranking, trust, legitimacy, or authorization.

## Authority boundary

This milestone grants **no runtime activation** and performs **no PostgreSQL connection**, migration, provisioning, or administration. It performs **no filesystem asset loading**, environment or secret loading, socket bind/listen/accept, HTTP server execution, browser action, Android build/runtime/sign/install, dependency installation, provider selection, deployment, service/configuration mutation, or external side effect.

The factory returns the same inert launch-plan object already reviewed by M17.1M–O. Initialization and foreground execution remain separate explicit boundaries. A merge remains a separate exact-head governance boundary.

## Validation

Focused tests prove that the factory binds the exact reviewed Product Listing and Proposal builder function objects and, in the pinned-OLP CI environment, that structured authoring materializes genuine `RecordV1` values with exact Proposal parent binding. Artifact tests preserve the application-to-reference dependency boundary and reject runtime-resource selection in this module.