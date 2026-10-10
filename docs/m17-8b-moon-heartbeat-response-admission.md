# M17.8B — Admit an opt-in Moon heartbeat only after a completed HTTP response

## Problem

The prior opt-in Marketplace Moon heartbeat wrapper started a periodic lease
**before** invoking the application for its first HTTP request. A request that
raised an application exception, failed while writing the response or returned
HTTP 5xx still started an ongoing heartbeat. A failed request must not be
misrepresented as successful application admission.

## Reviewed boundary

`MarketplaceMoonHeartbeatServerProvider` still wraps only an explicitly
selected foreground server; `MARKETPLACE_MOON_HEARTBEAT_ENABLED=1` is
required. It does not launch a process, open a socket, query PostgreSQL or
enable health reporting implicitly.

The wrapper observes the actual ASGI send path of an HTTP request. It admits
the heartbeat lease only **after** the application returns without exception,
the response-start status is an integer from 200 through 499, and the final
`http.response.body` frame has been sent successfully with
`more_body=false` (or omitted). Successful HTTP 4xx responses count as
evidence that an application responded, **not** evidence of a successful
marketplace transaction. No heartbeat is admitted for only a request start,
an incomplete stream, a server-error (5xx) response, a failed send,
an application exception or a lifespan-only scope.

Once admitted, the existing 15-second default opt-in lease continues to
indicate **foreground process liveness**, and is removed on normal provider
shutdown. It does **not** continuously probe application responsiveness,
guarantee business readiness, prove the active listener runs current main,
or establish that any browser transaction has been performed.

## Moon Company 2.1 recovery boundaries

Repository-owned `moon.manifest.yaml` still declares a
`development` workspace with `health.kind=workspace`. This patch does not
change that truth, override the separately owned Moon Core registry, refresh
stale evidence, switch an existing runtime or supply supervision.

For Marketplace runtime recovery (tracked in
[Issue #519](https://github.com/open-trust-layer/marketplace/issues/519)),
the runtime/deployment owner still must decide whether Marketplace is
workspace-only or always-on. A supervised deployment and actual relay receipt
require their own authority and verification; no fabricated heartbeats or
backfilled timestamps are acceptable. The explicit localhost/browser
acceptance remains a separate boundary.

## Validation and rollback

`tests/test_marketplace_moon_runtime.py` exercises completed 200/204/404/499
admission, failed 500/503, incomplete streams, post-response application
exceptions, failed ASGI sends, lifespan-only scopes and binding failures.
All existing tests and full conformance CI must pass on the exact review head
before merging. Revert this source-only change to restore prior behavior;
no runtime or database rollback is involved.
