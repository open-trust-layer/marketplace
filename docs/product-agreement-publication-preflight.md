# Product Agreement publication preflight

This slice adds a pure, state-free preflight for a future protected Agreement
publication write.

The preflight re-verifies the Agreement candidate identity, requires formation
evidence to target that exact Agreement, validates formation-result consistency, and
checks that the authenticated actor is one of the Agreement parties.

A result of `preconditions_satisfied=true` is only a local precondition decision.
It deliberately does **not** publish the Agreement and does **not** authorize a side
effect.

The preflight always reports:

- `publishes_agreement=false`
- `authorizes_side_effects=false`

Actual Agreement publication remains a later HIGH-risk protected write requiring its
own authenticated application/API composition, exact-state checks, and governance
qualification. HTTP, Web, Android, database, network, signing, payment, settlement,
fulfillment, service mutation, and deployment remain outside this slice.
