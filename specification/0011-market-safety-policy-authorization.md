# Marketplace — Safety, Policy & Authorization Boundaries

**Status:** Draft v0.1
**Milestone:** 11 — Safety, Policy & Authorization Boundaries
**Filename:** `specification/0011-market-safety-policy-authorization.md`

---

## 1. Purpose

This specification defines Marketplace safety, policy-decision, and authorization boundaries without creating a global censor, regulator, moderation authority, universal allow/deny registry, or protocol-level permission oracle.

It standardizes one deterministic local reference method for combining explicit policy observations into an explainable `PolicyDecision` process result.

The result is method-relative and local. It does not become universal Marketplace truth merely because the evaluated records, proofs, authority grants, trust results, or disclosure plans are valid.

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are interpreted as described by RFC 2119 and RFC 8174 when written in all capitals.

## 3. Dependency baseline

M11 depends on Marketplace Specifications 0001–0010 and applicable OLP specifications, especially OLP 0004 for proof purposes and OLP 0006–0007 for identity, authority, delegation, and lifecycle evidence.

The executable conformance profile is pinned to OLP source commit `41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c`.
OLP remains authoritative for `authorization` proof-purpose semantics, AuthorityGrantStatementV1, authority delegation scope, authority/lifecycle status, exact evidence identity, and the distinction between authority evidence and final application authorization.

## 4. Core invariants

A conforming M11 processor MUST preserve these separations:

```text
protocol expressibility       != permission
record validity                != permission
proof validity                 != permission
authorization proof            != final authorization
authority grant                 != final authorization
authority evidence              != local policy decision
trust evaluation                != permission
privacy planning                != permission
discovery visibility            != legitimacy
PolicyDecision                  != universal truth
ALLOW                           != universal permission
DENY                            != universal prohibition
result fingerprint              != result authentication
observation source URI          != observation authentication
evaluation time input           != trusted timestamp evidence
```

M11 MUST NOT silently collapse evidence validity, authentication, attribution, identity, authority, delegation, lifecycle, trust, legality/compliance, safety, moderation, and business policy into one hidden score.

## 5. Core reference method

The M11 core reference method URI is:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/policy/method/core-authorization-v1
```
The core method is a non-record processing profile. It does not define a universal policy language, global policy source, globally ordered rule set, or mandatory moderation regime.

Extensions MAY define other method URIs. The core helper MUST fail closed for an unsupported method.

## 6. Core protected-operation taxonomy

M11 defines these exact core operation URIs:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/policy/operation/local-inspection
https://open-trust-layer.github.io/marketplace/semantics/v1/policy/operation/discovery-visibility
https://open-trust-layer.github.io/marketplace/semantics/v1/policy/operation/display
https://open-trust-layer.github.io/marketplace/semantics/v1/policy/operation/submission-ingestion
https://open-trust-layer.github.io/marketplace/semantics/v1/policy/operation/negotiation-handling
https://open-trust-layer.github.io/marketplace/semantics/v1/policy/operation/autonomous-execution
https://open-trust-layer.github.io/marketplace/semantics/v1/policy/operation/fulfillment-side-effect
https://open-trust-layer.github.io/marketplace/semantics/v1/policy/operation/settlement-side-effect
https://open-trust-layer.github.io/marketplace/semantics/v1/policy/operation/federation-exchange
https://open-trust-layer.github.io/marketplace/semantics/v1/policy/operation/disclosure
https://open-trust-layer.github.io/marketplace/semantics/v1/policy/operation/trust-result-consumption
```

`local-inspection` is the only core operation that is not protected by default. Local inspection and verification may be policy `NOT_APPLICABLE` when no protected effect is requested.

Unknown core operation identifiers MUST fail closed.

## 7. Protected side effects

The following operations are classified as protected side effects in M11 v1:

```text
submission-ingestion
autonomous-execution
fulfillment-side-effect
settlement-side-effect
federation-exchange
disclosure
```
Every protected side-effect request MUST explicitly require the `authorization` policy dimension.

An application MUST NOT execute a protected side effect merely because a Marketplace record is valid, an OLP proof verifies, an authority grant exists, a trust method is favorable, or a prior operation was allowed.

## 8. Policy request model

The M11 reference request is a process artifact with these semantic fields:

```text
version
method
decision_scope
operation
actor
target
context
evaluation_time
required_dimensions
```

`version` MUST be exact integer `1`; boolean values are not integers for this purpose.

