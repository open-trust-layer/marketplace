"""Generate Marketplace lifecycle and negotiation v1 conformance vectors."""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from olp import RecordV1, create_proof
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity, record_identity_text
from olp.evidence import record_ref, relationship_record
from olp.model.proof import OLPProof
from olp.model.verification import ResolvedVerificationMethod
from olp.transport import project_abstract

from marketplace_record_v1 import BASE, CORE_PROFILE, TYPE_AGREEMENT, TYPE_EVENT, TYPE_INTENT, validate_market_record
from marketplace_lifecycle_v1 import (
    AssentEvidence,
    EVENT_PROPOSAL_ACCEPTANCE,
    EVENT_PROPOSAL_DECLINE,
    FORMATION_PROFILE,
    NEGOTIATION_SCOPE,
    WITHDRAWAL_REASON,
    evaluate_acceptance_withdrawal_coexistence,
    evaluate_agreement_formation,
    evaluate_negotiation,
    evaluate_supersession,
    evaluate_temporal_applicability,
    validate_amendment_relationship,
    validate_proposal_response_event,
    validate_withdrawal_statement,
    withdrawal_statement,
)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "lifecycle-negotiation-v1.json"


def olp_commit() -> str:
    import olp

    repo = Path(olp.__file__).resolve().parents[2]
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def sort_set(values):
    return tuple(sorted(tuple(values), key=olp_encode))


def market_record(record_type: str, content: dict, profiles: tuple[str, ...]) -> RecordV1:
    record = RecordV1(envelope_version=1, type=record_type, content=content, profiles=profiles)
    validate_market_record(record)
    return record


def record_mapping(record: RecordV1) -> dict:
    value = {
        "envelope_version": record.envelope_version,
        "type": record.type,
        "content": record.content,
    }
    if record.semantic_bindings:
        value["semantic_bindings"] = record.semantic_bindings
    if record.profiles:
        value["profiles"] = record.profiles
    if record.relationships:
        value["relationships"] = record.relationships
    if record.extensions:
        value["extensions"] = record.extensions
    return value


def proof_mapping(proof: OLPProof) -> dict:
    value = {
        "type": proof.type,
        "version": proof.version,
        "cryptosuite": proof.cryptosuite,
        "proofPurpose": proof.proofPurpose,
        "verificationMethod": proof.verificationMethod,
        "recordCommitment": (proof.recordCommitment.algorithm, proof.recordCommitment.digest),
        "proofValue": proof.proofValue,
    }
    for key in ("created", "expires", "domain", "challenge", "nonce"):
        item = getattr(proof, key)
        if item is not None:
            value[key] = item
    if proof.critical:
        value["critical"] = proof.critical
    if proof.extensions:
        value["extensions"] = proof.extensions
    return value


def projected_record(record: RecordV1):
    return project_abstract(record_mapping(record))


def projected_proof(proof: OLPProof):
    return project_abstract(proof_mapping(proof))


