# M17.7X — Local authenticated-provisioning lease preflight

Profile: `MARKETPLACE_LOCAL_AUTHENTICATION_LEASE_PREFLIGHT_V1`

Linked acceptance: #510.

## Background

The operator-authorized M17.7V localhost acceptance preflight originally failed with
the broad error `M17_5Y_COMPOSITION_FAILED`. Read-only tracing identified that the
reused, correctly signed local development identity evidence was **expired**. The
full source composition refused it as designed. This is not justification to
relax authentication verification.

M17.7X adds a **separate, deliberate, source-only** preflight to identify this
condition before starting or stopping a service. It does **not** change runtime
authentication behavior or bootstrap failure semantics.

## Usage

From a clean, reviewed Marketplace checkout with its pinned Python dependencies
and `src` on the Python module search path:

```powershell
$env:PYTHONPATH = "src"
python tools/marketplace_authentication_lease_preflight.py `
  --authentication-provisioning-directory "C:\MarketplaceRuntime\auth-0a621c4-flight" `
  --minimum-remaining-seconds 1800
```

The path above is an illustrative already-known local development provisioning
directory, not a new authority or embedded secret. The operator must use their
own explicitly approved **absolute** local path and an appropriately reviewed
lease threshold. The default threshold is **1,800 seconds** (30 minutes).

The diagnostic uses the **existing canonical bounded loader** and exact
Ed25519 trust-anchor signature verifier. It checks that the signed claims hash
and authority agree with the verifier result, and finally exercises the
existing verification-method projection at the sampled clock time.

Successful output has the form:

```text
status=PASS lease_remaining_seconds=2400 identities=2 signature_verified=true server_invoked=false postgres_invoked=false
```

The remaining time and identity count are **not guaranteed values**; they depend
on the valid local evidence. An invalid invocation prints only
`status=FAIL code=<stable-code>` and exits nonzero. Failure codes are:

- `PROVISIONING_DIRECTORY_INVALID` for non-absolute, empty, or invalid path shape.
- `TIME_INVALID` or `MINIMUM_REMAINING_INVALID` for invalid guard parameters.
- `PROVISIONING_INVALID` for missing, malformed, unverifiable, or invalidly
  signed evidence, without reflection of the underlying private error.
- `LEASE_NOT_YET_VALID` for verified claims whose lease has not started.
- `LEASE_EXPIRED` for verified claims at or after the lease end.
- `LEASE_TOO_SHORT` for verified current evidence with less validity remaining
  than the chosen threshold.

The expiry classification occurs **only after signature verification**, preventing
unsigned or tampered claims from being treated as a routine renewal situation.
The script never prints a principal, public key, claims body, attestation,
private key, token, DSN, or provisioning path.

## Capabilities and non-authority

- **Risk:** LOW, bounded local read-only authentication material diagnostics.
- No issuance, renewal, persistence, database connection, listener, process
  restart, browser automation, transport, payment, or public deployment.
- No external network call or new dependency; existing pinned authentication
  verification dependency remains required.
- No implicit permission to use an expired lease or to bypass cryptographic
  verification. Renewal needs separate approved provisioning handling.
- The diagnostic is an *additional prerequisite*; PASS does not prove database
  availability, server readiness, buyer/seller authentication, completed
  Agreement/fulfillment, or accepted evidence JSON.
- The script does not supersede the required clean exact merged-main checkout,
  merged-main CI, full 14-asset parity check, browser flight, or offline M17.7R
  evidence validator.
- For accepted local flight, verify sufficient remaining lease time **immediately
  before runtime activation**, and repeat if the lease approaches expiry.

## Recovery

A failure should stop the planned local flight *before* stopping any existing
Marketplace service. Renew the local development signed evidence through the
separately approved controlled generator, use an isolated directory and re-run
this check; do not modify or weaken the clock or signature verifier.

There are no runtime changes to roll back. Source-only rollback is a revert of
this tool, test and documentation change. The existing guarded bootstrap remains
unchanged throughout.
