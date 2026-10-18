# Marketplace: real Caddy HTTPS to separate-UID Unix ASGI — opt-in only

**Status: disposable Linux acceptance test, NOT staging/production deployment.**

The two previous independent tests proved (a) a real Caddy v2.11.7 process can reach the reviewed Unix/ASGI edge over local HTTPS, but shared the same Unix user with the backend; and (b) a real Unix server under backend UID 1101 correctly rejects a separate unauthorized UID and accepts a Caddy-like UID 2101, but the authorized client was not actual Caddy. This new test combines these into a *single, authentic multi-process integration path*.

It is only enabled if **both** the exact `MARKETPLACE_CADDY_DISTINCT_USERNS_TEST` opt-in token and an absolute `MARKETPLACE_CADDY_INTEROP_BIN` path to a pre-verified Caddy executable are provided, and a non-host-root subordinate-ID Linux namespace with mapped ranges is detected. Normal Windows/CI discovery skips it safely. Do **not** run as privileged host root or enable new kernel namespace settings just for this gate.

## Safety and interaction

- Temporary directory `/tmp/mkt-caddy-distinct-userns-...`, owned inside the new namespace by **backend UID 1101, Caddy group GID 2101**, mode `2750`. The actual `marketplace-edge.sock` is mode `0660`, backend owner and Caddy group. No preexisting file is replaced.
- Independent backend process runs as **UID/GID 1101/1101**, and uses the real `SO_PEERCRED` verifier requiring an exact client **UID/GID 2101/2101**, then the reviewed HTTP/1.1/ASGI/Host/Origin chain. It accepts exactly two transport connections and issues only one successful application response.
- Unrelated local UID/GID 3101/3101 is denied by filesystem traversal; peer UID/GID 2102/2101 is group-authorized to connect, then rejected by the kernel credential check, **without reaching the in-memory app**.
- **Actual Caddy executable**, adapted and launched under its own separate **UID/GID 2101/2101**, uses the exact merged inert Unix-upstream review directives. Its test-local host/Unix path/HTTPS port/certificate are substituted in memory, Caddy admin API disabled, config/data HOME isolated and writable only by the Caddy UID. Caddy TLS binds **127.0.0.1** on an ephemeral high port. The HTTPS client validates a test-only one-day SAN certificate, the exact Marketplace hostname and response. Fake browser-supplied forwarding values are overwritten or rejected by the real proxy plus verified edge.
- The ASGI application is an in-memory stub; **no real buyers, sellers, keys, PostgreSQL, Moon Coin transfers, accounts, payments, public DNS, VPS, global Caddy or TLS/ACME actions**. Test-owned Caddy and backend processes are terminated and their temporary keys, configs and socket removed.

## Reproducible independent gate

On a **separate, trusted Linux test machine** with existing subordinate UID/GID mappings, run from a disposable exact-source checkout. Verify the official Caddy release and its published cryptographic checksum before supplying its executable path:

```sh
unshare --user --map-auto --setuid 0 --setgid 0 --fork \
  env MARKETPLACE_CADDY_DISTINCT_USERNS_TEST=RUN_MARKETPLACE_REAL_CADDY_DISTINCT_USERNS_V1 \
      MARKETPLACE_CADDY_INTEROP_BIN=/ABSOLUTE/PATH/TO/VERIFIED/CADDY \
      PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. \
      python3 -m unittest tests.test_marketplace_caddy_distinct_uid_interop -v
```

The path to the verified Caddy binary must be traversable/executable by the mapped non-root Caddy identity. If unavailable, this opt-in test must be reported as **not executed**, never silently replaced by a same-UID result. It is intentionally skipped in the ordinary full acceptance suite; the independent Linux result must be recorded separately with the exact source commit.

## What the test does **not** prove

The user IDs above exist only in a disposable unprivileged user namespace. This is **not** evidence that the selected VPS actually has those accounts, group membership, permissions or service unit identities. The public `marketplace.open-trust-layer.org` TLS/SNI certificate still requires independent verification and repair. A persistent Marketplace service needs bounded concurrency and backpressure, a dedicated account, monitoring and rollback; separate isolated PostgreSQL role, secrets and **tested backup/restoration**; and actual signed two-principal authenticated browser Agreement publication plus seller `seller-delivery` Evidence V1. Staging on the shared VPS and any Caddy/DNS/certificate change must have **separately scoped operational authorization**, preserving all neighboring Moon services.

The release tracker is [#528](https://github.com/open-trust-layer/marketplace/issues/528). All changes here are inert test code and documentation only.
