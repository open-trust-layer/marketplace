# M17 evaluator: separate-origin localhost sync recovery on port 18481

Tracking: [Marketplace acceptance #525](https://github.com/open-trust-layer/marketplace/issues/525)

This is a **separately authorized, interactive Windows operator-console** lane for
retesting the merged PostgreSQL root-Intent filter. It must not execute in
GitHub Actions, Remote Desktop Commander, remote agents, or an automated shell.
Source and CI acceptance is not authorization to activate the server.

## Recorded source checkpoint

- Merged Marketplace main: `7e08eb95c9a0d8c40f3070090681e0c1bec2fc46`
  (CI [#1245](https://github.com/open-trust-layer/marketplace/actions/runs/42493701393) PASS).
- Pinned OLP: `4e57057d5d946797814f33125f77c4b6732cbfda`.
- Source-only checkout: `D:\MarketplaceEvaluatorFresh\marketplace-sync-retest-main-7e08eb95`.
- Evaluator Python interpreter: `D:\MarketplaceEvaluatorFresh\marketplace-sources-main-94d659bc-20261016\evaluator-venv\Scripts\python.exe`.

The original `127.0.0.1:18480` evaluator and its already validated
`MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1` evidence are historical
baseline artifacts. Do **not** stop or overwrite the original server, reload
the original buyer/seller tabs, reset their in-memory keys, or treat a successful
source test as a browser retest.

## Operator-only prerequisites

1. Select and immediately recheck a free `127.0.0.1:18481` listening
   destination; an earlier free-port observation is not a reservation.
2. Create **new** seller and buyer Chrome browser-key sessions in distinct
   contexts both using the exact origin `http://127.0.0.1:18481/`.
   The previously provisioned 18480 keys and their signed bundle **must not**
   be recycled. The new origin needs freshly reviewed signed two-party
   provisioning and sufficient remaining lease.
3. Review the isolated PostgreSQL identity, data directory, retention policy,
   and whether simultaneous reads/writes from both local evaluator services
   are permitted. The existing database may contain records that have expired
   under its retention policy; do not assume historical IDs are still live.
4. Independently verify the clean exact Git revisions, expected dependency
   pins, and the inert authenticated graph preflight. All secrets stay in the
   operator's local secure process and provisioned files; never paste DSN,
   private keys, session tokens, signed key claims or `mkpk1_` carriers into
   ChatGPT, GitHub, logs or PR comments.
5. Obtain separately scoped live authorization from the operator. Only the
   original interactive Windows console may run active mode; never have an
   agent automate the live command.

The reviewed `tools/marketplace_evaluator_operator_runtime.ps1` accepts
`-LoopbackPort 18480` (default) or `-LoopbackPort 18481` only. In active
mode it checks the selected port is free, requires typed confirmation that
**both** browser tabs show the exact selected origin, performs hidden-input
public-carrier comparison against independently signed provisioning, verifies
the bounded PostgreSQL evaluator identity, and separately prompts before
initializing state and starting the server. It cannot copy or transfer
private browser keys between origins.

## Source-only readiness and safe stop

The helper's default **inert** mode has no browser, database, credential or
server authority. For an independently prepared reviewed provisioning
directory, the operator can run it with `-LoopbackPort 18481` and without
`-ExecuteLocalOperatorRuntime`, then inspect the non-secret
`OPERATOR_RUNTIME_INERT_READY` marker. This requires only paths and
source-validation operations, not authentication provisioning reads.

If the selected port is busy, source SHA differs, browser origin differs,
signed lease is stale, identity is uncertain, or any security check fails:
**stop**, retain original evaluator and evidence, and diagnose locally
without bypassing the guard.

## Browser acceptance and signoff

After a separately authorized live session on the new origin:

- Authenticate seller and buyer independently.
- Confirm the corrected `/api/intents` root listing contains only genuine
  Intents, not acceptance `MarketEvent` or `MarketAgreement` records.
- Confirm repeated **Sync now** succeeds after Proposal acceptance and
  Agreement publication, with correct response-parent visibility and no
  duplicate writes. Exercise full resync, pagination, stale cursor recovery,
  and negative/authentication checks.
- Record only safe IDs, exact run SHA, CI URL, non-secret status/error codes
  and independent evidence validation. An attributable delivery claim is not
  a universal truth or a payment/settlement signal.

Keep #525 **HOLD** until that live evidence is independently reviewed. There
is no production deployment or public network activation in this workflow.
