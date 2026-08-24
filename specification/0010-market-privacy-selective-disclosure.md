# Marketplace — Privacy, Selective Disclosure & Data Minimization Profiles

**Status:** Draft v0.1
**Milestone:** 10 — Privacy, Selective Disclosure & Data Minimization Profiles
**Filename:** `specification/0010-market-privacy-selective-disclosure.md`

---

## 1. Purpose

This specification defines Marketplace-specific privacy and disclosure profiles over Open Layer Protocol Specification 0010.

It standardizes task-scoped disclosure planning for discovery, negotiation, fulfillment verification, settlement verification, federation exchange, and trust evaluation without introducing a parallel privacy protocol, redactable Marketplace record format, universal consent model, or mandatory encryption or credential scheme.

Marketplace M10 reuses OLP whole-object and graph-subset selective disclosure. Exact immutable OLP and Marketplace identities remain authoritative.

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are interpreted as described by RFC 2119 and RFC 8174 when written in all capitals.

## 3. Dependency baseline

Marketplace Privacy v1 depends on Marketplace Specifications 0001–0009 and applicable OLP specifications, especially OLP 0010 for privacy/selective disclosure and OLP 0008 for evidence bundles.

The executable vectors use OLP source commit:

```text
41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c
```

OLP remains authoritative for `DisclosureRequestV1`, disclosure dependency semantics, exact Record/Proof identity, resource commitments, bundle construction, native privacy warnings, and external selective-disclosure format semantics.

## 4. Core invariants

A conforming M10 processor MUST preserve these separations:

```text
selective disclosure        != field deletion
withheld evidence            != nonexistent evidence
withheld evidence            != adverse evidence
task-scoped minimized        != globally minimal
task-scoped closure          != global graph closure
privacy warning              != evidence invalidity
pairwise/contextual identity != globally linkable identity
offline verification         != universally more private
online verification          != universally more private
recipient intent             != cryptographic audience binding
privacy planning             != authorization
privacy planning             != consent / lawful basis
privacy planning             != trust
native selective disclosure  != reconstructed hidden claims
```

Privacy planning MUST NOT silently rewrite Marketplace lifecycle, fulfillment, settlement, federation, or trust-evaluation semantics.

## 5. Core Marketplace privacy profile

The core Marketplace privacy profile URI is:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/privacy/profile/core-v1
```

The profile is a processing profile, not a new Marketplace record type, OLP envelope, privacy credential, consent receipt, or encryption format.

## 6. Core disclosure tasks

M10 core recognizes exactly these task-purpose URIs:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/privacy/task/discovery
https://open-trust-layer.github.io/marketplace/semantics/v1/privacy/task/negotiation
https://open-trust-layer.github.io/marketplace/semantics/v1/privacy/task/fulfillment-verification
https://open-trust-layer.github.io/marketplace/semantics/v1/privacy/task/settlement-verification
https://open-trust-layer.github.io/marketplace/semantics/v1/privacy/task/federation-exchange
https://open-trust-layer.github.io/marketplace/semantics/v1/privacy/task/trust-evaluation
```

Unknown task URIs MUST fail closed in the core reference profile. Extensions MAY define other absolute task URIs under their own profiles.

## 7. Request model

M10 reuses OLP `DisclosureRequestV1` unchanged. The Marketplace task URI is carried in the OLP request `purpose` position.

A core M10 request MUST therefore remain an OLP disclosure request and MUST NOT be wrapped in a Marketplace-specific disclosure envelope.

M10 adds processing limits around the OLP request but does not redefine OLP request identity or encoding.

## 8. Marketplace roots

Every M10 core disclosure root MUST be an OLP Record reference.

When a requested root is available in local planner inventory, its decoded record body MUST be present and MUST validate as one of the three core Marketplace record types:

```text
MarketIntent
MarketAgreement
MarketEvent
```

A proof reference cannot serve as an M10 core Marketplace root. Proofs and other OLP evidence MAY appear as supporting dependencies.

