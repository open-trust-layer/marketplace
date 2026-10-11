# Authenticated local-flight dependency-pin metadata check

Issue: [#525](https://github.com/open-trust-layer/marketplace/issues/525).

Use `tools/marketplace_evaluator_dependency_pins.py` after the
[prerequisite presence checker](authenticated-local-flight-prerequisites.md)
and before the authoritative provisioning-based graph preflight. It checks
installed **distribution metadata** in the exact Python interpreter used to
invoke the checker against the review-pinned optional dependencies in the
local Marketplace `pyproject.toml`. No optional dependency is imported or
installed. It is an **inert metadata check**, not authentication or runtime
acceptance.

The standard-library-only check requires each dependency in the
`postgres`, `local-server`, and `auth-verify` optional groups to have
an exact `==` version pin. The reviewed `postgres` entry must be
`psycopg[binary]`, and the metadata versions of **both** `psycopg` and
`psycopg-binary` must equal that same pin. The code discovers pins from the
repository's local manifest, rather than assuming today's versions forever.
Absent groups, malformed or unpinned requirements, unsupported extras,
duplicate dependency entries and unreadable, symlinked or overlarge
`pyproject.toml` fail closed.

The checker has **no package installer**. Use the normal reviewed dependency
setup under separately approved evaluator-environment authority; do not
paste credential values into package-install commands, source control,
terminal captures or GitHub.

## Linux (X230i)

Run with the Python interpreter intended for the authenticated local-flight
preflight. For a checked-out Marketplace tree:

```bash
python3 tools/marketplace_evaluator_dependency_pins.py \
  --marketplace-root /absolute/path/to/reviewed/marketplace
```

## Windows / PowerShell

```powershell
python tools/marketplace_evaluator_dependency_pins.py `
  --marketplace-root "C:\absolute\path\to\reviewed\marketplace"
```

If the metadata for all reviewed optional dependencies is present with the
expected versions, stdout is:

```text
status=DEPENDENCY_PINS_PRESENT_UNVERIFIED
pip_invoked=false external_dependencies_imported=false postgres_connection_invoked=false
server_invoked=false browser_invoked=false credentials_emitted=false runtime_acceptance=false
```

This is a **presence/metadata result**, not proof the packages can import,
that wheel artifacts are authentic, that their optional native dependencies
will load, or that the evaluator is correctly configured. Runtime readiness
and source/CI provenance must be checked independently.

Missing or mismatched installed versions produce nonzero exit and stable
category codes such as `POSTGRES_DEPENDENCY_PIN_UNVERIFIED`,
`LOCAL_SERVER_DEPENDENCY_PIN_UNVERIFIED` or
`AUTH_VERIFIER_DEPENDENCY_PIN_UNVERIFIED`; invalid/missing manifest metadata
returns `PINSET_UNAVAILABLE_OR_INVALID`. No installed version strings,
distribution filesystem paths, interpreter errors, DSNs or provisioning
contents are emitted.

## Boundaries and next gates

- Use the existing [offline source verifier](authenticated-local-flight-source-provenance.md)
  to confirm exact clean Marketplace and pinned OLP Git trees.
- Obtain successful independent merged-main CI provenance and verify reviewed
  interpreter, install artifacts and any dependency-transitive hashes by the
  applicable evaluator controls. This checker does not attest package origin.
- Configure the local evaluator DSN and authentication provisioning **only
  within the authorized evaluator environment** and perform the existing
  inert graph preflight as described in
  [MARKETPLACE_MVP_ACCEPTANCE.md](../MARKETPLACE_MVP_ACCEPTANCE.md).
- Do **not** start the loopback PostgreSQL/browser two-party flight without
  separate scoped runtime authorization; an offline result never grants it.

Rollback: revert this source-only change. It does not touch the database,
browse URLs, import optional distributions, install packages, emit secrets,
publish Moon heartbeats, activate payments or change production state.
