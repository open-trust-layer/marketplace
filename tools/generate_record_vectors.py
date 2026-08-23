"""Generate Marketplace Record Representation v1 conformance vectors.

Requires the OLP reference implementation on PYTHONPATH. Expected identities are
computed only through OLP's RecordV1 and record_identity functions.
"""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from olp import RecordV1, record_identity, record_identity_bytes, record_identity_text
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.transport import project_abstract

from marketplace_record_v1 import (
    BASE, CORE_PROFILE, PROPOSAL_PROFILE, TYPE_AGREEMENT, TYPE_EVENT, TYPE_INTENT,
    validate_market_record,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "record-representation-v1.json"


def olp_commit() -> str:
    try:
        import olp
        src = Path(olp.__file__).resolve()
        repo = src.parents[2]
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def sort_set(values):
    return sorted(values, key=olp_encode)


def record_mapping(record_type, content, profiles=None):
    return {
        "envelope_version": 1,
        "type": record_type,
        "content": content,
        "profiles": list(profiles or [CORE_PROFILE]),
    }


def to_record(mapping):
    record = RecordV1.from_mapping(mapping)
    validate_market_record(record)
    return record


def record_ref(record):
    return (0, record_identity(record))


def positive_record(vector_id, mapping, note):
    record = to_record(mapping)
    return {
        "id": vector_id,
        "note": note,
        "record": project_abstract(mapping),
        "expected_record_identity": record_identity_text(record),
        "expected_record_identity_hex": record_identity(record).hex(),
        "expected_identity_preimage_hex": record_identity_bytes(record).hex(),
    }, record


def negative_record(vector_id, mapping, expected_error, note):
    return {
        "id": vector_id,
        "note": note,
        "record": project_abstract(mapping),
        "expected_error": expected_error,
    }


def structure(vector_id, name, value, note, expected_error=None):
    item = {"id": vector_id, "structure": name, "value": project_abstract(value), "note": note}
    if expected_error is not None:
        item["expected_error"] = expected_error
    return item


def build():
    alice = {"principal": "did:example:alice", "role": "https://example.test/roles/requester"}
    bob = {"principal": "did:example:bob", "role": "https://example.test/roles/provider"}
    subject = {"uri": "urn:example:software-issue:42"}
    action = {"id": "https://example.test/actions/fix"}
    reward = {"kind": "monetary", "amount": {"coefficient": 500, "scale": 0}, "currency_code": "EUR"}
    terms = {"https://example.test/terms/reward": reward}

    intent_map = record_mapping(TYPE_INTENT, {
        "version": 1,
        "issuer": alice,
        "subjects": [subject],
        "action": action,
        "terms": terms,
        "constraints": [{"id": "https://example.test/constraints/deadline", "mode": "mandatory", "value": "2026-09-01T00:00:00Z"}],
        "validity": {"not_after": "2026-09-01T00:00:00Z"},
    })
    intent_vec, intent = positive_record("intent-basic", intent_map, "A fix intent with exact reward and validity terms.")

    proposal_map = record_mapping(TYPE_INTENT, {
        "version": 1,
        "issuer": bob,
        "subjects": [subject],
        "action": action,
        "terms": terms,
        "response_to": [record_ref(intent)],
    }, [CORE_PROFILE, PROPOSAL_PROFILE])
    proposal_vec, proposal = positive_record("intent-proposal", proposal_map, "Proposal is a MarketIntent profile with an immutable response reference.")

    parties = sort_set([alice, bob])
    sources = sort_set([record_ref(intent), record_ref(proposal)])
    criterion = {"criterion": "https://example.test/criteria/tests-pass", "mode": "required"}
    commitment = {
        "id": "c1",
        "party": bob,
        "action": action,
        "subjects": [subject],
        "acceptance_criteria": [criterion],
    }
    agreement_map = record_mapping(TYPE_AGREEMENT, {
        "version": 1,
        "parties": parties,
        "subjects": [subject],
        "actions": [action],
        "terms": terms,
        "commitments": [commitment],
        "source_records": sources,
    })
    agreement_vec, agreement = positive_record("agreement-basic", agreement_map, "Agreement binds exact parties, terms, commitment, and source records; assent proofs remain detached.")

    event_map = record_mapping(TYPE_EVENT, {
        "version": 1,
        "issuer": bob,
        "event": "https://example.test/events/work-submitted",
        "occurred_at": "2026-08-24T12:00:00Z",
        "related_records": [record_ref(agreement)],
        "commitment_ids": ["c1"],
        "outcome": {"type": "https://example.test/outcomes/submitted"},
    })
    event_vec, event = positive_record("event-work-submitted", event_map, "MarketEvent refers to the agreement and commitment without mutating either.")

    positive = [intent_vec, proposal_vec, agreement_vec, event_vec]

    bad_unknown = deepcopy(intent_map); bad_unknown["content"]["is_active"] = True
    bad_proposal = deepcopy(proposal_map); del bad_proposal["content"]["response_to"]
    bad_response = deepcopy(intent_map); bad_response["content"]["response_to"] = [record_ref(intent)]
    two_subjects = sort_set([subject, {"uri": "urn:example:software-issue:7"}])
    bad_order = deepcopy(intent_map); bad_order["content"]["subjects"] = list(reversed(two_subjects))
    bad_party = deepcopy(agreement_map); bad_party["content"]["commitments"][0]["party"] = {"principal": "did:example:mallory"}
    bad_event = record_mapping(TYPE_EVENT, {"version": 1, "issuer": bob, "event": "https://example.test/events/nocontext"})
    bad_time = deepcopy(event_map); bad_time["content"]["occurred_at"] = "2026-08-24T12:00:00+00:00"
    bad_critical = deepcopy(intent_map); bad_critical["content"]["extensions"] = {}; bad_critical["content"]["critical"] = ["https://example.test/ext/required"]
    bad_ref = deepcopy(proposal_map); bad_ref["content"]["response_to"] = [(1, bytes(32))]

    negative = [
        negative_record("intent-unknown-state-field", bad_unknown, "UNKNOWN_FIELD", "Mutable state is not part of MarketIntent content."),
        negative_record("proposal-missing-response", bad_proposal, "PROPOSAL_RESPONSE_REQUIRED", "proposal-v1 requires response_to."),
        negative_record("response-without-proposal-profile", bad_response, "PROPOSAL_PROFILE_REQUIRED", "response_to is not silently interpreted without the proposal profile."),
        negative_record("intent-noncanonical-subject-order", bad_order, "NON_CANONICAL_ORDER", "Set-like subject arrays must be OLP-CIE-1 sorted."),
        negative_record("agreement-unbound-commitment-party", bad_party, "COMMITMENT_PARTY_NOT_BOUND", "Commitment principal must be present in agreement parties."),
        negative_record("event-without-context", bad_event, "EVENT_CONTEXT_REQUIRED", "A MarketEvent must identify what it concerns."),
        negative_record("event-noncanonical-time", bad_time, "INVALID_TIMESTAMP", "Core timestamp profile uses canonical UTC-second form."),
        negative_record("critical-extension-missing", bad_critical, "CRITICAL_EXTENSION_MISSING", "Critical extensions must be present."),
        negative_record("proposal-proof-ref-instead-of-record", bad_ref, "WRONG_REFERENCE_KIND", "response_to must reference Records, not Proofs."),
    ]

    positive_structures = [
        structure("decimal-canonical", "DecimalV1", {"coefficient": 12345, "scale": 2}, "Canonical decimal 123.45."),
        structure("decimal-zero", "DecimalV1", {"coefficient": 0, "scale": 0}, "Zero has unique canonical form."),
        structure("quantity-hours", "QuantityV1", {"value": {"coefficient": 500, "scale": 0}, "unit": "https://qudt.org/vocab/unit/HR"}, "Exact quantity with URI-named unit."),
        structure("value-money", "ValueExpressionV1", reward, "Monetary expression is exact and does not assert fair value."),
        structure("value-semantic", "ValueExpressionV1", {"kind": "semantic", "semantic": "https://example.test/value/barter", "value": {"item": "urn:example:item:1"}}, "Non-monetary value remains semantically namespaced."),
        structure("temporal-window", "TemporalConditionV1", {"not_before": "2026-08-24T00:00:00Z", "not_after": "2026-08-25T00:00:00Z"}, "Canonical bounded UTC interval."),
        structure("location-external", "LocationConditionV1", {"scheme": "https://example.test/location/geohash", "value": "u173zq"}, "Location semantics are profile-defined, not hard-coded globally."),
    ]
    negative_structures = [
        structure("decimal-trailing-zero", "DecimalV1", {"coefficient": 1230, "scale": 2}, "Duplicate numeric spellings are forbidden.", "NON_CANONICAL_DECIMAL"),
        structure("decimal-zero-nonzero-scale", "DecimalV1", {"coefficient": 0, "scale": 2}, "Zero must use scale zero.", "NON_CANONICAL_DECIMAL"),
        structure("money-lowercase-currency", "ValueExpressionV1", {"kind": "monetary", "amount": {"coefficient": 1, "scale": 0}, "currency_code": "eur"}, "ISO-style currency codes are uppercase in this helper structure.", "INVALID_CURRENCY"),
        structure("temporal-offset-form", "TemporalConditionV1", {"not_before": "2026-08-24T00:00:00+00:00"}, "Offset variants are rejected by the core canonical timestamp profile.", "INVALID_TIMESTAMP"),
        structure("subject-two-targets", "SubjectBindingV1", {"uri": "urn:example:a", "record_ref": (0, bytes(32))}, "A subject binding has exactly one target.", "SUBJECT_TARGET_CARDINALITY"),
        structure("settlement-invalid-mode", "SettlementPreferenceV1", {"method": "https://example.test/settlement/bank", "mode": "maybe"}, "Settlement preference modes are closed in core-v1.", "INVALID_ENUM"),
    ]

    return {
        "format": "marketplace-record-representation-v1-conformance-vectors",
        "marketplace_semantic_base": BASE,
        "olp_reference_source_commit": olp_commit(),
        "note": "record/value fields use the OLP implementation-neutral conformance projection; this JSON file is not a Marketplace wire format",
        "positive_records": positive,
        "negative_records": negative,
        "positive_structures": positive_structures,
        "negative_structures": negative_structures,
    }


def main():
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    print(f"positive records: {len(data['positive_records'])}")
    print(f"negative records: {len(data['negative_records'])}")
    print(f"positive structures: {len(data['positive_structures'])}")
    print(f"negative structures: {len(data['negative_structures'])}")
    for item in data["positive_records"]:
        print(item["id"], item["expected_record_identity"])


if __name__ == "__main__":
    main()
