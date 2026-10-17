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

## Approved Web destination and remaining operator decisions

On October 17, 2026, the product owner selected **the existing open-trust-layer.org VPS** as the authoritative Marketplace Web deployment target, with the canonical HTTPS origin **https://marketplace.open-trust-layer.org/**. Treat that selection as a *hosting decision*, not authorization to install a service, modify DNS/TLS, open an external port, deploy credentials, or expose users.

A read-only external check on October 17 observed that both `open-trust-layer.org` and `marketplace.open-trust-layer.org` resolved to IPv4 `168.113.210.63`. The main domain responded over HTTPS, but an HTTPS request with Marketplace SNI failed during TLS negotiation with an `internal error` alert. **Marketplace HTTPS was not verified or working at the checkpoint.** DNS parity is not proof of VPS administrative ownership, appropriate capacity, an installed Marketplace application or valid TLS certificate. Reconfirm live DNS/A/AAAA resolution, IP and host ownership at deployment time. Never hard-code an observed IP as an application identity or secret.

Before any live infrastructure work, the operator must resolve these remaining decisions under #528:

1. **VPS isolation and capacity:** verify operating system, administrative access, CPU/RAM/disk headroom, existing services/vhosts and available resources on the selected **open-trust-layer.org VPS**. Use a dedicated least-privileged Marketplace service identity and isolated storage. Preserve every existing website and workload on that VPS; no default placement on Windows Machine, Moon inference, Johnny 5 PostgreSQL or CI runners.
2. **Canonical alpha FQDN and TLS:** use exactly **https://marketplace.open-trust-layer.org/** as the Web application's canonical public origin. An operator must approve the DNS records and establish/renew a certificate with valid SAN coverage and SNI routing, secure HTTPS-only behavior and a reviewed reverse-proxy vhost without replacing other hosts' routing or certificates. The current TLS error is a **blocking prerequisite**, not permission to disable certificate verification.
3. **Persistent database and secret boundary:** provision a logically isolated private PostgreSQL database and minimally privileged role with approved storage/backups; credentials flow only through an operator-controlled secret mechanism. Never copy evaluator DPAPI material or its short-lived signed lease into the VPS.
4. **Operations ownership:** identify the release/rollback operator, access controls, backup location/retention, demonstrated restore, alerting endpoint and security-contact route.
5. **Invitation policy:** agree on number of invitees, enrollment/revocation design, data-retention consent, and launch jurisdiction/legal review for actual economic transactions.

The VPS and canonical URL are **selected**. Actual host address, capacity and cost have not been independently verified; the certificate, reverse-proxy configuration, production adapter, live customer access and launch date remain **unverified / not deployed**.

## Architecture boundary: localhost is not production

The reviewed authenticated fulfillment launcher in `tools/marketplace_localhost.py` and [M17.7H](m17-7h-fulfillment-completion-localhost-runtime.md) binds **exactly `127.0.0.1`**. It is a high-risk, foreground, explicitly authorized evaluator pathway, **not a production service entry point**.

A hosted Web alpha needs a separately reviewed deployment application and security composition. The expected boundary is:

```text
invited HTTPS browser at https://marketplace.open-trust-layer.org/
    -> operator-reviewed VPS TLS reverse proxy / SNI / origin policy / rate limits
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
3. Verify isolation/capacity of the selected open-trust-layer.org VPS, fix Marketplace SNI/TLS under separately approved change control, and review the production adapter; prepare automated build, private service lifecycle, persistence, backup and restore.
4. Validate an HTTPS staging deployment with no customers, then invite a small operator-approved test cohort.
5. Rehearse rollback and failure modes before any expansion to public beta.

A limited invitation-only alpha remains a **planning target** rather than a dated release. External hosting approvals, actual defects, dependency supply-chain validation and legal/provider lead times are not covered by a green CI result.

## Explicit non-authority and rollback

This document/test change creates no compute, process, credentials, encryption keys, sockets, DNS/TLS records, database schema, persistent files outside source, customer accounts, Moon heartbeat, payment, Android build or public exposure. It does not grant deployment authority.

Rollback is a source-only revert of the future merge. A subsequent production rollout, if approved, must provide its own scoped rollback plan with verified backups and no loss of committed customer records.
