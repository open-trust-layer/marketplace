# M68 — Loopback Execution Gate Preflight Failure-Binding Hardening

## Baseline

M68 starts from merged-green M67 commit
`d7460256a17e3f570937dd4732ede1d2f7ccf4e3`.

M67 hardened the inert post-release terminal error artifact. The remaining entry-path
gap was earlier: both public methods checked retained validator authority before normal
binding validation, but the failure branch itself invoked retained `_fail_function`.

## Tests-first finding

Behavioral regression coverage was committed before the source fix:

- `486d3632cfaf5cdcfc45aea177d6c3aebb4c6e1f` — coherent validator/fail poisoning and hostile retained-gate-type tests.

The tests require both `dry_run()` and `execute_once()` to report stable
`LOOPBACK_EXECUTION_BINDING_DRIFT` without executing substituted validator/fail code,
and without dereferencing an unvalidated retained gate-type object.

## Implementation

Implementation commit `b3af135206b6c425f452b53d4c23c281f9feaec0` removes pre-validation failure dispatch
through `_fail_function` and compares retained `_gate_type` by identity with `type(self)`
before any attribute access through the retained value.

When the preflight detects drift, it reconstructs the reviewed gate exception directly
from the already-reviewed inert M67 terminal anchors using `BaseException` primitives.
It does not call a retained failure helper, constructor, descriptor, network operation,
or other unvalidated project authority.

The normal `_validate_bindings()` path remains authoritative whenever the retained
validator identity passes the preflight check.

## Safety boundary

M68 changes no socket construction, bind/listen/accept/connect behavior, DNS, TLS,
peer traffic, deployment, credentials, opt-in policy, or external authorization.
All new tests are deterministic and offline. Existing `NETWORK_EXTERNAL` and `DEPLOY`
boundaries remain unchanged and require separate fresh authorization.

## Optimization evidence

The change adds only constant-size identity checks and exception reconstruction on a
drift/failure path. The normal green execution path replaces one retained-class
attribute lookup with the exact runtime class lookup and performs no new loop, retry,
background task, I/O, queue, cache, concurrency, or unbounded allocation.

No required quality, security, integration, governance, or conformance gate is renamed,
removed, skipped, bypassed, weakened, or short-circuited.
