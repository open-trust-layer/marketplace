# Product Agreement assent PostgreSQL coordination store

## Purpose

This source-only slice adds a bounded PostgreSQL adapter for the Agreement
assent coordination semantics frozen by the preceding application/reference
slices.

Construction is inert. The adapter receives an injected DB-API connection
factory and clock. This slice does not connect to PostgreSQL, apply a schema,
load configuration, select a provider, or activate any runtime service.

## Separate schema

The adapter deliberately does not reuse marketplace_app_records and does not
extend the application-state migration registry.

It defines separate relations:

- marketplace_agreement_assent_schema_migrations
- marketplace_agreement_assent_evidence
- marketplace_agreement_assent_expires_idx

The stored value is not a Marketplace RecordV1.

The logical primary key is the exact pair:

    agreement_record_id, principal

Stored public coordination material is limited to:

- exact Agreement Record Identity;
- exact principal;
- exact verification-method URI;
- exact 32-byte Proof Identity;
- bounded canonical proof bytes;
- accepted timestamp;
- absolute expiry timestamp.

No private key, CryptoKey serialization, session token, challenge, password,
caller-supplied trust decision, or unrelated request payload is stored.

## Retention

Profile:

    MARKETPLACE_AGREEMENT_ASSENT_COORDINATION_MVP

The absolute lifetime is at most 30 days from accepted insertion.

Reads:

- filter expired rows;
- never refresh retention;
- never perform hidden expiry deletion.

Cleanup occurs only on:

- explicit store initialization;
- explicit expire_due;
- bounded write maintenance.

Duplicate evidence preserves the original accepted and expiry timestamps and
does not extend lifetime.

Conflicting evidence for the same Agreement/principal fails closed.

## Capacity and concurrency

The first profile remains bounded to at most 4096 active coordination entries.

A put operation takes a PostgreSQL SHARE ROW EXCLUSIVE table lock for the
bounded write transaction, performs bounded expiry maintenance, removes an
expired row for the exact target key if necessary, then checks
duplicate/collision/capacity before insertion.

The coarse write lock is intentional for this small MVP coordination profile.
It avoids a count/insert race without introducing advisory-lock or provider-
specific concurrency semantics.

Reads do not take this write lock.

## Migration boundary

The migration is additive and separate. It is applied only if an operator later
calls the store migration or initialization path.

This source slice does not call that path and does not alter any live database.

If later activated, migration execution remains a separate HIGH-risk runtime
action with exact-target verification, backup/recovery planning, and rollback
authorization.

## Trust boundary

The PostgreSQL adapter stores PreparedAgreementAssent only.

It does not:

- create proofs;
- verify signatures;
- establish principal attribution;
- resolve verification methods;
- decide formation sufficiency;
- publish Agreements.

Persisted or decoded proof bytes do not become trusted simply because they were
stored. Before #360 formation evaluation, a later aggregation boundary must
reverify the proof against the exact Agreement candidate, current trusted
verification-method evidence, and principal/controller attribution policy.

Persistence is coordination, not truth.

## Errors and rollback

Database/provider details are not reflected through public errors.

Write, read, migration, and cleanup transactions fail closed and attempt
rollback. Rollback failure is itself surfaced as a stable error.

Source rollback is a normal git revert because this slice performs no migration.

A later live schema rollback, if ever needed after activation, is a separate
operator procedure and must account for retained public proof evidence before
dropping the dedicated table.

## Explicit non-scope

No reference composition change, no application launch-plan wiring, no DSN or
credential handling, no filesystem/environment configuration, no HTTP route,
no browser activation, no background job, no live PostgreSQL action, no
Agreement publication, no payment/settlement/fulfillment, and no deployment.
