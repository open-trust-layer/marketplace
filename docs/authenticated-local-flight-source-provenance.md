# M17.7 — Offline evaluator source-provenance check

Issue: [#525](https://github.com/open-trust-layer/marketplace/issues/525).

After the read-only [prerequisite presence check](authenticated-local-flight-prerequisites.md),
use `tools/marketplace_evaluator_source_provenance.py` to verify the two
**local** Git working-tree roots against explicitly reviewed 40-hex commit IDs.
This has no PostgreSQL, browser, socket, credential or production authority.

The checker uses local Git commands only, with fixed argument arrays (no
shell), disabled Git filesystem-monitor hooks, bounded command timeouts and
redacted stdout/stderr. It validates, **for each repository separately**:

- the supplied absolute directory is the exact Git worktree root, not a
  nested directory in a larger checkout;
- `HEAD` equals the operator-supplied expected commit, including a detached
  evaluator checkout;
- `git status --porcelain=v1 --untracked-files=all
  --ignore-submodules=none` reports no visible tracked or untracked
  changes.

The current reviewed OLP pin appears in
[conformance.yml](../.github/workflows/conformance.yml).
Obtain the reviewed Marketplace `main` commit and successful independent
`main` CI separately; enter the exact SHA you want to evaluate. **Do not**
substitute a branch name or invent a passing CI result.

## Example (Linux / X230i)

From the Marketplace project checkout:

```bash
python3 tools/marketplace_evaluator_source_provenance.py \
  --marketplace-root /home/tehki/Projects/marketplace-evaluator-20261011 \
  --marketplace-sha 6083802c1d6959ff8a0c3e1c6fd5ac3325a4bbe6 \
  --olp-root /home/tehki/Projects/protocol-marketplace-ci-pin \
  --olp-sha 4e57057d5d946797814f33125f77c4b6732cbfda
```

The listed SHAs represent a recorded 2026-10-11 checkpoint, **not** a
permanent latest-release pointer; use newly verified SHAs as `main` advances.

## Example (Windows / PowerShell)

```powershell
python tools/marketplace_evaluator_source_provenance.py `
  --marketplace-root "C:\absolute\path\to\marketplace" `
  --marketplace-sha "<reviewed-40-hex-main-commit>" `
  --olp-root "C:\absolute\path\to\pinned-olp" `
  --olp-sha "<40-hex-workflow-OLP-pin>"
```

A successful offline result prints:

```text
status=SOURCE_PROVENANCE_MATCHED_OFFLINE
network_invoked=false postgres_connection_invoked=false server_invoked=false browser_invoked=false
runtime_acceptance=false credentials_emitted=false
```

A mismatch emits `status=BLOCKED codes=<stable-codes>` and exits nonzero.
Valid categories include `MARKETPLACE_REVISION_MISMATCH`,
`MARKETPLACE_TREE_DIRTY`, `OLP_REVISION_MISMATCH` and
`OLP_TREE_DIRTY`. Git errors, invalid paths, timeouts, malformed expected
SHAs and non-root worktree locations also fail closed. No local paths, Git
output, or untracked filenames are included in normal reports.

This is a read-only **local checkout consistency** check, not a
cryptographic attestation of Git object origin, CI provenance or asset
integrity against a remote trusted source. Git config, ignored files, Git's
skip-worktree/assume-unchanged flags and a hostile local filesystem remain
outside the guarantee. Never infer authentication or live acceptance from
this result.

**Next:** verify independent main CI and relevant source/asset integrity;
run the authoritative inert fulfillment-completion graph preflight when
locally provisioned; perform the buyer/seller PostgreSQL/browser flight only
with separately scoped runtime authorization. Source-only rollback is to
revert the PR. No production or persistent state is mutated.
