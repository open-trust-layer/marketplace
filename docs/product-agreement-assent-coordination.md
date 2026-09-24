# Product Agreement assent coordination semantics

## Purpose

This slice freezes bounded coordination rules for already-verified Agreement
assent evidence before any PostgreSQL schema is added.

The memory store in this slice is a deterministic reference model. It is not a
durability claim and is not selected by the current runtime.

## Retention profile

Profile:

    MARKETPLACE_AGREEMENT_ASSENT_COORDINATION_MVP

The first profile allows an absolute lifetime of at most 30 days from accepted
insertion.

Reads do not extend retention. Reads also do not delete expired evidence.
Cleanup occurs only at reviewed mutation/maintenance boundaries:

- initialization;
- put;
- explicit expire_due.

A duplicate does not extend the original accepted_at or expires_at values.

## Key and collision rule

Logical key:

    (agreement_record_id, principal)

For one key:

- no existing live value -> STORED;
- byte-identical prepared evidence -> DUPLICATE;
- any different verification method, proof identity, or proof bytes -> fail
  closed with AGREEMENT_ASSENT_COLLISION.

There is no latest-proof-wins behavior.

## Prepared evidence boundary

The coordination store accepts only PreparedAgreementAssent. It contains:

- exact Agreement Record Identity;
- exact attributed principal;
- exact verification method;
- exact 32-byte Proof Identity digest;
- bounded canonical public proof bytes.

It does not accept or retain:

- private key material;
- browser CryptoKey objects;
- authentication/session tokens;
- caller-supplied trust decisions;
- unverified raw requests;
- unrelated request metadata.

The serialization/preparation adapter from VerifiedAgreementAssent is injected
and separately reviewable.

## Capacity and party bounds

The deterministic reference store is bounded to at most 4096 live entries and
expires at most 256 due entries in one cleanup batch.

Formation-facing listing is bounded to at most 16 party observations, matching
the existing Agreement formation evidence ceiling.

If more evidence exists than the reviewed formation-facing limit, the read
fails closed rather than silently returning an incomplete subset.

## Read semantics

peek and list_for_agreement:

- return only unexpired evidence;
- never refresh expiry;
- never delete expired rows;
- never claim global completeness;
- never publish an Agreement.

## Runtime and persistence boundary

This slice adds no:

- PostgreSQL schema or migration;
- filesystem persistence;
- network I/O;
- background cleanup worker;
- browser activation;
- HTTP route;
- Agreement publication;
- payment, settlement, escrow, fulfillment, or ownership transfer.

A later PostgreSQL adapter must implement these exact coordination semantics
under a separately reviewed schema/migration and must preserve absolute
retention, idempotency, collision handling, and no-refresh reads.

## Rollback

Rollback is source-only. The current application runtime does not select this
memory coordination store, and this slice creates no persistent state.
