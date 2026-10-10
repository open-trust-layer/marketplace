# Product Agreement assent candidate resolution

## Purpose

This slice resolves the exact unpublished Agreement candidate needed by the
assent workflow without allowing an HTTP caller to choose a Listing identity.

Input is limited to:

- one exact Proposal Record Identity;
- one exact Proposal-acceptance Record Identity.

The resolver reads the Proposal without refreshing application retention,
requires exactly one parent Listing identity, and delegates candidate creation
to the already-reviewed Agreement candidate authoring seam.

## No automatic acceptance selection

The acceptance identity is explicit immutable evidence.

This slice does not search response history, select a latest event, rank
multiple acceptances, or infer an acceptance from ambient application state.

The existing candidate builder independently verifies that the supplied
acceptance targets the exact Proposal and was issued by the exact Listing
seller.

## Authority boundary

The resolver is read-only. It does not publish the Agreement, create an assent
proof, persist coordination evidence, evaluate formation, authorize payment,
settlement, escrow, fulfillment, or ownership transfer, or perform network I/O.

A successful result remains unpublished with formation evidence NOT_EVALUATED.

## Future HTTP adapter

A later authenticated route may place the Proposal identity in the path and the
exact acceptance identity in a bounded request body. The Listing identity must
continue to come only from the resolved Proposal parent.

## Rollback

Rollback is source-only: revert this additive source/test/doc change.
