# Reference authenticated launch: Proposal acceptance resolution selection

## Purpose

Select the already-reviewed deterministic Proposal-acceptance resolver inside
the inert authenticated reference launch graph.

The authenticated browser now has an explicit read-only acceptance-resolution
action. The server-side authenticated HTTP composition already accepts an exact
`MarketplaceProposalAcceptanceResolutionService`, but without this reference
selection the normal authenticated PostgreSQL launch graph would leave that
capability unconfigured.

This slice closes only that composition gap.

## Exact construction

`build_reference_authenticated_marketplace_launch_plan(...)` now constructs
one exact `MarketplaceProposalAcceptanceResolutionService` from the same reviewed application state and reference semantics already used by Proposal
acceptance publication:

- application state: `application_plan.composition.state`;
- Proposal predicate: `is_marketplace_proposal_record`;
- Proposal parent extraction: `marketplace_response_parent_ids`;
- product Listing extraction: `extract_product_listing`;
- record issuer extraction: `marketplace_record_issuer_principal`;
- canonical acceptance builder: `build_proposal_acceptance_record`;
- acceptance-to-Proposal extraction: `proposal_acceptance_proposal_id`;
- canonical acceptance identity: `proposal_acceptance_record_id`.

The exact resolver object is then passed once to
`compose_marketplace_authenticated_startup(...)`.

## Shared-state invariant

The seller acceptance authoring service and the read-only acceptance resolver
share the exact same `MarketplaceApplicationStateService` instance.

This prevents a launch graph where publication and later resolution accidentally
observe different application-state stores.

## Inert composition boundary

Construction does not call `resolve(...)`, `peek(...)`, initialize the
application, open PostgreSQL connections, read environment/filesystem data,
generate authentication material, start a server, or execute browser code.

The source change only selects an already-reviewed capability into the inert
reference composition.

## Runtime boundary

This PR does not execute authenticated localhost and does not authorize runtime
activation.

If this source is later merged and a separately authorized authenticated
localhost run is performed, the existing reference launch will then provide the
resolver required by the authenticated GET route.

No deployment, provider mutation, database migration, trust-anchor mutation,
key generation, Agreement signing, Agreement publication, payment, settlement,
escrow, fulfillment, or public-network activity is authorized by this source
slice.

## Rollback

Rollback is source-only: remove resolver construction and the startup injection.
No external or durable state is created by this composition selection.
