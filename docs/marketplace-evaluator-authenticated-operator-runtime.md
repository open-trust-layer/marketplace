# #525 — Operator-console authenticated Marketplace runtime handoff

This is a source-only procedure. It is NOT authorization for remote execution,
production deployment, payment, settlement or courier activation.
Use only at the original authorized interactive Windows Machine console, under
the original DPAPI user. NEVER run active mode through Desktop Commander,
GitHub Actions, a remote shell, an agent, a scheduler, or a transcript.
Never paste a password, DSN, private key, signed provisioning contents,
or public carrier into chat, GitHub, or logs.

## Why this exists

The inert authenticated fulfillment graph preflight passed but did not
initialize PostgreSQL, start HTTP, authenticate either browser or validate
Evidence V1. The existing operator read-only probe remains available
separately. This reviewed launcher combines an exact restricted identity
probe with a single locally approved authenticated runtime invocation.

## Preconditions

- Only the isolated evaluator PostgreSQL 16.15 on 127.0.0.1:15432 is active.
  It must use the reviewed executable with exactly one -D argument pointing
  to D:\MarketplaceEvaluatorFresh\pgdata. Do not touch Johnny5 port 5432.
- The Marketplace and pinned OLP checkouts are clean, at reviewed commits.
  Supply the newly merged Marketplace main SHA, not an example SHA.
- Evaluator Python lives at the reviewed isolated virtualenv path.
  DPAPI protected credential remains in its original user-bound local file.
- The two original seller and buyer browser sessions retain their
  non-extractable private keys at http://127.0.0.1:18480/.
  Do not close, reload or navigate away.
- Signed two-party provisioning is in a fresh isolated absolute directory
  outside the Git worktrees with >=1800 seconds of effective lease remaining.
  If expired, renew from the SAME preserved browser public keys.
- Manually stop ONLY the static preview foreground process (Ctrl+C) while
  keeping both browser pages alive. Confirm port 18480 is free.

## Inert source check — original Windows operator console only

Review the exact committed script and helper first. Run the inert check
with reviewed current SHA and the local bundle directory:

~~~powershell
cd C:\Users\ilyav\MarketplaceEvaluatorFlight-20261025\marketplace

$params = @{
    ExpectedMarketplaceSha = '<reviewed-current-40-character-main-SHA>'
    ExpectedOlpSha = '4e57057d5d946797814f33125f77c4b6732cbfda'
    OlpRoot = 'D:\MarketplaceEvaluatorFresh\marketplace-sources-main-94d659bc-20261016\olp'
    PythonPath = 'D:\MarketplaceEvaluatorFresh\marketplace-sources-main-94d659bc-20261016\evaluator-venv\Scripts\python.exe'
    AuthenticationProvisioningDirectory = '<fresh-approved-absolute-bundle-directory>'
}
& .\tools\marketplace_evaluator_operator_runtime.ps1 @params
~~~

Expected: status=OPERATOR_RUNTIME_INERT_READY
credential_opened=false postgres_connection_invoked=false
server_invoked=false browser_invoked=false

## Explicit active handoff — only under separate local operator approval

Use the SAME reviewed file and parameter table:

~~~powershell
& .\tools\marketplace_evaluator_operator_runtime.ps1 @params -ExecuteLocalOperatorRuntime
~~~

Active mode fails closed on source mismatch, unreviewed Python, unexpected
PostgreSQL listener/process, port collision, existing PG/credential environment
variables, invalid bundle or noninteractive execution. It collects the
seller and buyer browser PUBLIC key carriers through hidden console input,
verifies both signed bindings and >=1800-second remaining lease,
then requires the exact typed phrase RUN AUTHENTICATED LOCAL EVALUATOR
before touching DPAPI.

The original user-bound DPAPI password is decrypted only inside local
PowerShell, tested with the existing restricted read-only SQL identity probe,
and encoded into a loopback evaluator-only DSN in transient process
environment. No password or DSN is written to disk, logs, GitHub,
or command-line arguments. A finally block clears environment
variables and frees the unmanaged BSTR. Immutable managed string erasure
cannot be guaranteed.

No automatic PostgreSQL startup, preview shutdown, database role grants,
migration bypass, port reassignment, browser automation or production
deployment is performed.

If M17_5Y_DATABASE_INITIALIZATION_FAILED returns, stop and investigate
the actual evaluator database schema and migration permissions,
without privilege escalation, resetting data or touching port 5432.
Read-only identity PASS alone does not establish write access.

## Real acceptance gate after local server starts

Using preserved seller and buyer browser sessions, complete:
Listing → Proposal → Acceptance → Agreement formation →
explicit Publish Agreement → seller CLAIMED_COMPLETE_PERFORMANCE
for seller-delivery.

Export non-secret MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1
JSON and validate offline with
tools/marketplace_authenticated_local_flight_evidence.py.

Only a genuine PostgreSQL-backed two-browser flight with offline
validator PASS closes issue #525:
https://github.com/open-trust-layer/marketplace/issues/525

Report fixed non-secret markers, exact reviewed main SHA and CI link.
Never put protected credentials, raw DSNs, private keys, public carriers,
or provisioning material into issue comments or artifacts. The public
binding preflight does not prove private-key possession or live login.
