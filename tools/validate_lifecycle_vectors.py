"""Validate committed Marketplace lifecycle and negotiation v1 vectors."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from olp import RecordV1
from olp.identity_authority_lifecycle_v1 import evaluate_authority_lifecycle
from olp.model.proof import OLPProof, RecordCommitment
from olp.model.verification import ResolvedVerificationMethod
from olp.transport import materialize_map, unproject_abstract

from marketplace_lifecycle_v1 import (
    AssentEvidence,
    MarketplaceLifecycleError,
    NEGOTIATION_SCOPE,
    evaluate_acceptance_withdrawal_coexistence,
    evaluate_agreement_formation,
    evaluate_negotiation,
    evaluate_supersession,
    evaluate_temporal_applicability,
    validate_amendment_relationship,
    validate_proposal_response_event,
    validate_withdrawal_statement,
)

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "conformance" / "vectors" / "lifecycle-negotiation-v1.json"


def decode(value):
    return materialize_map(unproject_abstract(value), allowed_key_types=(str, int))


def record_from(value) -> RecordV1:
    return RecordV1.from_mapping(decode(value))


def proof_from(value) -> OLPProof:
    raw = decode(value)
    algorithm, digest = raw["recordCommitment"]
    return OLPProof(
        type=raw["type"],
        version=raw["version"],
        cryptosuite=raw["cryptosuite"],
        proofPurpose=raw["proofPurpose"],
        verificationMethod=raw["verificationMethod"],
        recordCommitment=RecordCommitment(algorithm, digest),
        proofValue=raw["proofValue"],
        created=raw.get("created"),
        expires=raw.get("expires"),
        domain=raw.get("domain"),
        challenge=raw.get("challenge"),
        nonce=raw.get("nonce"),
        critical=tuple(raw.get("critical", ())),
        extensions=raw.get("extensions", {}),
    )


def actual_olp_commit() -> str:
    try:
        import olp

        repo = Path(olp.__file__).resolve().parents[2]
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def formation_evidence(items) -> tuple[AssentEvidence, ...]:
    evidence = []
    for item in items:
        proof = proof_from(item["proof"])
        public_key = decode(item["public_key"])
        method = ResolvedVerificationMethod(proof.verificationMethod, "Ed25519", public_key)
        evidence.append(
            AssentEvidence(
                item["principal"],
                proof,
                method,
                bool(item["attribution_accepted"]),
            )
        )
    return tuple(evidence)


def select(result, expected):
    if not isinstance(expected, dict):
        return result
    return {key: result[key] for key in expected}


def run_case(item):
    kind = item["kind"]
    if kind == "negotiation":
        result = evaluate_negotiation(tuple(record_from(value) for value in item["records"]))
        return select(result, item.get("expected", {}))
    if kind == "proposal_response_event":
        return validate_proposal_response_event(record_from(item["event"]), record_from(item["proposal"]))
    if kind == "temporal":
        return evaluate_temporal_applicability(record_from(item["intent"]), item["evaluation_time"])
    if kind == "formation":
        result = evaluate_agreement_formation(
            record_from(item["agreement"]),
            formation_evidence(item.get("assent", ())),
        )
        return select(result, item.get("expected", {}))
    if kind == "withdrawal":
        result = validate_withdrawal_statement(
            decode(item["statement"]),
            record_from(item["target"]),
            evaluation_time=item.get("evaluation_time"),
        )
        return {
            "marketplace_event": result["marketplace_event"],
            "operational_state": result["operational_state"],
            "olp_event": result["olp_lifecycle"]["events"][0]["event"],
            "effective": result["olp_lifecycle"]["events"][0]["effective"],
        }
    if kind == "acceptance_withdrawal_race":
        result = evaluate_acceptance_withdrawal_coexistence(
            record_from(item["proposal"]),
            record_from(item["response_event"]),
            decode(item["statement"]),
            evaluation_time=item.get("evaluation_time"),
        )
        return select(result, item.get("expected", {}))
    if kind == "amendment":
        result = validate_amendment_relationship(
            record_from(item["amended"]),
            record_from(item["previous"]),
            record_from(item["relationship"]),
        )
        return select(result, item.get("expected", {}))
    if kind == "supersession":
        result = evaluate_supersession(
            record_from(item["target"]),
            tuple(record_from(value) for value in item["relationships"]),
        )
        return select(result, item.get("expected", {}))
    if kind == "olp_lifecycle_conflict":
        result = evaluate_authority_lifecycle(
            {
                "mode": "lifecycle",
                "target": decode(item["target"]),
                "statuses": tuple(decode(value) for value in item["statuses"]),
                "required_scope": NEGOTIATION_SCOPE,
                "evaluation_time": item["evaluation_time"],
            }
        )
        return select(result, item.get("expected", {}))
    raise MarketplaceLifecycleError("UNSUPPORTED_VECTOR_KIND", f"unsupported vector kind {kind!r}")


def main() -> int:
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    errors: list[str] = []

    if data.get("format") != "marketplace-lifecycle-negotiation-v1-conformance-vectors":
        errors.append("unexpected lifecycle vector format discriminator")
    all_items = list(data.get("cases", ())) + list(data.get("negative_cases", ()))
    ids = [item.get("id") for item in all_items]
    if len(ids) != len(set(ids)):
        errors.append("lifecycle vector ids MUST be unique")

    active_commit = actual_olp_commit()
    if active_commit != "unknown" and active_commit != data["olp_reference_source_commit"]:
        errors.append(
            f"OLP source pin mismatch: vectors={data['olp_reference_source_commit']} active={active_commit}"
        )

    for item in data["cases"]:
        try:
            actual = run_case(item)
        except Exception as exc:
            errors.append(f"{item['id']}: unexpected failure: {type(exc).__name__}: {exc}")
            continue
        if actual != item["expected"]:
            errors.append(f"{item['id']}: expected {item['expected']!r} got {actual!r}")

    for item in data["negative_cases"]:
        try:
            run_case(item)
        except MarketplaceLifecycleError as exc:
            if exc.code != item["expected_error"]:
                errors.append(f"{item['id']}: expected {item['expected_error']} got {exc.code}: {exc}")
        except Exception as exc:
            errors.append(f"{item['id']}: wrong exception type: {type(exc).__name__}: {exc}")
        else:
            errors.append(f"{item['id']}: negative case unexpectedly accepted")

    if errors:
        print("Marketplace lifecycle vector validation FAILED")
        for error in errors:
            print("-", error)
        return 1
    total = len(data["cases"]) + len(data["negative_cases"])
    print(f"Marketplace lifecycle vector validation PASS: {total} vectors")
    print("OLP source commit:", data["olp_reference_source_commit"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