`method`, `decision_scope`, `operation`, and `actor` MUST be absolute URIs. `target` identifies an exact Record, Principal, Subject URI, or resource URI. `context` is a bounded semantic map whose keys are absolute URIs and whose values are valid OLP values.

`evaluation_time` MUST be valid RFC 3339 text. M11 compares instants for applicability but fingerprints the exact request representation. The reference evaluator does not establish that this time came from a trusted clock or independent timestamp source.

## 9. Required policy dimensions

M11 v1 recognizes these exact dimensions:

```text
evidence-validity
proof-validity
authentication
attribution
identity
authority
delegation
lifecycle
authorization
trust
legal-compliance
safety
business-policy
moderation
```
`required_dimensions` MUST be duplicate-free and canonical UTF-8 sorted in the reference profile.

Protected non-local operations MUST require at least one explicit dimension. Protected side effects MUST include `authorization`.

The selected dimensions are a local method input. M11 core does not require every application to use the same legal, safety, fraud, moderation, trust, or business-policy dimensions.

## 10. Policy observations

A `PolicyObservation` is a non-record process artifact carrying:

```text
dimension
status
source
reason
evidence_ids
valid_from?
valid_until?
subject_fingerprint
```

`source` and `reason` MUST be absolute URIs. A source URI identifies provenance asserted to the evaluator; it does not authenticate that source.

`evidence_ids` contains canonical, sorted, duplicate-free OLP Record identities when evidence provenance is available. Evidence references do not make an observation true merely by being listed.

`valid_from` and `valid_until`, when present, are RFC 3339 inputs used for temporal applicability. They are policy inputs, not independent historical timestamp evidence.

## 11. Observation status vocabulary

M11 v1 recognizes:

```text
SATISFIED
UNSATISFIED
UNKNOWN
UNSUPPORTED
NOT_APPLICABLE
REQUIRE_ADDITIONAL_EVIDENCE
REQUIRE_HUMAN_REVIEW
QUARANTINE
```

These are method-relative observations, not universal labels on a participant, record, jurisdiction, or subject.

## 12. Observation subject binding

Every M11 v1 observation MUST carry a canonical `subject_fingerprint` bound to the exact policy subject for which the observation was produced.

The subject fingerprint is the unpadded base64url SHA-256 digest of deterministic OLP encoding of the normalized request fields:

```text
version
method
decision_scope
operation
actor
target
context
required_dimensions
```

`evaluation_time` is intentionally excluded from the subject fingerprint because time applicability is evaluated separately. The full request fingerprint still includes `evaluation_time`.

An observation bound to a different actor, operation, target, context, decision scope, method, or required-dimension set MUST NOT be reused. The core helper fails with `POLICY_OBSERVATION_SUBJECT_MISMATCH`.

This binding prevents a locally accepted observation such as “authorization satisfied for actor A performing operation X on resource R” from being silently reused for actor B, operation Y, or another target.

## 13. OLP authority and authorization evidence

M11 does not redefine OLP authority records, delegation, status, or proof-purpose semantics.

An OLP `authorization` proof can establish attributable authorization intent according to OLP. An AuthorityGrantStatementV1 can represent a grant assertion. Delegation and lifecycle evidence can support or weaken reliance on that grant.

None of those artifacts alone is the M11 final `ALLOW` decision.

Applications SHOULD derive distinct `authority`, `delegation`, `lifecycle`, and `authorization` observations from accepted OLP evidence and local policy rather than treating graph reachability or one valid proof as automatic permission.

## 14. Temporal applicability

For each observation, the reference method compares `evaluation_time` with optional `valid_from` and `valid_until` instants.

An observation that is before its declared interval or at/after its declared upper bound is `STALE` for that evaluation.

A stale required observation MUST NOT produce `ALLOW`. Stale and unsupported required dimensions resolve to `INDETERMINATE` unless a stronger explicit restrictive outcome applies.

Changing `evaluation_time` changes the full request binding and therefore requires a new PolicyDecision. The same subject-bound observation MAY be reevaluated at a later time if it remains temporally applicable.

The reference result reports `evaluation_time_trust_established = false`. Security-sensitive applications SHOULD use a trusted local clock or accepted independent temporal evidence when policy depends on trustworthy time.

## 15. Per-dimension aggregation

The core reference method evaluates each required dimension independently.

Exact duplicate observations are deduplicated. Input order MUST NOT affect the normalized observation set.

