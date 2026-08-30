# M62 — Explicit Opt-In Inbound HTTP Loopback Acceptance Harness

M62 adds a manual one-shot loopback acceptance boundary above the exact M59 → M55 source graph.
It is intentionally inert on import and is not a service, daemon, deployment entry point, or network authorization mechanism.

## Authority boundary

- source/CI acceptance != `NETWORK_EXTERNAL` authorization
- `--dry-run` != socket construction
- CLI opt-in token != project/user authorization
- `NETWORK_EXTERNAL` != `DEPLOY`
- loopback connection != peer authentication
- HTTP success != Marketplace truth, trust, ownership, or authorization

Actual live execution requires fresh explicit `NETWORK_EXTERNAL` authorization immediately before invocation.
Production/service activation remains separately `DEPLOY`.

## Safe dry run

```text
python tools/inbound_http_loopback_acceptance.py --port 18080 --dry-run
```

This composes and validates the exact M59 → M55 graph with an offline constructor that must never be invoked.
It prints only `M62_DRY_RUN_READY` on success.

## Live command shape — do not run without fresh authorization

```text
python tools/inbound_http_loopback_acceptance.py --port 18080 \
  --execute-one-loopback-network-session EXECUTE_ONE_LOOPBACK_NETWORK_SESSION
```

Only after the exact token is validated does the tool import/select `socket.socket`. M55 then remains one-shot:
one listener construction, one bind to fixed `127.0.0.1`, backlog one, one accept, one connection, one transaction, cleanup.
No loop, retry, polling, worker, thread, task, daemon, persistence, queue, pool, DNS, TLS, credential, or provider-admin surface is added.
