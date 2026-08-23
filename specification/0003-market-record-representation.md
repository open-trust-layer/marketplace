# Marketplace — Record Representation and Identity

**Status:** Draft v0.1
**Milestone:** 3 — Marketplace Record Representation & Identity
**Filename:** `specification/0003-market-record-representation.md`

---

## 1. Purpose

This specification makes the Marketplace object model from Specification 0002 exact enough for independent implementations to construct, validate, identify, exchange, and test Marketplace records.

It defines stable Marketplace semantic identifiers; exact abstract `content` structures for `MarketIntentV1`, `MarketAgreementV1`, and `MarketEventV1`; reusable embedded structures; cardinality and omission rules; canonical ordering for set-like arrays; exact decimal, quantity, time, location, reference, extension, and critical-extension rules; and executable conformance vectors.

It does **not** define a second Marketplace record envelope, hash, canonical encoder, proof system, relationship graph, lifecycle mechanism, transport format, payment rail, matching algorithm, or legal interpretation layer.

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are interpreted as described by RFC 2119 and RFC 8174 when written in all capitals.

## 3. Dependency baseline

Marketplace Record Representation v1 is built on Open Layer Protocol (OLP). It inherits the OLP `RecordV1` envelope, abstract value model, OLP-CIE-1 canonical identity encoding, OLP-CI-1 Record Identity, detached proofs, `EvidenceRefV1`, evidence relationships, Principal Identifiers, additive lifecycle evidence, `ResourceRefV1`, and OLP identity presentation rules.
The Milestone 3 conformance vectors were generated against OLP reference implementation source commit:

```text
41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c
```

This pin is a draft reproducibility baseline, not a fork. A future Marketplace release MUST bind to a released OLP compatibility target.

## 4. Core identity rule

A first-class Marketplace record is an ordinary OLP `RecordV1`. Marketplace defines semantic type, profile identifiers, and exact Marketplace `content` only.

```text
MarketplaceRecordIdentity(R) := OLPRecordIdentity(R)
```

Marketplace MUST NOT define another digest, canonical encoder, or identity preimage. OLP remains authoritative for canonical identity bytes, SHA-256 Record Identity, canonical `r1_...` presentation, proof binding and verification, evidence references, relationships, and lifecycle evidence.

A Marketplace implementation that derives a different identity for the same OLP Record is non-conforming.

## 5. Semantic namespace

Marketplace v1 uses:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1
```
Core type/profile identifiers are exact strings:

```text
MarketIntentV1
https://open-trust-layer.github.io/marketplace/semantics/v1/record/market-intent

MarketAgreementV1
https://open-trust-layer.github.io/marketplace/semantics/v1/record/market-agreement

MarketEventV1
https://open-trust-layer.github.io/marketplace/semantics/v1/record/market-event

core-v1
https://open-trust-layer.github.io/marketplace/semantics/v1/profile/core-v1

