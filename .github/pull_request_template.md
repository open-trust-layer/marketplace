## Purpose and scope

Describe the smallest coherent change and what remains intentionally unchanged.

## Risk and capabilities

- Risk classification: `LOW` / `MODERATE` / `HIGH` / `CRITICAL`
- Required capabilities: `READ_PROJECT` / `WRITE_PROJECT` / `EXECUTE_LOCAL` / `NETWORK_EXTERNAL` / `INSTALL_DEPENDENCY` / `DEPLOY` / `DELETE` / `MANAGE_SECRETS` / `ADMIN`
- Exact target repository/branch/environment/resources:

## Safety / security / privacy

- [ ] SAFETY FIRST precedence preserved
- [ ] trust boundaries identified where relevant
- [ ] authentication/authorization/capability checks precede protected side effects
- [ ] no new unsafe command/query/path/template/network-destination construction
- [ ] secrets are not committed, logged, exposed, or embedded in fixtures/vectors/benchmarks
- [ ] external operations are bounded and timed out
- [ ] known material security defects are not hidden by green tests

Notes:

## Retention and project isolation

- Retention classes affected:
- [ ] transient content defaults to maximum 10-second post-use retention unless an explicit authorized exception applies
- [ ] operational metadata contains no message/file/prompt/response bodies or secrets
- [ ] automatic expiry/deletion is implemented and tested where applicable
- [ ] project boundaries/cross-project flows remain explicit
- [ ] benchmark/profile/cache data follows normal retention and isolation rules
- [ ] deletion/retention guarantees are not claimed without verification

Notes:

## Destructive / privileged actions

- [ ] not applicable
- [ ] exact target re-verified immediately before execution
- [ ] blast radius reviewed
- [ ] dry-run/reversible alternative considered
- [ ] rollback/recovery defined where possible
- [ ] result independently verified

Notes:

## Dependencies and provenance

- New/changed dependencies or benchmark/profiling tools:
- Dependency admission review:
- Provenance/integrity impact:

## Marketplace semantics and conformance

- Specifications affected:
- Vector suites affected:
- OLP compatibility/pin impact:
- [ ] no semantic behavior changed
- [ ] semantic behavior changed and corresponding specification/vectors/tests are included

## Performance / optimization evidence

- [ ] not applicable — no material performance/resource claim or optimization-sensitive change
- Problem / user or operational impact:
- Critical path:
- Metric:
- Budget / success condition:
- Representative baseline:
- Profiling or bottleneck evidence:
- Optimization hypothesis:
- Candidate measurement:
- Resource effects (CPU / memory / allocation / I/O / network / queue / external service):
- Tail latency / saturation impact where relevant:
- Cache / batching / concurrency / backpressure / invalidation notes where relevant:
- Variance / limitations:
- Result: `KEEP` / `REVISE` / `REVERT`

- [ ] baseline and candidate measurements are equivalent enough for the claim, or limitations are stated
- [ ] caches/precomputed state do not bypass authorization, revocation, policy, retention, or project isolation
- [ ] concurrency/fan-out/queues/pools remain bounded and use backpressure/admission control where needed
- [ ] required quality/security/integration/governance/conformance gates were not renamed, removed, skipped, bypassed, weakened, or short-circuited for speed
- [ ] benchmark/profile evidence contains no disallowed project payload or secrets

## Verification

Focused checks:

```text
<commands / results>
```

Full acceptance, when applicable:

```text
python tools/conformance_gate.py --olp-root <path-to-pinned-olp-checkout>
```

- [ ] focused tests pass
- [ ] repository audit passes
- [ ] all applicable conformance vectors pass
- [ ] deterministic generator replay passes where applicable
- [ ] Git whitespace checks pass
- [ ] material performance claims have evidence adequate to the claim

## Governance / external controls

List any provider-side or administrative controls that were not independently verified (for example branch protection/rulesets). Do not describe desired policy as active enforcement without verification.

## Completion review

- [ ] change is small and coherent
- [ ] unrelated behavior is preserved
- [ ] docs/config/policy companions are updated
- [ ] exceptions are explicit, scoped, owned, approved, and expiring
- [ ] optimization complexity is justified by measured benefit where applicable
- [ ] no known material security/privacy/isolation/retention defect remains unresolved without an authorized exception
