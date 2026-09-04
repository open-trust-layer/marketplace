# Product M17.1S — Web + Android structured root product-listing creation

Parent roadmap: #175. Work item: #219.

Baseline is exact merged-green `main` `91aac27b14cc20559cc3bc5a19d3d90d493429bb`.

## Purpose

M17.1R established `POST /api/product-listings` as the shared structured HTTP boundary for root product listings. M17.1S migrates both Web and Android root-create surfaces to that endpoint without creating client-side Marketplace record semantics.

Both clients expose the same 12 primitive transport fields: seller principal, subject URI, title, description, consideration coefficient/scale, currency code, quantity coefficient/scale, unit URI, and WGS84-E6 latitude/longitude.

String values are JSON-string encoded. Integer inputs remain text until canonical JSON integer-token validation, avoiding JavaScript floating-point coercion or an Android numeric-domain fork. M17.1Q/M72 remains authoritative for semantic bounds, normalization, URI/currency rules, location ranges, and record construction.

## Web

The Web create form now collects the 12 structured fields and posts only to `POST /api/product-listings`. It does not submit a raw root record or build/sign/identify an OLP record.

The existing response form remains a raw response reviewed-record boundary and continues to use `/api/intents/{id}/responses`.

## Android

The Android source adds `ProductListingInput`, a bounded structured JSON encoder, and `createProductListing(...)`. `MarketplaceState` and the Compose root-create surface use that path; the low-level raw intent API client remains available for reviewed protocol-level compatibility, while the product UI no longer uses it for root creation.

Response authoring remains raw response reviewed-record JSON. Structured Proposal/response authoring is still deferred until a shared reviewed backend builder exists.

## Parity and authority

Web and Android use the same field names and same structured endpoint. Neither client validates Marketplace semantics beyond transport shape, canonical integer-token syntax, safe JSON string escaping, and the existing request byte bound.

This is source-only client work: no browser launch, no Android build, no emulator/device runtime, no live network/server/socket activation, no PostgreSQL action, no dependency installation, no credentials/secrets, no filesystem asset activation, no deployment, no service/configuration mutation, and no provider administration.

No runtime activation is authorized by M17.1S. Merge and any later runtime validation remain separately governed by Policy v1.6.
