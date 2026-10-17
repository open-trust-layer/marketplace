# Marketplace canonical HTTPS/SNI preflight — source-only

**Scope:** narrow, opt-in, read-only diagnosis of the **public TLS certificate and SNI handshake**, not a Marketplace product health check.

**Approved target:** existing open-trust-layer.org VPS, canonical origin **https://marketplace.open-trust-layer.org/**. The prior verified DNS A result was `168.113.210.63`, but that address is **not pinned** or assumed permanent. At the October 17 checkpoint, external HTTPS failed during TLS negotiation with `internal error`; successful source/CI gates do not mean this endpoint works.

## Boundary and execution

The script is **inert by default**:

```sh
python tools/marketplace_canonical_https_preflight.py
# status=INERT_CANONICAL_HTTPS_PROBE_NOT_RUN
```

The separately selected **explicit read-only external-network invocation** is:

```sh
python tools/marketplace_canonical_https_preflight.py --probe-canonical-https PROBE_MARKETPLACE_CANONICAL_HTTPS_READONLY_V1
```

The opt-in performs one bounded, IPv4-only DNS lookup and, only if **all** candidate destinations are globally routable public IPv4 addresses, one direct numeric-IP TCP connection on port **443**, with exact TLS SNI and hostname verification for `marketplace.open-trust-layer.org`. It uses Python's default public-root certificate verifier, enforces `CERT_REQUIRED`, `check_hostname=True`, minimum TLS 1.2, and a five-second connection/socket timeout.

The CLI cannot accept a host, IP address, URL, port, CA bundle, HTTP method, path, proxy, TLS-insecure option or additional flags. The only server interaction is a TLS handshake; **no HTTP GET/HEAD/POST**, browser, session token, private key, cookie, database operation or customer payload is used. Return codes and output are bounded fixed tokens without exceptions, certificate bodies, source paths, IPs or credentials.

DNS and TLS results use fail-closed redacted outcomes such as `status=BLOCKED_DNS_UNSAFE`, `status=BLOCKED_TLS_CERTIFICATE`, `status=BLOCKED_TLS_HANDSHAKE`, or `status=BLOCKED_TLS_TRANSPORT`. Invalid opt-ins return exit code 2. External probing failures return exit code 3. Successful validated TLS returns `status=CANONICAL_HTTPS_TLS_VERIFIED`, exit code 0.

**Even a valid public TLS certificate and successful handshake proves only that transport property.** It does **not** establish valid HTTP reverse-proxy routing, an installed/authenticated Marketplace application, exact `main` backend, production release, database isolation/backup, invitation policy, two-principal signed browser Evidence V1, or that Moon Company's Marketplace heartbeat is live.

## Operational stop conditions

- No live command runs on import, tests, default CLI or this source-only PR. An operator must separately authorize/exercise external network probing in the appropriate environment.
- No socket is opened if DNS is missing, malformed, non-public, oversized or mixed with non-public addresses. IPv6-only results are not supported by this narrowly scoped profile.
- If the TLS check fails, stop and investigate the selected VPS's actual vhosts/certificates/SNI, ACME/issuer challenge readiness, and existing websites using separately approved read-only operations. Do not disable verification, accept a self-signed certificate, change DNS or replace the Caddyfile just to silence the diagnostic.
- Before a production change, review the full effective Caddy config, existing website constraints, app ownership/privilege boundaries, dedicated PostgreSQL and backups, staging, rollback and actual authenticated browser acceptance in [#528](https://github.com/open-trust-layer/marketplace/issues/528).
- Certificate/transport verification is not a DNSSEC or domain-ownership attestation and does not guarantee a complete HTTP application.

## Validation

```sh
python -m unittest tests.test_marketplace_canonical_https_preflight -v
```

The tests use injected, entirely synthetic resolver/socket/TLS providers and exercise allowed host/SNI, public DNS validation, unsafe DNS rejection, no-run defaults, redaction, certificate failures, timeouts, bad TLS configuration and opt-in gating. They make **zero external network connections**. The existing full Marketplace conformance CI is required for the final exact PR head; merged-main independent CI is required afterward.

**Rollback:** revert this source-only change. It never configures the VPS or changes its running state.
