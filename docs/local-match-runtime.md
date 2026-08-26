# Marketplace Local Match Evaluation Runtime

**Status:** Milestone 19 — in development
**Scope:** exact local record lookup plus method-relative M5 match evaluation

Milestone 19 composes the local reference runtime with the existing Milestone 5 `evaluate_match` semantics. It does not define a new matching method and does not turn a method result into agreement, ranking, recommendation, authorization, or protocol truth.

## Boundary

```text
match result                  != protocol truth
compatibility under method    != agreement
incompatibility under method  != universal prohibition
missing local evidence        != negative evidence
local record lookup           != global resolution
method result                 != ranking / recommendation
runtime evaluation            != authorization
```

Milestone 5 remains authoritative for match input interpretation, mandatory/preferred constraint handling, critical-semantics treatment, evidence-completeness behavior, and the final method-relative conclusion.

## Runtime composition

```text
left Record Identity ----+
                         |
right Record Identity ---+--> LocalMatchService
                                  |
                                  +--> exact local get(left)
                                  +--> exact local get(right)
                                  |
                                  +--> existing M5 evaluate_match(...)
                                             |
                                             v
                                   method-relative result
```

The reference service depends on two narrow injected capabilities:

- `ExactRecordSource.get(record_id)`;
- `MatchEvaluator(...)`.

`InMemoryEphemeralRecordRepository` already satisfies the exact local source contract. `tools/marketplace_matching_v1.py::evaluate_match` supplies the reference semantic evaluator.

## Exact lookup behavior

The runtime accepts only non-empty text identities and performs exact-key lookup. It does not perform:

- prefix or fuzzy lookup;
- latest-version selection;
- search fallback;
- remote/federated resolution;
- alternate-source discovery.

A missing record produces `LOCAL_RECORD_NOT_FOUND` with the missing side. This is a local availability condition only and is not negative marketplace evidence.

If the same exact identity is supplied for both sides, the runtime performs one local read and reuses the resolved record for both evaluator arguments. The runtime does not add a semantic prohibition on self-comparison that M5 itself does not define.

## Retention behavior

Successful local `get()` operations are active use and retain M17/M18 behavior: the referenced content's `EPHEMERAL` post-use deadline is refreshed, with a maximum of **10 seconds**.

Only records that are actually looked up are refreshed. Unrelated repository entries are untouched. If the left record is found but the right record is absent, the successful left lookup has still occurred and its deadline is refreshed; the service then fails explicitly for the missing right side without attempting any fallback.

No match-result cache or second retained copy is introduced.

## Semantic delegation

`LocalMatchService` forwards these inputs unchanged to the injected evaluator:

- `method`;
- `base_status`;
- `observations`;
- `evidence_completeness`;
- `understood_critical`.

The runtime does not duplicate M5 validation or inspect/modify the evaluator's conclusion. It only requires that the evaluator return a mapping.

For the existing M5 reference evaluator:

- `COMPATIBLE_UNDER_METHOD` still returns `protocol_truth = false` and `creates_agreement = false`;
- `INCOMPATIBLE_UNDER_METHOD` remains method-relative;
- unknown/unsupported critical semantics and incomplete required inputs can remain `INDETERMINATE`;
- different methods may legitimately disagree.

## Safety and resource properties

M19 introduces no:

- network access or remote fallback;
- filesystem/database persistence;
- new dependency;
- ranking/recommendation engine;
- agreement formation or negotiation mutation;
- credential or secret handling;
- deployment capability;
- settlement, fulfillment, remedy, or other protected side effect.

The service performs two exact local reads at most, or one when both identities are the same. Existing repository capacity and per-record retention bounds remain unchanged.

## Acceptance

M19 tests must demonstrate:

- invalid local identity input fails before source/evaluator use;
- missing left and missing right records are explicit local-not-found outcomes;
- exact successful reads refresh only referenced EPHEMERAL records;
- same-identity input performs one lookup;
- actual M5 compatible output remains non-truth and non-agreement;
- actual M5 incompatible output remains method-relative;
- actual M5 unknown critical semantics remain indeterminate;
- evaluator mappings are returned without reinterpretation;
- invalid evaluator result types fail explicitly;
- all existing semantic vectors and deterministic generator replay remain unchanged and green.

M19 remains a local read-only runtime capability. Network federation, durable persistence, ranking/recommendation, and higher-level automatic coordination remain separate future milestones with their own authority, retention, and safety analysis.
