# Packageable Reference Semantic Adapters

Status: Milestone 22 reference implementation

## Purpose

Milestone 22 moves the Marketplace reference semantic behavior already used by the local runtime from repository-only `tools/` modules into the installable `marketplace.reference` namespace.

The move changes where the non-normative reference implementation lives. It does not change Marketplace semantics or make the reference implementation authoritative.

```text
reference validator          != protocol authority
reference discovery          != global marketplace view
reference match              != protocol truth
compatible under method      != agreement
installed reference adapter  != mandatory implementation
package convenience          != semantic monopoly
```

## Package boundary

The installed distribution now contains:

```text
marketplace.runtime
    transport-neutral runtime/application core
    no implicit OLP import
    zero declared runtime dependencies

marketplace.reference
    explicit non-normative M3/M5 reference adapters
    requires an explicitly supplied OLP implementation when imported
```

The base package continues to declare:

```toml
dependencies = []
```

`marketplace.runtime` does not import `marketplace.reference` implicitly. Applications remain free to provide other conforming validator, identity, discovery, or matching implementations.

## Extracted semantic sources

### M3 record validation

`src/marketplace/reference/record_v1.py` is the single implementation source for the existing Marketplace Record Representation v1 validation helper.

Its implementation was moved from `tools/marketplace_record_v1.py` without semantic edits. It continues to validate Marketplace-specific content while OLP remains responsible for RecordV1 validation, canonical identity encoding, hashing, proofs, relationships, and lifecycle semantics.

### M5 matching and discovery

`src/marketplace/reference/matching_v1.py` is the single implementation source for the existing M5 matching/discovery helper surface, including discovery, exact index verification, method-relative match evaluation, ranked-view validation, federated-view merging, and cursor binding.

The extraction preserves the existing boundaries:

```text
search result              != resolved evidence
source completeness        != global completeness
match                      != protocol truth
compatibility under method != agreement
ranking                    != canonical ordering
```

## Compatibility wrappers

The historical repository tool imports remain available:

```text
tools/marketplace_record_v1.py
tools/marketplace_matching_v1.py
```

They are now thin compatibility wrappers that delegate to `marketplace.reference`. They do not retain duplicate semantic algorithms.

This allows existing generators, validators, tests, and developer commands to continue using their established import paths while conformance execution exercises the packaged implementation source.

Repository audit requires the wrapper files to remain small and to delegate to `marketplace.reference`.

## OLP dependency and dependency-confusion boundary

The reference adapters require OLP types and canonical operations. The Marketplace conformance baseline is tied to the exact OLP source commit:

```text
41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c
```

Milestone 22 deliberately does **not** declare `open-layer-protocol` as a mandatory or optional public-index dependency. Until OLP publication ownership and release provenance are separately established, adding that dependency name would create an unnecessary dependency-confusion / package-resolution trust path.

At the M22 baseline, repository audit rejected non-empty `project.dependencies` and non-empty `project.optional-dependencies`. Product M17.1A later preserves empty mandatory `project.dependencies` while allowlisting only the exact reviewed PostgreSQL application extra documented in `docs/m17-1a-postgres-application-state.md`; the OLP package name remains neither a mandatory nor optional public-index dependency.

## Isolated installed-reference smoke

The unified acceptance gate performs two independent package checks.

The first proves the base Marketplace runtime can be installed and imported without OLP.

The second creates a fresh temporary installation target and:

1. verifies the reviewed `setuptools==80.9.0` build backend;
2. installs the exact local pinned OLP checkout with `PIP_NO_INDEX=1`, `--no-deps`, and `--no-build-isolation`;
3. installs Marketplace into the same target with the same no-index/no-dependency controls;
4. launches Python in isolated mode;
5. admits only the temporary installation target ahead of the interpreter environment;
6. verifies `olp`, `marketplace.reference`, and `marketplace.runtime` resolve from that target;
7. constructs two valid MarketIntent records;
8. composes `create_in_memory_runtime` from packaged reference capabilities;
9. ingests both records;
10. performs local discovery;
11. performs local matching;
12. verifies the compatible result still has `protocol_truth = false` and `creates_agreement = false`.

No repository `tools/` path is available to the installed-reference smoke.

## Retention and side-effect impact

Semantic adapter extraction does not change the runtime retention model. Runtime-held evidence remains bounded by the existing EPHEMERAL policy, including the 10-second default/maximum post-use retention behavior.

The reference adapters introduce no network transport, filesystem/database persistence, cache, background service, credentials, deployment path, agreement formation, ranking authority, or protected side-effect executor.

## Conformance requirements

The extraction is accepted only if:

- existing tool-path imports resolve to the packaged implementation objects;
- M3/M5 behavior remains identical through package and wrapper paths;
- all existing unit tests pass;
- all 816 semantic vectors pass unchanged;
- all 13 deterministic generators replay byte-for-byte;
- repository audit passes;
- both isolated package smoke checks pass;
- Git whitespace checks pass;
- the OLP source pin remains unchanged.

## Follow-on

With M22 complete, an installed application can use either a custom conforming semantic implementation or the project’s explicit packaged reference adapters without depending on repository tooling.

The next architecture decision should remain separate: publication/provenance hardening versus the first external federation transport adapter. External networking introduces materially different authentication, TLS, SSRF/egress, retry, rate-limit, abuse, and remote-retention risks and should not be smuggled into the semantic package boundary.
