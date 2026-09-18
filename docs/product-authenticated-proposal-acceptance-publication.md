# Authenticated Proposal acceptance publication

## Product objective

Expose the smallest server-side Marketplace product seam that lets an authenticated seller publish one immutable Proposal-acceptance event for the exact Proposal selected by the application.

This slice deliberately stops at publication of acceptance evidence. It does not enable the Web **Accept Proposal** button yet.

## HTTP contract

The authenticated application adapter recognizes exactly:

```text
POST /api/intents/{proposal_record_id}/acceptance
```

The request has no query parameters, no body, and no `Content-Type` header. The route is protected by the existing application bearer-session boundary.

The seller principal is never accepted from caller payload. It is derived only from the active authenticated application session.

## Publication preconditions

Before publication, the application must resolve and verify all of the following:

1. the target is an exact valid Marketplace Proposal with exactly one `response_to` parent;
2. the exact parent record resolves as a valid structured product listing;
3. the listing seller principal exactly matches the authenticated session principal;
4. the built acceptance event references exactly the requested Proposal Record Identity;
5. the acceptance Record Identity can be derived before publication.

Any failed precondition fails closed before the acceptance record is published.

## Acceptance record

The reference record is an ordinary immutable Marketplace `MarketEventV1` using:

```text
event = https://open-trust-layer.github.io/marketplace/semantics/v1/event/proposal-acceptance
```

It has the core Marketplace profile, names the authenticated seller as issuer, and contains exactly one `related_records` reference to the accepted Proposal.

A successful request returns only the stored acceptance Record Identity, store disposition, and change sequence.

## Semantic boundary

Acceptance evidence means only that an attributed immutable event asserts acceptance of the exact referenced Proposal.

It does **not** by itself:

- create a `MarketAgreement`;
- prove that all required parties assented;
- prove that the Proposal is universally current;
- establish legal enforceability, ownership, payment, settlement, or fulfillment;
- delete, supersede, or invalidate competing Proposals.

These boundaries follow `specification/0004-market-lifecycle-negotiation.md`.

## Explicit non-authority

This source slice does not authorize or perform browser acceptance activation, Agreement formation, payment, settlement, fulfillment, trust-evidence mutation, key persistence, database/configuration/service mutation, deployment, public-network exposure, Android runtime activity, or any production action.

The existing browser acceptance control remains disabled and has no click handler.

## Rollback

Repository rollback is source-only: revert the acceptance publication source/composition changes. Runtime activation, external evidence changes, and operational rollback are outside this slice.
