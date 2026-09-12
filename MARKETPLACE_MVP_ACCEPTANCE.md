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
