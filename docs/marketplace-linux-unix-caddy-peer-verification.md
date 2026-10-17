# Linux kernel-attested Caddy Unix peer — source-only

**Scope:** source-level Linux `AF_UNIX` transport verification for the Marketplace private-alpha edge. Not an operating server or authorization to deploy.

**Current source baseline:** Marketplace main `14e58a2d9256f2bc22bff861cf5198ca7b7e3cf5`, independent full [CI #39052115686](https://github.com/open-trust-layer/marketplace/actions/runs/39052115686) SUCCESS.

## Motivation and implementation

The Caddy-to-ASGI normalization seam from PR #589 requires a real transport-identity verifier, rather than trusting `127.0.0.1`, a user-supplied `X-Forwarded-Proto`, `Host`, or a nominally true stub. This change provides the first kernel-attested implementation for **Linux only**:

- `MarketplaceLinuxUnixCaddyPeerVerifier` takes a reviewed, exact absolute Unix listener path and the **non-root UID/GID of the Caddy service**. These values must be obtained directly by the operator at staging time; no identifiers or path are invented as production facts.
- For each request, the hosting ASGI server **must attach the actual accepted `socket.socket` object** under the internal-only key `marketplace.internal.accepted_unix_socket`. This cannot be supplied through raw HTTP headers, cookies, remote IPs, or request bodies. The verifier checks exact real socket type, AF_UNIX stream transport, connected state, exact accepted local socket path, positive kernel peer PID and Linux `SO_PEERCRED` UID/GID equal to reviewed Caddy identity. Everything else fails closed.
- No listener, socket bind, network connection, server, credential, DB, package, TLS setting or service is created on module import or construction. On Windows/non-Linux platforms the verifier denies, rather than silently substituting a weaker identity check.
- `MarketplaceAttestedCaddyEdgeAsgiAdapter` now **strips the private accepted socket object from the copied scope** before delegating to the canonical-origin guard and product application. The original server-owned scope remains unchanged; the socket object is not exposed to application/auth handlers. Unknown forwarding headers, forged origins and user-supplied socket-like text remain rejected.

## Operational boundary still to be implemented

**This module does not yet make Marketplace deployable.** Stock Uvicorn ASGI does not expose a Python accepted connection socket in the HTTP scope with this private key. A separately reviewed Unix-socket-capable HTTP/ASGI server adapter must own the actual `accept()` lifecycle, bind precisely one real accepted socket to its request scopes, preserve ownership until all requests complete, avoid user-controlled scope fields, avoid FD passing to untrusted request handlers, and prove that requests cannot cross between connections.

The operator must separately verify and implement:
- Caddy service UID/GID and an independently configured **different**, least-privileged Marketplace service identity; exact Unix listener path, creation/ownership/mode and protected parent directories. A user sharing Caddy's UID/GID could otherwise impersonate Caddy, so dedicated service identity and OS access controls are essential.
- A secure listener whose Unix-domain socket path is owned by the Marketplace service and writable/connectable only to authorized Caddy. Restrict the server process to this socket; no TCP wildcard, public loopback bypass, socket forwarding from unauthorized users or symlink/path replacement.
- Actual correct Caddy `reverse_proxy` Unix-upstream syntax/version, TLS and public SNI certificate at **https://marketplace.open-trust-layer.org/**, valid Host/Origin and forwarded-header handling, and full security tests including local untrusted-client attempts and replay/session cases.
- Separate approved Marketplace PostgreSQL database/role, isolated backups **and restore**, monitoring, rate limiting, lifecycle, incident and release/rollback operator. Product seller/buyer authenticated Agreement-publish and `seller-delivery` Evidence V1 are unverified live; a source unit test does not satisfy them.
- Independent end-to-end staging evidence and **separate scoped runtime/deployment authority** under [hosting issue #528](https://github.com/open-trust-layer/marketplace/issues/528), preserving the neighboring production sites.

This source change is not permission to run Caddy, open a port, mount a socket, install a service or load private credentials. It does not change Moon Marketplace health reporting or launch payments.

## Tests and rollback

```sh
PYTHONPATH=src:. python3 -m unittest tests.test_linux_unix_caddy_peer tests.test_attested_caddy_edge tests.test_canonical_origin_guard -v
```

The positive tests use a **real local temporary Linux AF_UNIX listener/client/accept triple**, inspect actual `SO_PEERCRED`, test wrong UID/GID/path, client/listener/closed socket denial, and verify the accepted socket capability never enters downstream ASGI product scope. These local tests create and destroy only their isolated temporary sockets. Windows CI skips Linux-only positive socket tests but still executes portable structural rejection tests; Linux integration evidence is required before declaring the OS boundary validated.

Any source rollback reverts this module and the associated scope-stripping change. There is no corresponding production state to roll back, because no deployment is performed here.
