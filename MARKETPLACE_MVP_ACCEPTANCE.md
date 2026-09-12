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