If applicable observations for one required dimension contain more than one distinct decisive status, the dimension state is `CONFLICT`.

If one decisive status is present, that status is preserved unless an `UNKNOWN` or `UNSUPPORTED` state makes an otherwise satisfied dimension unresolved.

If only stale observations exist, the dimension state is `STALE`. If no applicable observation exists, the dimension state is `MISSING`.

M11 core does not silently assign one source global precedence over another. A different policy-composition method MAY define explicit precedence under another method URI.

## 16. Decision outcome lattice

The core reference method returns exactly one of:

```text
ALLOW
DENY
REQUIRE_ADDITIONAL_EVIDENCE
REQUIRE_HUMAN_REVIEW
QUARANTINE
CONFLICTING_POLICY
INDETERMINATE
NOT_APPLICABLE
```
The reference precedence is deterministic:

```text
any required-dimension conflict       -> CONFLICTING_POLICY
any UNSATISFIED required dimension    -> DENY
any QUARANTINE required dimension     -> QUARANTINE
any REQUIRE_HUMAN_REVIEW              -> REQUIRE_HUMAN_REVIEW
any UNSUPPORTED or STALE dimension    -> INDETERMINATE
any UNKNOWN, MISSING, or explicit
  REQUIRE_ADDITIONAL_EVIDENCE         -> REQUIRE_ADDITIONAL_EVIDENCE
all required dimensions SATISFIED     -> ALLOW
no required dimensions                -> NOT_APPLICABLE
```

This precedence is the behavior of `core-authorization-v1`; it is not a universal policy ordering for all Marketplace applications.

## 17. Fail-closed authorization

A security-sensitive protected side effect MUST NOT proceed on `REQUIRE_ADDITIONAL_EVIDENCE`, `REQUIRE_HUMAN_REVIEW`, `QUARANTINE`, `CONFLICTING_POLICY`, `INDETERMINATE`, `NOT_APPLICABLE`, or `DENY` when the local application requires an affirmative M11 authorization decision.

`INDETERMINATE` and `REQUIRE_ADDITIONAL_EVIDENCE` are not aliases for `DENY`; they preserve why authorization could not be established.

An unsupported, unresolved, stale, missing, out-of-scope, or conflicting authorization input MUST NOT be silently upgraded to `ALLOW`.

## 18. Policy conflicts

Conflicting applicable policy observations MUST remain visible in the result trace.

The core method MUST NOT resolve a conflict merely by lexical source ordering, record arrival order, latest timestamp, highest trust score, or hidden implementation preference.

Applications MAY use a different explicitly named policy method with documented precedence rules. Such a method's result remains local and method-relative.

## 19. Explainable decision trace

Every required dimension produces a summary containing its state, contributing source URIs, reason URIs, evidence Record identities, and observation count.

The complete normalized observation trace is also returned with effective temporal status.
A conforming result MUST NOT expose only an unexplained Boolean permission bit while discarding the dimension/source/reason provenance that produced it.

## 20. Fingerprints and integrity bindings

The reference helper defines three SHA-256 fingerprints using deterministic OLP encoding and canonical unpadded base64url text:

- `request_fingerprint` binds the full normalized request, including `evaluation_time`;
- `policy_subject_fingerprint` binds the policy subject defined in Section 12, excluding `evaluation_time`; and
- `policy_input_fingerprint` binds the full normalized request plus the normalized observation set.

The result also carries `result_fingerprint`, an integrity digest over the exact core result projection.

These fingerprints are deterministic bindings. They are not signatures, MACs, trusted timestamps, producer authentication, or authority evidence.

## 21. Reference result contract

The M11 v1 result includes at least:

```text
version
method
decision_scope
operation
actor
target
evaluation_time
required_dimensions
outcome
dimension_summaries
observation_trace
duplicate_observations
request_fingerprint
policy_subject_fingerprint
policy_input_fingerprint
protected_operation
protected_side_effect
local_policy_allows_operation
result_fingerprint
```

The result further reports explicit boundary flags described below.

## 22. Explicit non-authority boundary flags

The reference result reports all of the following as `false`:

```text
policy_decision_is_universal
authority_evidence_is_final_permission
trust_is_policy_permission
legal_finality_established
decision_is_marketplace_record
hidden_network_fallback_permitted
policy_observation_authentication_established
result_authentication_established
evaluation_time_trust_established
```

These flags are normative safeguards against accidental semantic escalation.