def public_bytes(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def expected_subset(result: dict, *keys: str) -> dict:
    return {key: result[key] for key in keys}


def build() -> dict:
    from marketplace_record_v1 import PROPOSAL_PROFILE

    alice = {"principal": "did:example:alice", "role": "https://example.test/roles/requester"}
    bob = {"principal": "did:example:bob", "role": "https://example.test/roles/provider"}
    subject = {"uri": "urn:example:software-issue:42"}
    action = {"id": "https://example.test/actions/fix"}
    reward_500 = {"kind": "monetary", "amount": {"coefficient": 500, "scale": 0}, "currency_code": "EUR"}
    reward_550 = {"kind": "monetary", "amount": {"coefficient": 550, "scale": 0}, "currency_code": "EUR"}
    reward_600 = {"kind": "monetary", "amount": {"coefficient": 600, "scale": 0}, "currency_code": "EUR"}
    base = market_record(
        TYPE_INTENT,
        {
            "version": 1,
            "issuer": alice,
            "subjects": (subject,),
            "action": action,
            "terms": {"https://example.test/terms/reward": reward_500},
            "validity": {"not_after": "2026-09-01T00:00:00Z"},
        },
        (CORE_PROFILE,),
    )
    bob_commitment = {"id": "c1", "party": bob, "action": action, "subjects": (subject,)}
    proposal = market_record(
        TYPE_INTENT,
        {
            "version": 1,
            "issuer": bob,
            "subjects": (subject,),
            "action": action,
            "terms": {"https://example.test/terms/reward": reward_500},
            "commitments": (bob_commitment,),
            "response_to": (record_ref(base).to_value(),),
        },
        (CORE_PROFILE, PROPOSAL_PROFILE),
    )
    counter = market_record(
        TYPE_INTENT,
        {
            "version": 1,
            "issuer": alice,
            "subjects": (subject,),
            "action": action,
            "terms": {"https://example.test/terms/reward": reward_550},
            "response_to": (record_ref(proposal).to_value(),),
        },
        (CORE_PROFILE, PROPOSAL_PROFILE),
    )
    alternate = market_record(
        TYPE_INTENT,
        {
            "version": 1,
            "issuer": bob,
            "subjects": (subject,),
            "action": action,
            "terms": {"https://example.test/terms/reward": reward_600},
            "commitments": (bob_commitment,),
            "response_to": (record_ref(base).to_value(),),
        },
        (CORE_PROFILE, PROPOSAL_PROFILE),
    )

    acceptance = market_record(
        TYPE_EVENT,
        {
            "version": 1,
            "issuer": alice,
            "event": EVENT_PROPOSAL_ACCEPTANCE,
            "related_records": (record_ref(proposal).to_value(),),
        },
        (CORE_PROFILE,),
    )
    decline = market_record(
        TYPE_EVENT,
        {
            "version": 1,
            "issuer": alice,
            "event": EVENT_PROPOSAL_DECLINE,
            "related_records": (record_ref(alternate).to_value(),),
        },
        (CORE_PROFILE,),
    )

    parties = sort_set((alice, bob))
    sources = sort_set((record_ref(base).to_value(), record_ref(proposal).to_value()))
    agreement = market_record(
        TYPE_AGREEMENT,
        {
            "version": 1,
            "parties": parties,
            "subjects": (subject,),
            "actions": (action,),
            "terms": {"https://example.test/terms/reward": reward_500},
            "commitments": (bob_commitment,),
            "source_records": sources,
        },
        (CORE_PROFILE, FORMATION_PROFILE),
    )
    alice_key = Ed25519PrivateKey.from_private_bytes(bytes([0x11]) * 32)
    bob_key = Ed25519PrivateKey.from_private_bytes(bytes([0x22]) * 32)
    alice_proof = create_proof(
        agreement,
        proof_purpose="assertion",
        verification_method="did:example:alice#key-1",
        private_key=alice_key,
        created="2026-08-24T00:00:00Z",
    )
    bob_proof = create_proof(
        agreement,
        proof_purpose="assertion",
        verification_method="did:example:bob#key-1",
        private_key=bob_key,
        created="2026-08-24T00:00:01Z",
    )
    bob_wrong_purpose = create_proof(
        agreement,
        proof_purpose="authorization",
        verification_method="did:example:bob#key-1",
        private_key=bob_key,
        created="2026-08-24T00:00:02Z",
    )
    unknown_critical = "https://example.test/proof/critical-formation-semantics"
    bob_unknown_critical = create_proof(
        agreement,
        proof_purpose="assertion",
        verification_method="did:example:bob#key-1",
        private_key=bob_key,
        created="2026-08-24T00:00:03Z",
        extensions={unknown_critical: True},
        critical=(unknown_critical,),
    )
    alice_method = ResolvedVerificationMethod(alice_proof.verificationMethod, "Ed25519", public_bytes(alice_key))
    bob_method = ResolvedVerificationMethod(bob_proof.verificationMethod, "Ed25519", public_bytes(bob_key))

    formation_full = evaluate_agreement_formation(
        agreement,
        (
            AssentEvidence(alice["principal"], alice_proof, alice_method, True),
            AssentEvidence(bob["principal"], bob_proof, bob_method, True),
        ),
    )
    formation_partial = evaluate_agreement_formation(
        agreement,
        (AssentEvidence(bob["principal"], bob_proof, bob_method, True),),
    )
    formation_bad_purpose = evaluate_agreement_formation(
        agreement,
        (
            AssentEvidence(alice["principal"], alice_proof, alice_method, True),
            AssentEvidence(bob["principal"], bob_wrong_purpose, bob_method, True),
        ),
    )
    formation_unknown_critical = evaluate_agreement_formation(
        agreement,
        (
            AssentEvidence(alice["principal"], alice_proof, alice_method, True),
            AssentEvidence(bob["principal"], bob_unknown_critical, bob_method, True),
        ),
    )
    amended = market_record(
        TYPE_AGREEMENT,
        {
            **dict(agreement.content),
            "terms": {"https://example.test/terms/reward": reward_550},
        },
        (CORE_PROFILE, FORMATION_PROFILE),
    )
    competing_amendment = market_record(
        TYPE_AGREEMENT,
        {
            **dict(agreement.content),
            "terms": {"https://example.test/terms/reward": reward_600},
        },
        (CORE_PROFILE, FORMATION_PROFILE),
    )
    amendment_rel = relationship_record(
        "supersedes",
        subject=record_ref(amended),
        objects=(record_ref(agreement),),
    )
    competing_rel = relationship_record(
        "supersedes",
        subject=record_ref(competing_amendment),
        objects=(record_ref(agreement),),
    )
    correction_rel = relationship_record(
        "corrects",
        subject=record_ref(amended),
        objects=(record_ref(agreement),),
    )

    withdrawal = withdrawal_statement(
        proposal,
        effective_at="2026-08-24T00:30:00Z",
        sequence=1,
    )
    withdrawal_result = validate_withdrawal_statement(
        withdrawal,
        proposal,
        evaluation_time="2026-08-24T01:00:00Z",
    )
    def assent_item(principal: str, proof: OLPProof, key: Ed25519PrivateKey, accepted: bool = True) -> dict:
        return {
            "principal": principal,
            "proof": projected_proof(proof),
            "public_key": project_abstract(public_bytes(key)),
            "attribution_accepted": accepted,
        }

    linear_result = evaluate_negotiation((base, proposal, counter))
    branch_result = evaluate_negotiation((base, proposal, alternate))
    acceptance_result = validate_proposal_response_event(acceptance, proposal)
    decline_result = validate_proposal_response_event(decline, alternate)
    amendment_result = validate_amendment_relationship(amended, agreement, amendment_rel)
    supersession_result = evaluate_supersession(agreement, (amendment_rel, competing_rel))

    unresolved = market_record(
        TYPE_INTENT,
        {
            "version": 1,
            "issuer": bob,
            "subjects": (subject,),
            "action": action,
            "terms": {},
            "response_to": ((0, bytes([0x77]) * 32),),
        },
        (CORE_PROFILE, PROPOSAL_PROFILE),
    )
    unresolved_result = evaluate_negotiation((unresolved,))
    race_result = evaluate_acceptance_withdrawal_coexistence(
        proposal, acceptance, withdrawal, evaluation_time="2026-08-24T01:00:00Z"
    )

    cases: list[dict] = [
        {
            "id": "proposal-chain-counterproposal",
            "kind": "negotiation",
            "records": [projected_record(item) for item in (base, proposal, counter)],
            "expected": expected_subset(linear_result, "proposal_count", "negotiation_shape", "completeness", "cycles_detected", "canonical_head"),
        },
        {
            "id": "proposal-branch-preserved",
            "kind": "negotiation",
            "records": [projected_record(item) for item in (base, proposal, alternate)],
            "expected": expected_subset(branch_result, "proposal_count", "negotiation_shape", "completeness", "canonical_head"),
        },
        {
            "id": "proposal-unresolved-parent-is-incomplete",
            "kind": "negotiation",
            "records": [projected_record(unresolved)],
            "expected": expected_subset(unresolved_result, "proposal_count", "proposal_classification", "completeness", "missing_response_targets", "canonical_head"),
        },
        {
            "id": "proposal-acceptance-event",
            "kind": "proposal_response_event",
            "event": projected_record(acceptance),
            "proposal": projected_record(proposal),
            "expected": acceptance_result,
        },
        {
            "id": "proposal-decline-event",
            "kind": "proposal_response_event",
            "event": projected_record(decline),
            "proposal": projected_record(alternate),
            "expected": decline_result,
        },
        {
            "id": "withdrawal-retire-scope",
            "kind": "withdrawal",
            "target": projected_record(proposal),
            "statement": project_abstract(withdrawal),
            "evaluation_time": "2026-08-24T01:00:00Z",
            "expected": {
                "marketplace_event": withdrawal_result["marketplace_event"],
                "operational_state": withdrawal_result["operational_state"],
                "olp_event": withdrawal_result["olp_lifecycle"]["events"][0]["event"],
                "effective": withdrawal_result["olp_lifecycle"]["events"][0]["effective"],
            },
        },
        {
            "id": "acceptance-withdrawal-race-preserved",
            "kind": "acceptance_withdrawal_race",
            "proposal": projected_record(proposal),
            "response_event": projected_record(acceptance),
            "statement": project_abstract(withdrawal),
            "evaluation_time": "2026-08-24T01:00:00Z",
            "expected": expected_subset(race_result, "response_evidence", "withdrawal_evidence", "chronology", "authority", "canonical_winner"),
        },
        {
            "id": "intent-validity-within-window",
            "kind": "temporal",
            "intent": projected_record(base),
            "evaluation_time": "2026-08-31T23:59:59Z",
            "expected": evaluate_temporal_applicability(base, "2026-08-31T23:59:59Z"),
        },
        {
            "id": "intent-validity-half-open-end",
            "kind": "temporal",
            "intent": projected_record(base),
            "evaluation_time": "2026-09-01T00:00:00Z",
            "expected": evaluate_temporal_applicability(base, "2026-09-01T00:00:00Z"),
        },
        {
            "id": "agreement-formation-complete",
            "kind": "formation",
            "agreement": projected_record(agreement),
            "assent": [
                assent_item(alice["principal"], alice_proof, alice_key),
                assent_item(bob["principal"], bob_proof, bob_key),
            ],
            "expected": expected_subset(formation_full, "formation_evidence", "missing_principals", "legal_enforceability", "universal_truth"),
        },
        {
            "id": "agreement-formation-incomplete",
            "kind": "formation",
            "agreement": projected_record(agreement),
            "assent": [assent_item(bob["principal"], bob_proof, bob_key)],
            "expected": expected_subset(formation_partial, "formation_evidence", "missing_principals", "universal_truth"),
        },
        {
            "id": "agreement-formation-wrong-purpose",
            "kind": "formation",
            "agreement": projected_record(agreement),
            "assent": [
                assent_item(alice["principal"], alice_proof, alice_key),
                assent_item(bob["principal"], bob_wrong_purpose, bob_key),
            ],
            "expected": expected_subset(formation_bad_purpose, "formation_evidence", "missing_principals", "universal_truth"),
        },
        {
            "id": "agreement-formation-unsupported-critical-proof",
            "kind": "formation",
            "agreement": projected_record(agreement),
            "assent": [
                assent_item(alice["principal"], alice_proof, alice_key),
                assent_item(bob["principal"], bob_unknown_critical, bob_key),
            ],
            "expected": expected_subset(formation_unknown_critical, "formation_evidence", "missing_principals", "universal_truth"),
        },
        {
            "id": "agreement-amendment-supersedes",
            "kind": "amendment",
            "amended": projected_record(amended),
            "previous": projected_record(agreement),
            "relationship": projected_record(amendment_rel),
            "expected": expected_subset(amendment_result, "relation", "effective_amendment", "requires_new_formation_evidence"),
        },
        {
            "id": "multiple-agreement-successors",
            "kind": "supersession",
            "target": projected_record(agreement),
            "relationships": [projected_record(amendment_rel), projected_record(competing_rel)],
            "expected": expected_subset(supersession_result, "successor_count", "conflict", "canonical_successor", "authority"),
        },
    ]
    from olp.identity_authority_lifecycle_v1 import evaluate_authority_lifecycle

    resume_same_sequence = list(withdrawal)
    resume_same_sequence[3] = "resume"
    resume_same_sequence[9] = None
    sequence_conflict = evaluate_authority_lifecycle(
        {
            "mode": "lifecycle",
            "target": ("record", record_ref(proposal).to_value()),
            "statuses": (withdrawal, tuple(resume_same_sequence)),
            "required_scope": NEGOTIATION_SCOPE,
            "evaluation_time": "2026-08-24T01:00:00Z",
        }
    )
    cases.append(
        {
            "id": "olp-lifecycle-sequence-conflict-preserved",
            "kind": "olp_lifecycle_conflict",
            "target": project_abstract(("record", record_ref(proposal).to_value())),
            "statuses": [project_abstract(withdrawal), project_abstract(tuple(resume_same_sequence))],
            "evaluation_time": "2026-08-24T01:00:00Z",
            "expected": {
                "conflicts": sequence_conflict["conflicts"],
                "operational_state": sequence_conflict["operational_state"],
                "absence_is_active": sequence_conflict["absence_is_active"],
            },
        }
    )

    bad_target_proposal = market_record(
        TYPE_INTENT,
        {
            "version": 1,
            "issuer": bob,
            "subjects": (subject,),
            "action": action,
            "terms": {},
            "response_to": (record_ref(acceptance).to_value(),),
        },
        (CORE_PROFILE, PROPOSAL_PROFILE),
    )
    two_refs = sort_set((record_ref(proposal).to_value(), record_ref(alternate).to_value()))
    bad_response_event = market_record(
        TYPE_EVENT,
        {"version": 1, "issuer": alice, "event": EVENT_PROPOSAL_ACCEPTANCE, "related_records": two_refs},
        (CORE_PROFILE,),
    )
    wrong_event = list(withdrawal)
    wrong_event[3] = "revoke"
    wrong_authority = list(withdrawal)
    wrong_authority[4] = "did:example:mallory"
    wrong_scope = list(withdrawal)
    wrong_scope[7] = "https://example.test/scope/other"
    wrong_next_update = list(withdrawal)
    wrong_next_update[8] = "2026-08-25T00:00:00Z"
    wrong_reason = list(withdrawal)
    wrong_reason[9] = "https://example.test/reason/other"

    agreement_no_formation = market_record(
        TYPE_AGREEMENT,
        dict(agreement.content),
        (CORE_PROFILE,),
    )

    negative_cases = [
        {
            "id": "proposal-response-target-not-intent",
            "kind": "negotiation",
            "records": [projected_record(item) for item in (base, acceptance, bad_target_proposal)],
            "expected_error": "PROPOSAL_RESPONSE_TARGET_TYPE",
        },
        {
            "id": "proposal-response-event-two-targets",
            "kind": "proposal_response_event",
            "event": projected_record(bad_response_event),
            "proposal": projected_record(proposal),
            "expected_error": "PROPOSAL_RESPONSE_EVENT_TARGET",
        },
        {
            "id": "proposal-response-event-target-mismatch",
            "kind": "proposal_response_event",
            "event": projected_record(acceptance),
            "proposal": projected_record(alternate),
            "expected_error": "PROPOSAL_RESPONSE_EVENT_TARGET",
        },
        {
            "id": "withdrawal-wrong-event",
            "kind": "withdrawal",
            "target": projected_record(proposal),
            "statement": project_abstract(tuple(wrong_event)),
            "expected_error": "WITHDRAWAL_EVENT_MISMATCH",
        },
        {
            "id": "withdrawal-wrong-authority",
            "kind": "withdrawal",
            "target": projected_record(proposal),
            "statement": project_abstract(tuple(wrong_authority)),
            "expected_error": "WITHDRAWAL_AUTHORITY_MISMATCH",
        },
        {
            "id": "withdrawal-wrong-scope",
            "kind": "withdrawal",
            "target": projected_record(proposal),
            "statement": project_abstract(tuple(wrong_scope)),
            "expected_error": "WITHDRAWAL_SCOPE_MISMATCH",
        },
        {
            "id": "withdrawal-next-update-forbidden",
            "kind": "withdrawal",
            "target": projected_record(proposal),
            "statement": project_abstract(tuple(wrong_next_update)),
            "expected_error": "WITHDRAWAL_NEXT_UPDATE_FORBIDDEN",
        },
        {
            "id": "withdrawal-wrong-reason",
            "kind": "withdrawal",
            "target": projected_record(proposal),
            "statement": project_abstract(tuple(wrong_reason)),
            "expected_error": "WITHDRAWAL_REASON_MISMATCH",
        },
        {
            "id": "agreement-formation-profile-missing",
            "kind": "formation",
            "agreement": projected_record(agreement_no_formation),
            "assent": [],
            "expected_error": "FORMATION_PROFILE_REQUIRED",
        },
        {
            "id": "agreement-amendment-corrects-not-supersedes",
            "kind": "amendment",
            "amended": projected_record(amended),
            "previous": projected_record(agreement),
            "relationship": projected_record(correction_rel),
            "expected_error": "AMENDMENT_RELATION_REQUIRED",
        },
    ]

    return {
        "format": "marketplace-lifecycle-negotiation-v1-conformance-vectors",
        "marketplace_semantic_base": BASE,
        "olp_reference_source_commit": olp_commit(),
        "note": "record/proof/value fields use OLP implementation-neutral conformance projection; this JSON file is not a Marketplace wire format",
        "record_identities": {
            "base_intent": record_identity_text(base),
            "proposal": record_identity_text(proposal),
            "counterproposal": record_identity_text(counter),
            "alternate_proposal": record_identity_text(alternate),
            "agreement": record_identity_text(agreement),
            "amended_agreement": record_identity_text(amended),
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
