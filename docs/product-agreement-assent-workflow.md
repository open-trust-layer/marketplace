# Product Agreement assent workflow

## Purpose

This slice composes the reviewed Agreement assent services into one
transport-neutral workflow for a later authenticated HTTP adapter.

The workflow exposes three explicit operations:

1. prepare exact signing bytes for one trusted party/method binding;
2. submit one exact Ed25519 signature, verify it, and retain the verified assent;
3. read the current formation status through the separate aggregation service.

## No hidden lifecycle

Construction and prepare do not initialize the coordination store.

Submit does not run hidden expiry maintenance beyond the behavior already owned
by the injected coordination store. If the store has not been initialized by
the reviewed runtime lifecycle, submission fails closed.

Formation status is a separate read-only operation. Submit does not
automatically evaluate formation after a successful write, avoiding a
cross-service pseudo-transaction that could report failure after evidence was
already retained.

## Authority boundary

A successful submission means only that one exact Agreement assent proof was
verified and accepted into the bounded coordination store.

It does not publish an Agreement and does not authorize payment, settlement,
escrow, fulfillment, ownership transfer, browser activation, deployment, or
any other protected side effect.

The submission result permanently freezes both authority flags to false.

## Future HTTP adapter

A later authenticated HTTP slice may map exact session identity and bounded
request fields onto this workflow.

That adapter still must not accept caller-supplied acting-principal authority,
public-key trust, or attribution decisions. Browser signer delivery and
selection remain separate reviewed capabilities.

## Rollback

Rollback is source-only: revert this additive workflow source/test/doc change.
No schema, retained data, browser state, or runtime service is created by this
slice.
