# Packageable Runtime Distribution Boundary

Status: Milestone 21 reference implementation

## Purpose

Milestone 21 establishes a minimal installable Python distribution boundary for the Marketplace runtime created in Milestones 17–20.

The package is intentionally narrower than the repository. It contains the transport-neutral runtime/application layer under `src/marketplace`; it does not silently turn repository conformance helpers, generators, validators, network transports, persistence systems, or protected-side-effect executors into runtime dependencies.

```text
installable runtime package != mandatory Marketplace implementation
package metadata             != protocol version
runtime distribution         != semantic authority
zero runtime dependency      != self-contained Marketplace semantics
package import               != network service
installed code               != repository tools
```

## Distribution metadata

The repository root `pyproject.toml` defines the experimental package:

```text
name: open-layer-marketplace
version: 0.0.1.dev0
Python: >=3.11
license: Apache-2.0
package root: src/
runtime dependencies: none
console scripts: none
plugin entry points: none
reviewed build backend: setuptools==80.9.0
```

The development version is distribution metadata only. It does not establish a Marketplace protocol version, specification maturity claim, conformance level, or stable API guarantee.

The exact setuptools version is part of the reviewed M21 build boundary. CI provisions that version explicitly, and the acceptance gate independently verifies the installed build backend version before attempting the package smoke. This prevents `--no-build-isolation` from silently using an arbitrary ambient setuptools release.

## Explicit semantic dependencies

The runtime remains dependency-injected. Applications must explicitly provide the semantic/identity capabilities required by the composition boundary, including:

- Marketplace record validation;
- OLP Record Identity derivation;
- discovery evaluation;
- match evaluation.

Milestone 21 does not move the current M3/M5 reference helpers from `tools/` into the installed package. Those helpers remain repository conformance/reference implementations until a separate semantic-adapter extraction milestone reviews that authority boundary deliberately.

Therefore:

```text
installed MarketplaceRuntime
        |
        +-- requires explicit validator
        +-- requires explicit identity provider
        +-- requires explicit discovery evaluator
        +-- requires explicit match evaluator
```

No fallback imports from repository `tools/` are permitted or required by the installed runtime.

## Isolated package smoke gate

The unified acceptance gate performs a deterministic installation/import smoke test in a temporary directory outside the repository worktree.

Before installation, the gate verifies that the active build environment contains exactly `setuptools==80.9.0`. A missing or different build backend fails acceptance before pip is invoked.

Installation is then invoked with all of the following controls:

```text
--no-deps
--no-build-isolation
PIP_NO_INDEX=1
PIP_NO_INPUT=1
PIP_DISABLE_PIP_VERSION_CHECK=1
```

These controls prevent the smoke test from silently resolving runtime dependencies or package build requirements from a registry. The reviewed build backend must already be present in the controlled CI/local environment.

The import probe then launches Python in isolated mode (`-I`), removes repository `PYTHONPATH` influence, manually adds only the temporary installation target, and verifies that:

- `marketplace` imports from the temporary target;
- `marketplace.runtime` imports from the temporary target;
- neither module resolves from repository `src/` or `tools/`;
- `MarketplaceRuntime` is available;
- `compose_runtime` is available;
- `create_in_memory_runtime` is available.

The temporary installation target is destroyed automatically when the smoke check exits.

## Repository-audited packaging invariants

`tools/repository_audit.py` parses `pyproject.toml` using the Python standard-library `tomllib` parser and fails acceptance if critical M21 packaging assumptions drift.

The audit currently requires:

- build backend `setuptools.build_meta` with exactly `setuptools==80.9.0`;
- package name `open-layer-marketplace`;
- experimental `0.0.N.devN` version form;
- Apache-2.0 license metadata;
- an explicitly empty runtime dependency array;
- no runtime console scripts;
- no plugin/entry-point discovery;
- package discovery rooted at `src/`;
- package discovery limited to `marketplace*`.

A future milestone that intentionally changes one of these constraints must update the policy, tests, and review evidence rather than bypassing the audit.

## Retention and security impact

Packaging does not change runtime evidence retention.

The in-memory reference runtime remains bounded by the existing EPHEMERAL policy, including the default and maximum 10-second post-use retention behavior. Installing the package does not persist Marketplace records, create caches, start services, create background workers, open sockets, read secrets, or perform protected side effects.

The package itself has no import-time network or filesystem side effects beyond normal Python module loading.

## Publication boundary

Milestone 21 does not publish the distribution to PyPI or any other registry. It introduces no upload credentials, publishing workflow, signing key, release token, or registry account.

A future publication milestone would require separate review of supply-chain security, reproducible build expectations, artifact signing/provenance, release authority, dependency policy, and credential handling.

## Follow-on

The next package-related architectural step should be a separate reference semantic-adapter extraction milestone. That work may move selected M3/M5 reference capabilities into an importable package boundary while keeping compatibility wrappers for existing repository tools and proving that the 816-vector conformance corpus remains unchanged.

External federation/network transport remains a later, explicitly higher-risk capability boundary.
