# Product M17.1R - shared structured product-listing HTTP endpoint

Parent roadmap: #175. Work item: #216.

Baseline is exact merged-green `main` `9b1d32598972c4414db868d3d255ac19f340bb6d`.

## Purpose

M17.1Q established one transport-neutral structured root product-listing authoring service. M17.1R exposes that exact application capability through the existing framework-neutral HTTP adapter without moving Marketplace or OLP record construction into Web or Android.

The reviewed route is:

```text
POST /api/product-listings
Content-Type: application/json
```

The existing low-level `POST /api/intents` reviewed-record route remains unchanged.

## Transport contract

The request body is one exact JSON object with these members:

```text
seller_principal
subject_uri
title
description
consideration_coefficient
consideration_scale
currency_code
quantity_coefficient
quantity_scale
unit_uri
latitude_e6
longitude_e6
```
String members must be exact JSON strings. Decimal coefficient/scale and WGS84-E6 members must be exact JSON integers; JSON booleans are rejected as integers. Duplicate, unknown, missing, malformed, BOM-prefixed, non-object, oversized, query-bearing, or non-`application/json` requests fail before authoring.

Transport validation does not duplicate M72 listing semantics. After exact shape/type checking, the adapter creates `ProductListingAuthoringFields` and delegates once to the M17.1Q creator. M17.1Q/M72 remain authoritative for field bounds and record construction.

## Stable failure boundary

Malformed JSON uses `INVALID_JSON_BODY`. Exact-member/type failures use `PRODUCT_LISTING_REQUEST_INVALID`. Reviewed M17.1Q failures keep `PRODUCT_LISTING_FIELDS_INVALID` or `PRODUCT_LISTING_BUILD_FAILED` without reflecting caller/provider detail. Existing `ApplicationApiError` mappings remain authoritative for application failures.

Successful creation returns the existing bounded write receipt shape:

```json
{"change_seq": 1, "disposition": "STORED"}
```

## Composition

`compose_marketplace_application(...)` now receives an injected `ProductListingRecordBuilder`, constructs one `MarketplaceProductListingAuthoringService` over the same application API, and gives only its `create_product_listing` callable to the HTTP adapter. The application package does not import the reference implementation.

`MarketplaceApplicationComposition` exposes the inert authoring service alongside state, API, HTTP and site surfaces. The launch-plan builder only carries the injected record builder into this inert graph; it does not initialize or activate runtime authority.

## Deferred client slice

M17.1R deliberately does not modify `web/**` or `android/**`. The next client slice can migrate both clients to `POST /api/product-listings` using human fields while retaining raw reviewed-record submission as the low-level path.

## Explicit non-authority

No live PostgreSQL connection or migration, Psycopg execution, dependency installation, Uvicorn/server/socket activation, browser launch, Android build/runtime/sign/install, filesystem asset loading, credentials/secrets/environment loading, deployment, service/configuration mutation, provider administration, payment, settlement, fulfillment, or structured Proposal/response authoring is authorized or performed by M17.1R.

Merge and every later runtime/activation boundary remain separately governed by Policy v1.6.
