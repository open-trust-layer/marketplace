# Specification 0015 — Remedy & Workflow Profiles

**Status:** Draft v0.1
**Milestone:** 16 — Remedy & Workflow Profiles
**Filename:** `specification/0015-market-remedy-workflow-profiles.md`

## 1. Purpose

This specification defines portable, domain-scoped coordination profiles that produce explainable follow-up proposals from explicitly supplied outcome observations. A proposal coordinates possible next steps; it does not decide legal rights, mutate a universal case, create settlement or fulfillment evidence, or execute an action.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, and **MAY** have the meanings defined by RFC 2119 and RFC 8174 when capitalized.

## 2. Dependency and constitutional boundaries

Marketplace Specifications 0001–0014 and the applicable Open Layer Protocol specifications remain authoritative. The executable compatibility target is the OLP source commit `41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c`; a release MUST bind to an explicit released compatibility target.

Conforming implementations MUST preserve these distinctions:

```text
workflow proposal           != legal remedy
proposal                    != obligation
proposal                    != authorization
protected proposal          != executed side effect
proposed refund             != settlement evidence
proposed replacement        != fulfillment evidence
workflow status             != mutable global case state
source outcome              != universal truth
profile rule                != universal policy
fingerprint                 != authentication
```

Milestone 13 remains authoritative for dispute-resolution conclusions; Milestones 7 and 6 remain authoritative for settlement and fulfillment evidence; Milestone 11 remains authoritative for protected-side-effect authorization. M16 MUST NOT duplicate, silently replace, or bypass those boundaries.

## 3. Processing profile and algorithm plurality

The non-normative reference processing profile is:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/remedy-workflow/profile/outcome-rules-v1
```

This URI identifies one reproducible algorithm, not a canonical remedy system, global court, mandatory workflow, legal authority, or universal policy. Concrete methods MUST declare distinct absolute method URIs and explicit domain/purpose scopes. Unrelated profiles MAY disagree without establishing a universally correct remedy.

## 4. Remedy workflow method profile

```text
RemedyWorkflowProfileV1 = {
  version: 1,
  profile: AbsoluteURI,
  method: AbsoluteURI,
  domain: AbsoluteURI,
  purposes: SortedUniqueAbsoluteURIs,
  rules: SortedUniqueRuleProfiles,
  critical: SortedUniqueAbsoluteURIs
}
```

`version` MUST be integer 1; boolean values MUST NOT be accepted as integer versions. Purposes and rules MUST be nonempty, bounded, sorted, and duplicate-free. A method URI MUST NOT silently retain its old meaning when its normalized profile changes; its exact profile fingerprint MUST invalidate reuse.

## 5. Rules and workflow steps

```text
RuleProfileV1 = {
  id: AbsoluteURI,
  trigger: AbsoluteURI,
  required: Boolean,
  steps: SortedUniqueWorkflowSteps,
  critical: SortedUniqueAbsoluteURIs
}

WorkflowStepV1 = {
  id: AbsoluteURI,
  action: AbsoluteURI,
  depends_on: SortedUniqueAbsoluteURIs,
  protected: Boolean,
  conflict_group: AbsoluteURI | null,
  critical: SortedUniqueAbsoluteURIs
}
```

Rule and action identifiers carry no universal legal or policy meaning. Step identifiers MUST be unique across the entire profile. Dependencies MUST identify declared steps and form a directed acyclic graph. Cycles, dangling dependencies, repeated identifiers, and resource-limit violations MUST fail explicitly.

`conflict_group` groups mutually incompatible proposed actions under this profile. The reference planner MUST retain all simultaneously applicable conflicting steps and require human review; it MUST NOT choose a winner by arrival order, timestamps, rule count, or undisclosed priority.

## 6. Coordination request and outcome observations

```text
WorkflowRequestV1 = {
  version: 1,
  method: AbsoluteURI,
  domain: AbsoluteURI,
  purpose: AbsoluteURI,
  target_record_ids: SortedUniqueCanonicalOLPRecordIdentities,
  context: SemanticMap,
  understood_critical: SortedUniqueAbsoluteURIs
}

