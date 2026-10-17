# Marketplace Caddy-to-ASGI trusted edge — inert source contract

**Risk:** MODERATE source-only security component, **not integrated or deployed**.

**Selected public origin:** https://marketplace.open-trust-layer.org/ on the existing open-trust-layer.org VPS. Prior external TLS handshakes with Marketplace SNI failed. There is no live authenticated Marketplace production service under this feature.

## Problem and deliberate non-authority

Caddy normally forwards `X-Forwarded-For`, `X-Forwarded-Host` and `X-Forwarded-Proto`. Its loopback HTTP upstream is normally presented to an ASGI application as scheme `http`. The reviewed `MarketplaceCanonicalOriginAsgiGuard` correctly rejects these potentially untrusted forwarding headers and requires a verified `https` scheme. Connecting the two directly is not a reviewed release path.

The new `MarketplaceAttestedCaddyEdgeAsgiAdapter` is an **unwired, dependency-free ASGI wrapper** that demonstrates one strictly gated normalization contract. It requires:
1. an exact existing `MarketplaceCanonicalOriginAsgiGuard`;
2. an explicit **per-request** `verify_connection(scope)` provider, whose result must be the literal Python `True`;
3. a valid ASGI 3 HTTP scope from a local cleartext `http` upstream, with a bounded header set, exactly one canonical `Host`, exactly matching `X-Forwarded-Host` and exactly `X-Forwarded-Proto: https`.

It rejects requests with mismatched hosts, invalid forwarded scheme, duplicate forwarding/Host values, unknown `X-Forwarded-*`, `Forwarded`, `X-Real-IP`, prohibited original/rewrite metadata, malformed headers, unsupported scope, non-root mount, missing/false/raising verifier or unsafe header bytes. It emits only fixed, non-reflective `403` responses, without reading a request body or invoking the protected application.

Only **after** structural and peer verification does the wrapper strip Caddy-generated forwarding metadata (including all `X-Forwarded-For` client data, which is never promoted to auth identity), set a *copied* ASGI scope's scheme to `https`, and forward unchanged caller `Host`/`Origin` to the existing canonical-origin guard. That guard still enforces same-origin for mutation requests. The original scope stays unchanged.

## Critical unresolved trust dependency

The source deliberately provides **no positive production transport verifier**.

A Python verifier that simply returns `True`, checks `scope["client"] == ("127.0.0.1", ...)`, or trusts `X-Forwarded-Proto` is **not valid authorization**. A local process can potentially reach loopback and forge HTTP headers. A valid future production implementation must establish Caddy identity through an OS-enforced, narrowly scoped transport mechanism (for example a carefully permissioned Unix-domain socket plus trustworthy per-connection peer credentials or an equivalently reviewed authenticated private channel), prove the peer binding independently of user HTTP fields, and verify the ASGI server is not exposed on an unauthenticated TCP address. Uvicorn's generic forwarded-header parsing must not silently manufacture the peer or HTTPS authority used by this verifier.

Caddy's actual HTTP upstream and site configuration, service accounts, socket permissions, certificate acquisition, forwarded-header semantics, secure canonical Host/Origin flow, and ability to support trustworthy per-request transport evidence are **not verified or configured here**. If a trustworthy transport verifier cannot be provided, this wrapper must **remain disconnected**. Neither source tests nor a nominally `True` test double authorize deployment. Avoid disabling certificate verification, weakening the canonical guard, adding a wildcard listener, or weakening system isolation to make synthetic tests pass.

## Isolated integration acceptance required before any launch

The next separately scoped delivery must:
- pin exact versions and independent source/artifact provenance for the selected ASGI server and Caddy provider;
- implement the actual transport-attested verifier with strong connection provenance, OS-level service separation and no arbitrary-client access;
- prove forged local-client traffic and hostile `Host`, `Origin` and forwarding headers are denied while properly attested Caddy traffic passes;
- test valid browser authentication, duplicate/replayed sessions, signed seller/buyer principal separation, Agreement publication and `seller-delivery` completion on the composed ASGI path;
- validate real HTTPS/SNI and certificate hostname externally at **marketplace.open-trust-layer.org**; preserve all neighboring VPS vhosts and unrelated workloads;
- provide isolated PostgreSQL/database roles, backup and **restore**, non-destructive migration, resource headroom, monitoring, service lifecycle and rollback;
- obtain separate explicit operational authorization before executing or editing live TLS, Caddy, service, database or credential state on the selected VPS.

The owner-closed [issue #525](https://github.com/open-trust-layer/marketplace/issues/525) is not a substitute for live two-principal Evidence V1. Track the release blockers under [issue #528](https://github.com/open-trust-layer/marketplace/issues/528).

## Offline regression

```sh
PYTHONPATH=src:. python3 -m unittest tests.test_attested_caddy_edge -v
```

The tests use synthetic scopes and explicit test-double verifiers only; they start no server or network connection. They cover trusted vs untrusted peer, rejected loopback impersonation, forged headers, no Origin for mutating requests, scope immutability, redaction and no downstream call on denial.

The runtime import creates no listener, verifier, credentials, database state or proxy connection. This change never wires the wrapper into a Marketplace composition, Caddy config, localhost script, CI deployment, public website or Moon heartbeat. **Rollback** is simply reverting the source and tests.