`local_policy_allows_operation = true` means only that the named local method produced `ALLOW` for the exact bound inputs.

## 23. Decision reuse and stale-decision boundary

A prior M11 result MAY be considered reusable only when:

1. the prior result is structurally valid and its `result_fingerprint` matches its exact core content;
2. the prior outcome is `ALLOW`;
3. the current request fingerprint exactly matches the prior request fingerprint; and
4. the current policy-input fingerprint exactly matches the prior policy-input fingerprint.

A changed actor, operation, target, context, decision scope, required-dimension set, observation set, or evaluation time requires reevaluation.

A non-ALLOW result MUST NOT become reusable permission merely because the caller presents it again.

Unknown extra fields in a prior result MUST be rejected by the v1 reuse validator so unbound permission-like metadata cannot be smuggled alongside an otherwise valid result.

## 24. Result authentication

The M11 result fingerprint detects accidental or malicious content modification relative to the hashed result projection. It does not authenticate who produced the PolicyDecision.
The reuse helper therefore reports `prior_result_authentication_evaluated = false`.

An application that receives a PolicyDecision from another process, host, organization, or participant MUST authenticate that decision through a trusted local channel or separate attributable evidence before using it as authority for a protected side effect.

A PolicyDecision MAY itself be intentionally logged or attested as an ordinary attributable OLP record when portable audit evidence is required. Such an attestation remains evidence about the decision, not universal permission.

## 25. Legal, compliance, safety, moderation, and business policy

M11 provides independent dimensions for `legal-compliance`, `safety`, `moderation`, and `business-policy` but does not define universal rules for any of them.

Jurisdictional legality, sanctions screening, fraud detection, age/capability restrictions, hazardous-domain controls, platform moderation, organizational approvals, and risk models remain application- or profile-specific unless represented as attributable evidence under a separate specification.

One implementation's `DENY`, `QUARANTINE`, or `REQUIRE_HUMAN_REVIEW` does not become a global prohibition.

Likewise, one implementation's `ALLOW` does not bind another application, regulator, court, participant, or jurisdiction.

## 26. Trust and recommendation boundary

A favorable M9 trust result MAY be one policy input if the local method chooses to require `trust`.

Trust evidence or evaluation MUST NOT bypass authorization, safety, legal, moderation, or business-policy dimensions required by the local policy method.

A low trust result likewise does not automatically prove illegality, fraud, or lack of authority.

## 27. Privacy and disclosure boundary

M10 disclosure planning and M11 permission evaluation are separate.

A disclosure plan answers what evidence would be selected for a declared disclosure task. M11 answers whether the local application permits performing the disclosure operation under its current policy inputs.

A privacy-safe disclosure set is not automatically authorized, and an authorized disclosure does not prove that the disclosure is globally minimal, lawful in every jurisdiction, or risk-free.

## 28. Network behavior

M11 performs no implicit network dereference.

Policy observation collection, OLP evidence resolution, sanctions/compliance lookup, identity resolution, external trust services, or other network access MUST be performed explicitly by the surrounding application or profile before observation aggregation.

The reference result reports `hidden_network_fallback_permitted = false`.

Any network-enabled policy system SHOULD apply explicit resolver policy, SSRF defenses, redirect limits, response-size limits, timeouts, rate limits, caching rules, privacy controls, and auditability appropriate to the environment.

## 29. Resource bounds

The M11 v1 reference profile applies these ceilings:

```text
required dimensions              32
policy observations            4096
evidence Record IDs per obs     256
semantic context entries        128
URI UTF-8 length               2048 bytes
```

Implementations MAY choose lower local limits. An implementation MUST NOT silently claim the exact M11 v1 reference profile while raising these ceilings without an explicitly different profile or documented compatibility rule.

Resource-limit failure MUST remain distinct from authorization denial, proof failure, evidence absence, or policy conflict.

## 30. Protected-side-effect execution and idempotency

An M11 `ALLOW` is a permission decision input, not evidence that the protected side effect actually executed.

Execution systems MUST retain their own idempotency, replay protection, transactional safety, settlement safety, fulfillment safety, and audit controls.

Decision reuse MUST NOT be confused with side-effect idempotency. A reusable decision can still accompany a duplicate or unsafe execution attempt that the application must reject separately.

## 31. Security considerations

Implementations MUST treat externally supplied Marketplace records, policy observations, claimed source URIs, PolicyDecision results, and timestamps as untrusted until validated under the applicable layer.