proposal-v1
https://open-trust-layer.github.io/marketplace/semantics/v1/profile/proposal-v1
```

The URI is an identifier; dereferenceability is optional. Implementations MUST NOT trim, case-fold, Unicode-normalize, percent-decode/re-encode, or otherwise rewrite authenticated identifiers.

Marketplace/domain role, action, term, constraint, event, outcome, unit, location, settlement, evidence-profile, and extension identifiers MUST be absolute URIs unless a later specification explicitly defines another collision-resistant namespace.

## 6. OLP envelope requirements
A Marketplace v1 record uses the ordinary OLP envelope:

```text
RecordV1 = {
  envelope_version: 1,
  type: SemanticIdentifier,
  content: MarketplaceContentV1,
  semantic_bindings?: Map,
  profiles?: Array,
  relationships?: Array,
  extensions?: Map
}
```

For Marketplace v1, `type` MUST be one of the three Marketplace record type URIs, and `profiles` MUST contain the Marketplace `core-v1` URI. Every Marketplace/domain profile identifier in `profiles` MUST be an absolute URI. OLP rules for profile uniqueness, envelope extensions, relationships, identity, and omission/default handling remain authoritative.

Detached OLP proofs MUST NOT be inserted into the identity-bearing record merely for convenience.

## 7. Common representation rules

Marketplace content maps use the exact text keys defined here. Unknown direct fields MUST be rejected unless a structure explicitly provides an extension/semantic-map mechanism.

Map member order is not semantic; OLP canonical identity encoding determines it. Arrays are order-sensitive OLP values, so every Marketplace array intended as a set is explicitly marked **set-like**.
A set-like array MUST be non-duplicating and sorted ascending by the complete OLP-CIE-1 encoded bytes of each member. Consumers MUST reject non-canonical set ordering rather than silently reorder authenticated input.

Where this specification says **UTF-8 sorted**, values MUST be unique and sorted by exact UTF-8 bytes.

Optional arrays and optional `SemanticMap`-valued fields SHOULD be omitted when semantically empty. Unless a structure explicitly permits an empty value, a present optional array or `SemanticMap` MUST be non-empty. `TermsV1` is an explicit exception and MAY be empty.

Booleans MUST NOT satisfy integer fields. Floating-point values MUST NOT appear in identity-bearing Marketplace content; exact decimal helpers use OLP integers.

## 8. References

Marketplace reuses OLP references.

A `RecordRef` is exactly an OLP `EvidenceRefV1` whose kind is `RECORD`:

```text
RecordRef := [0, RecordIdentityDigest32]
```

A proof reference MUST NOT be accepted where a `RecordRef` is required. A field described as `EvidenceRef` MAY carry an OLP Record or Proof reference only when that field explicitly permits both.

A `ResourceRef` is exactly OLP `ResourceRefV1`; Marketplace does not redefine its media type, hash, digest, or resource-identifier rules.

Human-facing `r1_...` text is an OLP identity presentation, not the abstract digest-bearing `EvidenceRefV1` value.

## 9. `PartyBindingV1`
```text
PartyBindingV1 = {
  principal: AbsoluteURI,
  role?: AbsoluteURI
}
```

`principal` is REQUIRED and is an opaque exact OLP-style Principal Identifier. `role`, when present, is contextual to the containing record. No other fields are allowed.

A PartyBinding does not prove real-world identity, organizational authority, legal capacity, ownership, or trustworthiness.

## 10. `SubjectBindingV1`

```text
SubjectBindingV1 = {
  uri?: AbsoluteURI,
  record_ref?: RecordRef,
  resource_ref?: ResourceRefV1,
  qualifiers?: SemanticMap
}
```

Exactly one of `uri`, `record_ref`, or `resource_ref` MUST be present. `qualifiers`, when present, maps absolute-URI keys to valid OLP values.

Subject representation does not establish existence, ownership, custody, control, transferability, authority, legality, authenticity, availability, or value.

## 11. `ActionDescriptorV1`
```text
ActionDescriptorV1 = {
  id: AbsoluteURI,
  parameters?: SemanticMap
}
```

`id` is REQUIRED. `parameters`, when present, maps absolute-URI semantic identifiers to OLP values. Marketplace core does not infer legal effect or permission from an action URI.

## 12. `TermsV1`

```text
TermsV1 := Map<AbsoluteURI, OLPValue>
```

A Terms map MAY be empty in universal core. Every key identifies the semantics of its associated value. Domain profiles SHOULD define exact expected structures for term identifiers they introduce.

Terms do not become fair, lawful, feasible, mutually accepted, or enforceable merely because they are syntactically valid.

## 13. `ConstraintV1`

```text
ConstraintV1 = {
  id: AbsoluteURI,
  mode: "mandatory" | "preferred" | "negotiable" | "informational",
  value?: OLPValue
}
```

`id` and `mode` are REQUIRED. Matching or negotiation systems MUST NOT silently reinterpret `mandatory` as `preferred`. Constraint evaluation remains an application result.

## 14. `DecimalV1`
```text
DecimalV1 = {
  coefficient: Integer,
  scale: Integer
}

