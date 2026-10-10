# M17.7R — Authenticated local-flight evidence validator

Profile: `MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_VALIDATOR_V1`

Evidence profile: `MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1`

Issue: #502.

## Purpose

M17.7Q freezes the observable evidence required before the post-P authenticated
local product flight may be called accepted. M17.7R makes that evidence
machine-checkable without performing the live flight itself.

The validator reads one local JSON document and either accepts the exact reviewed
shape or returns a stable error code. It does not infer success from partial
authentication, source/CI results, or listing/Proposal authoring.

## Exact evidence contract

The top-level record contains:

- exact merged `main_commit` and positive `ci_run_number`;
- `runtime_host` exactly `127.0.0.1`;
- exact boolean seller/buyer authentication observations;
- listing, Proposal, acceptance, and Agreement Record Identities;
- formation evidence exactly `EVIDENCE_SUFFICIENT_FOR_PROFILE`;
- no missing required principals;
- explicit Agreement publication metadata;
- explicit completion metadata.

Agreement publication must reference the same Agreement and report `STORED` or
`DUPLICATE`, plus a positive or null local change sequence.

Completion must reference that same Agreement and exact semantics:

- commitment: `seller-delivery`;
- evidence kind: `CLAIMED_COMPLETE_PERFORMANCE`;
- disposition: `STORED` or `DUPLICATE`;
- completion Record Identity;
- positive or null local change sequence.

The record also requires all of these exact false values:

- `universal_truth`;
- `payment_or_settlement_evaluated`;
- `public_network_exposed`;
- `public_deployment`.

Unknown top-level or nested fields are rejected. This keeps the final acceptance
record narrow and prevents unrelated runtime material from becoming part of the
reviewed evidence shape.

### M17.7AB — Strict JSON member uniqueness

Python's permissive default JSON decoder silently keeps only the last value of
a repeated object member. That could erase a contradictory earlier seller-
authentication, Agreement-disposition or completion field **before** the exact
evidence schema is checked. The offline loader now uses a fail-closed parser
which rejects duplicate JSON object names at every nesting depth with
`EVIDENCE_JSON_DUPLICATE_KEY`. It also rejects the nonstandard `NaN`,
`Infinity`, and `-Infinity` tokens with `EVIDENCE_JSON_INVALID`.
The parser never includes a member name, value or file content in its failure
message. The existing 64 KiB file bound, strict expected keys and offline
non-authority remain unchanged.

This validation improvement does **not** authenticate the file's origin or
turn self-reported login booleans into cryptographic proof. Final acceptance
still requires the actual operator-observed seller/buyer browser flight.

## Usage

After an operator-authorized post-P browser flight has produced the non-secret
observable evidence record:

```powershell
python tools/marketplace_authenticated_local_flight_evidence.py .\authenticated-local-flight-evidence.json
```

Successful validation prints `status=PASS` with the reviewed public acceptance
metadata. A rejected record prints `status=FAIL code=<stable-code>` and exits
non-zero.

M17.7R does not create the evidence file and does not claim that a post-P live
flight has completed.

## Non-authority

The validator uses Python standard-library file/JSON processing only. It starts no
server or browser, binds no socket, performs no HTTP request, opens no PostgreSQL
connection, initializes no application database, generates or handles no
authentication credentials, and performs no signing.

It adds no production deployment, public networking, Android, payment,
settlement, ownership-transfer, or universal-truth authority.

## Rollback

Source-only rollback: revert the M17.7R merge. No runtime or external-system
rollback is introduced.
