# M65 — Authority Lifecycle Hardening Scope

## Status

Draft implementation scope after M64 terminal authority-release hardening.

## Baseline

M64 established that terminal loopback execution gate paths release retained capability-bearing references after completion or close.

## M65 objective

Extend the same safety property from terminal cleanup into explicit lifecycle observability and regression protection.

## First implementation slice

Bounded scope:

1. Document lifecycle invariants for retained authority references.
2. Add regression coverage for terminal-state authority absence.
3. Preserve existing execution semantics, opt-in requirements, and safety gates.

## Invariants

- Released authority is not reusable.
- Terminal state remains terminal.
- Cleanup does not reopen execution capability.
- Diagnostics must not retain protected capability-bearing objects.

## Explicit exclusions

- No network capability expansion.
- No authorization model changes.
- No deployment behavior changes.
- No marketplace semantic changes.
