# M67 — Loopback Execution Gate Terminal Error Artifact Hardening

## Baseline

M67 starts from merged-green M66 commit
`4d8277a6688c81eff75725fca553c5dccc732308`.

M66 intentionally retained an inert terminal error template after authority release so
second calls could raise the original stable gate error without consulting a mutable
module-level constructor. The remaining gap was that the private template slot itself
could be rebound after release.

## Tests-first finding

Behavioral regression coverage was committed before the source fix:

- `9815905e3be461d619908a4a0e110734749e95b3` — initial template-rebinding tests;
- `29ccb7cfe18dc3d4f35996ef8adb5175b288cfc7` — one-slot poisoning coverage for all retained terminal anchors.

The tests require both public terminal entry points to keep raising
`InboundHttpLoopbackExecutionGateError` with code `LOOPBACK_EXECUTION_EXHAUSTED`.

## Implementation

Implementation commit `b4fe44a1a96475a4c599417857ae7c1fff1bdb11` adds two inert anchors:

- an immutable witness tuple containing the reviewed terminal template; and
- an integer identity for the reviewed terminal error type.

Terminal reconstruction cross-checks the template, witness, and type identity. If any
single retained slot is poisoned, one of the other inert anchors still identifies the
reviewed exception type. No retained callable, constructor, network capability, or
released M64 helper authority is reintroduced.

The normal pre-release binding validator also checks the terminal witness shape,
identity relationship, and type identity before the gate is consumed.

## Safety boundary

M67 changes no socket construction, bind/listen/accept/connect behavior, DNS, TLS,
peer traffic, deployment, credentials, or external authorization semantics. Tests are
deterministic and offline. Existing `NETWORK_EXTERNAL` and `DEPLOY` boundaries remain
unchanged and require separate fresh authorization.

## Optimization evidence

The hot/live execution path is unchanged after the initial binding validation. Extra
work is limited to constant-size identity checks during gate validation and terminal
second-call handling. No loop, retry, background task, additional I/O, or unbounded
allocation is introduced.
