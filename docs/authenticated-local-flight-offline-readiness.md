# Authenticated local flight — consolidated offline readiness

Tracking: https://github.com/open-trust-layer/marketplace/issues/525

Run the standard-library `tools/marketplace_evaluator_offline_readiness.py` with the intended evaluator Python interpreter. It combines three existing offline checks:

1. Exact clean Marketplace and pinned OLP Git roots/revisions, including concealed Git index flags.
2. Exact reviewed optional dependency distribution metadata versions.
3. Python/module availability, bounded evaluator DSN *presence* in the process environment, and existence of pinned OLP source and separately specified auth provisioning directories.

All three are evaluated independently, even if one reports BLOCKED. The receipt reports only allowlisted diagnostic codes. It never emits DSNs, version strings, local paths, filenames, exception text or provisioning bytes. It does not import optional packages, install dependencies, connect to PostgreSQL, start a server/browser, or publish a heartbeat.

## Linux (X230i)

From the exact reviewed Marketplace checkout, execute:

```bash
python3 -m tools.marketplace_evaluator_offline_readiness \
  --marketplace-root /absolute/path/to/reviewed/marketplace \
  --marketplace-sha <reviewed-40-hex-main-commit> \
  --olp-root /absolute/path/to/pinned-olp \
  --olp-sha <reviewed-40-hex-olp-pin> \
  --provisioning-directory /absolute/path/to/marketplace-auth
```

The provisioning argument may be omitted to get a safe setup-gap report before credentials exist. An absent directory is then reported as PROVISIONING_DIRECTORY_ABSENT. The DSN must never be supplied on the command line; if it is already configured locally, only its presence and bounded length are assessed, without parsing or printing its contents.

## Windows / PowerShell

```powershell
python -m tools.marketplace_evaluator_offline_readiness `
  --marketplace-root "C:\absolute\path\to\marketplace" `
  --marketplace-sha "<reviewed-40-hex-main-commit>" `
  --olp-root "C:\absolute\path\to\pinned-olp" `
  --olp-sha "<reviewed-40-hex-olp-pin>" `
  --provisioning-directory "C:\absolute\path\to\marketplace-auth"
```

## Non-secret receipt

If all superficial checks return no blockers:

```text
status=OFFLINE_CHECKS_PRESENT_UNVERIFIED
source_provenance=PRESENT_UNVERIFIED
dependency_pins=PRESENT_UNVERIFIED
prerequisites=PRESENT_UNVERIFIED
network_invoked=false pip_invoked=false optional_packages_imported=false
auth_provisioning_opened=false postgres_connection_invoked=false server_invoked=false browser_invoked=false
credentials_emitted=false runtime_acceptance=false
```

This is **not** an acceptance PASS, runtime-ready signal, dependency-origin attestation, verified package import, authenticated graph preflight, or permission to start a server. Exit code zero means only that these superficial checks found no blocker.

On any failure, exit code is 1 with status=BLOCKED. Each gate emits an independent PRESENT_UNVERIFIED or BLOCKED:CODE status. Unexpected exceptions become stable SOURCE_CHECK_UNAVAILABLE, DEPENDENCY_CHECK_UNAVAILABLE or PREREQUISITE_CHECK_UNAVAILABLE codes without exposing the exception.

After this report, verify independent green merged-main CI and the correct interpreter and dependency artifact provenance, then perform the separately reviewed inert auth-provisioning graph preflight documented in MARKETPLACE_MVP_ACCEPTANCE.md. The post-M17.7P buyer/seller PostgreSQL/browser acceptance remains a **separately authorized runtime operation**.

Rollback: revert the documentation/tool PR. No persistent evaluator, database, payment or production state is modified.
