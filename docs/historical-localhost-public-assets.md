# Read-only historical localhost Web asset provenance

Tracks the Moon Company Marketplace host/release question in [#528](https://github.com/open-trust-layer/marketplace/issues/528). This diagnostic provides a **byte-for-byte public Web snapshot comparison**, not a deployment, health, authentication, or backend provenance claim.

## Purpose

The strict current-checkout asset preflight correctly rejects older or mismatched Web shells. For an existing older **loopback** Marketplace process that must not be interrupted, the historical public asset checker compares the fixed set of 14 reviewed public routes against the exact public files in a selected **ancestor Git commit**.

Unlike a simple HTTP 200 test, it verifies each expected asset's contents and expects HTTP 404 for a module that did not exist at that commit. It does not follow redirects, use environment proxies, submit forms, read credentials, issue non-GET requests, start a server, or connect to PostgreSQL.

## Windows evaluator example

Use a clean, reviewed Marketplace checkout with a local Git history containing the reference commit. From that checkout:

    python -m tools.marketplace_historical_public_assets --historical-sha ed4063ace32858a8b148127dabb1c7ca33ba3622 --port 18080

A successful, non-secret result is explicitly limited:

    status=PASS historical_sha=ed4063ace32858a8b148127dabb1c7ca33ba3622 host=127.0.0.1 port=18080 matched_public_assets=13 expected_absent_assets=1 historical_web_snapshot_only=true backend_provenance_verified=false auth_verified=false production_verified=false

That reference revision is the October 7 M17.7P source. The unavailable /authenticated_local_flight_evidence.js route is expected to be absent in that release. Successful comparison to a different commit does not identify the running Python process's actual checkout, data store, loaded modules, configuration or effective authorities. Differences fail closed with stable codes, without printing HTTP bodies or secret paths.

For the latest static preview, use the currently reviewed exact main SHA on a clean checkout and its own exact loopback port. Do not confuse a preview with an authenticated product runtime.

## Boundaries and interpretation

- Only the fixed 14 Web asset routes from the reviewed asset preflight are inspected. A positive check makes **no claim about other routes**.
- The historical SHA must resolve to a Git commit that is an ancestor of the selected checkout's HEAD. Independently establish local Git provenance against the trusted GitHub repository.
- Git tree entries must be regular file blobs; missing historical assets must produce HTTP 404, not redirects or other statuses.
- HTTP bodies are limited to 2 MiB each, read from exact IPv4 127.0.0.1 with proxies disabled. A repeat read of the index helps detect, but cannot atomically prevent, a mid-probe swap.
- No customer state, API POST, login, payment, database, external network binding, process termination or credential inspection occurs.
- PASS does **not** prove the running backend revision, current GitHub main, production deployment, Moon heartbeat, user authentication or Issue #525's authenticated PostgreSQL acceptance.
- Authoritative host/lifecycle classification remains a separate decision in Issue #528. Never fabricate a positive runtime heartbeat based on asset parity.

Unit tests are in tests/test_marketplace_historical_public_assets.py. The check is safe for a separately reviewed historical commit without altering a running service.
