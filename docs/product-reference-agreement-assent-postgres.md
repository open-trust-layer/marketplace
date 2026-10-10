# Reference Agreement assent PostgreSQL selection

## Purpose

This source-only slice selects the existing bounded PostgreSQL Agreement-assent
coordination store into the reviewed reference Agreement launch graph.

Profile:

    MARKETPLACE_REFERENCE_AGREEMENT_ASSENT_POSTGRES_V1

The store is constructed but remains uninitialized.

## Exact inputs

The builder accepts:

- one authenticated Marketplace loopback launch plan;
- one injected PostgreSQL connection factory;
- one injected aware-datetime clock.

The provider callables are retained by
PostgresAgreementAssentCoordinationStore but are not invoked during composition.

## Exact store selection

The builder constructs exactly one
PostgresAgreementAssentCoordinationStore with the supplied provider callables.

That exact store is passed into
build_reference_agreement_assent_launch and is retained by the exact Agreement
coordination service.

## No initialization

The source path does not call:

- store.initialize();
- store.apply_migrations();
- the connection factory;
- the store clock;
- put/peek/list/expiry operations.

Therefore constructing this reference graph does not connect to PostgreSQL,
create tables/indexes, apply migrations, expire records, or retain Agreement
assent evidence.

## Lifecycle boundary

A later source slice may define an explicit coordination initialization step
before foreground execution.

Actual initialization would be a database/runtime mutation and remains a
separate authority. This PR does not perform or authorize that mutation.

## Non-scope

No runtime activation, localhost execution, deployment, database migration,
provider administration, trust/key mutation, browser/WebCrypto execution,
Agreement signing/publication, payment, settlement, escrow, fulfillment,
ownership transfer, or public-network activity is performed or authorized.

## Rollback

Rollback is source-only: remove this additive PostgreSQL selection module,
tests, and documentation. No external or durable state is created by
composition.
