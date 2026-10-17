# Marketplace private-alpha Caddy vhost — review candidate only

**Risk:** MODERATE source-only pre-deployment template.  
**Tracking:** [Marketplace host authority #528](https://github.com/open-trust-layer/marketplace/issues/528).  
**Target selected by owner:** existing **open-trust-layer.org VPS**, canonical **https://marketplace.open-trust-layer.org/**.

## Why this exists

The owner selected the domain and VPS. Prior read-only checks found both domains resolving to the same IPv4 address but an `internal error` TLS alert when the Marketplace SNI was requested. Caddy and PostgreSQL services were active on the VPS; Marketplace's live authenticated application and its public HTTPS service have **not** been verified. The VPS is shared with other workloads and has limited free RAM/disk.

This tool generates a **Caddyfile fragment for source review only**. It is not an installable release artifact, approved vhost, current VPS configuration, checked TLS certificate, isolated production application, database migration, deployment or public-availability assertion. It must **not deploy** or be pasted into live Caddy until all required review/authorization gates are complete.

Caddy normally offers automatic HTTPS for a hostname site block (subject to public DNS, valid issuer/challenges and operator-approved routing). Its `reverse_proxy` directive can send requests to a private loopback upstream. These behaviors do not prove that this VPS has the right routing, cert, host import or app adapter.

## Inert CLI and explicit review output

From an existing reviewed Marketplace source checkout, the default action is **inert**:

```sh
python tools/marketplace_caddy_vhost_candidate.py
# status=INERT_CADDY_CANDIDATE_NOT_RENDERED
```

With explicit source-review opt-in, render **only to stdout**:

```sh
python tools/marketplace_caddy_vhost_candidate.py \
  --render-candidate RENDER_REVIEW_ONLY_MARKETPLACE_CADDY_CANDIDATE_V1 \
  --upstream-port 24081
```

`24081` is **an illustration, not a reserved or inspected port**. The renderer requires exactly five ASCII decimal digits in `20000..60999`, must use the single exact host `marketplace.open-trust-layer.org`, and always proxies to exact IPv4 loopback `127.0.0.1`. It does not accept an arbitrary hostname, IP, URL, file path, TLS setting, shell expression or request header from its arguments. Unknown options, malformed values and unsafe ports return one redacted `BLOCKED` marker with no configuration content.

The emitted candidate has only the host site block and a single `reverse_proxy` directive. It intentionally **does not** include a `tls internal`, plaintext `http://` site, TLS-insecure bypass, wildcard/catch-all vhost, `forward_auth`, public listener, or any other unreviewed feature.

## Required independent operational gates

1. **No VPS change by this command.** No SSH, Caddy binary, systemd, subprocess, socket, browser, DNS, filesystem write, PostgreSQL, credential, backup or certificate operation occurs in default, import or review-render paths.
2. **Existing vhosts first.** Independently verify the actual VPS, Caddy version, full effective configuration (including imports, dynamic configuration, existing vhosts and cert policies), named operator ownership, DNS A/AAAA and current SNI failure. Never replace the root Caddyfile or disturb other websites/services.
3. **Private upstream first.** Independently verify the proposed localhost port is unoccupied and that a *separately reviewed production-authenticated app* is ready, bounded, least privileged and served **only** to the intended local proxy. The existing evaluator command `tools/marketplace_localhost.py` is **not** the production service.
4. **TLS and session security.** Confirm an operator-approved publicly valid certificate for `marketplace.open-trust-layer.org`, correct Caddy SNI/Host/Origin handling, trusted proxy/authentication boundary, HTTPS redirects, secure headers, request bounds, security rate limits and negative cases. Do not disable certificate verification.
5. **Persistence and rollout.** Provision an isolated least-privilege database and credentials under separate authority, verify encrypted backup **and restore**, migration/rollback plan, monitored service lifecycle, rate limits, source artifact integrity, release ownership, customer policy and invitation constraints. Payments remain OFF.
6. **Real alpha acceptance.** Require real authenticated seller/buyer browser evidence: explicit **Publish Agreement**, seller `seller-delivery` claimed completion and an independently validated non-secret Evidence V1 record; closed [#525](https://github.com/open-trust-layer/marketplace/issues/525) and a green CI check are not substitutes.

Only after these gates and **separate, scoped operator deployment authorization** may a reviewed vhost change be proposed, staged, validated and rolled back if necessary. This module provides no privileged deployment or testing authority.

## Validation and rollback

```sh
python -m unittest tests.test_marketplace_caddy_vhost_candidate -v
```

A source PR using this tool requires the existing full Marketplace conformance CI, source review and exact-head merge conditions. Any rollback of this source-only helper is a normal source revert. **It cannot roll back a production Caddy change because it never made one.**
