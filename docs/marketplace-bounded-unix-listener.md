# Private Marketplace bounded Unix listener — source-only

**Scope:** opt-in, short-duration foreground local Unix-listener component for a future separately reviewed deployment. **Not a production launch, service installer, or authority to change the VPS.** The owner-selected VPS is **open-trust-layer.org**, canonical origin **https://marketplace.open-trust-layer.org/**.

## Connection path

A future operator-owned dedicated Marketplace service may compose the approved canonical Host/Origin guard, Caddy metadata normalizer, Linux `SO_PEERCRED` verifier, single-request HTTP/1.1-to-ASGI adapter, and **this** bounded listener. The listener has no default process or server startup. A caller must explicitly invoke `serve_bounded_marketplace_unix_foreground` with exact authorization string `EXECUTE_BOUNDED_MARKETPLACE_UNIX_EDGE_FOREGROUND_V1` and an exact Linux peer-verifier composition.

This is **source code only**, not invoked from `tools/marketplace_localhost.py`, `moon.manifest.yaml`, Caddy, a workflow deployment job, or a systemd unit.

The caller must precreate a private absolute directory, owned by the **non-root Marketplace process UID**, with no world access or group write. Symlinks, mismatched/relative paths and existing targets are rejected. Only a literal fixed socket basename `marketplace-edge.sock` may be created, and its exact resulting path must match the kernel verifier's pre-reviewed path. The listener binds an AF_UNIX stream socket with `0660` mode and a small backlog. It **never removes or replaces a pre-existing socket, regular file or symlink**. On completion it unlinks only the same socket inode it bound.

The source enforces up to 16 accepted connections, at most 2 active requests and a maximum 20-second foreground accept lifetime, with stricter runtime limits allowed. Each accepted connection is handled by the reviewed single-request transport, which kernel-verifies the true Unix peer before reading bytes, rejects ambiguous HTTP/1.1 framing and untrusted forwarding headers, protects application Host/Origin and closes the connection. No wildcard TCP, HTTPS/ACME action, public ingress, credential storage, database or application service is started.

## Security limitations — why this is **not** a deployable service

- **Caddy UID/GID and Marketplace UID/GID must be separate, non-root and administratively verified**. Tests use the same local test account on one machine to exercise kernel properties; that is not production isolation. Actual Unix listener filesystem directory and group permissions must allow only the real Caddy worker to connect. Otherwise any local process sharing that UID or group can potentially reach this private socket.
- The listener is an explicitly bounded foreground code path, not a resilient daemon. It has no persistent process supervisor, atomically installed service unit, authenticated operator control channel, systemd sandbox, startup/rollback provider, version-linked live health, global abuse/rate limits, orchestration, gracefully coordinated shutdown or service-oriented metrics. The max 2 requests/20s acceptance cap is intended for safe staging probes, not user traffic.
- Caddy's real Unix-upstream behavior, response framing, per-request Host/Origin metadata, trusted peer identity, file ownership/ACLs, and platform versions need end-to-end tests. The existing `X-Forwarded-*` normalization is safe only in the reviewed kernel-verified chain, never as a free-standing HTTP trust assertion.
- TLS/SNI for `marketplace.open-trust-layer.org` has been repeatedly observed failing with `tlsv1 alert internal error`. Neither this source nor green CI fixes certificates or Caddy vhosts.
- A true private alpha needs the separately reviewed authenticated ASGI application service and isolated PostgreSQL role/storage, validated backups **and restoration**, privacy/retention controls, actual signed two-principal buyer/seller Agreement publication and seller-attributed delivery Evidence V1, legitimate customer invitations, incident/rollback controls and owner-approved rollout. Payments and public signup remain OFF.
- **Do not run this on the selected VPS, open public ports, modify Caddy/systemd or handle secrets without separate operational authority**. No source test implies a valid deployment.

## Offline acceptance

```sh
PYTHONPATH=src:. python3 -m unittest tests.test_unix_listener tests.test_unix_http11_asgi tests.test_linux_unix_caddy_peer tests.test_attested_caddy_edge tests.test_canonical_origin_guard -v
```

On a non-root Linux disposable test host, tests create only temporary Unix sockets and clean up. They verify authorized/unauthorized peer cases, two bounded local requests, cross-origin rejection, no unexpected unlink, private directory enforcement, limits and idle deadline, plus all prior real-socket/ASGI security regressions. Windows CI skips Linux-specific positive socket tests and still runs portable checks; require independent Linux PASS in addition to exact-head full CI.

## Non-authority and rollback

Source-only addition. Nothing runs on import; no VPS installation, Caddy/TLS/DNS/PG/network egress, customers or Moon production heartbeat change. Reverting the source PR rolls back this code. The release blockers are tracked in [#528](https://github.com/open-trust-layer/marketplace/issues/528).
