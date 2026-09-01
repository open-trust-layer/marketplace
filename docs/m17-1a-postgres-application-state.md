# Product M17.1A — PostgreSQL Application State Foundation

## Scope

M17.1A introduces the first durable Marketplace application-state boundary above the existing OLP and Marketplace semantic layers. PostgreSQL is the authoritative shared application database for Web, Android, and future agent clients. This milestone does not redesign OLP, invent a second MarketIntent model, or turn database rows into protocol truth.

The implementation remains connection-injected and source-level only. It does not open a live database connection, choose a database host, provision PostgreSQL, deploy a server, or migrate real-user data.

## Retention profile

The authorized content-retention class is `MARKETPLACE_APPLICATION_STATE_MVP`.

Validated user-authored Marketplace records and the minimum coordination rows needed to browse, respond, and synchronize may remain for at most **30 days** after their last legitimate application use. Reads or writes refresh retention only for records actually used by the operation. Expired local copies are deleted through explicit retention maintenance; deletion failure is surfaced as a stable retention/security error and must never silently become indefinite retention.

Removing a local application copy is not deletion of the underlying protocol record from the world. Operational logs and telemetry must remain content-free under the existing metadata policy.

## Canonical records and identity

The PostgreSQL adapter accepts only `PreparedApplicationRecord` values produced after the existing Marketplace validation, exact OLP Record Identity derivation, and canonical serialization boundary has succeeded. The adapter stores the exact canonical bytes under that exact Record Identity. A conflicting byte sequence for an existing identity fails closed as an identity collision.

No mutable application column may override the immutable Marketplace record. Application indexes exist only to make local coordination/querying efficient.

## Responses remain Proposals

A user response is not a new protocol-level `Response` object. It remains a genuine Proposal `MarketIntentV1` using the existing `proposal-v1` profile and `response_to` references. `marketplace_app_response_links` is only an application index over those already-validated references.

Proposal compatibility, indexing, display order, or local discovery does not create agreement, acceptance, authority, ownership, legitimacy, or ranking.

## Application sync cursor

`marketplace_app_changes` provides a monotonic local application sync cursor for future `/api/sync` clients. The cursor orders local coordination changes only. It is **not protocol truth**, does not claim global completeness, and does not replace OLP/federation lifecycle or discovery semantics.

When retained sync metadata eventually expires, the application sync floor must advance so stale cursors fail closed and clients can perform a bounded full resynchronization rather than silently missing history.

## PostgreSQL schema and migrations

Migration v1 creates:

- `marketplace_app_schema_migrations`;
- `marketplace_app_records` with canonical `BYTEA` content and retention timestamps;
- `marketplace_app_response_links` with cascade cleanup tied only to the locally stored response copy;
- `marketplace_app_changes` with a PostgreSQL identity sequence;
- `marketplace_app_sync_state` for the retained sync floor; and
- bounded indexes for expiry and response lookup.

Migrations run inside one transaction and fail closed on unknown schema versions or database errors. No migration is executed automatically by importing the package.

## Dependency boundary

The base `open-layer-marketplace` package keeps `dependencies = []`. PostgreSQL support is explicitly allowlisted as the optional extra `postgres = ["psycopg[binary]==3.3.5"]` so protocol/runtime consumers do not inherit database authority or native client dependencies merely by importing Marketplace.

The packaged M17.1A source itself does not import Psycopg, open sockets, parse DSNs, choose hosts, create pools, or provision a database. A future composition/deployment layer may supply a reviewed DB-API connection factory after separate runtime/deployment authorization.

## Safety and authority boundaries

M17.1A authorizes source-level PostgreSQL persistence capability and deterministic connection-injected tests only. It grants **no live database** provisioning or administration, no production deployment, no external client traffic, no browser/mobile execution, no credential issuance, and no payment, settlement, fulfillment, or other protected side effect.

The existing 10-second EPHEMERAL runtime remains unchanged for runtime components that have not explicitly adopted this application-state profile.

## Acceptance

M17.1A is acceptable only when existing Marketplace conformance remains green, PostgreSQL migration/repository/service contracts are deterministic, collision and transaction failures fail closed, retention expiry/deletion is observable, Proposal `response_to` semantics are preserved, the application sync cursor makes no global-truth claim, and dependency/artifact gates allow only the reviewed PostgreSQL provider rather than arbitrary package-index dependencies.