numeric_value = coefficient x 10^(-scale)
```

`coefficient` MUST be an OLP-valid integer. `scale` MUST be integer `0..18`. If `coefficient == 0`, `scale` MUST equal `0`. If `scale > 0`, `coefficient` MUST NOT be divisible by `10`.

These rules create one core-v1 spelling for a decimal value and prevent identity distinctions caused only by redundant trailing zeros.

```text
123.45 -> {coefficient: 12345, scale: 2}
1      -> {coefficient: 1, scale: 0}
0      -> {coefficient: 0, scale: 0}
```

`{coefficient: 1230, scale: 2}` is non-canonical because `{coefficient: 123, scale: 1}` represents the same decimal.

## 15. `QuantityV1`

```text
QuantityV1 = {
  value: DecimalV1,
  unit: AbsoluteURI
}
```

Marketplace core does not create a universal unit registry. Profiles SHOULD reuse established unit vocabularies where suitable.
## 16. `ValueExpressionV1`

A value expression is an attributed economic expression, not a universal valuation.

Monetary form:

```text
{
  kind: "monetary",
  amount: DecimalV1,
  currency_code?: Text,
  currency_uri?: AbsoluteURI
}
```

Exactly one of `currency_code` or `currency_uri` MUST be present. `currency_code` MUST be exactly three uppercase ASCII letters; profiles using it SHOULD bind it to an appropriate currency-code standard.

Quantity form:

```text
{kind: "quantity", quantity: QuantityV1}
```

Semantic form:

```text
{kind: "semantic", semantic: AbsoluteURI, value: OLPValue}
```

The semantic form permits barter, rights, credits, allocations, or other non-monetary expressions without forcing all exchange into currency semantics.
## 17. `TemporalConditionV1`

```text
TemporalConditionV1 = {
  not_before?: TimestampV1,
  not_after?: TimestampV1
}
```

At least one bound MUST be present. `TimestampV1` uses exactly `YYYY-MM-DDTHH:MM:SSZ` with a valid Gregorian date/time and UTC `Z` suffix. Fractional seconds and numeric UTC offsets are outside core-v1.

If both bounds exist, `not_before` MUST NOT be later than `not_after`. A valid timestamp remains an attributed value, not proof from a trusted global clock.

## 18. `LocationConditionV1`

```text
LocationConditionV1 = {
  scheme: AbsoluteURI,
  value: OLPValue
}
```

Marketplace core remains geospatially neutral. Profiles may bind postal, coordinate, geohash, jurisdiction, orbital, virtual-space, or other location systems.

## 19. `EvidenceRequirementV1`

```text
EvidenceRequirementV1 = {
  profile: AbsoluteURI,
  mode: "required" | "preferred",
  subject?: SubjectBindingV1
}
```

The structure expresses requested evidence semantics; it does not establish evidence sufficiency, authenticity, authority, or trustworthiness.
## 20. `SettlementPreferenceV1`

```text
SettlementPreferenceV1 = {
  method: AbsoluteURI,
  mode: "accepted" | "preferred" | "required" | "excluded",
  parameters?: SemanticMap
}
```

This structure expresses preference/constraint only. It does not make Marketplace a payment processor, bank, ledger, escrow provider, or settlement authority.

## 21. `AcceptanceCriterionV1`

```text
AcceptanceCriterionV1 = {
  criterion: AbsoluteURI,
  mode: "required" | "informational",
  parameters?: SemanticMap
}
```

The presence of a criterion does not prove its satisfaction.

## 22. `ProfileBindingV1`

```text
ProfileBindingV1 = {
  profile: AbsoluteURI,
  parameters?: SemanticMap
}
```

A profile binding conveys intended semantics; implementations must still validate actual conformance.

## 23. `CommitmentV1`
```text
CommitmentV1 = {
  id: LocalId,
  party: PartyBindingV1,
  action: ActionDescriptorV1,
  subjects?: [SubjectBindingV1, ...],
  terms?: TermsV1,
  acceptance_criteria?: [AcceptanceCriterionV1, ...]
}
```

`id`, `party`, and `action` are REQUIRED. `LocalId` MUST match `[A-Za-z][A-Za-z0-9._-]{0,63}` and is scoped to the containing immutable record.

`subjects` and `acceptance_criteria`, when present, are non-empty set-like arrays. A Commitment does not automatically establish a legal obligation.

## 24. `OutcomeV1`

```text
OutcomeV1 = {
  type: AbsoluteURI,
  details?: OLPValue
}
```

An Outcome is an attributable representation of a result. Different participants MAY publish conflicting Outcomes; core does not silently select one as universal truth.

## 25. Content extensions

Each first-class Marketplace record-content map MAY contain:

```text
extensions?: Map<AbsoluteURI, OLPValue>
critical?: [AbsoluteURI, ...]
```
When present, `extensions` and `critical` MUST be non-empty. `critical` MUST be unique and UTF-8 sorted. Every critical URI MUST be present in `extensions`. An implementation that does not understand a critical extension MUST NOT claim full semantic processing.

Unknown non-critical extensions MAY be preserved and ignored according to policy. Content extensions are distinct from OLP envelope extensions; use the narrowest appropriate scope.

## 26. `MarketIntentV1`

A MarketIntent record uses the type URI from Section 5 and this exact content shape:

```text
MarketIntentContentV1 = {
  version: 1,
  issuer: PartyBindingV1,
  subjects: [SubjectBindingV1, ...],
  action: ActionDescriptorV1,
  terms: TermsV1,
  constraints?: [ConstraintV1, ...],
  evidence_requirements?: [EvidenceRequirementV1, ...],
  validity?: TemporalConditionV1,
  settlement_preferences?: [SettlementPreferenceV1, ...],
  profile_bindings?: [ProfileBindingV1, ...],
  response_to?: [RecordRef, ...],
  extensions?: SemanticMap,
  critical?: [AbsoluteURI, ...]
}
```

`version`, `issuer`, `subjects`, `action`, and `terms` are REQUIRED. `version` MUST equal integer `1`; `subjects` MUST be non-empty.

The following are set-like: `subjects`, `constraints`, `evidence_requirements`, `settlement_preferences`, `profile_bindings`, and `response_to`.
Mutable status shortcuts such as `is_active`, `is_withdrawn`, `is_matched`, `is_sold`, `is_completed`, `current_status`, `view_count`, and `ranking_score` are not valid core fields. Later state is additive evidence or derived application state.

## 27. Proposal specialization

A Proposal is a `MarketIntentV1` whose OLP `profiles` contains the exact `proposal-v1` URI from Section 5.

A Proposal MUST contain a non-empty set-like `response_to` array of `RecordRef` values. A MarketIntent containing `response_to` MUST include `proposal-v1`.

Changing Proposal terms creates a different OLP Record Identity. A later Proposal MUST NOT overwrite an earlier Proposal. Proposal compatibility does not create assent.

## 28. `MarketAgreementV1`

```text
MarketAgreementContentV1 = {
  version: 1,
  parties: [PartyBindingV1, ...],
  subjects: [SubjectBindingV1, ...],
  actions: [ActionDescriptorV1, ...],
  terms: TermsV1,
  commitments: [CommitmentV1, ...],
  source_records?: [RecordRef, ...],
  evidence_requirements?: [EvidenceRequirementV1, ...],
  settlement_preferences?: [SettlementPreferenceV1, ...],
  profile_bindings?: [ProfileBindingV1, ...],
  extensions?: SemanticMap,
  critical?: [AbsoluteURI, ...]
}
```
`version`, `parties`, `subjects`, `actions`, `terms`, and `commitments` are REQUIRED. Required arrays MUST be non-empty. Universal core requires at least one party; narrower profiles MAY require more.

These fields are set-like: `parties`, `subjects`, `actions`, `source_records`, `evidence_requirements`, `settlement_preferences`, and `profile_bindings`.

`commitments` MUST be non-empty. Commitment IDs MUST be unique and UTF-8 sorted. Every Commitment `party.principal` MUST appear among `parties[*].principal`.

### 28.1 Agreement record does not self-prove formation

A syntactically valid `MarketAgreementV1` does not prove that all named parties assented. A participant can create a valid record naming another participant without that participant's consent.

Applications MUST evaluate detached OLP proofs, countersignature relationships, authority evidence, profile-specific assent requirements, and local policy before concluding that formation is sufficiently evidenced.

```text
valid MarketAgreement record != sufficient assent evidence
```

Changing identity-bearing Agreement content creates a new OLP Record Identity. Amendments MUST use a new immutable record plus explicit relationship/lifecycle evidence where applicable.

## 29. `MarketEventV1`

```text
MarketEventContentV1 = {
  version: 1,
  issuer: PartyBindingV1,
  event: AbsoluteURI,
  occurred_at?: TimestampV1,
  subjects?: [SubjectBindingV1, ...],
  related_records?: [RecordRef, ...],
  commitment_ids?: [LocalId, ...],
  parties?: [PartyBindingV1, ...],
  outcome?: OutcomeV1,
  evidence?: [EvidenceRef, ...],
  profile_bindings?: [ProfileBindingV1, ...],
  extensions?: SemanticMap,
  critical?: [AbsoluteURI, ...]
}
```

`version`, `issuer`, and `event` are REQUIRED. `version` MUST equal integer `1`.

At least one of `subjects`, `related_records`, or `commitment_ids` MUST be present and non-empty, preventing an unscoped core MarketEvent.

The following are set-like: `subjects`, `related_records`, `parties`, `evidence`, and `profile_bindings`. `commitment_ids` MUST be unique and UTF-8 sorted.

`occurred_at`, when present, is an issuer-attributed time assertion, not proof from a trusted global clock. An embedded Outcome is evidence about a result and does not mutate an Agreement, Commitment, Subject, settlement system, or another participant's outcome claim.

## 30. Canonical ordering summary

The following are OLP-CIE-1 sorted set-like arrays:

```text
MarketIntent: subjects, constraints, evidence_requirements,
              settlement_preferences, profile_bindings, response_to
