# M70 — Loopback Execution Gate Close Preflight Gate-Type Hardening

## Baseline

M70 starts from merged-green M69 commit
`b90a11ca0202ce0ea88f7892129b288e9ed57185`.

M68 hardened the public `dry_run()` / `execute_once()` preflight and M69 hardened
reviewed `_begin_once()`. The remaining narrow seam was explicit `close()`: retained
`_gate_type` was dereferenced through `.__dict__` before its identity was independently
established.

## Tests-first finding

Behavioral regression coverage was committed before the source fix:

- `2cbbfad5cc9f40573cd0d231cd3b94f6afe0bd16` — hostile retained-gate-type close preflight test.

A dependency-free probe compiled the exact current `close()` body from source. Against
the unchanged M69 runtime, hostile `__getattribute__("__dict__")` executed and cleanup
did not complete (`closed=False`). The temporary probe file was deleted immediately
after execution.

No socket, DNS, TLS, peer, deployment, credential, production runtime, or other
external effect was used to demonstrate the finding.

## Implementation

Implementation commit `6729aa8502cf1863e5ddfefedc25cdd206babdf2` captures
`actual_gate_type = type(self)` in `close()` and requires retained `_gate_type` to be
that exact identity before reading the actual runtime class mapping to confirm the
retained `_validate_bindings` function.

The M65 release-selection logic is unchanged. For the single-slot retained gate-type
drift case, `close()` skips uncertain validation dispatch and still invokes only the
reviewed release authority selected by M65 identity agreement. The gate becomes used,
closed, and stripped of released construction/policy authority.

M64 terminal authority release, M65 cleanup binding recovery, M66 retained begin
identity, M67 inert terminal-error artifacts, and M68/M69 entry preflights remain
unchanged. Public signatures and one-shot/terminal semantics are unchanged.

## Safety boundary

M70 adds no runtime capability and changes no socket construction, bind/listen/accept/
connect behavior, DNS, TLS, peer traffic, deployment, credentials, opt-in policy, or
external authorization. `NETWORK_EXTERNAL` and `DEPLOY` remain separately governed.

Development and acceptance are deterministic/offline except for the repository's normal
CI bootstrap. No live application-network or production-runtime acceptance is part of
M70.

## Optimization evidence

The green path adds one constant-time `type(self)` capture and one identity comparison.
It replaces a potentially attacker-controlled retained-object attribute dereference with
an actual-runtime-class lookup only after retained identity matches.

There is no new loop, retry, background task, queue, cache, concurrency, persistence,
unbounded allocation, network I/O, dependency, or retained capability. No required
quality, security, integration, governance, or conformance gate is weakened or bypassed.

## Recovery / blast radius

Recovery is an ordinary source-control revert of the M70 source, test, and documentation
commits. The blast radius is limited to explicit-close validation ordering for one
execution-gate instance; M70 creates no listener, connection, deployment, durable state,
or protected external effect.

## 2026-09-04 Policy v1.6 requalification

The original M70 tests-first history and five-line security fix remain unchanged. Before
requesting any merge authority, the open PR is being requalified against exact current
merged-green Marketplace `main`
`0c356ce8ffde629f38fda9fc0fafa49f02791821` (M17.1O / Policy v1.6).

Read-only forensic review of that exact `main` confirmed the M70 seam is still present:
`close()` still dereferences retained `gate_type.__dict__` before independently proving
that retained object is the actual runtime class. The M70 regression files are also not
present on `main`.

This documentation-only commit intentionally does not rebase, rewrite, or weaken the
original RED→GREEN provenance. Its purpose is to trigger a fresh PR merge-ref FULL against
the current `main` while preserving the reviewed source patch and tests exactly. Merge
remains separately governed by current Policy v1.6 exact-head review/authorization and
post-merge provenance requirements. No runtime, dependency, socket, network, deployment,
service/configuration, database, secret, or repository-administration authority is added.