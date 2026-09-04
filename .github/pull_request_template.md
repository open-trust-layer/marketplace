## Purpose and scope

Describe the smallest coherent change and what remains intentionally unchanged.

## Work Unit Contract

- Project / repository:
- Goal:
- Exact base / head / target where material:
- Behavior to change:
- Behavior to preserve:
- Mutation boundary:
- Authorization state:
- Validation lane: `FAST` / `FULL` / `RELEASE`
- Rollback / recovery:
- Stop conditions:

## Risk and capabilities

- Risk classification: `LOW` / `MODERATE` / `HIGH` / `CRITICAL`
- Required capabilities: `READ_PROJECT` / `WRITE_PROJECT` / `EXECUTE_LOCAL` / `NETWORK_EXTERNAL` / `INSTALL_DEPENDENCY` / `DEPLOY` / `DELETE` / `MANAGE_SECRETS` / `ADMIN`
- Exact target repository/branch/environment/resources:
- [ ] mixed-risk work uses the highest included risk
- [ ] privileged/destructive exact targets will be re-verified immediately before execution

## Safety / security / privacy

- [ ] SAFETY FIRST precedence preserved
- [ ] trust boundaries identified where relevant
- [ ] authentication/authorization/capability checks precede protected side effects
- [ ] no new unsafe command/query/path/template/network-destination construction
- [ ] secrets are not committed, logged, exposed, or embedded in fixtures/vectors/benchmarks
- [ ] external operations are bounded and timed out
- [ ] known material security defects are not hidden by green tests
- [ ] fast paths/caches/evidence reuse do not bypass required controls

Notes:

## Retention and project isolation

- Retention classes affected:
- [ ] transient content defaults to maximum 10-second post-use retention unless an explicit authorized exception/hold applies
- [ ] operational metadata contains no message/file/prompt/response bodies, secrets, raw media, or equivalent payload
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

## Authorization reuse / activation boundary

- Prior authorization reused, if any:
- Unchanged authorization inputs: project / target / exact head where specified / scope / risk / capability / side-effect class / rollback assumptions / expiry state
- [ ] no stale exact-head authorization is being reused after head movement
- [ ] merge authorization is not being treated as runtime activation authority
- [ ] runtime activation is not being treated as deployment or different-release authority
- [ ] dependency install / database migration / config-service mutation / provider admin / deployment remains separately authorized unless explicitly combined
- Preauthorized rollback condition/method, if any:

## Dependencies, cryptography, and provenance

- New/changed dependencies or benchmark/profiling tools:
- Dependency admission review:
- Provenance/integrity impact:
- Cryptographic/transport/key-management impact:
- [ ] no custom cryptography or ad-hoc key derivation/protocol design
- [ ] authenticated encryption / TLS / key separation requirements are satisfied where applicable
- [ ] encryption does not extend retention or authorization
- Reproducible-build claim: `NONE` / `INDEPENDENT MATCHING REPRODUCTION ATTACHED`

## Marketplace semantics and conformance

- Specifications affected:
- Vector suites affected:
- OLP compatibility/pin impact:
- [ ] no semantic behavior changed
- [ ] semantic behavior changed and corresponding specification/vectors/tests are included

## v1.6 Evidence Ledger

Record only decision-relevant evidence; do not copy project payload into long-lived metadata.

- VERIFIED:
- DECIDED:
- CHANGED:
- VALIDATED:
- WAITING:
- BLOCKED:
- NEXT:

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

- [ ] baseline and candidate are equivalent enough for the claim, or limitations are stated
- [ ] caches/precomputed state do not bypass authorization, revocation, policy, retention, or project isolation
- [ ] concurrency/fan-out/queues/pools remain bounded and use backpressure/admission control where needed
- [ ] required quality/security/integration/governance/conformance gates were not renamed, removed, skipped, bypassed, weakened, or short-circuited for speed
- [ ] benchmark/profile evidence contains no disallowed project payload or secrets

## Validation lane and evidence reuse

- Selected lane: `FAST` / `FULL` / `RELEASE`
- Why this lane is sufficient:
- Exact source/tree identity:
- Dependency/toolchain identity:
- Policy/governance version:
- Relevant config/test/build identity:
- Reused artifact digest(s), if any:
- [ ] ambiguous relevance falls back to FULL
- [ ] final review head uses FULL when policy/security/governance/dependency/HIGH/CRITICAL/ambiguous scope applies
- [ ] reused validation is integrity-bound to the same relevant inputs; otherwise it is not reused
- [ ] while CI ran, no mutation invalidated the head whose result is cited as evidence

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
- [ ] reproducible-build wording is used only when independent matching reproduction evidence exists

## Governance / external controls

- Current provider enforcement facts actually verified:
- Desired but unverified/unavailable provider controls:
- Independent approval count on exact accepted head:
- Unresolved review-thread count:
- Solo-maintainer procedure / governance exception, if applicable:

Do not describe desired policy, CODEOWNERS, CI, or a self-review as provider enforcement or independent human approval without verification.

## Completion review

- [ ] change is small and coherent
- [ ] unrelated behavior is preserved
- [ ] docs/config/policy companions are updated
- [ ] exceptions are explicit, scoped, owned, approved, and expiring
- [ ] rollback/recovery verified where material
- [ ] merge/runtime/deployment authority boundaries remain explicit
- [ ] optimization complexity is justified by measured benefit where applicable
- [ ] no known material security/privacy/isolation/retention/governance defect remains unresolved without an applicable authorized exception/compensating procedure
