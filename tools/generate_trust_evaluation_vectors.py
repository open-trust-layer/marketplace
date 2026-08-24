from __future__ import annotations

import json
import subprocess
from pathlib import Path

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text
from olp.transport import project_abstract

from marketplace_record_v1 import (
    BASE, CORE_PROFILE, TYPE_AGREEMENT, TYPE_EVENT, TYPE_INTENT,
    validate_market_record,
)
from marketplace_trust_evaluation_v1 import (
    METHOD_CORE, EvidenceCandidate, evaluate_trust, query_fingerprint,
    select_evidence, validate_evidence_query,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "trust-evaluation-v1.json"


def olp_commit() -> str:
    import olp
    repo = Path(olp.__file__).resolve().parents[2]
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def sort_set(values):
    return tuple(sorted(tuple(values), key=olp_encode))


def market_record(record_type: str, content: dict, profiles=(CORE_PROFILE,)) -> RecordV1:
    record = RecordV1(envelope_version=1, type=record_type, content=content, profiles=profiles)
    validate_market_record(record)
    return record


def record_mapping(record: RecordV1) -> dict:
    value = {"envelope_version": record.envelope_version, "type": record.type, "content": record.content}
    if record.semantic_bindings:
        value["semantic_bindings"] = record.semantic_bindings
    if record.profiles:
        value["profiles"] = record.profiles
    if record.relationships:
        value["relationships"] = record.relationships
    if record.extensions:
        value["extensions"] = record.extensions
    return value


def projected_record(record: RecordV1):
    return project_abstract(record_mapping(record))


def jsonable(value):
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def candidate(record: RecordV1, source: str) -> EvidenceCandidate:
    return EvidenceCandidate(record=record, source=source)


def candidate_wire(record: RecordV1, source: str) -> dict:
    return {"record": projected_record(record), "source": source}


def observation(
    record: RecordV1,
    *,
    domain: str = "SUPPORTS",
    proof: str = "VERIFIED",
    identity: str = "ACCEPTED",
    authority: str = "ACCEPTED",
    lifecycle: str = "ACCEPTABLE",
    source_accepted: bool = True,
    critical_understood: bool = True,
    disputed: bool = False,
) -> dict:
    return {
        "record_id": record_identity_text(record),
        "proof_status": proof,
        "identity_status": identity,
        "authority_status": authority,
        "lifecycle_status": lifecycle,
        "domain_status": domain,
        "source_accepted": source_accepted,
        "critical_understood": critical_understood,
        "disputed": disputed,
    }


def build() -> dict:
    alice = {"principal": "did:example:alice", "role": "https://example.test/roles/requester"}
    bob = {"principal": "did:example:bob", "role": "https://example.test/roles/provider"}
    subject = {"uri": "urn:example:trust:42"}
    action = {"id": "https://example.test/actions/provide-service"}
    intent = market_record(TYPE_INTENT, {
        "version": 1, "issuer": alice, "subjects": (subject,), "action": action, "terms": {},
    })
    agreement = market_record(TYPE_AGREEMENT, {
        "version": 1, "parties": sort_set((alice, bob)), "subjects": (subject,),
        "actions": (action,), "terms": {},
        "commitments": ({"id": "c1", "party": bob, "action": action, "subjects": (subject,)},),
    })
    positive_event = market_record(TYPE_EVENT, {
        "version": 1, "issuer": bob, "event": f"{BASE}/event/trust-positive-example",
        "subjects": (subject,),
    })
    negative_event = market_record(TYPE_EVENT, {
        "version": 1,
        "issuer": alice,
        "event": f"{BASE}/event/trust-negative-example",
        "subjects": (subject,),
    })
    extra_profile = "https://example.test/profiles/trust-extra"
    profiled_event = market_record(
        TYPE_EVENT,
        {
            "version": 1,
            "issuer": bob,
            "event": f"{BASE}/event/profiled",
            "subjects": (subject,),
        },
        profiles=sort_set((CORE_PROFILE, extra_profile)),
    )
    source_a = "https://peer-a.example/evidence"
    source_b = "https://peer-b.example/evidence"
    purpose = "https://example.test/purpose/select-provider"
    context_key = "https://example.test/context/risk-class"
    query = {
        "version": 1,
        "method": METHOD_CORE,
        "purpose": purpose,
        "target": {"kind": "principal", "value": "did:example:bob"},
        "max_records": 32,
    }
    query_all = dict(query)
    query_all["record_types"] = tuple(sorted((TYPE_AGREEMENT, TYPE_EVENT, TYPE_INTENT)))
    candidates_all = (
        candidate(intent, source_a),
        candidate(agreement, source_a),
        candidate(positive_event, source_a),
        candidate(negative_event, source_b),
    )
    cases: list[dict] = []
    negative_cases: list[dict] = []

    def add(case_id: str, kind: str, payload: dict, expected) -> None:
        cases.append({"id": case_id, "kind": kind, **payload, "expected": jsonable(expected)})

    def negative(case_id: str, kind: str, payload: dict, code: str) -> None:
        negative_cases.append({"id": case_id, "kind": kind, **payload, "expected_error": code})
    add("query-principal-target-valid", "query", {"query": query}, {
        "query": validate_evidence_query(query), "fingerprint": query_fingerprint(query),
    })
    query_record = dict(query)
    query_record["target"] = {"kind": "record", "value": record_identity_text(agreement)}
    add("query-record-target-valid", "query", {"query": query_record}, {
        "query": validate_evidence_query(query_record), "fingerprint": query_fingerprint(query_record),
    })
    query_subject = dict(query)
    query_subject["target"] = {"kind": "subject-uri", "value": subject["uri"]}
    add("query-subject-target-valid", "query", {"query": query_subject}, {
        "query": validate_evidence_query(query_subject), "fingerprint": query_fingerprint(query_subject),
    })
    query_context = dict(query)
    query_context["context"] = {context_key: "medium"}
    add("query-context-bound", "query", {"query": query_context}, {
        "query": validate_evidence_query(query_context), "fingerprint": query_fingerprint(query_context),
    })
    query_sources = dict(query_all)
    query_sources["sources_any"] = (source_a,)
    add("query-source-scope-valid", "query", {"query": query_sources}, {
        "query": validate_evidence_query(query_sources), "fingerprint": query_fingerprint(query_sources),
    })
    selection_all = select_evidence(candidates_all, query_all)
    add("selection-all-core-records", "selection", {
        "query": query_all,
        "candidates": [candidate_wire(item.record, item.source) for item in candidates_all],
    }, selection_all)
    selection_source = select_evidence(candidates_all, query_sources)
    add("selection-source-filter-is-explicit", "selection", {
        "query": query_sources,
        "candidates": [candidate_wire(item.record, item.source) for item in candidates_all],
    }, selection_source)
    duplicate_candidates = (candidate(positive_event, source_a), candidate(positive_event, source_a))
    add("selection-exact-replay-deduplicated", "selection", {
        "query": query_all,
        "candidates": [candidate_wire(item.record, item.source) for item in duplicate_candidates],
    }, select_evidence(duplicate_candidates, query_all))
    multi_source = (candidate(positive_event, source_a), candidate(positive_event, source_b))
    add("selection-preserves-multiple-source-provenance", "selection", {
        "query": query_all,
        "candidates": [candidate_wire(item.record, item.source) for item in multi_source],
    }, select_evidence(multi_source, query_all))
    query_profile = dict(query_all)
    query_profile["profiles_all"] = (extra_profile,)
    profile_candidates = (candidate(positive_event, source_a), candidate(profiled_event, source_a))
    add("selection-profile-filter", "selection", {
        "query": query_profile,
        "candidates": [candidate_wire(item.record, item.source) for item in profile_candidates],
    }, select_evidence(profile_candidates, query_profile))

    single = (candidate(positive_event, source_a),)
    support_obs = (observation(positive_event),)
    add("evaluation-support-sufficient-under-method", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)],
        "observations": list(support_obs),
    }, evaluate_trust(single, support_obs, query_all))
    oppose_obs = (observation(negative_event, domain="OPPOSES"),)
    add("evaluation-opposition-insufficient-under-method", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(negative_event, source_b)],
        "observations": list(oppose_obs),
    }, evaluate_trust((candidate(negative_event, source_b),), oppose_obs, query_all))
    conflict_candidates = (candidate(positive_event, source_a), candidate(negative_event, source_b))
    conflict_obs = (observation(positive_event), observation(negative_event, domain="OPPOSES"))
    add("evaluation-conflict-preserved", "evaluation", {
        "query": query_all,
        "candidates": [candidate_wire(item.record, item.source) for item in conflict_candidates],
        "observations": list(conflict_obs),
    }, evaluate_trust(conflict_candidates, conflict_obs, query_all))
    disputed_obs = (observation(positive_event, disputed=True),)
    add("evaluation-disputed-evidence-preserved", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)],
        "observations": list(disputed_obs),
    }, evaluate_trust(single, disputed_obs, query_all))
    unknown_proof = (observation(positive_event, proof="UNKNOWN"),)
    add("evaluation-unknown-proof-indeterminate", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)],
        "observations": list(unknown_proof),
    }, evaluate_trust(single, unknown_proof, query_all))
    failed_proof = (observation(positive_event, proof="FAILED"),)
    add("evaluation-failed-proof-not-positive", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)],
        "observations": list(failed_proof),
    }, evaluate_trust(single, failed_proof, query_all))
    neutral_obs = (observation(positive_event, domain="NEUTRAL"),)
    add("evaluation-neutral-evidence-is-not-positive", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)],
        "observations": list(neutral_obs),
    }, evaluate_trust(single, neutral_obs, query_all))
    source_rejected = (observation(positive_event, source_accepted=False),)
    add("evaluation-source-policy-does-not-become-trust", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)],
        "observations": list(source_rejected),
    }, evaluate_trust(single, source_rejected, query_all))
    critical_unknown = (observation(positive_event, critical_understood=False),)
    add("evaluation-unknown-critical-semantics-indeterminate", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)],
        "observations": list(critical_unknown),
    }, evaluate_trust(single, critical_unknown, query_all))
    authority_unknown = (observation(positive_event, authority="UNKNOWN"),)
    add("evaluation-authority-unknown-indeterminate", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)],
        "observations": list(authority_unknown),
    }, evaluate_trust(single, authority_unknown, query_all))
    lifecycle_adverse = (observation(positive_event, lifecycle="ADVERSE"),)
    add("evaluation-adverse-lifecycle-excluded", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)],
        "observations": list(lifecycle_adverse),
    }, evaluate_trust(single, lifecycle_adverse, query_all))
    add("evaluation-empty-open-world-indeterminate", "evaluation", {
        "query": query_all, "candidates": [], "observations": [],
    }, evaluate_trust((), (), query_all))

    negative("query-boolean-version", "query", {"query": {**query, "version": True}}, "INVALID_EVIDENCE_QUERY")
    negative("query-future-version", "query", {"query": {**query, "version": 2}}, "INVALID_EVIDENCE_QUERY")
    negative("query-non-uri-method", "query", {"query": {**query, "method": "core"}}, "INVALID_URI")
    negative("query-non-uri-purpose", "query", {"query": {**query, "purpose": "trust"}}, "INVALID_URI")
    negative("query-max-records-zero", "query", {"query": {**query, "max_records": 0}}, "INVALID_RESOURCE_LIMIT")
    negative("query-max-records-ceiling", "query", {"query": {**query, "max_records": 4097}}, "INVALID_RESOURCE_LIMIT")
    negative("query-max-records-boolean", "query", {"query": {**query, "max_records": True}}, "INVALID_RESOURCE_LIMIT")
    negative("query-extra-field", "query", {"query": {**query, "score": 0.9}}, "INVALID_EVIDENCE_QUERY")
    negative("query-invalid-target-kind", "query", {"query": {**query, "target": {"kind": "user", "value": "did:example:bob"}}}, "INVALID_EVALUATION_TARGET")
    negative("query-invalid-record-target", "query", {"query": {**query, "target": {"kind": "record", "value": "r1_bad"}}}, "INVALID_RECORD_ID")
    bad_types = dict(query)
    bad_types["record_types"] = ("https://example.test/record/other",)
    negative("query-unsupported-record-type", "query", {"query": bad_types}, "UNSUPPORTED_RECORD_TYPE")
    bad_sources = dict(query)
    bad_sources["sources_any"] = (source_b, source_a)
    negative("query-unsorted-source-set", "query", {"query": bad_sources}, "NONCANONICAL_SET")
    bad_context = dict(query)
    bad_context["context"] = {"not-a-uri": "x"}
    negative("query-invalid-context-key", "query", {"query": bad_context}, "INVALID_URI")

    unsupported_method = dict(query_all)
    unsupported_method["method"] = "https://example.test/trust/method/other"
    negative("evaluation-unsupported-method", "evaluation", {
        "query": unsupported_method, "candidates": [candidate_wire(positive_event, source_a)],
        "observations": list(support_obs),
    }, "UNSUPPORTED_EVALUATION_METHOD")
    negative("evaluation-missing-observation", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)], "observations": [],
    }, "INCOMPLETE_EVIDENCE_OBSERVATIONS")
    negative("evaluation-observation-outside-selection", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)],
        "observations": [observation(negative_event, domain="OPPOSES")],
    }, "OBSERVATION_OUTSIDE_SELECTED_EVIDENCE")
    negative("evaluation-duplicate-observation", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)],
        "observations": [observation(positive_event), observation(positive_event)],
    }, "DUPLICATE_EVIDENCE_OBSERVATION")
    bad_obs = observation(positive_event)
    bad_obs["proof_status"] = "TRUSTED"
    negative("observation-invalid-proof-status", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)], "observations": [bad_obs],
    }, "INVALID_OBSERVATION_STATUS")
    bad_obs_bool = observation(positive_event)
    bad_obs_bool["source_accepted"] = 1
    negative("observation-inexact-boolean", "evaluation", {
        "query": query_all, "candidates": [candidate_wire(positive_event, source_a)], "observations": [bad_obs_bool],
    }, "INVALID_EVIDENCE_OBSERVATION")

    reordered_candidates = tuple(reversed(conflict_candidates))
    reordered_obs = tuple(reversed(conflict_obs))
    add("evaluation-order-independent", "evaluation", {
        "query": query_all,
        "candidates": [candidate_wire(item.record, item.source) for item in reordered_candidates],
        "observations": list(reordered_obs),
    }, evaluate_trust(reordered_candidates, reordered_obs, query_all))
    replay_eval_candidates = (candidate(positive_event, source_a), candidate(positive_event, source_a))
    add("evaluation-transport-replay-does-not-change-semantic-input", "evaluation", {
        "query": query_all,
        "candidates": [candidate_wire(item.record, item.source) for item in replay_eval_candidates],
        "observations": list(support_obs),
    }, evaluate_trust(replay_eval_candidates, support_obs, query_all))
    multi_source_eval = (candidate(positive_event, source_a), candidate(positive_event, source_b))
    add("evaluation-multi-source-provenance-bound", "evaluation", {
        "query": query_all,
        "candidates": [candidate_wire(item.record, item.source) for item in multi_source_eval],
        "observations": list(support_obs),
    }, evaluate_trust(multi_source_eval, support_obs, query_all))
    purpose_query = dict(query_all)
    purpose_query["purpose"] = "https://example.test/purpose/credit-risk"
    add("query-purpose-changes-fingerprint", "query", {"query": purpose_query}, {
        "query": validate_evidence_query(purpose_query), "fingerprint": query_fingerprint(purpose_query),
    })
    context_query = dict(query_all)
    context_query["context"] = {context_key: "high"}
    add("query-context-changes-fingerprint", "query", {"query": context_query}, {
        "query": validate_evidence_query(context_query), "fingerprint": query_fingerprint(context_query),
    })
    negative("selection-resource-limit", "selection", {
        "query": {**query_all, "max_records": 1},
        "candidates": [candidate_wire(positive_event, source_a), candidate_wire(negative_event, source_b)],
    }, "RESOURCE_LIMIT_EXCEEDED")
    negative("selection-invalid-source-uri", "selection", {
        "query": query_all,
        "candidates": [candidate_wire(positive_event, "not-a-uri")],
    }, "INVALID_URI")
    empty_types = dict(query)
    empty_types["record_types"] = ()
    negative("query-empty-record-types", "query", {"query": empty_types}, "EMPTY_SET")
    duplicate_profiles = dict(query)
    duplicate_profiles["profiles_all"] = (CORE_PROFILE, CORE_PROFILE)
    negative("query-duplicate-profile-set", "query", {"query": duplicate_profiles}, "NONCANONICAL_SET")
    duplicate_sources = dict(query)
    duplicate_sources["sources_any"] = (source_a, source_a)
    negative("query-duplicate-source-set", "query", {"query": duplicate_sources}, "NONCANONICAL_SET")
    for field, value in (
        ("identity_status", "TRUSTED"), ("authority_status", "TRUSTED"),
        ("lifecycle_status", "TRUSTED"), ("domain_status", "TRUSTED"),
    ):
        obs = observation(positive_event)
        obs[field] = value
        negative(f"observation-invalid-{field}", "evaluation", {
            "query": query_all, "candidates": [candidate_wire(positive_event, source_a)],
            "observations": [obs],
        }, "INVALID_OBSERVATION_STATUS")
    too_much_context = dict(query)
    too_much_context["context"] = {
        f"https://example.test/context/{i:03d}": i for i in range(129)
    }
    negative("query-context-resource-limit", "query", {"query": too_much_context}, "INVALID_EVALUATION_CONTEXT")
    return {
        "format": "marketplace-trust-evaluation-v1-conformance-vectors",
        "olp_reference_source_commit": olp_commit(),
        "cases": cases,
        "negative_cases": negative_cases,
        "identities": {
            "intent": record_identity_text(intent), "agreement": record_identity_text(agreement),
            "positive_event": record_identity_text(positive_event), "negative_event": record_identity_text(negative_event),
        },
    }


def main() -> int:
    data = build()
    OUT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    print(f"positive/evaluation cases: {len(data['cases'])}")
    print(f"negative cases: {len(data['negative_cases'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
