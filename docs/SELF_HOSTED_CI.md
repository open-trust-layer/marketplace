# Marketplace Self-Hosted CI

Status: repository-scoped CI infrastructure for `open-trust-layer/marketplace`.
This document records intended controls and migration-time provenance; provider-side state must still be re-verified directly.

## Runner provenance

- runner name: `marketplace-ci-win-x64-01`
- repository scope: `open-trust-layer/marketplace` only
- labels: `self-hosted`, `Windows`, `X64`, `marketplace-ci`
- OS: Windows 11 Pro x64
- service account: `MACHINE\marketplace-ci`
- service account administrator membership: false at provisioning and acceptance verification
- runner version: `2.337.0`
- official runner package: `actions-runner-win-x64-2.337.0.zip`
- verified runner package SHA-256: `1150692afa94e71f872017e254ea55b6eece1eece3fe7e3a6d4c93d0a1b85cfc`
- automatic runner self-update: disabled; updates require a new provenance review
- runner installer archive: deleted after verified extraction

## Runtime boundary

The persistent runner installation is separate from job-local language environments.
The verified Python toolcache is `C:\CI\marketplace-toolcache` and is read-only to the CI account.
The workflow creates a fresh virtual environment under the runner temporary directory for every job.

- Python: `3.12.10` x64
- official Python package SHA-256: `17e4ee587e0ecee4674040da8b248e151475ff65becae18fe0ec81f8312b5035`
- reviewed build backend: `setuptools==80.9.0`
- pinned OLP source commit: `41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c`

No production virtual environment, package directory, runtime configuration, database, or credential store is reused by CI.

## Public-repository threat boundary

Marketplace is public, so persistent self-hosted runner use is allowed only with the separately reviewed compensating controls recorded in Infrastructure Issue #109.
At migration time GitHub's fork approval policy was verified as `all_external_contributors`.
External-fork jobs must not be approved until the exact workflow and code to be executed have been manually reviewed as trusted for this runner.

The repository had no Actions secrets, variables, or environments at migration inspection time.
The workflow retains `permissions: contents: read` and does not use `pull_request_target`.
The dedicated CI account is explicitly denied read access to the interactive administrator profile and other project runner roots inspected during provisioning.

## Filesystem and cleanup

Runner binaries/configuration and host hooks are administrator/SYSTEM owned and read-only to `MACHINE\marketplace-ci`.
The CI account has modify access only to the runner work/diagnostic directories and Marketplace temporary directory needed for job execution.
The toolcache and host hooks are read-only to the CI account.

An administrator-owned pre-job hook verifies repository scope, service identity, non-admin status, workspace location, and the inspected forbidden-root ACL boundary.
An administrator-owned post-job hook removes Marketplace job workspace and transient runner temp content.
The workflow itself additionally uses an `always()` cleanup step for the disposable virtualenv, pip cache, build output, test caches, and Python bytecode caches.
A cleanup failure is a CI failure rather than a warning.

## Preserved acceptance semantics

The workflow name remains `Marketplace conformance` and the job/check identity remains `acceptance`.
The exact repository acceptance authority remains:

```text
python tools/conformance_gate.py --olp-root ../olp --timeout 90
```

The two `actions/checkout` uses are pinned to commit `3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1).
No formatter, linter, policy, repository-audit, unit, semantic-vector, replay, packaging, package-smoke, or git-cleanliness behavior inside the unified conformance gate is removed or renamed by this migration.

## Databases and deployment

The pre-migration workflow has no database, service-container, or external integration-service step.
Therefore this migration introduces no database port, user, service, or production-service dependency and skips none.
If future CI requires a database or service, it must use a separately isolated test-only service and must not reuse production state.

CI migration does not authorize deployment or production restart.

## Persistent runner hardening

- The service account Windows profile is read-only; disposable `HOME`, `APPDATA`, `LOCALAPPDATA`, `TEMP`, and `TMP` live under `C:\CI` and are purged after jobs.
- The runner work tree and `_PipelineMapping` are writable only as required runner state and are treated as transient.
- The `_actions` cache is also transient. Before repository steps execute, an administrator-owned hook validates the exact pinned `actions/checkout` cache against a trusted 101-file SHA-256 manifest generated independently from commit `3d3c42e5aac5ba805825da76410c181273ba90b1`; the cache is purged after every job.
- PowerShell remains unchanged machine-wide. `RemoteSigned` is scoped only to the dedicated CI account; workflow steps explicitly use that policy and never require administrator elevation.
- Both checkout steps set `persist-credentials: false`.
- External fork workflows require manual approval for all external contributors and MUST NOT be approved before workflow code is trusted for local-runner execution.

The runner host itself is persistent, so these controls reduce but do not make public-repository self-hosting equivalent to an ephemeral VM. If the trust boundary cannot be maintained, the runner MUST be disabled rather than relaxing these controls.
