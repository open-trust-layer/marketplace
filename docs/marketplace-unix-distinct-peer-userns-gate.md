# Real separate-service Unix peer isolation — isolated user-namespace gate

**Scope: opt-in source test only. No production deployment or machine account mutations.**

Earlier Marketplace integration tests used the same disposable Linux UID to run Caddy and its Unix backend, so a kernel `SO_PEERCRED` positive result did **not** prove different process identities could be enforced. The `tests/test_unix_distinct_peer_userns.py` gate exercises a real Linux temporary AF_UNIX socket with **three independent non-root UIDs** inside an **unprivileged subordinate-ID user namespace**, without sudo, Docker, global account changes or VPS operations.

The test runs only when explicitly supplied `MARKETPLACE_DISTINCT_USERNS_TEST=RUN_MARKETPLACE_DISTINCT_UNIX_USERNS_V1` in an isolated user namespace where the test process has mapped effective UID/GID zero. In normal CI and on ordinary Linux hosts without this opt-in it is **skipped**. The test also explicitly checks `/proc/self/uid_map` and `/proc/self/gid_map` for a subordinate range mapping with inner UID/GID zero mapped to outside IDs at or above 65536; **actual host root, a single-UID remap and namespaces with insufficient mapped identities cannot execute the test**, even if someone sets the opt-in environment variable. Never run as actual host root.

The temporary private socket directory belongs to backend UID 1101 and the Caddy group GID 2101, mode `2750`; the bound socket is `0660` and inherits that group. A source-reviewed bounded listener is owned by backend UID/GID 1101. The kernel verifier requires exact accepted peer UID/GID 2101/2101. Three real child processes exercise the boundary:

- UID/GID 3101/3101: cannot traverse/connect to the private socket path due to Unix filesystem permissions, with no accepted backend request.
- UID 2102 with GID 2101: can traverse/connect by group, but fails **kernel `SO_PEERCRED` UID verification** and must not enter the in-memory application.
- UID/GID 2101/2101: authorized Caddy-like peer can connect, passes exact kernel identity and receives HTTP 200 through the real canonical Host/Origin guard.

The backend accepts exactly two socket connections (kernel-denied and authorized), and its application is invoked once. The unauthorized filesystem-denied connection never reaches the backend. All processes and temporary files are owned exclusively by the test; no ports, services, Caddy daemon, real PostgreSQL, user accounts, credentials, external network or production data are opened.

## Example disposable test-host invocation

Only on an independent trusted Linux test machine with working unprivileged subordinate UID/GID mappings and the Marketplace source available to mapped IDs:

```sh
unshare --user --map-auto --setuid 0 --setgid 0 --fork \
  env MARKETPLACE_DISTINCT_USERNS_TEST=RUN_MARKETPLACE_DISTINCT_UNIX_USERNS_V1 \
      PYTHONPATH=src:. python3 -m unittest tests.test_unix_distinct_peer_userns -v
```

The root-like identity **exists only inside the fresh Linux user namespace**; this command cannot become a privileged host user and must never be used as justification to run privileged tests on a production host. Where user namespace creation is unavailable or disabled, the gate is BLOCKED rather than substituting mocks. Do not change kernel user-namespace sysctls or permissions solely to enable a test.

**Remaining limitations:** even real distinct-UID test PASS does not prove the target VPS's actual Caddy UID/GID, directory ownership and ACLs, Unix upstream effective routing, Caddy version, public TLS/SNI, production service supervision, genuine authenticated two-browser Agreement/seller-delivery Evidence V1 or isolated PostgreSQL backup with tested restore. Real production accounts and startup require separately scoped operator authorization. All live-host changes remain blocked under [#528](https://github.com/open-trust-layer/marketplace/issues/528).

Source-only rollback: revert this test and documentation. It changes no deployed artifact or service.
