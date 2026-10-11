# Authenticated Marketplace local-flight prerequisite presence check

Issue: [#525](https://github.com/open-trust-layer/marketplace/issues/525).

This is an **inert, read-only presence check** to narrow setup gaps before
the reviewed authenticated PostgreSQL localhost preflight. It is not the
authenticated preflight itself, a credential validator, a source provenance
check, or a live buyer/seller browser acceptance. A successful result never
authorizes execution.

The standard-library tool `tools/marketplace_authenticated_flight_prerequisites.py`
checks only:

- Python 3.11 or newer;
- whether `MARKETPLACE_POSTGRES_DSN` is present, non-whitespace and no more
  than 8192 characters (it **never prints or parses the DSN**);
- the existence of operator-supplied absolute provisioning and pinned OLP
  source **directories** (it does not open provisioning files, validate keys,
  resolve the OLP revision, or disclose paths);
- whether the current Python environment can locate the reviewed top-level
  dependencies `psycopg`, `uvicorn` and `cryptography` **without importing
  them**.

The check uses filesystem directory metadata only. Directory presence does
not establish provisioning validity or verify a pinned OLP commit. Missing
inputs produce stable category codes rather than local paths or credential
contents; a `PREREQUISITES_PRESENT_UNVERIFIED` result means only that the
initial superficial checks passed.

## Example on X230i / Linux

From a fresh reviewed Marketplace `main` checkout, with the PostgreSQL DSN
**already configured locally without echoing or committing it**:

```bash
python3 tools/marketplace_authenticated_flight_prerequisites.py \
  --provisioning-directory "/absolute/local/path/to/marketplace-auth" \
  --olp-src "/absolute/local/path/to/pinned-olp/src"
```

## Example on Windows / PowerShell

In the same separately prepared evaluator environment:

```powershell
python tools/marketplace_authenticated_flight_prerequisites.py `
  --provisioning-directory "C:\absolute\path\to\marketplace-auth" `
  --olp-src "C:\absolute\path\to\pinned-olp\src"
```

A missing prerequisite exits with code 1 and a bounded marker such as:

```text
status=BLOCKED codes=POSTGRES_DSN_ABSENT_OR_INVALID_LENGTH
postgres_connection_invoked=false server_invoked=false browser_invoked=false
authentication_provisioning_opened=false credentials_emitted=false
```

When presence checks pass, the first marker is
`status=PREREQUISITES_PRESENT_UNVERIFIED`. It does **not** say PASS, READY,
authorized, authenticated, or accepted.

## Next independent gates

1. Verify fresh clean `main`, pinned OLP revision, successful exact
   merged-main acceptance and dependency provenance separately.
2. Run the **existing inert, authenticated fulfillment-completion graph
   preflight** in `MARKETPLACE_MVP_ACCEPTANCE.md`, which reads the local
   provisioning material but connects to no database and starts no server.
3. Only under **separate explicit runtime authorization**, execute the
   reviewed loopback service on exact `127.0.0.1` and perform the two-party
   buyer/seller browser flight, then export and offline-validate non-secret
   evidence.

No credential provisioning, PostgreSQL connection, browser, socket, public
networking, payment, settlement, Moon heartbeat or production action is
triggered by this prerequisite checker. Remove the source-only change by
reverting its merge; there is no runtime or persistent state to roll back.
