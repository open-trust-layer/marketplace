# M17.7N — Authenticated local flight readiness refresh

Profile: `MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_READINESS_V1`

Risk: **documentation/acceptance-contract only**.

## Purpose

M17.7H-L made the reviewed authenticated Agreement-publication and
fulfillment-completion path selectable on exact IPv4 loopback and actionable
from the active Web surface. M17.7M then exercised the final session-aware ASGI
overlay and active Web/runtime delivery contracts in the full conformance lane.

M17.7N updates the repository's top-level flight-readiness statements so they
match that merged reality without upgrading source/CI evidence into a false
claim of live-runtime execution.

## Evidence baseline

The accepted baseline is merged M17.7M:

`7e356b7259b4736772e15da434f9a237b5c88b63`

Its exact-head full conformance run **#946** succeeded.

That evidence establishes:

- exact Bearer/session transport into the final fulfillment HTTP overlay;
- authenticated principal as the only fulfillment issuer;
- zero publication for unauthenticated or authority-injecting requests;
- preserved Agreement-publication delegation;
- explicit **Publish Agreement** and **Claim delivery complete** Web actions;
- exact `seller-delivery` / `CLAIMED_COMPLETE_PERFORMANCE` completion semantics;
- reviewed static Web-module delivery; and
- exact loopback-only fulfillment runtime selection.

## Truthful readiness status

Two local evaluator lanes are distinct:

1. **Database-free demonstrator** — executed and accepted end to end.
2. **Authenticated PostgreSQL-capable product path** — source/CI accepted,
   **live-runtime pending**.

The second lane has not yet been recorded as one real PostgreSQL-backed
localhost server + browser execution. M17.7N therefore does not mark that gate
complete.

## Final local runtime gate

The existing bootstrap already provides the required inert preflight:

`--preflight-fulfillment-completion-localhost`

and separately authorized live mode:

`--execute-fulfillment-completion-localhost EXECUTE_FULFILLMENT_COMPLETION_AUTHENTICATED_MARKETPLACE_LOCALHOST_V1`

Both require an explicit absolute authentication provisioning directory. The
composition reads the locally supplied `MARKETPLACE_POSTGRES_DSN`; preflight
does not connect to PostgreSQL, initialize database/coordination state, bind a
socket, or run a server.

The live path remains exact `127.0.0.1` and requires a separate operator
runtime authorization.

## Evidence to record when the live gate is executed

Only non-secret observable evidence should be retained:

- successful authenticated state without token/key disclosure;
- selected Proposal and exact Agreement Record Identity;
- Agreement publication metadata;
- seller-attributed claimed-complete evidence for `seller-delivery`;
- resulting immutable Record Identity, disposition, and local change sequence;
- UI wording that completion is attributable evidence rather than universal
  truth, payment, or settlement; and
- confirmation that the runtime remained loopback-only.

DSN text, provisioning bytes, private keys, session material, challenges, and
other credentials must not be copied into committed evidence.

## Non-authority

M17.7N performs no PostgreSQL connection or initialization, filesystem
provisioning mutation, credential generation, socket/server execution, browser
automation, public-network exposure, deployment, payment/settlement action,
Android action, publishing/distribution, or production-health assertion.

## Rollback

**documentation-only rollback:** revert the exact M17.7N merge.

No runtime, database, credential, external-system, payment, settlement, or
deployment rollback is involved.
