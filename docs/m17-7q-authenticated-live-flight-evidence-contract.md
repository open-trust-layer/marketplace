# M17.7Q — Authenticated live-flight evidence contract

Profile: `MARKETPLACE_AUTHENTICATED_LIVE_FLIGHT_EVIDENCE_CONTRACT_V1`

Baseline: merged-green Marketplace `main`
`39153a271a407cf8d0f236c61e616621242c9fed`.

Issue: #500.

## Purpose

The first PostgreSQL-backed loopback browser acceptance exposed two real defects
before the final `Accept -> Agreement -> Complete` evidence could be recorded.
This contract records those findings and freezes the exact non-secret evidence
required before authenticated local product flight may be called accepted.

The path is source/CI accepted and **live-runtime partially exercised**, but is
**not yet live-runtime accepted**. A fresh post-P browser repeat remains required.

## Confirmed live findings

### M17.7O — runtime clock

The real authenticated fulfillment-completion runtime reached PostgreSQL
application initialization and failed before socket bind with
`AGREEMENT_ASSENT_CLOCK_INVALID`.

M17.7O corrected the shared localhost clock to aware whole-second UTC without
changing runtime authority. It merged at
`2777307cf77e20261c6b6a893f29669902ac9e74`.
Exact-head run #952 and merged-main run #953 succeeded.

### M17.7P — authenticated Web authoring

After the clock correction, the browser established an authenticated seller
session, but visible listing creation failed with `AUTH_REQUIRED`.

M17.7P binds listing and Proposal authoring to the exact established in-memory
session and derives actor attribution from that session instead of trusting an
editable principal field. It merged at
`39153a271a407cf8d0f236c61e616621242c9fed`.
Exact-head run #954 and merged-main run #955 succeeded.

## Required final evidence

The final evaluator record must contain only non-secret observable values:

1. exact merged `main` commit and successful required conformance result;
2. runtime bound only to `127.0.0.1`;
3. successful seller and buyer authentication state;
4. listing, Proposal, and seller-acceptance Record Identities;
5. exact Agreement candidate Record Identity;
6. formation state `EVIDENCE_SUFFICIENT_FOR_PROFILE` with no missing parties;
7. explicit **Publish Agreement** result with exact Agreement Record Identity,
   `STORED` or `DUPLICATE` disposition, and local change sequence;
8. separate explicit **Claim delivery complete** result for commitment
   `seller-delivery`;
9. completion evidence kind exactly `CLAIMED_COMPLETE_PERFORMANCE`;
10. completion evidence Record Identity, `STORED` or `DUPLICATE`
    disposition, and local change sequence;
11. visible confirmation that completion remains seller-attributed evidence,
    not universal truth and not payment or settlement;
12. confirmation that no public deployment or public-network exposure was used.

Authentication success or successful listing/Proposal authoring alone is
insufficient for final product-flight acceptance.

## Secret boundary

The evidence record **must not contain** Bearer/session-token text, browser private keys,
PostgreSQL DSN text, or other private runtime material.

## Non-authority

M17.7Q adds **no server execution**, **no browser automation dependency**, no
database initialization, no socket bind, no persistence expansion, no
public-network exposure, no deployment authority, no Android action, no
payment or settlement authority, and no production credential handling.

## Rollback

Rollback is acceptance-contract only: revert the M17.7Q documentation/test
merge. No runtime or external-system rollback is introduced.