An unavailable requested Marketplace root remains an explicit unresolved/missing dependency under OLP planning semantics; absence MUST NOT be converted into a negative Marketplace claim.

## 9. Supporting evidence

Supporting disclosure dependencies MAY include Marketplace records, OLP proofs, relationship records, identity/authority evidence, lifecycle evidence, and committed external resources.

A selected supporting record whose OLP type is a Marketplace core record type MUST also satisfy Marketplace semantic validation. A malformed selected Marketplace record MUST fail with a structured M10 error rather than being treated as a harmless privacy warning.

Supporting evidence does not become a Marketplace root merely because it is selected.

## 10. Explicit dependency closure

M10 MUST NOT infer that every record reference inside a Marketplace record is automatically required for the declared disclosure task.

Dependencies are followed only when the planner context explicitly classifies them as protocol, policy, or offline dependencies under OLP 0010.

This prevents privacy planning from degenerating into broad graph export. `source_records`, `related_records`, `commitment_refs`, subjects, evidence references, and other Marketplace links remain semantically meaningful without being automatically traversed.

Unresolved required dependencies MUST be surfaced explicitly. They MUST NOT be silently omitted while claiming a complete task closure.

## 11. Exact identity and no field redaction

M10 inherits OLP 0010's whole-object disclosure rule.

A selected Marketplace record MUST retain its exact OLP Record Identity. Removing, changing, or replacing a field creates a different record and MUST NOT be presented as the original identified record.

A detached proof over the original record cannot be reused as proof over a field-deleted record unless a separate cryptographic selective-disclosure system explicitly provides those semantics.

The reference profile reports `field_redaction_performed = false`.

## 12. Withholding and open-world semantics

Withholding an unrelated or unavailable record is not protocol falsification.

A recipient MUST NOT infer from omission that the record does not exist, is invalid, is adverse, has been withdrawn, proves non-performance, proves non-payment, or reduces trust.

The reference profile reports:

```text
withheld_evidence_is_negative_evidence = false
global_completeness_established = false
global_minimality_claimed = false
```

## 13. Task-scoped minimization

A conforming planner MAY state that a result is task-scoped minimized disclosure when it follows OLP 0010 dependency planning for the declared task.

It MUST NOT claim that the selected set is the globally smallest possible disclosure unless a separate formal method establishes that claim.

Different valid disclosure sets MAY satisfy the same task under different policy, offline/online, authority, proof, or resource assumptions.

## 14. OLP privacy warnings

M10 preserves OLP 0010 privacy warnings unchanged.

A privacy warning is diagnostic evidence about disclosure risk. It MUST NOT automatically invalidate otherwise conforming evidence or convert the disclosure result into a trust, legal, moderation, or authorization decision.

## 15. Marketplace privacy warnings

M10 adds deterministic Marketplace-specific warning codes for linkability or sensitive workflow disclosure that OLP core cannot infer from Marketplace semantics alone.

Core warning codes include principal/subject correlation, multiparty and negotiation-graph disclosure, commitment/reference correlation, fulfillment and settlement history, settlement preferences, role bindings, evidence/related-record links, query scope, federation cursors, trust traces, and recipient identifiers.

The reference helper emits these exact codes:

```text
MARKETPLACE_PRINCIPAL_IDENTIFIER_CORRELATION
MARKETPLACE_SUBJECT_REFERENCE_CORRELATION
MARKETPLACE_MULTIPARTY_RELATIONSHIP_DISCLOSURE
MARKETPLACE_NEGOTIATION_GRAPH_DISCLOSURE
MARKETPLACE_COMMITMENT_REFERENCE_CORRELATION
MARKETPLACE_FULFILLMENT_HISTORY_DISCLOSURE
MARKETPLACE_SETTLEMENT_HISTORY_DISCLOSURE
MARKETPLACE_SETTLEMENT_PREFERENCE_DISCLOSURE
MARKETPLACE_QUERY_SCOPE_DISCLOSURE
MARKETPLACE_FEDERATION_CURSOR_DISCLOSURE
MARKETPLACE_TRUST_TRACE_DISCLOSURE
MARKETPLACE_RECIPIENT_IDENTIFIER_CORRELATION
MARKETPLACE_ROLE_BINDING_DISCLOSURE
MARKETPLACE_EVIDENCE_REFERENCE_CORRELATION
MARKETPLACE_RELATED_RECORD_CORRELATION
```

