"""Generate Marketplace dispute-resolution v1 conformance vectors."""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text
from olp.evidence import record_ref, relationship_record
from olp.transport import project_abstract

from marketplace_dispute_resolution_v1 import (
    AUTHORITY_STATUSES,
    ATTRIBUTION_STATUSES,
    LIFECYCLE_STATUSES,
    MAX_CONTEXT_ENTRIES,
    MAX_DISPUTES,
    MAX_RESOLUTIONS,
    METHOD_CORE,
    OBS_ADDITIONAL_EVIDENCE,
    OBS_HUMAN_REVIEW,
    OBS_PARTIAL,
    OBS_REJECT,
    OBS_UPHOLD,
    PROOF_STATUSES,
    DisputeEvidence,
    ResolutionObservation,
    evaluate_dispute_resolution,
    evaluate_resolution_reuse,
    resolution_request_fingerprint,
    validate_resolution_request,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "dispute-resolution-v1.json"
SOURCE_A = "https://source.example/a"
SOURCE_B = "https://source.example/b"
AUTHORITY_A = "https://authority.example/a"
AUTHORITY_B = "https://authority.example/b"
PURPOSE = "https://example.test/dispute-purpose/review"
CRITICAL = "https://example.test/dispute/critical/procedure-v1"


def olp_commit() -> str:
    import olp
    repo = Path(olp.__file__).resolve().parents[2]
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


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


def generic_record(kind: str, value: str) -> RecordV1:
    return RecordV1(
        envelope_version=1,
        type=f"https://example.test/record/{kind}",
        content={"https://example.test/value": value},
    )


def dispute_wire(value: DisputeEvidence) -> dict:
    return {
        "record": projected_record(value.record),
        "source": value.source,
        "authority": value.authority,
        "proof_status": value.proof_status,
        "attribution_status": value.attribution_status,
        "authority_status": value.authority_status,
        "lifecycle_status": value.lifecycle_status,
    }


def resolution_wire(value: ResolutionObservation) -> dict:
    return {
        "resolution_record_id": value.resolution_record_id,
        "dispute_record_ids": list(value.dispute_record_ids),
        "target_record_ids": list(value.target_record_ids),
        "outcome": value.outcome,
        "source": value.source,
        "authority": value.authority,
        "proof_status": value.proof_status,
        "attribution_status": value.attribution_status,
        "authority_status": value.authority_status,
        "lifecycle_status": value.lifecycle_status,
        "critical_uris": list(value.critical_uris),
        "reason_uris": list(value.reason_uris),
    }


def request(target_ids: tuple[str, ...], *, understood=(), sources=(SOURCE_A,), authorities=(AUTHORITY_A,), context=None, max_disputes=32, max_resolutions=32) -> dict:
    return {
        "version": 1,
        "method": METHOD_CORE,
        "purpose": PURPOSE,
        "challenged_record_ids": list(sorted(target_ids)),
        "context": context or {},
        "accepted_sources": list(sorted(sources)),
        "accepted_authorities": list(sorted(authorities)),
        "understood_critical": list(sorted(understood)),
        "max_disputes": max_disputes,
        "max_resolutions": max_resolutions,
    }


def dispute_item(record: RecordV1, *, source=SOURCE_A, authority=AUTHORITY_A, proof="VERIFIED", attribution="ACCEPTED", authority_status="ACCEPTED", lifecycle="ACCEPTABLE") -> DisputeEvidence:
    return DisputeEvidence(record, source, authority, proof, attribution, authority_status, lifecycle)


def resolution_item(record: RecordV1, dispute_ids: tuple[str, ...], target_ids: tuple[str, ...], outcome: str, *, source=SOURCE_A, authority=AUTHORITY_A, proof="VERIFIED", attribution="ACCEPTED", authority_status="ACCEPTED", lifecycle="ACCEPTABLE", critical=(), reasons=()) -> ResolutionObservation:
    return ResolutionObservation(
        record_identity_text(record), tuple(sorted(dispute_ids)), tuple(sorted(target_ids)), outcome,
        source, authority, proof, attribution, authority_status, lifecycle,
        tuple(sorted(critical)), tuple(sorted(reasons)),
    )


def build() -> dict:
    target_a = generic_record("claim", "target-a")
    target_b = generic_record("claim", "target-b")
    target_other = generic_record("claim", "outside")
    challenger_a = generic_record("challenge", "challenger-a")
    challenger_b = generic_record("challenge", "challenger-b")
    target_a_id = record_identity_text(target_a)
    target_b_id = record_identity_text(target_b)
    target_other_id = record_identity_text(target_other)

    dispute_a = relationship_record("disputes", subject=record_ref(challenger_a), objects=[record_ref(target_a)])
    dispute_b = relationship_record("disputes", subject=record_ref(challenger_b), objects=[record_ref(target_b)])
    dispute_ab = relationship_record("disputes", subject=record_ref(challenger_a), objects=[record_ref(target_b), record_ref(target_a)])
    dispute_other = relationship_record("disputes", subject=record_ref(challenger_a), objects=[record_ref(target_other)])
    dispute_critical = relationship_record(
        "disputes",
        subject=record_ref(challenger_a),
        objects=[record_ref(target_a)],
        qualifiers={CRITICAL: "required"},
        critical=[CRITICAL],
    )
    non_dispute = relationship_record("references", subject=record_ref(challenger_a), objects=[record_ref(target_a)])
    malformed_relation_record = generic_record("claim", "not-a-relationship")

    did_a = record_identity_text(dispute_a)
    did_b = record_identity_text(dispute_b)
    did_ab = record_identity_text(dispute_ab)
    did_critical = record_identity_text(dispute_critical)

    resolution_records = {
        name: generic_record("resolution", name)
        for name in (
            "uphold-a", "reject-a", "partial-a", "human-a", "additional-a",
            "uphold-b", "uphold-critical", "unknown-a", "scope-mismatch",
            "binding-mismatch", "target-binding-mismatch", "conflict-id",
        )
    }

    req_a = request((target_a_id,))
    req_ab = request((target_a_id, target_b_id), sources=(SOURCE_A, SOURCE_B), authorities=(AUTHORITY_A, AUTHORITY_B))
    d_a = dispute_item(dispute_a)
    d_b = dispute_item(dispute_b, source=SOURCE_B, authority=AUTHORITY_B)
    d_ab = dispute_item(dispute_ab)

    r_uphold = resolution_item(resolution_records["uphold-a"], (did_a,), (target_a_id,), OBS_UPHOLD)
    r_reject = resolution_item(resolution_records["reject-a"], (did_a,), (target_a_id,), OBS_REJECT)
    r_partial = resolution_item(resolution_records["partial-a"], (did_a,), (target_a_id,), OBS_PARTIAL)
    r_human = resolution_item(resolution_records["human-a"], (did_a,), (target_a_id,), OBS_HUMAN_REVIEW)
    r_additional = resolution_item(resolution_records["additional-a"], (did_a,), (target_a_id,), OBS_ADDITIONAL_EVIDENCE)

    cases: list[dict] = []
    negative_cases: list[dict] = []

    def add(case_id: str, kind: str, payload: dict, expected) -> None:
        cases.append({"id": case_id, "kind": kind, **payload, "expected": jsonable(expected)})

    def negative(case_id: str, kind: str, payload: dict, code: str) -> None:
        negative_cases.append({"id": case_id, "kind": kind, **payload, "expected_error": code})

    add("request-single-valid", "request", {"request": req_a}, {
        "request": validate_resolution_request(req_a),
        "fingerprint": resolution_request_fingerprint(req_a),
    })
    add("request-multi-target-valid", "request", {"request": req_ab}, {
        "request": validate_resolution_request(req_ab),
        "fingerprint": resolution_request_fingerprint(req_ab),
    })

    def evaluation(case_id: str, req: dict, disputes, resolutions) -> dict:
        result = evaluate_dispute_resolution(req, disputes, resolutions)
        add(case_id, "evaluation", {
            "request": req,
            "disputes": [dispute_wire(item) for item in disputes],
            "resolutions": [resolution_wire(item) for item in resolutions],
        }, result)
        return result

    evaluation("evaluation-no-dispute", req_a, (), ())
    evaluation("evaluation-dispute-needs-resolution", req_a, (d_a,), ())
    uphold_result = evaluation("evaluation-uphold", req_a, (d_a,), (r_uphold,))
    evaluation("evaluation-reject", req_a, (d_a,), (r_reject,))
    evaluation("evaluation-partial", req_a, (d_a,), (r_partial,))
    evaluation("evaluation-conflicting-uphold-reject", req_a, (d_a,), (r_uphold, r_reject))
    evaluation("evaluation-mixed-uphold-partial", req_a, (d_a,), (r_uphold, r_partial))
    evaluation("evaluation-human-review", req_a, (d_a,), (r_human,))
    evaluation("evaluation-additional-evidence", req_a, (d_a,), (r_additional,))
    evaluation("evaluation-unresolved-dispute-proof", req_a, (dispute_item(dispute_a, proof="UNKNOWN"),), ())
    evaluation("evaluation-unresolved-dispute-authority", req_a, (dispute_item(dispute_a, authority_status="UNKNOWN"),), ())
    evaluation("evaluation-unknown-critical-dispute", req_a, (dispute_item(dispute_critical),), ())
    req_a_critical = request((target_a_id,), understood=(CRITICAL,))
    evaluation("evaluation-understood-critical-dispute", req_a_critical, (dispute_item(dispute_critical),), ())
    evaluation("evaluation-dispute-source-excluded", req_a, (dispute_item(dispute_a, source=SOURCE_B),), ())
    evaluation("evaluation-dispute-authority-excluded", req_a, (dispute_item(dispute_a, authority=AUTHORITY_B),), ())
    evaluation("evaluation-dispute-proof-failed", req_a, (dispute_item(dispute_a, proof="FAILED"),), ())
    evaluation("evaluation-dispute-lifecycle-adverse", req_a, (dispute_item(dispute_a, lifecycle="ADVERSE"),), ())
    evaluation("evaluation-dispute-out-of-scope", req_a, (dispute_item(dispute_other),), ())

    r_unknown_proof = resolution_item(resolution_records["unknown-a"], (did_a,), (target_a_id,), OBS_UPHOLD, proof="UNKNOWN")
    evaluation("evaluation-resolution-proof-unknown", req_a, (d_a,), (r_unknown_proof,))
    r_unknown_critical = resolution_item(resolution_records["uphold-critical"], (did_a,), (target_a_id,), OBS_UPHOLD, critical=(CRITICAL,))
    evaluation("evaluation-resolution-critical-unknown", req_a, (d_a,), (r_unknown_critical,))
    evaluation("evaluation-resolution-critical-understood", req_a_critical, (d_a,), (r_unknown_critical,))
    evaluation("evaluation-resolution-source-excluded", req_a, (d_a,), (resolution_item(resolution_records["uphold-b"], (did_a,), (target_a_id,), OBS_UPHOLD, source=SOURCE_B),))
    evaluation("evaluation-resolution-authority-excluded", req_a, (d_a,), (resolution_item(resolution_records["uphold-b"], (did_a,), (target_a_id,), OBS_UPHOLD, authority=AUTHORITY_B),))
    evaluation("evaluation-resolution-proof-failed", req_a, (d_a,), (resolution_item(resolution_records["uphold-b"], (did_a,), (target_a_id,), OBS_UPHOLD, proof="FAILED"),))
    evaluation("evaluation-resolution-lifecycle-adverse", req_a, (d_a,), (resolution_item(resolution_records["uphold-b"], (did_a,), (target_a_id,), OBS_UPHOLD, lifecycle="ADVERSE"),))
    r_scope_mismatch = resolution_item(resolution_records["scope-mismatch"], (did_a,), (target_a_id, target_b_id), OBS_UPHOLD)
    evaluation("evaluation-resolution-target-scope-mismatch", req_a, (d_a,), (r_scope_mismatch,))
    r_binding_mismatch = resolution_item(resolution_records["binding-mismatch"], (did_b,), (target_a_id,), OBS_UPHOLD)
    evaluation("evaluation-resolution-dispute-binding-mismatch", req_a, (d_a,), (r_binding_mismatch,))
    r_target_binding_mismatch = resolution_item(
        resolution_records["target-binding-mismatch"], (did_a,), (target_b_id,), OBS_UPHOLD
    )
    evaluation(
        "evaluation-resolution-dispute-target-binding-mismatch",
        req_ab,
        (d_a,),
        (r_target_binding_mismatch,),
    )

    evaluation("evaluation-duplicate-dispute-delivery", req_a, (d_a, d_a), (r_uphold,))
    evaluation("evaluation-duplicate-resolution-delivery", req_a, (d_a,), (r_uphold, r_uphold))
    evaluation("evaluation-multi-target-two-disputes", req_ab, (d_a, d_b), (
        resolution_item(resolution_records["uphold-a"], (did_a,), (target_a_id,), OBS_UPHOLD),
        resolution_item(resolution_records["uphold-b"], (did_b,), (target_b_id,), OBS_UPHOLD, source=SOURCE_B, authority=AUTHORITY_B),
    ))
    evaluation("evaluation-multi-target-combined-dispute", req_ab, (d_ab,), (
        resolution_item(resolution_records["uphold-a"], (did_ab,), (target_a_id, target_b_id), OBS_PARTIAL),
    ))

    excluded_duplicate = dispute_item(dispute_a, source=SOURCE_B)
    evaluation("evaluation-same-dispute-admitted-and-excluded-source", req_a, (d_a, excluded_duplicate), (r_uphold,))
    r_excluded_same = resolution_item(resolution_records["uphold-a"], (did_a,), (target_a_id,), OBS_UPHOLD, source=SOURCE_B)
    evaluation("evaluation-same-resolution-admitted-and-excluded-source", req_a, (d_a,), (r_uphold, r_excluded_same))

    add("reuse-exact-input", "reuse", {
        "prior_result": jsonable(uphold_result),
        "request": req_a,
        "disputes": [dispute_wire(d_a)],
        "resolutions": [resolution_wire(r_uphold)],
    }, evaluate_resolution_reuse(uphold_result, req_a, (d_a,), (r_uphold,)))
    changed_context = deepcopy(req_a)
    changed_context["context"] = {"https://example.test/context/review-mode": "strict"}
    add("reuse-changed-request", "reuse", {
        "prior_result": jsonable(uphold_result),
        "request": changed_context,
        "disputes": [dispute_wire(d_a)],
        "resolutions": [resolution_wire(r_uphold)],
    }, evaluate_resolution_reuse(uphold_result, changed_context, (d_a,), (r_uphold,)))
    add("reuse-changed-resolution-evidence", "reuse", {
        "prior_result": jsonable(uphold_result),
        "request": req_a,
        "disputes": [dispute_wire(d_a)],
        "resolutions": [resolution_wire(r_reject)],
    }, evaluate_resolution_reuse(uphold_result, req_a, (d_a,), (r_reject,)))

    bad = deepcopy(req_a); bad["extra"] = True
    negative("request-unknown-field", "request", {"request": bad}, "INVALID_DISPUTE_REQUEST")
    bad = deepcopy(req_a); bad["version"] = True
    negative("request-version-bool", "request", {"request": bad}, "INVALID_DISPUTE_REQUEST")
    bad = deepcopy(req_a); bad["method"] = "relative"
    negative("request-method-not-uri", "request", {"request": bad}, "INVALID_DISPUTE_URI")
    bad = deepcopy(req_a); bad["purpose"] = "review"
    negative("request-purpose-not-uri", "request", {"request": bad}, "INVALID_DISPUTE_URI")
    bad = deepcopy(req_a); bad["challenged_record_ids"] = []
    negative("request-empty-targets", "request", {"request": bad}, "EMPTY_DISPUTE_SET")
    bad = deepcopy(req_a); bad["challenged_record_ids"] = [target_a_id, target_a_id]
    negative("request-duplicate-targets", "request", {"request": bad}, "NONCANONICAL_DISPUTE_SET")
    unsorted_targets = sorted((target_a_id, target_b_id), reverse=True)
    bad = deepcopy(req_ab); bad["challenged_record_ids"] = unsorted_targets
    negative("request-unsorted-targets", "request", {"request": bad}, "NONCANONICAL_DISPUTE_SET")
    bad = deepcopy(req_a); bad["max_disputes"] = 0
    negative("request-zero-dispute-limit", "request", {"request": bad}, "INVALID_RESOURCE_LIMIT")
    bad = deepcopy(req_a); bad["max_resolutions"] = MAX_RESOLUTIONS + 1
    negative("request-resolution-limit-too-large", "request", {"request": bad}, "INVALID_RESOURCE_LIMIT")
    bad = deepcopy(req_a); bad["accepted_sources"] = ["not-a-uri"]
    negative("request-invalid-source-uri", "request", {"request": bad}, "INVALID_DISPUTE_URI")
    bad = deepcopy(req_a); bad["accepted_authorities"] = ["not-a-uri"]
    negative("request-invalid-authority-uri", "request", {"request": bad}, "INVALID_DISPUTE_URI")
    bad = deepcopy(req_a); bad["understood_critical"] = ["not-a-uri"]
    negative("request-invalid-critical-uri", "request", {"request": bad}, "INVALID_DISPUTE_URI")
    bad = deepcopy(req_a); bad["method"] = "https://example.test/dispute/method/other"
    negative("evaluation-unsupported-method", "evaluation", {"request": bad, "disputes": [], "resolutions": []}, "UNSUPPORTED_DISPUTE_RESOLUTION_METHOD")

    negative("dispute-not-relationship-record", "evaluation", {
        "request": req_a,
        "disputes": [dispute_wire(dispute_item(malformed_relation_record))],
        "resolutions": [],
    }, "INVALID_OLP_DISPUTE")
    negative("dispute-wrong-relation-type", "evaluation", {
        "request": req_a,
        "disputes": [dispute_wire(dispute_item(non_dispute))],
        "resolutions": [],
    }, "NOT_A_DISPUTE_RELATIONSHIP")
    for field, value, code in (
        ("source", "not-a-uri", "INVALID_DISPUTE_URI"),
        ("authority", "not-a-uri", "INVALID_DISPUTE_URI"),
        ("proof_status", "MAYBE", "INVALID_DISPUTE_OBSERVATION_STATUS"),
        ("attribution_status", "MAYBE", "INVALID_DISPUTE_OBSERVATION_STATUS"),
        ("authority_status", "MAYBE", "INVALID_DISPUTE_OBSERVATION_STATUS"),
        ("lifecycle_status", "MAYBE", "INVALID_DISPUTE_OBSERVATION_STATUS"),
    ):
        item = dispute_wire(d_a); item[field] = value
        negative(f"dispute-invalid-{field.replace('_', '-')}", "evaluation", {"request": req_a, "disputes": [item], "resolutions": []}, code)

    bad_resolution = resolution_wire(r_uphold); bad_resolution.pop("reason_uris")
    negative("resolution-missing-field", "evaluation", {"request": req_a, "disputes": [dispute_wire(d_a)], "resolutions": [bad_resolution]}, "INVALID_RESOLUTION_OBSERVATION")
    bad_resolution = resolution_wire(r_uphold); bad_resolution["resolution_record_id"] = "r1_bad"
    negative("resolution-invalid-record-id", "evaluation", {"request": req_a, "disputes": [dispute_wire(d_a)], "resolutions": [bad_resolution]}, "INVALID_DISPUTE_RECORD_ID")
    bad_resolution = resolution_wire(r_uphold); bad_resolution["dispute_record_ids"] = [did_a, did_a]
    negative("resolution-duplicate-dispute-ids", "evaluation", {"request": req_a, "disputes": [dispute_wire(d_a)], "resolutions": [bad_resolution]}, "NONCANONICAL_DISPUTE_SET")
    bad_resolution = resolution_wire(resolution_item(resolution_records["uphold-a"], (did_a, did_b), (target_a_id,), OBS_UPHOLD)); bad_resolution["dispute_record_ids"] = sorted((did_a, did_b), reverse=True)
    negative("resolution-unsorted-dispute-ids", "evaluation", {"request": req_ab, "disputes": [dispute_wire(d_a), dispute_wire(d_b)], "resolutions": [bad_resolution]}, "NONCANONICAL_DISPUTE_SET")
    bad_resolution = resolution_wire(r_uphold); bad_resolution["target_record_ids"] = [target_a_id, target_a_id]
    negative("resolution-duplicate-target-ids", "evaluation", {"request": req_a, "disputes": [dispute_wire(d_a)], "resolutions": [bad_resolution]}, "NONCANONICAL_DISPUTE_SET")
    bad_resolution = resolution_wire(resolution_item(resolution_records["uphold-a"], (did_a,), (target_a_id, target_b_id), OBS_UPHOLD)); bad_resolution["target_record_ids"] = sorted((target_a_id, target_b_id), reverse=True)
    negative("resolution-unsorted-target-ids", "evaluation", {"request": req_ab, "disputes": [dispute_wire(d_a)], "resolutions": [bad_resolution]}, "NONCANONICAL_DISPUTE_SET")
    bad_resolution = resolution_wire(r_uphold); bad_resolution["outcome"] = "WIN"
    negative("resolution-invalid-outcome", "evaluation", {"request": req_a, "disputes": [dispute_wire(d_a)], "resolutions": [bad_resolution]}, "INVALID_DISPUTE_OBSERVATION_STATUS")
    for field in ("source", "authority"):
        bad_resolution = resolution_wire(r_uphold); bad_resolution[field] = "not-a-uri"
        negative(f"resolution-invalid-{field}", "evaluation", {"request": req_a, "disputes": [dispute_wire(d_a)], "resolutions": [bad_resolution]}, "INVALID_DISPUTE_URI")
    bad_resolution = resolution_wire(r_uphold); bad_resolution["critical_uris"] = ["not-a-uri"]
    negative("resolution-invalid-critical-uri", "evaluation", {"request": req_a, "disputes": [dispute_wire(d_a)], "resolutions": [bad_resolution]}, "INVALID_DISPUTE_URI")
    bad_resolution = resolution_wire(r_uphold); bad_resolution["reason_uris"] = ["not-a-uri"]
    negative("resolution-invalid-reason-uri", "evaluation", {"request": req_a, "disputes": [dispute_wire(d_a)], "resolutions": [bad_resolution]}, "INVALID_DISPUTE_URI")
    for field in ("proof_status", "attribution_status", "authority_status", "lifecycle_status"):
        bad_resolution = resolution_wire(r_uphold); bad_resolution[field] = "MAYBE"
        negative(f"resolution-invalid-{field.replace('_', '-')}", "evaluation", {"request": req_a, "disputes": [dispute_wire(d_a)], "resolutions": [bad_resolution]}, "INVALID_DISPUTE_OBSERVATION_STATUS")

    conflict_record = resolution_records["conflict-id"]
    conflict_one = resolution_item(conflict_record, (did_a,), (target_a_id,), OBS_UPHOLD)
    conflict_two = resolution_item(conflict_record, (did_a,), (target_a_id,), OBS_REJECT)
    negative("resolution-same-id-conflicting-semantics", "evaluation", {
        "request": req_a, "disputes": [dispute_wire(d_a)],
        "resolutions": [resolution_wire(conflict_one), resolution_wire(conflict_two)],
    }, "RESOLUTION_IDENTITY_CONFLICT")

    tampered = jsonable(uphold_result); tampered["outcome"] = "REJECT_CHALLENGE_UNDER_METHOD"
    negative("reuse-tampered-result-fingerprint", "reuse", {
        "prior_result": tampered, "request": req_a,
        "disputes": [dispute_wire(d_a)], "resolutions": [resolution_wire(r_uphold)],
    }, "DISPUTE_RESULT_INTEGRITY_MISMATCH")
    tampered = jsonable(uphold_result); tampered["protected_side_effect_authorized"] = True
    negative("reuse-tampered-boundary-flag", "reuse", {
        "prior_result": tampered, "request": req_a,
        "disputes": [dispute_wire(d_a)], "resolutions": [resolution_wire(r_uphold)],
    }, "INVALID_PRIOR_DISPUTE_RESULT")

    negative("synthetic-context-limit", "synthetic-context-limit", {"count": MAX_CONTEXT_ENTRIES + 1, "base_request": req_a}, "INVALID_DISPUTE_CONTEXT")
    negative("synthetic-uri-limit", "synthetic-uri-limit", {"utf8_bytes": 2049, "base_request": req_a}, "DISPUTE_RESOURCE_LIMIT_EXCEEDED")
    negative("synthetic-dispute-limit", "synthetic-dispute-limit", {"count": 2, "base_request": request((target_a_id,), max_disputes=1), "dispute": dispute_wire(d_a)}, "DISPUTE_RESOURCE_LIMIT_EXCEEDED")
    negative("synthetic-resolution-limit", "synthetic-resolution-limit", {"count": 2, "base_request": request((target_a_id,), max_resolutions=1), "dispute": dispute_wire(d_a), "resolution": resolution_wire(r_uphold)}, "DISPUTE_RESOURCE_LIMIT_EXCEEDED")

    return {
        "format": "marketplace-dispute-resolution-v1-conformance-vectors",
        "olp_reference_source_commit": olp_commit(),
        "method": METHOD_CORE,
        "note": "record/ref/value fields use OLP implementation-neutral conformance projection; this JSON file is not a Marketplace wire format",
        "identities": {
            "target_a": target_a_id,
            "target_b": target_b_id,
            "dispute_a": did_a,
            "dispute_b": did_b,
            "critical_dispute": did_critical,
        },
        "cases": cases,
        "negative_cases": negative_cases,
    }


def main() -> int:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT}")
    print(f"positive/evaluation={len(data['cases'])} negative/adversarial={len(data['negative_cases'])} total={len(data['cases']) + len(data['negative_cases'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
