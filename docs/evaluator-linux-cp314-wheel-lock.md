# Marketplace authenticated evaluator: Linux CPython 3.14 wheel lock (offline)

Tracking: [#525](https://github.com/open-trust-layer/marketplace/issues/525).

**Scope:** a source-only, platform-specific *dependency installation* reproducibility aid for an independently authorized local evaluator. This file **does not** provision authentication, authorize a PostgreSQL socket or browser, or satisfy authenticated acceptance. It is not a production deployment or multi-platform lock.

The reviewed [wheel requirements](evaluator-linux-cp314-requirements.txt) cover the full eight-distribution Linux x86_64 CPython 3.14 dependency closure of Marketplace `pyproject.toml` optional groups `postgres`, `local-server`, and `auth-verify` at protected Marketplace `main` `7259d654110f9e23b061af921a347038140a1410`. Exact file hashes and byte sizes were individually validated against PyPI release metadata on X230i on 2026-10-24. The two transitive packages are `cffi==2.1.1` and `pycparser==3.12`. If upstream dependencies, OS, Python ABI or cryptographic wheels change, this profile must be re-reviewed; **never bypass a hash mismatch**.

## Controlled use on Linux x86_64, CPython 3.14 only

In a **fresh nonproduction disposable environment** after verifying exact Marketplace and OLP source revisions, use the following. Shell variables are local scratch paths, not credentials:

```bash
set -eu
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/marketplace-evaluator-XXXXXX")"
test "$(uname -s)" = Linux
test "$(uname -m)" = x86_64
python3 -c 'import platform,sys; assert sys.implementation.name=="cpython" and sys.version_info[:2]==(3,14)'
python3 -m venv "$SCRATCH/venv"
PY="$SCRATCH/venv/bin/python"
WHEELS="$SCRATCH/wheels"
mkdir -p "$WHEELS"
LOCK="docs/evaluator-linux-cp314-requirements.txt"
"$PY" -m pip download --disable-pip-version-check --require-hashes \
  --only-binary=:all: --dest "$WHEELS" -r "$LOCK"
"$PY" -m pip install --disable-pip-version-check --no-index \
  --require-hashes --find-links "$WHEELS" -r "$LOCK"
"$PY" -m pip check
"$PY" -m tools.marketplace_evaluator_dependency_pins \
  --marketplace-root "$PWD"
```

The first command is **networked only for package acquisition**, not a Marketplace runtime action. It must be run on an approved trusted network; the second installation is offline against the verified wheelhouse and fails closed if bytes do not match. No `--trusted-host`, `--no-deps`, `--no-verify`, unpinned index or private package should be inserted. `--require-hashes` is indispensable. Never put a DSN, token or provisioning path in requirements, shell logs, PR discussions or artifacts.

The lock has no resolver snapshot for other Python versions or architectures. For other platforms, create and review their own exact-artifact hash profile rather than weakening checks or copying these Linux wheel hashes.

## Independent acceptance still required

`pip check`, the inert `marketplace_evaluator_offline_readiness` receipt and basic imports prove only prerequisites. They do not prove distribution origin beyond reviewed PyPI metadata, party authority, fresh keys, valid session/provisioning, PostgreSQL state, Agreement publication or seller-delivery evidence. The evaluator must use the separately authorized exact `127.0.0.1` origin, DSN and authentication material; never infer approval from CI.

The future operator must satisfy [MARKETPLACE_MVP_ACCEPTANCE.md](../MARKETPLACE_MVP_ACCEPTANCE.md) and [issue #525](https://github.com/open-trust-layer/marketplace/issues/525), including the inert graph preflight, two independent authenticated browsers, and offline-validated non-secret flight evidence. Public hosting, payments, real dispatch and settlement remain disabled.

**Rollback:** revert this source/test/docs addition. No runtime, data migration or external service change is involved.