These warnings describe disclosure risk, not protocol invalidity, falsity, trust, or illegality.

## 16. Workflow metadata

Some privacy-sensitive data is not contained in the selected evidence records themselves. The reference profile therefore accepts explicit boolean workflow metadata for query-scope disclosure, federation-cursor disclosure, trust-trace disclosure, and recipient-identifier disclosure.

Unknown workflow metadata keys MUST fail closed in the core profile. A false or absent metadata flag MUST NOT be interpreted as proof that the corresponding information was never disclosed elsewhere.

## 17. Pairwise and contextual identifiers

Marketplace participants MAY use pairwise or context-specific Principal Identifiers and verification methods where compatible with OLP identity semantics.

M10 MUST NOT require two such identifiers to be globally linkable merely because an application suspects they refer to the same actor.

A disclosed same-subject relation or repeated stable identifier may defeat unlinkability and SHOULD be treated as correlation-sensitive evidence.

The reference profile reports `global_identifier_linkability_established = false`.

## 18. Offline and online verification

M10 inherits OLP 0010's privacy tradeoff between self-contained and online verification.

Offline or bundle-first verification can reduce resolver-query leakage but may require additional authority, verification-method, lifecycle, or resource disclosure.

Online verification may reduce payload disclosure while exposing lookup interests, timing, endpoint metadata, and resolver activity.

Neither mode is universally more private. The declared threat model and verification task determine the preferable tradeoff.

## 19. External selective-disclosure systems

Marketplace may use external systems such as SD-JWT or BBS-derived presentations as supporting evidence when permitted by the OLP disclosure request and local policy.

Their native cryptographic verification semantics remain authoritative. Marketplace MUST NOT reconstruct, infer, synthesize, or claim receipt of undisclosed claims.

The surrounding Marketplace/OLP evidence graph may still contain stable identifiers or metadata that defeats an external format's unlinkability properties.

The reference profile therefore reports `external_undisclosed_claims_synthesized = false` and preserves OLP's external-presentation privacy warning behavior.

## 20. Audience and confidentiality boundaries

M10 does not define universal audience encryption, consent, confidentiality, retention, or one-time-use semantics.

A declared recipient or disclosure task is not cryptographic audience binding. Transport/storage encryption and proof-domain/challenge semantics remain separate mechanisms.

The reference profile reports `audience_binding_evaluated = false`.

## 21. Privacy planning versus authority and policy

A disclosure planner answers what evidence is selected for a declared task under explicit planner inputs. It does not decide whether the recipient is authorized to receive that evidence, whether consent exists, whether processing has a lawful basis, whether the content is true, or whether the target is trustworthy.

Those decisions remain separate application, legal, proof, identity/authority, and evaluator dimensions.

The reference profile reports:

```text
authorization_evaluated = false
consent_or_lawful_basis_evaluated = false
trust_evaluated = false
```

## 22. Network behavior

M10 performs no implicit network dereference. Any network resolution used by an application MUST be explicit, policy-controlled, bounded, and observable to the caller.

No-network, bundle-first, cache, relay, batching, timeout, redirect, and SSRF protections remain governed by applicable OLP resolution/privacy/transport profiles and local policy.

The reference profile reports `hidden_network_fallback_permitted = false`.

## 23. Resource bounds

The M10 v1 reference profile applies explicit ceilings to attacker-controlled collections before or during disclosure planning:

```text
roots                         256
inventory items              4096
resource items               4096
required/available capabilities 256
dependencies per item        4096
privacy warnings per item      64
```

Implementations MAY choose lower local limits. A conforming implementation MUST NOT silently claim the reference M10 v1 profile while accepting larger limits without an explicitly different profile.

