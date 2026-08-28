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