A valid OLP authority grant MUST NOT bypass local policy. A valid M11 result fingerprint MUST NOT be treated as a digital signature. A source URI MUST NOT be treated as authenticated merely because it parses.

Observation subject binding MUST be verified before aggregation so authorization evidence cannot cross actor, target, operation, decision-scope, context, or required-dimension boundaries.

Security-sensitive side effects SHOULD normally require a fresh affirmative local decision at execution time and SHOULD fail closed when required authorization dimensions cannot be evaluated.

Applications SHOULD preserve the reasons for `DENY`, `QUARANTINE`, `REQUIRE_HUMAN_REVIEW`, `CONFLICTING_POLICY`, `INDETERMINATE`, and `REQUIRE_ADDITIONAL_EVIDENCE` rather than collapsing them into one opaque failure.

## 32. Conformance vectors

The executable M11 corpus is:

`conformance/vectors/safety-policy-authorization-v1.json`

The reference helper is `tools/marketplace_policy_v1.py`, the deterministic generator is `tools/generate_policy_vectors.py`, and the independent replay validator is `tools/validate_policy_vectors.py`.

The reviewed M11 corpus contains **77 vectors: 35 positive/evaluation and 42 negative/adversarial**.

The corpus covers all eleven core operations, all eight decision outcomes, protected-side-effect authorization gates, exact provenance/reasons, conflict preservation, temporal applicability, deterministic fingerprints, decision reuse, result-integrity validation, subject-binding replay attacks, malformed inputs, and resource ceilings.

## 33. Examples

A local search index may evaluate `discovery-visibility` under safety and moderation policy without claiming that hidden records are globally prohibited.

A settlement worker may require authorization, authority/delegation, lifecycle, safety, and business-policy observations before performing a payment-side effect. Missing or stale authorization cannot become `ALLOW`.
A disclosure service may have a privacy-safe M10 plan but still receive `DENY` or `REQUIRE_HUMAN_REVIEW` from M11 because privacy minimization and recipient authorization are separate questions.

A previously allowed autonomous execution must be reevaluated if the actor, target, context, evidence set, or evaluation time changes.

Two local policy sources may disagree. `core-authorization-v1` surfaces the conflict rather than silently selecting whichever source arrived last.

## 34. Deferred and out of scope

M11 does not define:

- a universal moderation policy;
- a global sanctions or compliance list;
- a universal fraud or abuse model;
- jurisdiction-specific legal advice or legal finality;
- a universal age, capability, licensing, export-control, or hazardous-goods regime;
- one global policy language or policy source precedence;
- one global trust threshold;
- a global account or role authorization server;
- a universal PolicyDecision record type;
- result signatures or a mandatory decision-attestation format;
- a trusted timestamp service;
- protected-side-effect transactional/idempotency protocols already handled by other layers; or
- mandatory network access for policy evaluation.

Future profiles MAY define narrower domain-specific policy methods while preserving the separation between evidence, authority, local policy, and universal protocol truth.

## 35. Milestone 11 acceptance boundary

Milestone 11 is complete when:

1. Specification 0011 defines the normative safety/policy/authorization boundary;
2. OLP authority and authorization evidence is reused rather than redefined;
3. policy evaluation remains method-relative, local, attributable, and non-universal;
4. protected operations and side effects are explicit, with authorization required before protected side effects;
5. unsupported, unresolved, stale, missing, conflicting, or out-of-scope authorization inputs cannot silently produce `ALLOW`;
6. evidence validity, proof, authentication, attribution, identity, authority, delegation, lifecycle, authorization, trust, legal/compliance, safety, moderation, and business policy remain separate dimensions;
7. decision outcomes are deterministic and explainable without hidden weighting;
8. conflicting policy inputs remain explicit rather than being silently overridden;
9. observations are bound to the exact policy subject and cross-subject replay is rejected;
10. prior `ALLOW` reuse is bound to exact request/input fingerprints and changed assumptions require reevaluation;
11. result fingerprints are treated as integrity bindings rather than producer authentication;
12. PolicyDecision remains a process artifact by default and never becomes universal permission/prohibition;
13. no universal moderation, sanctions, fraud, safety, legal, or business policy is introduced;
14. resource/network bounds are explicit and hidden network fallback is prohibited;
15. the 77-vector M11 corpus passes independently and Milestones 3–10 remain green; and
16. deterministic regeneration, documentation, repository audit, pull-request review, and post-merge gates pass.
