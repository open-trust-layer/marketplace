# MARKETPLACE MVP ACCEPTANCE

Profile: `MARKETPLACE_MVP_FLIGHT_ACCEPTANCE_V1`

This is the frozen local MVP product-flow checklist. A checked item is backed by the executable two-user flight and focused repeatability tests. It does not imply production deployment, payment, settlement, or universal truth.

- [x] Application starts successfully
- [x] User A can create identity
- [x] User A can create listing
- [x] Listing can be published
- [x] User B can discover listing
- [x] User B can verify listing
- [x] User B can accept interaction
- [x] Agreement state is recorded
- [x] Final state is visible
- [x] Full flow can be repeated

## Required evidence

Run from the repository root in the reviewed dependency environment:

```powershell
$env:PYTHONPATH = "src;tools"
python -m unittest tests.test_marketplace_mvp_flight_acceptance
python tools/marketplace_mvp_flight_acceptance.py
```

## Evaluator browser path

The repository also exposes a database-free, process-memory localhost demo mode. It uses the existing reviewed loopback server provider and requires only the reviewed `local-server` optional dependency; it does not read `MARKETPLACE_POSTGRES_DSN` or initialize PostgreSQL.

After dependencies are present, an explicitly authorized live evaluator run is:

```powershell
$env:PYTHONPATH = "src;tools"
python tools/marketplace_localhost.py --port 18080 --execute-demo-localhost EXECUTE_MARKETPLACE_IN_MEMORY_DEMO_V1
```

Then browse to `http://127.0.0.1:18080/` and select **Run complete local MVP journey**. The page shows the lifecycle, participants, listing/agreement identities, verification results, completion timestamp, and audit identities.

The demo state is bounded and process-local only. The command starts a real loopback server, so repository tests and CI never invoke this live path and its execution remains a separate runtime-authorization boundary.

## Authenticated PostgreSQL-capable completion path

This is a **separate evaluator lane** from the database-free demo above. Merged M17.7H-P provide the source/runtime/Web path and full-conformance acceptance. The real PostgreSQL-backed browser lane is now **live-runtime partially exercised**: M17.7O corrected the whole-second localhost clock after a live initialization failure, and M17.7P corrected authenticated Web structured authoring after a live `AUTH_REQUIRED` finding. A fresh **post-P** browser repeat is still required before live-runtime acceptance.

Prerequisites are intentionally explicit:

- the reviewed `local-server`, `auth-verify`, and PostgreSQL client dependencies;
- `MARKETPLACE_POSTGRES_DSN` set locally to the evaluator PostgreSQL DSN;
- an absolute local authentication provisioning directory that satisfies M17.5S/M17.5Y;
- the pinned OLP source on `PYTHONPATH`;
- separate operator authorization for live runtime execution.

Do not place DSN text, provisioning bytes, keys, session material, or other credentials in committed files or acceptance transcripts.

### Inert server/database preflight

The fulfillment-completion preflight reads the explicit local provisioning, environment configuration, and reviewed Web assets so it can compose the exact graph. It does **not** connect to PostgreSQL, initialize application/coordination state, bind a socket, or run a server.

```powershell
$env:PYTHONPATH = "src;tools;C:\path\to\pinned-olp\src"
$env:MARKETPLACE_POSTGRES_DSN = "<local evaluator DSN>"
python tools/marketplace_localhost.py --port 18080 --preflight-fulfillment-completion-localhost --authentication-provisioning-directory "C:\absolute\path\to\marketplace-auth"
```

Expected readiness marker:

```text
FULFILLMENT_COMPLETION_AUTHENTICATED_LOCALHOST_PREFLIGHT_READY host=127.0.0.1 port=18080 postgres_connection_invoked=false database_initialized=false coordination_initialized=false server_invoked=false
```

### Explicit live loopback runtime

Only after separate runtime authorization, start the reviewed foreground path with its exact mode-specific token:

```powershell
python tools/marketplace_localhost.py --port 18080 --execute-fulfillment-completion-localhost EXECUTE_FULFILLMENT_COMPLETION_AUTHENTICATED_MARKETPLACE_LOCALHOST_V1 --authentication-provisioning-directory "C:\absolute\path\to\marketplace-auth"
```

The reviewed runtime remains bound to exact IPv4 loopback `127.0.0.1`. Open `http://127.0.0.1:18080/` in the evaluator browser and complete the authenticated flow through explicit **Publish Agreement** and **Claim delivery complete** actions.

A valid evaluator record should capture only non-secret observable evidence:

- successful authentication state without token/key disclosure;
- selected Proposal and exact Agreement Record Identity;
- successful Agreement publication metadata;
- seller-attributed `CLAIMED_COMPLETE_PERFORMANCE` for commitment `seller-delivery`;
- resulting immutable Record Identity / disposition / local change-sequence metadata;
- confirmation that the page still states completion is attributable evidence, not universal truth, payment, or settlement;
- confirmation that the runtime was loopback-only and no public deployment was involved.

Until the fresh **post-P** operator-authorized run reaches and records explicit Agreement publication plus seller-attributed `CLAIMED_COMPLETE_PERFORMANCE` for `seller-delivery`, authenticated local product flight remains **source/CI accepted, live-runtime partially exercised** rather than live-runtime accepted.

### Validate the recorded post-P evidence offline

After the operator-authorized browser flight has produced its non-secret evidence JSON, validate that record separately:

```powershell
python tools/marketplace_authenticated_local_flight_evidence.py .\authenticated-local-flight-evidence.json
```

The validator requires profile `MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1`, exact loopback host `127.0.0.1`, both authenticated parties, sufficient Agreement formation with no missing principals, matching Agreement publication/completion references, commitment `seller-delivery`, and evidence kind `CLAIMED_COMPLETE_PERFORMANCE`. It also requires the universal-truth, payment/settlement, public-network, and public-deployment claims to remain false.

The validator is offline acceptance tooling only. It does not start the server or browser, connect to PostgreSQL, generate the evidence record, or change the requirement for a fresh post-P live browser run.
