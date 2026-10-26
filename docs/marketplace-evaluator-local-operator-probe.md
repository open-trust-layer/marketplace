# Marketplace evaluator: local operator-only database probe

Tracker: [#525](https://github.com/open-trust-layer/marketplace/issues/525).

## Purpose and authority

This **source-only** helper addresses the blocked evaluator database-credential
gate without bringing the protected credential into ChatGPT, a remote MCP tool,
GitHub CI, issues, logs, or command-line arguments. It is **not an authenticated
buyer/seller flight**, not runtime acceptance, and not authorization to deploy
anything. Source delivery and the operator's separate live execution approval
are distinct.

The launcher is intended for an authorized **operator console** on the same
Windows Machine, under the same Windows account that originally encrypted
`D:\MarketplaceEvaluatorFresh\secrets\marketplace-evaluator.dpapi`.
**Never run through remote execution**, ChatGPT terminal/Desktop Commander,
GitHub Actions, an unattended scheduler, or a shared broker. An earlier
credential-handling tool operation was blocked by a safety control; do not
retry it through a different tool or conceal it inside another command.

The operator reviews the script, starts the already reviewed **isolated**
PostgreSQL cluster independently (only `127.0.0.1:15432`, not the Johnny 5
database on `127.0.0.1:5432`), checks the exact listener and database
directory, then explicitly runs this helper locally. The script itself never
starts, stops, migrates, or configures PostgreSQL; it does not start an HTTP
server, browser, or authenticated Marketplace application.

## Exact source and environment

Before using the launcher, obtain the newly verified protected Marketplace
`main` merge SHA and reviewed pinned OLP SHA. Do not reuse example SHAs
across later merges. The launcher requires both detached/clean local checkouts
and the operator's reviewed isolated virtualenv Python. It fails closed if
the source, executable, database listener or expected PostgreSQL process
is missing or differs. The listener PID must resolve to `postgres.exe` whose
Windows process command line contains an **exact** `-D` data-directory
argument for `D:\MarketplaceEvaluatorFresh\pgdata`. PostgreSQL may render
the same Windows path as `D:/MarketplaceEvaluatorFresh/pgdata`; the launcher
normalizes only path separators before matching this exact argument. Merely
mentioning the expected path elsewhere, a similarly prefixed directory, or a
different `-D` target is rejected. The data-directory check does not replace
the explicit local operator confirmation or restricted SQL identity probe.

The reviewed evaluator identity is fixed inside the Python probe:

- host `127.0.0.1`, TCP port `15432`;
- database and login `marketplace_evaluator`;
- a single read-only connection with six-second connect timeout;
- session transaction read-only, five-second statement timeout;
- two constant `SELECT` queries: exact connection identity/read-only state
  and absence of superuser, create-db, create-role, replication or bypass-RLS
  capabilities.

The password is decrypted only in the local operator's PowerShell process,
from that account's existing protected `ConvertFrom-SecureString` file, and
passed to the one child Python process via a transient environment variable.
The script does not write or print plaintext, DSNs, PostgreSQL errors, or
decrypted bytes. Temporary process material is cleared to the extent
supported by PowerShell; Windows process memory is not a cryptographic
erasure guarantee. Do not enable shell transcripts, PowerShell debugging,
verbose error capture or screen recording for this procedure.

## Local-only instructions (do not execute from this chat)

At the Windows Machine **operator console**, after reviewing the checked-out
files, navigate to the Marketplace checkout. Substitute the actual approved,
current 40-character SHAs and the paths of the isolated checkouts.

First inspect the inert source gate; it never opens the protected file:

```powershell
.\tools\marketplace_evaluator_operator_probe.ps1 `
  -ExpectedMarketplaceSha '<reviewed-40-char-Marketplace-merge-SHA>' `
  -ExpectedOlpSha '<reviewed-40-char-OLP-SHA>' `
  -OlpRoot 'D:\MarketplaceEvaluatorFresh\marketplace-sources-main-94d659bc-20261016\olp' `
  -PythonPath 'D:\MarketplaceEvaluatorFresh\marketplace-sources-main-94d659bc-20261016\evaluator-venv\Scripts\python.exe'
```

Only after separate approval for live restricted SQL and a fresh exact-target
check, the operator may rerun that command **locally** with
`-ExecuteLocalOperatorProbe`. The launcher requires them to type the
literal `RUN LOCAL READONLY PROBE` at the prompt. Do not paste credentials
into a command or reply.

On success, share **only** this fixed, non-secret receipt:

```text
status=LOCAL_EVALUATOR_RESTRICTED_READONLY_VERIFIED host=127.0.0.1 port=15432 identity=marketplace_evaluator credential_emitted=false schema_mutation=false browser_invoked=false server_invoked=false runtime_acceptance=false
```

Failure returns `status=BLOCKED code=...` with a fixed category. There is
no fallback to `localhost`, remote PostgreSQL, `5432`, alternative
database accounts, environment-supplied DSNs or connection strings. If the
Windows account cannot unlock the protected file, stop and recover via the
original operator-controlled account or explicitly approved credential
reprovisioning. Do not weaken DPAPI or PostgreSQL authentication.

## Non-authority and rollback

Even a PASS establishes only a restricted read-only evaluator DB connection.
A **fresh**, separately approved browser-key ceremony, newly signed lease,
same-origin preflight, authorized authenticated server and actual two-party
Agreement publication / seller `CLAIMED_COMPLETE_PERFORMANCE` evidence
remain mandatory. Do not reuse the discarded October 17 temporary bundle.
Offline Evidence V1 validation is still required before #525 can close.

Source rollback: revert this source-only PR after checks; no credential,
database or network change results from CI/source review. Runtime rollback
and cleanup belong to the operator controlling the isolated test cluster,
not to this probe.
