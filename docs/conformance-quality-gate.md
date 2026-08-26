# Unified Conformance Quality Gate

**Status:** Milestone 12 architecture decision and acceptance workflow.

## Context

Milestones 3–11 accumulated nine independently executable conformance suites. Each suite already had deterministic generators and validators, but acceptance depended on manually running the correct commands in the correct order and on manually reproducing repository hygiene checks.

That is a reliability boundary, not a Marketplace semantic problem. The semantic helpers and vector validators are already proven behavior and should not be rewritten merely to create automation.

Marketplace now also treats required development-policy/governance artifacts as repository invariants. This extends repository acceptance without changing Marketplace protocol semantics or vector meaning.

## Decision

Marketplace uses one provider-neutral local acceptance command:

```text
python tools/conformance_gate.py --olp-root <path-to-pinned-olp-checkout>
```

The gate is an orchestrator around the existing validators. It does not replace them.

The gate performs, in order:

1. exact OLP source-pin verification;
2. side-effect-free repository structure/content/governance audit;
3. deterministic offline unit tests for the gate and repository-audit boundaries;
4. all manifest-registered vector validators in fixed order;
5. byte-for-byte replay of every manifest-registered generator in an isolated temporary repository copy; and
6. Git whitespace checks across the working tree, staged index, and committed `HEAD^..HEAD` delta.

Every subprocess has an explicit finite timeout. Suites execute sequentially; M12 introduces no unbounded task fan-out or hidden concurrency.

## Required development-governance artifacts

The repository audit now requires these project policy/governance files to remain present:

```text
DEVELOPMENT_POLICY.md
docs/RETENTION_POLICY.md
docs/REPOSITORY_GOVERNANCE.md
.github/CODEOWNERS
.github/pull_request_template.md
```

The Markdown files participate in the existing UTF-8, relative-link, and fenced-block audit. Presence validation prevents accidental removal of the governance baseline.

This repository-side check does **not** prove that GitHub branch protection, required reviews, CODEOWNERS enforcement, or required status checks are enabled remotely. Desired remote governance and verified provider enforcement remain separate facts.

## OLP compatibility pin

The Marketplace compatibility source pin is stored in:

```text
conformance/olp-source-pin.txt
```

The gate refuses to proceed when the supplied OLP checkout does not resolve to that exact Git commit. Every vector artifact is also audited to ensure its embedded `olp_reference_source_commit` agrees with the same pin.

The GitHub Actions adapter checks out the same commit explicitly. The duplicated workflow `ref` is treated as infrastructure configuration and is verified again by the provider-neutral gate, preventing silent CI drift.

## Deterministic generator replay

Generators historically write their vector artifact in place. Running them directly during acceptance would therefore create unnecessary worktree side effects even when output is byte-for-byte identical.

M12 instead copies the repository to a temporary directory, runs all generators there, hashes the generated artifacts, and compares them with the committed vector hashes. The real worktree remains untouched.

## CI boundary

GitHub Actions is an adapter around the local gate, not the source of acceptance semantics. CI performs only environment composition:

- checkout Marketplace;
- checkout the exact public OLP source pin;
- install the OLP reference package dependency; and
- call the same local gate.

No secret or privileged credential is required for ordinary push/pull-request conformance validation.

Provider-side branch/ruleset enforcement is a separate administrative control and MUST NOT be inferred from CI configuration alone.

## Consequences

Positive consequences:

- one canonical acceptance command;
- deterministic and reviewable ordering;
- explicit failure/timeout outcomes;
- exact dependency pin validation;
- required development/governance artifacts cannot silently disappear;
- no generator mutation of the developer worktree;
- CI and local acceptance use the same orchestration; and
- future conformance suites can be added by extending the shared manifest.

Tradeoffs:

- full acceptance intentionally runs sequentially and is slower than speculative parallel execution;
- the draft Marketplace remains pinned to a source commit rather than a released OLP compatibility version;
- repository governance-as-code cannot prove provider-side branch protection/ruleset state; and
- GitHub Actions remains replaceable infrastructure, so provider-specific conveniences are intentionally kept out of the gate core.

A future released Marketplace version should replace the draft source pin with an explicit released OLP compatibility target.