OutcomeObservationV1 = {
  trigger: AbsoluteURI,
  state: PRESENT | ABSENT | UNKNOWN | UNSUPPORTED,
  target_record_id: CanonicalOLPRecordIdentity,
  source_result_fingerprint: SHA256Base64URL,
  critical: SortedUniqueAbsoluteURIs
}
```

The request method and domain MUST match its profile, its purpose MUST be declared, and target Record Identities MUST be exact OLP identities. Observations MUST reference declared triggers and requested targets. A source-result fingerprint identifies supplied process output only; it MUST NOT establish truth, authentication, settlement, fulfillment, or authority.

Exact duplicate observations MAY be deduplicated. Distinct observations for the same trigger/target MUST fail explicitly; delivery order MUST NOT choose a winner.

## 7. Open-world and critical-semantics processing

Missing optional observations MUST NOT become adverse evidence. Required triggers lacking sufficient supplied observations MUST fail closed to `REQUIRE_ADDITIONAL_EVIDENCE`; explicit `ABSENT` remains distinct from missing or unknown evidence.

Unknown profile, applicable-rule, selected-step, or supplied-observation critical semantics MUST fail closed to `INDETERMINATE`. Selected steps whose dependencies are not themselves supported by applicable observations MUST require additional evidence rather than silently acquiring unsupported prerequisite steps.

## 8. Deterministic proposal and explicit conflicts

The reference result uses exactly one method-relative outcome:

```text
PROPOSED
PARTIAL
REQUIRE_ADDITIONAL_EVIDENCE
REQUIRE_HUMAN_REVIEW
INDETERMINATE
```

Each result MUST preserve rule traces, proposed action identifiers, dependency order, side-effect classifications, unresolved required rules, unavailable dependencies, unknown critical semantics, and conflicting action groups. Topological ordering MUST use UTF-8 lexical tie breaking. A result is processing output, not a new first-class Marketplace record or mutable universal case state.

## 9. Protected operations and fresh authorization

Every proposed protected step MUST declare `requires_fresh_authorization: true`, `authorized: false`, and `executed: false`. Informational proposals also MUST NOT be represented as executed. A later executor MUST obtain a separate, fresh Milestone 11 authorization decision immediately before any protected side effect. Cached workflow output, dispute conclusions, positive trust results, and method fingerprints MUST NOT substitute for authorization.

The reference planner MUST perform no network, filesystem, process, environment, credential, settlement, fulfillment, or other side-effect activity.

## 10. Fingerprints, integrity, and exact reuse

Profiles, requests, normalized inputs, and results use deterministic OLP-compatible encoding and SHA-256 base64url fingerprints. Exact reuse MUST bind the normalized method profile, method, domain, purpose, target Record Identities, context, understood-critical semantics, normalized outcome observations, source-result fingerprints, and deterministic proposal graph.

Changed profiles, requests, observations, source-result fingerprints, or semantic proposal output MUST invalidate reuse. Duplicate-delivery counts are diagnostics only and MUST NOT change semantic input fingerprints, semantic result fingerprints, or exact reuse eligibility. Fingerprints establish deterministic content identity only; they do not authenticate their producer.

## 11. Resource limits and explicit errors

The reference profile bounds rules to 128, steps and dependencies to 256 each, observations to 512, target Record Identities and context entries to 128 each, URI sets to 256, and individual URI encodings to 2048 UTF-8 bytes. Invalid host-language values, malformed structures, unsupported states, conflicting observations, dangling dependencies, cycles, mismatched scope, and exceeded ceilings MUST produce explicit bounded failures.

## 12. Executable conformance

The reference helper is `tools/marketplace_remedy_workflow_v1.py`; its deterministic generator and independent validator are `tools/generate_remedy_workflow_vectors.py` and `tools/validate_remedy_workflow_vectors.py`. The vector artifact is `conformance/vectors/remedy-workflow-v1.json`.

Acceptance requires deterministic vector regeneration, independent validation, adversarial regressions, all previously registered Marketplace suites, repository audit, Git whitespace checks, and the unified local/GitHub CI acceptance gate.
