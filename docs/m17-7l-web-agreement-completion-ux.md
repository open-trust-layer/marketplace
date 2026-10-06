# M17.7L — Explicit Web Agreement publication and delivery-complete UX

Profile: `MARKETPLACE_WEB_AGREEMENT_COMPLETION_UX_V1`

Risk: **HIGH authenticated application-state writes**, explicit browser actions only.

## Purpose

M17.7I/J provide reviewed Web clients for fulfillment-completion and Agreement
publication. M17.7K selects those clients into the existing memory-only
authenticated browser bootstrap without calling either client automatically.

M17.7L adds the explicit product controls that complete the interactive local
journey.

## Exact user actions

The existing Proposal detail surface gains one additional handoff with two
separate buttons:

1. **Publish Agreement**
2. **Claim delivery complete**

Neither action runs automatically after Proposal acceptance, Agreement assent,
formation-status refresh, authentication, synchronization, or page rendering.

## Agreement publication gate

The Publish Agreement button remains disabled unless all of the following are
true for the currently selected Proposal:

- the exact Proposal acceptance is available;
- a current Agreement formation result is available;
- formation evidence is exactly `EVIDENCE_SUFFICIENT_FOR_PROFILE`;
- the missing-principal set is empty;
- an authenticated browser session is active;
- the authenticated principal is one of the required Agreement parties; and
- that principal is included in the reviewed covered-principal set.

On explicit click, the page calls the M17.7J client once with:

- the exact selected Proposal Record Identity;
- the exact resolved/published acceptance Record Identity; and
- the exact expected Agreement candidate Record Identity from the current
  formation result.

The returned Agreement identity must re-bind to that exact candidate before the
page stores the result in memory.

## Delivery-complete gate

The Claim delivery complete button remains disabled until Agreement publication
has succeeded in this page state.

It then additionally requires:

- the Proposal to be opened through its exact parent product listing context;
- an active authenticated session; and
- the authenticated principal to equal the exact listing seller principal.

The explicit click calls M17.7I with:

- the exact published Agreement Record Identity;
- exact commitment id `seller-delivery`; and
- exact evidence kind `CLAIMED_COMPLETE_PERFORMANCE`.

The returned Agreement identity, commitment id, and evidence kind are re-bound
again by the page before the result is displayed.

## Semantic boundary

**Claim delivery complete is an attributable seller-authored claim.**

It is evidence that the authenticated seller asserts the reviewed delivery
commitment was performed. It is not:

- universal truth;
- buyer acceptance;
- dispute resolution;
- legal enforceability;
- payment authorization;
- settlement authorization; or
- proof that payment or settlement occurred.

The UI states this boundary directly.

## Memory and invalidation

Publication, completion, pending, and error results are page-memory-only.

They are cleared when:

- a new authentication session is established;
- authentication is reset;
- a new Proposal acceptance is published;
- Proposal acceptance is freshly resolved; or
- Agreement formation is freshly checked.

This deliberately prefers repeating an idempotent reviewed publication over
allowing stale page state to authorize a downstream action.

## Non-authority

M17.7L adds no:

- server route;
- authentication authority;
- key generation/import/export;
- browser persistence;
- automatic or background write;
- timer/retry loop;
- WebSocket/EventSource;
- Android action;
- public-network exposure;
- production deployment;
- payment or settlement behavior.

## Rollback

**source-only / Web rollback:** revert the exact M17.7L merge and reload the
local page.

Existing server-side immutable evidence remains governed by the application
state; reverting the UI does not delete previously published records.