Limits are part of denial-of-service resistance and do not imply any global maximum size for the Marketplace evidence graph.

## 24. Reference result contract

`plan_marketplace_disclosure()` returns the authoritative OLP disclosure result together with the Marketplace privacy profile URI, task URI, sorted Marketplace warning codes, and explicit boolean boundary flags.

The Marketplace wrapper MUST NOT rewrite OLP-selected evidence, OLP privacy warnings, unresolved dependencies, or OLP disclosure status into a different semantic result.

## 25. Security considerations

A verifier MUST reject any attempt to present a field-deleted or modified Marketplace record under the original Record Identity.

A sender may selectively disclose favorable evidence and withhold unfavorable evidence. M10 does not solve completeness by assumption; closed-domain completeness requires a separate explicit mechanism.

Stable content-addressed identifiers, principals, roles, subjects, commitment references, relationship references, settlement preferences, traces, cursors, manifests, and resolver activity may all create correlation handles.

Privacy warnings are therefore conservative diagnostics. Their presence does not prove harm, and their absence does not prove anonymity.

Implementations MUST bound graph traversal, collections, network access, response sizes, recursion, and processing time according to the active profile and application threat model.

## 26. Conformance vectors

The executable M10 conformance corpus is `conformance/vectors/privacy-selective-disclosure-v1.json`.

The reference generator is `tools/generate_privacy_vectors.py`; the independent replay validator is `tools/validate_privacy_vectors.py`.

The reviewed M10 corpus contains 52 vectors: 26 positive/evaluation cases and 26 negative/adversarial cases. It is pinned to the same OLP source commit used by Milestones 3-9.

## 27. Examples

A discovery service may disclose one matching MarketIntent and omit unrelated sibling Intents. The omission does not prove that no other offers exist.

A negotiation verifier may disclose a proposal and only the source Intent needed for the declared task. It need not export every historical proposal branch.

A fulfillment verifier may disclose the Agreement, one CommitmentRef-targeted performance event, and only required proof/authority evidence. Unrelated fulfillment history may remain withheld.

A settlement verifier may disclose one settlement event and required rail evidence without disclosing unrelated settlement history or every settlement preference.

A trust-evaluation workflow may disclose the exact evidence subset needed for one evaluator method while warning that the query scope or trace itself is sensitive.

## 28. Deferred and out of scope

M10 does not define a universal consent or lawful-basis model, privacy score, anonymity network, retention period, audience-encryption scheme, pairwise-identifier format, zero-knowledge proof system, redactable Marketplace record, mandatory SD-JWT/BBS profile, global completeness mechanism, or jurisdiction-specific privacy compliance regime.

Future profiles MAY standardize additional mechanisms while preserving exact Record Identity, open-world withholding, native external-proof semantics, explicit network behavior, and separation from trust/authorization/legal conclusions.

## 29. Milestone 10 acceptance boundary

Milestone 10 is complete when:

1. OLP 0010 remains authoritative and no parallel Marketplace privacy envelope or universal privacy record is introduced;
2. exact Record Identity is preserved and silent field redaction is rejected;
3. disclosure tasks are explicit and selected evidence is task-scoped rather than globally minimal or complete;
4. withheld evidence remains open-world and never automatically adverse;
5. explicit dependencies are followed while unrelated graph branches remain omittable;
6. Marketplace and OLP privacy warnings are deterministic diagnostics rather than validity/trust/legal judgments;
7. pairwise/contextual identifiers remain compatible without forced global linkability;
8. online/offline, manifest, workflow-metadata, and resolver privacy tradeoffs remain explicit;
9. external selective-disclosure systems retain native semantics and hidden claims are never synthesized;
10. privacy planning remains separate from authorization, consent/lawful basis, proof validity, trust, moderation, and business policy;
11. collection, dependency, warning, network, and processing bounds are explicit;
12. the M10 conformance corpus passes independently and Milestones 3-9 remain green; and
13. documentation, deterministic regeneration, repository audit, and merge acceptance gates pass.
