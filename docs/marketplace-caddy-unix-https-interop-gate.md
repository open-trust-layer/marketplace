# Opt-in local Caddy HTTPS-to-Unix interoperability gate

**Status:** isolated nonproduction test; not a Caddy deployment or production launch.

This test closes one source-level evidence gap: does a real Caddy executable forward a *real authenticated HTTPS browser-like request* through a Unix upstream to the Marketplace source's Linux `SO_PEERCRED` verifier, request framer, ASGI edge and strict Host/Origin guard?

`tests/test_marketplace_caddy_unix_interop.py` provides an **opt-in** integration test. It is **skipped in normal CI** unless `MARKETPLACE_CADDY_INTEROP_BIN` is explicitly supplied as an absolute executable path. Import and default test discovery create no Caddy process, listener, TLS certificate, network socket or persistent file.

With the opt-in, run it **only on a disposable, separate non-root Linux test machine**, not the shared VPS:

```sh
MARKETPLACE_CADDY_INTEROP_BIN=/ABSOLUTE/PATH/TO/VERIFIED/CADDY \
PYTHONPATH=src:. python3 -m unittest tests.test_marketplace_caddy_unix_interop -v
```

The operator must independently fetch and checksum-verify an **official pinned Caddy binary**. This test does not fetch packages or silently trust an arbitrary binary. It assumes an installed OpenSSL executable for a temporary self-signed test certificate. An expected `openssl s_client` default trusted-host check is **not** used: Python's SSL client explicitly validates the ephemeral certificate with its own trust store and verifies the canonical hostname. The test opens an OS-assigned **127.0.0.1-only** HTTPS listener and a temporary AF_UNIX socket, never a public interface; Caddy's admin API is disabled and its configuration/home paths are temporary.

The test derives its outbound upstream directives from the **merged inert Unix Caddy review candidate**, with controlled test-only substitutions for the ephemeral private socket path, loopback-bound TLS endpoint and self-signed certificate. It first calls `caddy adapt` without service startup; only then does it launch a bounded subprocess on the same disposable test host. It tests HTTPS GET with canonical encoded query, a same-origin POST, denied POST without Origin and denied foreign-Origin POST. The same real proxy process then receives attacker-supplied `Forwarded`, `X-Real-IP`, `X-Forwarded-Proto` and `X-Forwarded-Host` headers; approved upstream normalization must prevent them from becoming a forged identity or protocol, while an unknown `X-Forwarded-*` field must be rejected by the attested edge. For negative cases, HTTP responses must use fixed, non-reflective denial codes. The ASGI product stub is in memory only; it issues **no real sessions, keys, accounts, agreements, orders, payments, or DB operations**. The test confirms no socket capability leaks into the stub.

**Critical limitation:** local test Caddy and local ASGI test process share the same Linux UID/GID, solely so a normal disposable test account can exercise the real kernel credential path. This is **not production process isolation**. The VPS rollout must use separate identities, a correctly permissioned Unix directory and the real Caddy UID/GID, with a separate unauthorized-local-peer negative test under actual service identities. These header tests do **not** substitute for OS-level different-UID isolation.

The test always terminates its owned Caddy subprocess, cancels pending foreground tasks on failure and deletes its own temporary socket, config and TLS key. It does not install Caddy, alter global or existing Caddy configuration, invoke systemd, contact Let's Encrypt, run ACME challenges, change DNS or access the public VPS.

**Remaining independent release blockers:** VPS Caddy effective configuration (including imports), Marketplace-hostname SNI/ACME certificate, actual Caddy-to-ASGI permissions and differing service identities, full request framing including larger uploads and retries, production-grade supervisor/capacity/backpressure, authenticated app composition, isolated PostgreSQL with backup **and restored copy**, fresh seller/buyer signed Evidence V1, and a separately scoped staging/deployment authorization. A local smoke PASS is not a live-host or customer-readiness PASS.

Track source and hosting boundaries in [#528](https://github.com/open-trust-layer/marketplace/issues/528). Rollback is a source revert; this test creates no lasting service.
