# Unified Conformance Quality Gate

**Status:** Milestone 12 architecture decision and acceptance workflow.

## Context

Milestones 3–11 accumulated nine independently executable conformance suites. Each suite already had deterministic generators and validators, but acceptance depended on manually running the correct commands in the correct order and on manually reproducing repository hygiene checks.

That is a reliability boundary, not a Marketplace semantic problem. The semantic helpers and vector validators are already proven behavior and should not be rewritten merely to create automation.

## Decision

Marketplace uses one provider-neutral local acceptance command:

```text
python tools/conformance_gate.py --olp-root <path-to-pinned-olp-checkout>
```

The gate is an orchestrator around the existing validators. It does not replace them.

The gate performs, in order:

1. exact OLP source-pin verification;
2. side-effect-free repository structure/content audit;
3. deterministic offline unit tests for the gate itself;
4. all Milestone 3–11 vector validators in fixed order;
5. byte-for-byte generator replay in an isolated temporary repository copy; and
6. `git diff --check` for the current working diff.

Every subprocess has an explicit finite timeout. Suites execute sequentially; M12 introduces no unbounded task fan-out or hidden concurrency.

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

## Consequences

Positive consequences:

- one canonical acceptance command;
- deterministic and reviewable ordering;
- explicit failure/timeout outcomes;
- exact dependency pin validation;
- no generator mutation of the developer worktree;
- CI and local acceptance use the same orchestration; and
- future conformance suites can be added by extending the shared manifest.

Tradeoffs:

- full acceptance intentionally runs sequentially and is slower than speculative parallel execution;
- the draft Marketplace remains pinned to a source commit rather than a released OLP compatibility version; and
- GitHub Actions remains replaceable infrastructure, so provider-specific conveniences are intentionally kept out of the gate core.

A future released Marketplace version should replace the draft source pin with an explicit released OLP compatibility target.