MarketAgreement: parties, subjects, actions, source_records,
                 evidence_requirements, settlement_preferences, profile_bindings
Commitment: subjects, acceptance_criteria
MarketEvent: subjects, related_records, parties, evidence, profile_bindings
```

The following are UTF-8 sorted and unique:

```text
MarketAgreement commitments by commitment.id
MarketEvent commitment_ids
content critical extension URIs
```

Arrays not declared set-like retain the order semantics defined by their profile.

## 31. Unknown and missing fields

Core Marketplace structures use closed field sets. A missing required field is malformed. An unknown direct field is malformed unless the containing structure explicitly defines an extension or semantic-map mechanism that carries it under an absolute URI.

This rule prevents misspellings and accidental schema drift from being authenticated as if they carried agreed semantics.

## 32. Relationship semantics remain OLP evidence

Marketplace does not encode evidentiary graph relationships as mutable platform metadata. Relationships such as Proposal response/supersession, Agreement derivation/amendment, Event-to-Agreement association, dispute, and correction SHOULD use OLP relationship records when the relationship itself needs portable provenance, proof, dispute, or lifecycle handling.

Identity-bearing direct references such as `response_to`, `source_records`, and `related_records` do not replace separately attributable relationship evidence when the relationship itself matters as evidence.

## 33. Lifecycle remains additive

Marketplace records are immutable OLP records. Withdrawal, suspension, resumption, retirement, revocation, deprecation, supersession, correction, dispute, compromise, and related lifecycle changes MUST NOT mutate an existing Marketplace record.

They use additive OLP lifecycle or relationship evidence. `current_status` is a derived application conclusion, not a mutable historical field.

## 34. Proofs remain detached

OLP proofs remain detached first-class artifacts. A Marketplace record MUST NOT include an identity-bearing `signature`, `proof`, or `proofs` field merely to authenticate itself.

Proof validity remains distinct from truth, identity, authority, ownership, legal sufficiency, agreement formation, fulfillment, acceptance, and policy permission.

## 35. Price and value remain contextual

`DecimalV1`, `QuantityV1`, and `ValueExpressionV1` provide exact representation only.

```text
quoted amount != fair value
price          != value
exchange ratio != universal valuation
```

Applications MAY publish valuation claims as attributable evidence under separate semantic profiles.

## 36. Subject-scale and participant-type neutrality

The same SubjectBinding can identify a software issue, physical item, service specification, company, bridge, energy interval, satellite, asteroid, planet, or galaxy. Representation does not imply that every action concerning every subject is possible, lawful, transferable, ownable, or meaningful.

Principal Identifiers similarly do not encode Marketplace privilege by actor type. Humans, organizations, software agents, services, devices, and other externally identified principals use the same PartyBinding shape.

## 37. Conformance vectors

Milestone 3 defines executable vectors at:

```text
conformance/vectors/record-representation-v1.json
```

The committed set covers positive MarketIntent, Proposal, MarketAgreement, and MarketEvent records; exact decimal/quantity/value/time/location structures; and negative mutable-state, proposal, ordering, commitment-party, event-context/time, critical-extension, reference-kind, decimal, subject, currency, and settlement cases.

Positive record vectors include:

```text
expected_record_identity
expected_record_identity_hex
expected_identity_preimage_hex
```

These values are produced by the OLP reference implementation, not by a Marketplace hash implementation.

The vector JSON uses OLP's implementation-neutral conformance projection so byte strings can be represented in JSON. It is **not** a normative Marketplace wire format.

## 38. Non-normative reference tooling

Milestone 3 provides:

```text
tools/marketplace_record_v1.py
tools/generate_record_vectors.py
tools/validate_record_vectors.py
```

The tooling imports OLP for `RecordV1` validation, OLP-CIE-1 member ordering, `EvidenceRefV1`, `ResourceRefV1`, Record Identity, identity preimage bytes, and textual identity presentation. Marketplace tooling SHOULD call OLP rather than reimplement OLP identity rules.

## 39. Security considerations

Marketplace input is attacker-controlled. Implementations MUST enforce OLP resource bounds and SHOULD impose finite Marketplace limits for arrays, maps, extensions, text, referenced resources, resolution, and network activity.

Validation MUST occur before protected side effects. A conforming record does not imply that an application should execute its Action.

Applications SHOULD separately evaluate authorization, policy, moderation, jurisdiction, fraud/abuse risk, resource cost, network safety, settlement risk, and identity/authority evidence.

A semantic URI MUST NOT be treated as an instruction to fetch or execute remote code merely because it is a URI.

## 40. Privacy considerations

Identity-bearing Marketplace records may become durable and correlatable. Implementations SHOULD minimize unnecessary principal identifiers, public subject identifiers, precise timestamps, locations, external links, cross-market correlation identifiers, and private commercial terms.

Public discoverability is not required. A Marketplace record can be exchanged privately while retaining the same OLP Record Identity.

## 41. Intentionally deferred

Milestone 3 does not define mandatory JSON/CBOR transport, Marketplace HTTP APIs, discovery/federation, global action/role/term/category registries, matching, negotiation state machines, universal proof-purpose or countersignature thresholds, ownership/title rules, legal-contract rules, settlement execution, escrow, dispute-resolution procedure, moderation/tax/compliance policy, universal reputation, universal ranking, or universal trust.

Those belong to later specifications or applications.

## 42. Foundational invariants

```text
Marketplace Record Identity             = OLP Record Identity
Marketplace canonical identity encoding = OLP-CIE-1
Marketplace record envelope             = OLP RecordV1
Marketplace proofs                      = detached OLP proofs
Marketplace evidence references         = OLP EvidenceRefV1
Marketplace resource references         = OLP ResourceRefV1
Marketplace lifecycle                   = additive OLP evidence
```

The representation also preserves:

```text
subject representation                  != ownership
principal identifier                    != identity proof
identity                                != authority
action identifier                       != permission
intent                                  != agreement
proposal compatibility                  != assent
valid MarketAgreement record            != sufficient formation proof
agreement                               != settlement
settlement                              != fulfillment
event assertion                         != universal outcome
price                                   != value
valid proof                             != truth
protocol expressibility                 != permission
```

## 43. Milestone 3 acceptance boundary

Milestone 3 is complete when:

- all three first-class Marketplace record profiles have exact v1 abstract content;
- reusable core structures have deterministic fields, cardinalities, and ordering rules;
- semantic identifiers and extension rules are stable for Draft v0.1;
- Marketplace identity is demonstrably inherited from OLP rather than reimplemented;
- positive and negative vectors are committed;
- positive Record Identities reproduce under the pinned OLP reference implementation;
- documentation and executable validation are green; and
- the acceptance pull request is merged to `main`.

The next protocol milestone should build lifecycle and negotiation semantics over these exact immutable records rather than casually changing their identity model.
