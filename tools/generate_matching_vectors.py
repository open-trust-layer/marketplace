"""Generate Marketplace matching and discovery v1 conformance vectors."""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text
from olp.evidence import record_ref
from olp.transport import project_abstract

from marketplace_record_v1 import BASE, CORE_PROFILE, TYPE_INTENT, validate_market_record
from marketplace_matching_v1 import (
    DEFAULT_MATCH_METHOD,
    bind_cursor,
    evaluate_discovery,
    evaluate_match,
    merge_federated_views,
    validate_cursor_binding,
    validate_ranked_view,
    verify_index_entry,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "matching-discovery-v1.json"


def olp_commit() -> str:
    import olp

    repo = Path(olp.__file__).resolve().parents[2]
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def sort_set(values):
    return tuple(sorted(tuple(values), key=olp_encode))


def market_intent(content: dict, profiles: tuple[str, ...] = (CORE_PROFILE,)) -> RecordV1:
    record = RecordV1(envelope_version=1, type=TYPE_INTENT, content=content, profiles=profiles)
    validate_market_record(record)
    return record


def record_mapping(record: RecordV1) -> dict:
    value = {"envelope_version": record.envelope_version, "type": record.type, "content": record.content}
    if record.profiles:
        value["profiles"] = record.profiles
    return value


def projected_record(record: RecordV1):
    return project_abstract(record_mapping(record))


def projected_ref(record: RecordV1):
    return project_abstract(record_ref(record).to_value())


def expected_subset(value: dict, *keys: str) -> dict:
    return {key: value[key] for key in keys}


def build() -> dict:
    alice = {"principal": "did:example:alice", "role": "https://example.test/roles/requester"}
    bob = {"principal": "did:example:bob", "role": "https://example.test/roles/provider"}
    carol = {"principal": "did:example:carol", "role": "https://example.test/roles/provider"}
    bug42 = {"uri": "urn:example:software-issue:42"}
    bug43 = {"uri": "urn:example:software-issue:43"}
    parcel = {"uri": "urn:example:parcel:9"}
    fix = {"id": "https://example.test/actions/fix"}
    deliver = {"id": "https://example.test/actions/deliver"}
    mandatory_license = {
        "id": "https://example.test/constraints/license",
        "mode": "mandatory",
        "value": "urn:example:license:eu",
    }
    preferred_speed = {
        "id": "https://example.test/constraints/speed",
        "mode": "preferred",
        "value": "fast",
    }
    request = market_intent(
        {
            "version": 1,
            "issuer": alice,
            "subjects": (bug42,),
            "action": fix,
            "terms": {},
            "constraints": sort_set((mandatory_license, preferred_speed)),
        }
    )
    offer_bob = market_intent(
        {"version": 1, "issuer": bob, "subjects": (bug42,), "action": fix, "terms": {}}
    )
    critical_semantic = "https://example.test/extensions/matching-context"
    critical_request = market_intent(
        {
            **dict(request.content),
            "extensions": {critical_semantic: "required-for-matching"},
            "critical": (critical_semantic,),
        }
    )
    offer_carol = market_intent(
        {"version": 1, "issuer": carol, "subjects": (bug43,), "action": fix, "terms": {}}
    )
    delivery = market_intent(
        {"version": 1, "issuer": bob, "subjects": (parcel,), "action": deliver, "terms": {}}
    )
    malformed = RecordV1(
        envelope_version=1,
        type=TYPE_INTENT,
        content={"version": 1, "issuer": alice, "subjects": (bug42,), "terms": {}},
        profiles=(CORE_PROFILE,),
    )

    all_records = (request, offer_bob, offer_carol, delivery, malformed)
    query_fix = {"version": 1, "action_ids_any": (fix["id"],)}
    query_bug42 = {"version": 1, "subject_uris_any": (bug42["uri"],)}
    query_bob = {"version": 1, "issuer_principals_any": (bob["principal"],)}
    source_a = "https://index-a.example.test/discovery"
    source_b = "https://index-b.example.test/discovery"
    view_fix = evaluate_discovery(
        all_records,
        query_fix,
        source=source_a,
        completeness="COMPLETE_FOR_DECLARED_SOURCE",
        freshness="FRESH",
    )
    view_bug42_a = evaluate_discovery(
        (request, offer_bob),
        query_bug42,
        source=source_a,
        completeness="COMPLETE_FOR_DECLARED_SOURCE",
        freshness="FRESH",
    )
    view_bug42_b = evaluate_discovery(
        (offer_bob,),
        query_bug42,
        source=source_b,
        completeness="PARTIAL_SOURCE",
        freshness="UNKNOWN",
    )
    query_none = {"version": 1, "issuer_principals_any": ("did:example:nobody",)}
    view_none = evaluate_discovery(
        (request, offer_bob),
        query_none,
        source=source_a,
        completeness="PARTIAL_SOURCE",
        freshness="UNKNOWN",
    )
    federated = merge_federated_views((view_bug42_a, view_bug42_b))

    index_entry = {
        "record_ref": record_ref(offer_bob).to_value(),
        "issuer": bob["principal"],
        "action": fix["id"],
        "profiles": offer_bob.profiles,
    }
    index_verified = verify_index_entry(index_entry, offer_bob)
    obs_satisfied = [
        {"side": "left", "constraint": mandatory_license, "status": "SATISFIED"},
        {"side": "left", "constraint": preferred_speed, "status": "UNSATISFIED"},
    ]
    obs_unsatisfied = [
        {"side": "left", "constraint": mandatory_license, "status": "UNSATISFIED"},
        {"side": "left", "constraint": preferred_speed, "status": "SATISFIED"},
    ]
    obs_unknown = [
        {"side": "left", "constraint": mandatory_license, "status": "UNSUPPORTED"},
    ]
    match_ok = evaluate_match(
        request,
        offer_bob,
        method=DEFAULT_MATCH_METHOD,
        base_status="SATISFIED",
        observations=obs_satisfied,
        evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
    )
    match_critical_unknown = evaluate_match(
        critical_request,
        offer_bob,
        method=DEFAULT_MATCH_METHOD,
        base_status="SATISFIED",
        observations=obs_satisfied,
        evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
    )
    match_critical_understood = evaluate_match(
        critical_request,
        offer_bob,
        method=DEFAULT_MATCH_METHOD,
        base_status="SATISFIED",
        observations=obs_satisfied,
        evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
        understood_critical=(critical_semantic,),
    )
    match_no = evaluate_match(
        request,
        offer_bob,
        method=DEFAULT_MATCH_METHOD,
        base_status="SATISFIED",
        observations=obs_unsatisfied,
        evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
    )
    match_unknown = evaluate_match(
        request,
        offer_bob,
        method=DEFAULT_MATCH_METHOD,
        base_status="SATISFIED",
        observations=obs_unknown,
        evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
    )
    match_missing = evaluate_match(
        request,
        offer_bob,
        method=DEFAULT_MATCH_METHOD,
        base_status="SATISFIED",
        observations=(),
        evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
    )
    match_incomplete = evaluate_match(
        request,
        offer_bob,
        method=DEFAULT_MATCH_METHOD,
        base_status="SATISFIED",
        observations=obs_satisfied,
        evidence_completeness="INCOMPLETE",
    )
    match_base_unknown = evaluate_match(
        request,
        offer_bob,
        method=DEFAULT_MATCH_METHOD,
        base_status="UNSUPPORTED",
        observations=obs_satisfied,
        evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
    )

    rank_a_method = "https://example.test/ranking/method/a"
    rank_b_method = "https://example.test/ranking/method/b"
    rank_a = validate_ranked_view(rank_a_method, (record_ref(request).to_value(), record_ref(offer_bob).to_value()))
    rank_b = validate_ranked_view(rank_b_method, (record_ref(offer_bob).to_value(), record_ref(request).to_value()))
    cursor_method = "https://example.test/discovery/method/exact"
    cursor_binding = bind_cursor(
        source=source_a,
        method=cursor_method,
        query=query_bug42,
        cursor=b"page-2",
    )
    cursor_valid = validate_cursor_binding(
        cursor_binding,
        source=source_a,
        method=cursor_method,
        query=query_bug42,
    )

    cases: list[dict] = []
    cases.append({
        "id": "discovery-exact-action-filter",
        "kind": "discovery",
        "records": [projected_record(item) for item in all_records],
        "query": project_abstract(query_fix),
        "source": source_a,
        "completeness": "COMPLETE_FOR_DECLARED_SOURCE",
        "freshness": "FRESH",
        "expected": expected_subset(view_fix, "result_count", "nonconforming_candidates_ignored", "global_completeness", "absence_is_negative_evidence", "ordering"),
    })
    cases.append({
        "id": "discovery-exact-subject-filter",
        "kind": "discovery",
        "records": [projected_record(item) for item in (request, offer_bob, offer_carol)],
        "query": project_abstract(query_bug42),
        "source": source_a,
        "completeness": "COMPLETE_FOR_DECLARED_SOURCE",
        "freshness": "FRESH",
        "expected": expected_subset(view_bug42_a, "result_count", "global_completeness", "absence_is_negative_evidence"),
    })
    view_bob = evaluate_discovery(
        all_records,
        query_bob,
        source=source_a,
        completeness="COMPLETE_FOR_DECLARED_SOURCE",
        freshness="FRESH",
    )
    cases.append({
        "id": "discovery-exact-issuer-filter",
        "kind": "discovery",
        "records": [projected_record(item) for item in all_records],
        "query": project_abstract(query_bob),
        "source": source_a,
        "completeness": "COMPLETE_FOR_DECLARED_SOURCE",
        "freshness": "FRESH",
        "expected": expected_subset(view_bob, "result_count", "nonconforming_candidates_ignored", "global_completeness"),
    })
    cases.append({
        "id": "discovery-zero-results-not-negative-evidence",
        "kind": "discovery",
        "records": [projected_record(item) for item in (request, offer_bob)],
        "query": project_abstract(query_none),
        "source": source_a,
        "completeness": "PARTIAL_SOURCE",
        "freshness": "UNKNOWN",
        "expected": expected_subset(view_none, "result_count", "completeness", "global_completeness", "absence_is_negative_evidence"),
    })
    cases.append({
        "id": "federation-deduplicates-record-identity",
        "kind": "federation",
        "views": [project_abstract(view_bug42_a), project_abstract(view_bug42_b)],
        "expected": expected_subset(federated, "result_count", "global_completeness", "canonical_ranking", "absence_is_negative_evidence"),
    })
    cases.append({
        "id": "verified-index-entry",
        "kind": "index",
        "entry": project_abstract(index_entry),
        "record": projected_record(offer_bob),
        "expected": index_verified,
    })
    cases.append({
        "id": "match-critical-extension-unsupported",
        "kind": "match",
        "left": projected_record(critical_request),
        "right": projected_record(offer_bob),
        "method": DEFAULT_MATCH_METHOD,
        "base_status": "SATISFIED",
        "observations": project_abstract(obs_satisfied),
        "evidence_completeness": "COMPLETE_FOR_METHOD_INPUTS",
        "understood_critical": [],
        "expected": expected_subset(match_critical_unknown, "unsupported_critical_semantics", "conclusion", "protocol_truth", "creates_agreement"),
    })
    cases.append({
        "id": "match-critical-extension-understood",
        "kind": "match",
        "left": projected_record(critical_request),
        "right": projected_record(offer_bob),
        "method": DEFAULT_MATCH_METHOD,
        "base_status": "SATISFIED",
        "observations": project_abstract(obs_satisfied),
        "evidence_completeness": "COMPLETE_FOR_METHOD_INPUTS",
        "understood_critical": [critical_semantic],
        "expected": expected_subset(match_critical_understood, "unsupported_critical_semantics", "conclusion", "protocol_truth", "creates_agreement"),
    })
    for case_id, result, observations, completeness, base_status in (
        ("match-mandatory-satisfied-preference-unsatisfied", match_ok, obs_satisfied, "COMPLETE_FOR_METHOD_INPUTS", "SATISFIED"),
        ("match-mandatory-unsatisfied", match_no, obs_unsatisfied, "COMPLETE_FOR_METHOD_INPUTS", "SATISFIED"),
        ("match-mandatory-unsupported", match_unknown, obs_unknown, "COMPLETE_FOR_METHOD_INPUTS", "SATISFIED"),
        ("match-mandatory-observation-missing", match_missing, (), "COMPLETE_FOR_METHOD_INPUTS", "SATISFIED"),
        ("match-evidence-incomplete", match_incomplete, obs_satisfied, "INCOMPLETE", "SATISFIED"),
        ("match-method-base-unsupported", match_base_unknown, obs_satisfied, "COMPLETE_FOR_METHOD_INPUTS", "UNSUPPORTED"),
    ):
        cases.append({
            "id": case_id,
            "kind": "match",
            "left": projected_record(request),
            "right": projected_record(offer_bob),
            "method": DEFAULT_MATCH_METHOD,
            "base_status": base_status,
            "observations": project_abstract(observations),
            "evidence_completeness": completeness,
            "expected": expected_subset(
                result,
                "mandatory_unsatisfied",
                "mandatory_unknown",
                "preferred_unsatisfied",
                "preference_unknown",
                "conclusion",
                "protocol_truth",
                "creates_agreement",
            ),
        })
    cases.append({
        "id": "ranking-method-a",
        "kind": "ranking",
        "method": rank_a_method,
        "record_refs": [projected_ref(request), projected_ref(offer_bob)],
        "expected": rank_a,
    })
    cases.append({
        "id": "ranking-method-b-disagrees",
        "kind": "ranking",
        "method": rank_b_method,
        "record_refs": [projected_ref(offer_bob), projected_ref(request)],
        "expected": rank_b,
    })
    cases.append({
        "id": "cursor-bound-to-source-method-query",
        "kind": "cursor",
        "binding": project_abstract(cursor_binding),
        "source": source_a,
        "method": cursor_method,
        "query": project_abstract(query_bug42),
        "expected": cursor_valid,
    })

    bad_index_identity = deepcopy(index_entry)
    bad_index_identity["record_ref"] = record_ref(request).to_value()
    bad_index_action = deepcopy(index_entry)
    bad_index_action["action"] = deliver["id"]
    missing_constraint = {"id": "https://example.test/constraints/other", "mode": "mandatory", "value": True}
    tampered_global = deepcopy(view_bug42_a)
    tampered_global["global_completeness"] = "COMPLETE"
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    canonical_identity = view_bug42_a["result_refs"][0]
    last_index = alphabet.index(canonical_identity[-1])
    assert last_index % 4 == 0
    noncanonical_identity = canonical_identity[:-1] + alphabet[last_index + 1]
    tampered_identity = deepcopy(view_bug42_a)
    tampered_identity["result_refs"][0] = noncanonical_identity
    duplicate_observation = [
        {"side": "left", "constraint": mandatory_license, "status": "SATISFIED"},
        {"side": "left", "constraint": mandatory_license, "status": "SATISFIED"},
    ]

    negative_cases = [
        {
            "id": "discovery-query-script-forbidden",
            "kind": "discovery",
            "records": [projected_record(request)],
            "query": project_abstract({"version": 1, "script": "return true"}),
            "source": source_a,
            "completeness": "UNKNOWN_SOURCE",
            "freshness": "UNKNOWN",
            "expected_error": "UNKNOWN_QUERY_FIELD",
        },
        {
            "id": "discovery-query-duplicate-set-value",
            "kind": "discovery",
            "records": [projected_record(request)],
            "query": project_abstract({"version": 1, "action_ids_any": (fix["id"], fix["id"])}),
            "source": source_a,
            "completeness": "UNKNOWN_SOURCE",
            "freshness": "UNKNOWN",
            "expected_error": "NONCANONICAL_QUERY_SET",
        },
        {
            "id": "discovery-global-completeness-value-forbidden",
            "kind": "discovery",
            "records": [projected_record(request)],
            "query": project_abstract(query_bug42),
            "source": source_a,
            "completeness": "GLOBAL_COMPLETE",
            "freshness": "UNKNOWN",
            "expected_error": "INVALID_COMPLETENESS",
        },
        {
            "id": "discovery-resource-limit",
            "kind": "discovery",
            "records": [projected_record(request), projected_record(offer_bob)],
            "query": project_abstract(query_bug42),
            "source": source_a,
            "completeness": "UNKNOWN_SOURCE",
            "freshness": "UNKNOWN",
            "max_records": 1,
            "expected_error": "RESOURCE_LIMIT_EXCEEDED",
        },
        {
            "id": "index-record-ref-mismatch",
            "kind": "index",
            "entry": project_abstract(bad_index_identity),
            "record": projected_record(offer_bob),
            "expected_error": "INDEX_IDENTITY_MISMATCH",
        },
        {
            "id": "index-projection-mismatch",
            "kind": "index",
            "entry": project_abstract(bad_index_action),
            "record": projected_record(offer_bob),
            "expected_error": "INDEX_PROJECTION_MISMATCH",
        },
        {
            "id": "match-observation-constraint-not-found",
            "kind": "match",
            "left": projected_record(request),
            "right": projected_record(offer_bob),
            "method": DEFAULT_MATCH_METHOD,
            "base_status": "SATISFIED",
            "observations": project_abstract(({"side": "left", "constraint": missing_constraint, "status": "SATISFIED"},)),
            "evidence_completeness": "COMPLETE_FOR_METHOD_INPUTS",
            "expected_error": "OBSERVATION_CONSTRAINT_NOT_FOUND",
        },
        {
            "id": "match-duplicate-observation",
            "kind": "match",
            "left": projected_record(request),
            "right": projected_record(offer_bob),
            "method": DEFAULT_MATCH_METHOD,
            "base_status": "SATISFIED",
            "observations": project_abstract(duplicate_observation),
            "evidence_completeness": "COMPLETE_FOR_METHOD_INPUTS",
            "expected_error": "DUPLICATE_MATCH_OBSERVATION",
        },
        {
            "id": "match-method-must-be-uri",
            "kind": "match",
            "left": projected_record(request),
            "right": projected_record(offer_bob),
            "method": "not-a-uri",
            "base_status": "SATISFIED",
            "observations": project_abstract(obs_satisfied),
            "evidence_completeness": "COMPLETE_FOR_METHOD_INPUTS",
            "expected_error": "INVALID_URI",
        },
        {
            "id": "ranking-duplicate-record-ref",
            "kind": "ranking",
            "method": rank_a_method,
            "record_refs": [projected_ref(request), projected_ref(request)],
            "expected_error": "DUPLICATE_RANKED_RESULT",
        },
        {
            "id": "federation-global-completeness-claim",
            "kind": "federation",
            "views": [project_abstract(tampered_global)],
            "expected_error": "GLOBAL_COMPLETENESS_FORBIDDEN",
        },
        {
            "id": "federation-noncanonical-record-identity",
            "kind": "federation",
            "views": [project_abstract(tampered_identity)],
            "expected_error": "INVALID_DISCOVERY_VIEW",
        },
        {
            "id": "federation-query-mismatch",
            "kind": "federation",
            "views": [project_abstract(view_bug42_a), project_abstract(view_fix)],
            "expected_error": "FEDERATION_QUERY_MISMATCH",
        },
        {
            "id": "cursor-source-mismatch",
            "kind": "cursor",
            "binding": project_abstract(cursor_binding),
            "source": source_b,
            "method": cursor_method,
            "query": project_abstract(query_bug42),
            "expected_error": "CURSOR_SOURCE_MISMATCH",
        },
    ]

    return {
        "format": "marketplace-matching-discovery-v1-conformance-vectors",
        "marketplace_semantic_base": BASE,
        "olp_reference_source_commit": olp_commit(),
        "note": "record/ref/value fields use OLP implementation-neutral conformance projection; this JSON file is not a Marketplace wire format",
        "record_identities": {
            "request": record_identity_text(request),
            "offer_bob": record_identity_text(offer_bob),
            "offer_carol": record_identity_text(offer_carol),
            "delivery": record_identity_text(delivery),
        },
        "cases": cases,
        "negative_cases": negative_cases,
    }


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    print(f"positive/evaluation cases: {len(data['cases'])}")
    print(f"negative cases: {len(data['negative_cases'])}")
    for name, identity in data["record_identities"].items():
        print(name, identity)


if __name__ == "__main__":
    main()
