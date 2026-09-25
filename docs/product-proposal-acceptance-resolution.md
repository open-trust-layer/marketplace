# Proposal acceptance deterministic resolution

## Purpose

Agreement assent requires every party to refer to the same immutable Proposal
acceptance Record Identity.

The seller already receives that identity when publishing acceptance. A buyer
session does not share the seller's browser memory, so the identity must be
resolvable without asking the buyer to guess, paste, rank, or select an
acceptance event.

This slice adds only a transport-neutral, read-only application service. It
does not add an HTTP route or browser activation yet.

## Deterministic resolution

For one exact Proposal Record Identity and one authenticated principal, the
service:

1. reads the exact Proposal with the non-refreshing application-state `peek`;
2. requires the exact reviewed Proposal profile and exactly one parent Listing;
3. derives the buyer from the Proposal issuer;
4. reads and validates the exact parent product Listing;
5. derives the seller from that Listing;
6. requires the caller principal to equal the buyer or seller;
7. deterministically rebuilds the canonical Proposal-acceptance event from the
   exact seller + Proposal identity;
8. derives that event's canonical Record Identity;
9. reads that exact identity with `peek`;
10. revalidates the stored acceptance identity, Proposal binding, and issuer.

Only then may it return:

- `proposal_record_id`;
- `record_id` for the exact published acceptance.

## No ambient selection

The resolver does **not**:

- enumerate response history;
- scan sync history;
- choose a latest/first acceptance;
- rank competing events;
- accept an acceptance identity from caller input;
- extend application-record retention;
- create or publish acceptance evidence.

If the deterministic acceptance has not actually been published into retained
application state, resolution returns a stable not-found failure. The fact that
the identity can be derived does not imply that acceptance exists.

## Party disclosure boundary

Only the exact Proposal buyer or parent-Listing seller may receive the
acceptance identity.

A non-party is rejected before the acceptance record is read or disclosed.

This is a discovery/read boundary only. Party membership here does not itself
prove Agreement assent, formation, legal enforceability, payment authority, or
ownership.

## Why no new database index

The acceptance profile is deterministic for the exact seller + Proposal pair.
Its canonical Record Identity can therefore be derived and looked up directly.

No related-record index, response-link reinterpretation, schema migration,
global scan, or new persistence table is required for this resolution step.

## Authority boundary

This slice performs no signing, proof creation, Agreement publication,
coordination write, payment, settlement, escrow, fulfillment, key mutation,
database migration, service/runtime mutation, deployment, or public-network
activation.

A later reviewed authenticated HTTP slice may expose this service to Proposal
parties. Browser consumption remains a separate explicit slice.

## Rollback

Rollback is source-only: remove this service/test/document slice. No external
state is created or mutated by resolution.
