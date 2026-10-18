# Marketplace Caddy Unix upstream — review-only candidate

**Status: INERT / NOT VALIDATED AGAINST LIVE CADDY / NOT DEPLOYED.**
**Canonical hostname:** `marketplace.open-trust-layer.org`
**Selected destination:** existing shared `open-trust-layer.org` VPS
**Release tracker:** [#528](https://github.com/open-trust-layer/marketplace/issues/528)

## Why this candidate is different

The older [loopback TCP Caddy candidate](marketplace-caddy-review-candidate.md) predates the reviewed Marketplace Linux kernel `SO_PEERCRED` security boundary. **It is not an approved proxy path for the newer authenticated app.** A loopback IP does not verify which local process sent an HTTP request; never publish the evaluator through that older candidate.

Caddy [officially documents Unix-socket upstream addresses](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy) of the form `unix//var/example.sock`. A Unix socket can be protected by operating-system credentials and filesystem access control. The Marketplace source now has reviewed—but not production-wired—components for:

1. `MarketplaceLinuxUnixCaddyPeerVerifier`: checks actual accepted socket against exact path and Linux `SO_PEERCRED` nonroot Caddy UID/GID.
2. `MarketplaceAttestedCaddyEdgeAsgiAdapter`: normalizes the default Caddy forwarding headers only after kernel peer verification; caller `Host` and `Origin` remain constrained.
3. `serve_one_attested_unix_http11`: strict one-request HTTP/1.1 framing, finite body/response and deadline.
4. `serve_bounded_marketplace_unix_foreground`: explicitly enabled temporary Unix listener with a small concurrency/lifetime cap and no existing path replacement. **Not a production service.**

## Inert candidate renderer

```sh
python tools/marketplace_caddy_unix_review_candidate.py
# status=INERT_CADDY_UNIX_REVIEW_NOT_RENDERED
```

A single exact review opt-in prints a candidate fragment **to stdout only**:

```sh
python tools/marketplace_caddy_unix_review_candidate.py \
  --render-candidate RENDER_ONLY_MARKETPLACE_CADDY_UNIX_REVIEW_V1
```

It has **no variable host, socket path, port, scheme, file-output parameter, service management, Caddy API, network access or credentials**. The illustrative socket path is `/run/moon-marketplace/marketplace-edge.sock` (Caddy upstream `unix//run/moon-marketplace/marketplace-edge.sock`). This path is **not known to exist or be reserved** on the chosen VPS; the operator must independently check that it does not conflict with an existing workload and matches an approved service-owned socket exactly.

The template preserves Caddy-generated `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Forwarded-Host` for the verified edge normalization; it requests removal of selected untrusted extra proxy metadata which the current guard rejects. It selects HTTP/1.1, disables keepalives (the bounded handler closes every accepted connection), disables upstream compression, and uses finite dial and response-header deadlines. These choices are based on current Caddy documentation **but have not passed a `caddy adapt` or live proxy interoperability test**. There is no `tls internal`, `tls_insecure_skip_verify`, wildcard hostname, public backend port, or bypass path.

## Release blockers — STOP, do not activate this candidate

- **Real TLS/SNI**: an independently verified read-only connection to `168.113.210.63:443` with the selected Marketplace SNI failed during handshake with TLS alert `internal error`, while an otherwise identical request with `open-trust-layer.org` SNI succeeded and served a valid certificate. This narrows the defect to Marketplace-hostname-specific TLS handling but does not prove a root cause. Inspect actual Caddy **effective** config/imports, certificate provisioning/challenges, logs, and namespaced route on VPS via a separately authorized operator change window.
- **Exact Caddy service identity**: inspect real service user/group, and configure a different nonroot Marketplace UID. Set the listener directory owner/group and permissions so only Caddy can traverse/connect, and verify symlink/ownership/race protection and actual kernel credentials from live Caddy, not a test double.
- **Real proxy framing**: Caddy's outbound HTTP/1.1 request behavior (Content-Length, Expect, streaming/chunked bodies, forwarding header normalization, Host, Origin, retries, redirect/TLS, timeout) must be tested against the exact bounded Unix handler. Unsupported requests must fail closed. No local Caddy executable/actual VPS Caddy config has been validated by this source candidate.
- **Capacity and lifecycle**: existing owner-approved VPS has other sites. The bounded listener (at most 16 accepts, 2 concurrent, 20s) is **a staging-probe construct**, not a serving daemon. Production needs a separately reviewed steady-state service/supervisor, isolation, observability, rate limiting, concurrency/backpressure, recovery and safe rollback preserving neighboring sites.
- **Product acceptance**: separately reviewed authenticated ASGI composition and isolated PostgreSQL role/storage, secret rotation, backup **plus tested restore**, and fresh real two-principal browser Evidence V1 showing signed authorization, explicit Agreement publication, and seller `seller-delivery`. Payments, settlements and open signup remain disabled.
- **Deployment authority**: approving routine repository PR merges is not permission to change production DNS, certificate, Caddy, systemd, Unix socket, database, user access or Moon live heartbeat. Require independently scoped operational authorization and preserve all unrelated sites.

## Validation

```sh
python -m unittest tests.test_marketplace_caddy_unix_review_candidate -v
```

The offline tests check exact canonical host and Unix path, approved downstream header expectations, one HTTP/1.1 transport with keepalive disabled, rejection of arbitrary host/path/port arguments, no public TCP fallback, inert default, deterministic source rendering and no resource operations. They do **not** validate Caddy syntax on an installed Caddy binary, prove a working HTTPS endpoint, or start an application.

Source-only rollback: revert this file/test/doc. **No live system change occurs.** For actual rollout requirements see [the private Web alpha deployment plan](private-web-alpha-deployment-plan.md).
