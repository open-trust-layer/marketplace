# Private Web alpha — deployment decision and acceptance gates

**Status:** proposed **source-only** engineering plan for Moon Commerce.  
**Tracker:** [#528](https://github.com/open-trust-layer/marketplace/issues/528).  
**Evidence baseline:** Marketplace `main` merge `e1be071a81692c416375f1fd6f36186f696d3f5a`, independently verified by successful [main CI #38983706343](https://github.com/open-trust-layer/marketplace/actions/runs/38983706343). This is **not** live browser acceptance or deployment.

## Product scope

The first customer-accessible release should be an **invitation-only HTTPS Web alpha** for two real authenticated principals: create/publish a listing, discover and negotiate, form and explicitly publish an Agreement, and submit seller-attributed fulfillment evidence. Show clearly that `CLAIMED_COMPLETE_PERFORMANCE` is attributable evidence, **not** universal completion, legal ownership, payment, settlement, or guaranteed delivery.

**Payments, settlement, public self-signup, production webhooks, Android distribution and unrestricted federation are OFF.** A public, synthetic database-free demonstration may precede the private alpha only if clearly labeled **DEMO** and isolated from production accounts, persistence, customer data and Moon live-health claims.

## Provenance and evidence truth

- The local database-free two-user Web demonstrator is executable and accepted within its in-memory scope.
- Merged source, CI, signed seller/buyer public-key binding and the inert localhost graph are verified. The authenticated PostgreSQL-capable buyer/seller product journey has **not** been shown to complete with accepted live Evidence V1 in the reviewed checkpoint.
- [Issue #525](https://github.com/open-trust-layer/marketplace/issues/525) was **manually closed** on October 16, 2026. The issue state is not a substitute for its originally specified signed browser session, actual Agreement publication, `seller-delivery` completion, and independent non-secret `MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1` validator PASS. The release gate remains **BLOCKED** until equivalent freshly reviewed evidence is recorded. Do not silently reopen the owner-closed issue or claim acceptance on closure alone.
- The Windows operator-only restricted database probe from [PR #584](https://github.com/open-trust-layer/marketplace/pull/584) is merged and passed synthetic tests. Its protected local execution has **not** been performed through ChatGPT. Never route its DPAPI credential handling through remote execution, chat, CI, or GitHub artifacts.

## The host decision (operator-controlled, not assumed)

Before any live infrastructure work, the operator must record these specific choices under #528:

1. **Authoritative execution host:** dedicated or strictly isolated Linux VM/VPS for Marketplace, with capacity measured for the actual service, PostgreSQL and expected alpha traffic; no default placement on Windows Machine, the Moon inference node, the shared Johnny 5 database, or a CI runner.
2. **Canonical alpha FQDN and TLS owner:** an operator-selected domain, certificate issuance/renewal ownership and authorized DNS administration. There is no approved production FQDN in this plan.
3. **Persistent database and secret boundary:** dedicated private PostgreSQL instance or DB and minimally privileged role; credentials provided by the operator-controlled secret mechanism only. Never copy evaluator DPAPI material or its short-lived signed lease to a hosted environment.
4. **Operations ownership:** named release/rollback operator, access controls, backup location/retention, restore rehearsal, alerting endpoint and security-contact route.
5. **Invitation policy:** number of invitees, identity enrollment/revocation design, data-retention consent and launch jurisdiction/legal review for actual economic transactions.

Infrastructure sizing, host name, DNS and launch date are **TBD** pending these decisions; no sample address, operator, cost or capacity estimate is a real reservation.

## Architecture boundary: localhost is not production

The reviewed authenticated fulfillment launcher in `tools/marketplace_localhost.py` and [M17.7H](m17-7h-fulfillment-completion-localhost-runtime.md) binds **exactly `127.0.0.1`**. It is a high-risk, foreground, explicitly authorized evaluator pathway, **not a production service entry point**.

A hosted Web alpha needs a separately reviewed deployment application and security composition. The expected boundary is:

```text
invited HTTPS browser
    -> approved TLS reverse proxy / origin policy / rate limits
    -> reviewed production ASGI HTTP and auth/session adapter (private listener)
    -> Marketplace product/Agreement/fulfillment services
    -> isolated least-privilege persistent PostgreSQL
```

This is an **architecture target only**; these arrows do not assert that a reviewed public adapter, production service, reverse proxy, database or secret store currently exists. Never simply set a wildcard bind, tunnel the loopback evaluator, publish port 18080, or forward unaudited `X-Forwarded-*` headers to claim production readiness.

Explicit production implementation/review must cover:
- same-origin URL, HTTPS-only WebCrypto/session semantics, verified Host/Origin boundaries, trusted-proxy configuration and redirect behavior;
- enrollment/invitation authority, key recovery/revocation, finite session expiry, sign-out and negative authentication cases; neither seller nor buyer may inject another principal's authority;
- bounded request bodies/responses, method/path allowlists, secure response headers, rate limits, abuse/backpressure controls and stable redacted errors;
- schema migration plan, non-destructive initialization, isolated persistence and transactional repeatability, backup encryption and *tested* restoration;
- secure secret injection and rotation, restricted service account/network ingress, outbound egress review, patched dependencies and pinned exact build artifact;
- lifecycle-owned startup/shutdown, version-linked health checks and Moon heartbeat derived only from actual live capability (never from stale HTML, a checkout, or an offline test).

## Ordered acceptance gates

| Gate | Required observable evidence | Exit criterion |
| --- | --- | --- |
| A. Exact source | Protected merged-main SHA, pinned OLP and **independent green merged-main CI** | Verified; not a runtime PASS |
| B. Restricted local evaluator | Operator-generated **non-secret** restricted read-only PostgreSQL receipt | No leaked secret; no remote credential execution |
| C. Authenticated local product | Fresh, same-origin two-browser Ed25519 keys and valid signed provisioning; real Agreement **Publish Agreement** and seller `seller-delivery` / `CLAIMED_COMPLETE_PERFORMANCE`; offline Evidence V1 validation | **Actual PASS** required, independent of closed issue labels |
| D. Production architecture review | Host/FQDN approved, threat model, production ASGI/proxy adapter and integration/negative tests | No inherited loopback authority; secure route and session behavior |
| E. Deployment operations | Least-privilege persistent DB, operator-owned secrets, HTTPS, backup **and restore**, smoke tests, logging/redaction and rollback drill | Private alpha may be activated only under separate operator deployment approval |
| F. Private alpha | Invited seller/buyer pass the end-to-end Web journey and negative cases on actual HTTPS host; version-linked service-health evidence | Owner signs off on controlled invitation cohort |
| G. Limited public beta | Abuse monitoring, tested recovery and legal/product policy readiness; separate public-access authorization | Payments remain disabled unless a separate product/security/legal release authorizes them |

If any gate fails, stop at that gate and retain an explicit **BLOCKED** result. A green offline source test must never be promoted into a live product or public-availability assertion.

## Release work packages and estimated effort

The existing [Roadmap](../Roadmap.md) estimates 6–16 engineering hours for local authenticated acceptance, 12–32 hours for Web UX/repeatability, and 24–72 hours for security/operations planning. Those are forecasts, not timesheets.

Practical execution order:
1. Finish gate B/C acceptance; record safe evidence or a narrowly reproducible defect.
2. Freeze a minimal private-alpha feature set and run user-facing negative/recovery paths.
3. Choose and review the authoritative host and production adapter; prepare automated build, private service lifecycle, persistence, backup and restore.
4. Validate an HTTPS staging deployment with no customers, then invite a small operator-approved test cohort.
5. Rehearse rollback and failure modes before any expansion to public beta.

A limited invitation-only alpha remains a **planning target** rather than a dated release. External hosting approvals, actual defects, dependency supply-chain validation and legal/provider lead times are not covered by a green CI result.

## Explicit non-authority and rollback

This document/test change creates no compute, process, credentials, encryption keys, sockets, DNS/TLS records, database schema, persistent files outside source, customer accounts, Moon heartbeat, payment, Android build or public exposure. It does not grant deployment authority.

Rollback is a source-only revert of the future merge. A subsequent production rollout, if approved, must provide its own scoped rollback plan with verified backups and no loss of committed customer records.
