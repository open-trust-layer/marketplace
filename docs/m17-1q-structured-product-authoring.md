# Product M17.1Q — shared structured product-listing authoring

Parent roadmap: #175. Work item: #214.

Baseline is exact merged-green `main` `e645c2c53679afe81b6b25d1b9fd51007a2bb573`.

## Purpose

M17.1C intentionally exposes create/respond through reviewed raw record JSON until a shared backend capability can provide human-friendly authoring without duplicating Marketplace or OLP semantics in Web or Android.

M17.1Q adds the first such shared source boundary for **root product listings**. It reuses the existing M72 product-listing profile rather than creating a second listing model.

## Contract

`ProductListingAuthoringFields` carries bounded transport-neutral primitive fields. `MarketplaceProductListingAuthoringService` converts those fields into the existing exact `ProductListingDraft` and `ExactDecimal` types.

Record materialization is injected through `ProductListingRecordBuilder`. This keeps the application package independent of the reference implementation and prevents an application -> reference dependency cycle. A later composition surface may inject the already-reviewed `build_product_listing_record(...)` implementation.
The built record is never written directly. It is passed only to the existing initialized `MarketplaceApplicationApiService.create_intent(...)` path, which remains authoritative for intent classification, root-vs-response rejection, state preparation, retention, and persistence behavior.

Invalid structured fields become stable `PRODUCT_LISTING_FIELDS_INVALID`. Builder exceptions become stable `PRODUCT_LISTING_BUILD_FAILED` without provider/input-detail reflection. Existing application API failures remain unchanged.

## Deliberate first-slice boundary

M17.1Q handles only root product listings. It does not invent structured Proposal/response authoring because the repository does not yet contain an equivalent reviewed proposal builder. Raw reviewed-record response submission therefore remains unchanged.

This slice also does not yet add an HTTP route or modify Web/Android. The next transport slice can expose one shared structured endpoint and then migrate both clients onto it while retaining the existing raw-record route as the low-level reviewed path.

## Explicit non-authority

No PostgreSQL connection or migration, Psycopg import/execution, dependency installation, Uvicorn/server/socket activation, browser launch, Android build/runtime, credentials/secrets/environment loading, deployment, service/configuration mutation, provider administration, payment, settlement, or fulfillment is authorized or performed by M17.1Q.

Merge and any later runtime activation remain separate governance boundaries under Policy v1.6.
