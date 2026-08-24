"""Non-normative Marketplace lifecycle and negotiation v1 helpers.

This module evaluates only Marketplace-specific semantics. OLP remains
responsible for immutable identity, proofs, evidence relationships, lifecycle
statement conformance, and identity/authority evidence.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from olp import RecordV1, verify_proof
from olp.encoding.record_identity import record_identity, record_identity_text
from olp.evidence import parse_relationship_record, record_ref as olp_record_ref
from olp.errors import ConformanceError, UnsupportedFeatureError
from olp.identity_authority_lifecycle_v1 import evaluate_authority_lifecycle
from olp.model.evidence import EvidenceKind, EvidenceRefV1
from olp.model.proof import OLPProof
from olp.model.verification import ResolvedVerificationMethod, Status

from marketplace_record_v1 import (
    BASE,
    PROPOSAL_PROFILE,
    TYPE_AGREEMENT,
    TYPE_EVENT,
    TYPE_INTENT,
    validate_market_record,
)
FORMATION_PROFILE = f"{BASE}/profile/agreement-formation-v1"
NEGOTIATION_SCOPE = f"{BASE}/scope/market-negotiation"
WITHDRAWAL_REASON = f"{BASE}/reason/intent-withdrawal"
EVENT_PROPOSAL_ACCEPTANCE = f"{BASE}/event/proposal-acceptance"
EVENT_PROPOSAL_DECLINE = f"{BASE}/event/proposal-decline"


class MarketplaceLifecycleError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplaceLifecycleError(code, message)


def _record_ref(record: RecordV1) -> EvidenceRefV1:
    return olp_record_ref(record)


def _record_ref_value(record: RecordV1) -> tuple[int, bytes]:
    return _record_ref(record).to_value()


def _record_ref_from_value(value: Any, path: str) -> EvidenceRefV1:
    try:
        ref = EvidenceRefV1.from_value(value)
    except ConformanceError as exc:
        fail("INVALID_RECORD_REF", f"{path}: {exc}")
    if ref.kind != EvidenceKind.RECORD:
        fail("WRONG_REFERENCE_KIND", f"{path} MUST reference an OLP Record")
    return ref
def is_proposal(record: RecordV1) -> bool:
    validate_market_record(record)
    return record.type == TYPE_INTENT and PROPOSAL_PROFILE in record.profiles


def _index_records(records: Iterable[RecordV1]) -> dict[bytes, RecordV1]:
    indexed: dict[bytes, RecordV1] = {}
    for record in records:
        validate_market_record(record)
        digest = record_identity(record)
        prior = indexed.get(digest)
        if prior is not None and prior != record:
            fail("IDENTITY_COLLISION_OR_CONFLICT", "conflicting Marketplace records share an identity")
        indexed[digest] = record
    return indexed


def _proposal_refs(record: RecordV1) -> tuple[EvidenceRefV1, ...]:
    if not is_proposal(record):
        fail("PROPOSAL_REQUIRED", "record MUST be a proposal-v1 MarketIntent")
    values = record.content.get("response_to", ())
    refs = tuple(_record_ref_from_value(item, "content.response_to[]") for item in values)
    if not refs:
        fail("PROPOSAL_RESPONSE_REQUIRED", "proposal-v1 requires response_to")
    return refs


def _identity_text_from_digest(digest: bytes) -> str:
    from olp.encoding.record_identity import record_identity_text

    return record_identity_text(digest)


def _detect_cycle(adjacency: Mapping[bytes, set[bytes]], nodes: set[bytes]) -> bool:
    indegree = {node: 0 for node in nodes}
    for source, targets in adjacency.items():
        if source not in nodes:
            continue
        for target in targets:
            if target in nodes:
                indegree[target] += 1
    queue = deque(sorted((node for node, degree in indegree.items() if degree == 0)))
    processed = 0
    while queue:
        node = queue.popleft()
        processed += 1
        for target in sorted(adjacency.get(node, ())):
            if target not in indegree:
                continue
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return processed != len(indegree)


def evaluate_negotiation(records: Iterable[RecordV1]) -> dict[str, Any]:
    """Build a deterministic local proposal graph without selecting a head."""
    indexed = _index_records(records)
    proposals = {digest: record for digest, record in indexed.items() if is_proposal(record)}
    parent_to_children: dict[bytes, set[bytes]] = defaultdict(set)
    child_to_proposal_parents: dict[bytes, set[bytes]] = defaultdict(set)
    missing: set[bytes] = set()
    classifications: dict[bytes, str] = {}

    for child_digest, proposal in proposals.items():
        resolved_proposal_parent = False
        unresolved_parent = False
        for ref in _proposal_refs(proposal):
            target = indexed.get(ref.identity_digest)
            if target is None:
                missing.add(ref.identity_digest)
                unresolved_parent = True
                continue
            if target.type != TYPE_INTENT:
                fail("PROPOSAL_RESPONSE_TARGET_TYPE", "proposal response_to MUST resolve to MarketIntent")
            parent_to_children[ref.identity_digest].add(child_digest)
            if is_proposal(target):
                resolved_proposal_parent = True
                child_to_proposal_parents[child_digest].add(ref.identity_digest)
        classifications[child_digest] = (
            "COUNTERPROPOSAL"
            if resolved_proposal_parent
            else "INDETERMINATE_MISSING_PARENT"
            if unresolved_parent
            else "PROPOSAL"
        )

    branches = {parent: children for parent, children in parent_to_children.items() if len(children) > 1}
    proposal_nodes = set(proposals)
    cycles = _detect_cycle(child_to_proposal_parents, proposal_nodes)
    return {
        "proposal_count": len(proposals),
        "proposal_classification": {
            _identity_text_from_digest(digest): classifications[digest]
            for digest in sorted(classifications)
        },
        "branches": {
            _identity_text_from_digest(parent): [
                _identity_text_from_digest(child) for child in sorted(children)
            ]
            for parent, children in sorted(branches.items())
        },
        "missing_response_targets": [
            _identity_text_from_digest(digest) for digest in sorted(missing)
        ],
        "completeness": "INCOMPLETE" if missing else "COMPLETE_FOR_SUPPLIED_RESPONSE_GRAPH",
        "cycles_detected": cycles,
        "negotiation_shape": "CONFLICTING_CYCLE" if cycles else "BRANCHED" if branches else "UNBRANCHED",
        "canonical_head": None,
    }


def validate_proposal_response_event(event_record: RecordV1, proposal: RecordV1) -> str:
    validate_market_record(event_record)
    if event_record.type != TYPE_EVENT:
        fail("MARKET_EVENT_REQUIRED", "proposal response evidence MUST be a MarketEvent")
    if not is_proposal(proposal):
        fail("PROPOSAL_REQUIRED", "proposal response event MUST target a proposal-v1 MarketIntent")
    event = event_record.content["event"]
    if event not in {EVENT_PROPOSAL_ACCEPTANCE, EVENT_PROPOSAL_DECLINE}:
        fail("UNSUPPORTED_NEGOTIATION_EVENT", "unsupported proposal response event")
    related = tuple(event_record.content.get("related_records", ()))
    if len(related) != 1:
        fail("PROPOSAL_RESPONSE_EVENT_TARGET", "proposal response event MUST reference exactly one proposal")
    ref = _record_ref_from_value(related[0], "content.related_records[0]")
    if ref != _record_ref(proposal):
        fail("PROPOSAL_RESPONSE_EVENT_TARGET", "proposal response event targets a different record")
    return "ACCEPTANCE_ASSERTED" if event == EVENT_PROPOSAL_ACCEPTANCE else "DECLINE_ASSERTED"
def withdrawal_statement(
    target: RecordV1,
    *,
    effective_at: str | None = None,
    sequence: int | None = None,
) -> tuple[Any, ...]:
    validate_market_record(target)
    if target.type != TYPE_INTENT:
        fail("INTENT_REQUIRED", "Marketplace withdrawal targets MarketIntent records only")
    return (
        "OLP-LIFECYCLE-STATUS",
        1,
        ("record", _record_ref_value(target)),
        "retire",
        target.content["issuer"]["principal"],
        effective_at,
        sequence,
        NEGOTIATION_SCOPE,
        None,
        WITHDRAWAL_REASON,
        {},
        (),
    )


def validate_withdrawal_statement(
    statement: Sequence[Any],
    target: RecordV1,
    *,
    evaluation_time: str | None = None,
) -> dict[str, Any]:
    validate_market_record(target)
    if target.type != TYPE_INTENT:
        fail("INTENT_REQUIRED", "Marketplace withdrawal targets MarketIntent records only")
    if not isinstance(statement, (list, tuple)) or len(statement) != 12:
        fail("MALFORMED_WITHDRAWAL", "withdrawal MUST be an OLP LifecycleStatusStatementV1")
    if statement[2] != ("record", _record_ref_value(target)) and statement[2] != ["record", list(_record_ref_value(target))]:
        fail("WITHDRAWAL_TARGET_MISMATCH", "withdrawal lifecycle target does not match MarketIntent")
    if statement[3] != "retire":
        fail("WITHDRAWAL_EVENT_MISMATCH", "Marketplace withdrawal MUST use OLP retire")
    if statement[4] != target.content["issuer"]["principal"]:
        fail("WITHDRAWAL_AUTHORITY_MISMATCH", "withdrawal statusAuthority MUST equal intent issuer principal")
    if statement[7] != NEGOTIATION_SCOPE:
        fail("WITHDRAWAL_SCOPE_MISMATCH", "withdrawal MUST use Marketplace negotiation scope")
    if statement[8] is not None:
        fail("WITHDRAWAL_NEXT_UPDATE_FORBIDDEN", "Marketplace withdrawal does not use nextUpdate")
    if statement[9] != WITHDRAWAL_REASON:
        fail("WITHDRAWAL_REASON_MISMATCH", "withdrawal MUST use the Marketplace withdrawal reason")
    if not isinstance(statement[10], Mapping) or statement[10]:
        fail("WITHDRAWAL_QUALIFIERS_FORBIDDEN", "core Marketplace withdrawal qualifiers MUST be empty")
    if not isinstance(statement[11], (list, tuple)) or len(statement[11]) != 0:
        fail("WITHDRAWAL_CRITICAL_FORBIDDEN", "core Marketplace withdrawal critical array MUST be empty")

    payload: dict[str, Any] = {
        "mode": "lifecycle",
        "target": ("record", _record_ref_value(target)),
        "statuses": (tuple(statement),),
        "required_scope": NEGOTIATION_SCOPE,
    }
    if evaluation_time is not None:
        payload["evaluation_time"] = evaluation_time
    result = evaluate_authority_lifecycle(payload)
    return {
        "marketplace_event": "WITHDRAWAL_ASSERTED",
        "target": record_identity_text(target),
        "authority": "NOT_EVALUATED",
        "operational_state": "INDETERMINATE",
        "olp_lifecycle": result,
    }


def _parse_timestamp(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError) as exc:
        fail("INVALID_TIMESTAMP", f"invalid Marketplace TimestampV1: {value!r}")
        raise AssertionError from exc


def evaluate_temporal_applicability(intent: RecordV1, evaluation_time: str) -> str:
    validate_market_record(intent)
    if intent.type != TYPE_INTENT:
        fail("INTENT_REQUIRED", "temporal applicability is defined here for MarketIntent")
    now = _parse_timestamp(evaluation_time)
    validity = intent.content.get("validity")
    if validity is None:
        return "NO_DECLARED_WINDOW"
    if "not_before" in validity and now < _parse_timestamp(validity["not_before"]):
        return "BEFORE_DECLARED_WINDOW"
    if "not_after" in validity and now >= _parse_timestamp(validity["not_after"]):
        return "AFTER_DECLARED_WINDOW"
    return "WITHIN_DECLARED_WINDOW"
@dataclass(frozen=True, slots=True)
class AssentEvidence:
    principal: str
    proof: OLPProof
    resolved_method: ResolvedVerificationMethod | None
    attribution_accepted: bool


def _proof_satisfies_assent(
    agreement: RecordV1,
    evidence: AssentEvidence,
    *,
    evaluation_time: datetime | None = None,
) -> tuple[bool, dict[str, str]]:
    result = verify_proof(
        agreement,
        evidence.proof,
        resolved_method=evidence.resolved_method,
        expected_purpose="assertion",
        evaluation_time=evaluation_time,
    )
    dimensions = {
        "record_binding": str(result.record_binding),
        "version_support": str(result.version_support),
        "cryptosuite_support": str(result.cryptosuite_support),
        "commitment_algorithm_support": str(result.commitment_algorithm_support),
        "critical_extension_status": str(result.critical_extension_status),
        "cryptographic_validity": str(result.cryptographic_validity),
        "purpose_status": str(result.purpose_status),
        "verification_method_resolution": str(result.verification_method_resolution),
        "verification_method_compatibility": str(result.verification_method_compatibility),
        "temporal_status": str(result.temporal_status),
        "attribution": "ACCEPTED" if evidence.attribution_accepted else "NOT_ACCEPTED",
    }
    ok = (
        result.conformance == Status.CONFORMING
        and result.version_support == Status.SUPPORTED
        and result.cryptosuite_support == Status.SUPPORTED
        and result.commitment_algorithm_support == Status.SUPPORTED
        and result.critical_extension_status == Status.UNDERSTOOD
        and result.record_binding == Status.VALID
        and result.cryptographic_validity == Status.VALID
        and result.purpose_status == Status.MATCH
        and result.verification_method_resolution == Status.RESOLVED
        and result.verification_method_compatibility == Status.COMPATIBLE
        and evidence.attribution_accepted
    )
    return ok, dimensions
def evaluate_agreement_formation(
    agreement: RecordV1,
    evidence: Iterable[AssentEvidence],
    *,
    evaluation_time: datetime | None = None,
) -> dict[str, Any]:
    validate_market_record(agreement)
    if agreement.type != TYPE_AGREEMENT:
        fail("AGREEMENT_REQUIRED", "formation evaluation requires MarketAgreement")
    if FORMATION_PROFILE not in agreement.profiles:
        fail("FORMATION_PROFILE_REQUIRED", "MarketAgreement MUST declare agreement-formation-v1")

    required = tuple(sorted({party["principal"] for party in agreement.content["parties"]}, key=lambda s: s.encode("utf-8")))
    covered: set[str] = set()
    observations: list[dict[str, Any]] = []
    extraneous: set[str] = set()

    for item in evidence:
        if item.principal not in required:
            extraneous.add(item.principal)
        ok, dimensions = _proof_satisfies_assent(agreement, item, evaluation_time=evaluation_time)
        if ok and item.principal in required:
            covered.add(item.principal)
        observations.append(
            {
                "principal": item.principal,
                "verification_method": item.proof.verificationMethod,
                "accepted_for_coverage": ok and item.principal in required,
                "dimensions": dimensions,
            }
        )

    missing = tuple(principal for principal in required if principal not in covered)
    return {
        "profile": FORMATION_PROFILE,
        "agreement": record_identity_text(agreement),
        "required_principals": list(required),
        "covered_principals": sorted(covered, key=lambda s: s.encode("utf-8")),
        "missing_principals": list(missing),
        "extraneous_principals": sorted(extraneous, key=lambda s: s.encode("utf-8")),
        "observations": observations,
        "formation_evidence": "EVIDENCE_SUFFICIENT_FOR_PROFILE" if not missing else "EVIDENCE_INCOMPLETE",
        "legal_enforceability": "NOT_EVALUATED",
        "universal_truth": False,
    }
def validate_amendment_relationship(
    amended: RecordV1,
    previous: RecordV1,
    relationship: RecordV1,
) -> dict[str, Any]:
    validate_market_record(amended)
    validate_market_record(previous)
    if amended.type != TYPE_AGREEMENT or previous.type != TYPE_AGREEMENT:
        fail("AGREEMENT_REQUIRED", "agreement amendment supersession requires two MarketAgreement records")
    try:
        statement = parse_relationship_record(relationship)
    except (ConformanceError, UnsupportedFeatureError) as exc:
        fail("INVALID_OLP_RELATIONSHIP", f"invalid OLP relationship: {exc}")
    if statement.relation_type != "supersedes":
        fail("AMENDMENT_RELATION_REQUIRED", "agreement amendment MUST use OLP supersedes")
    if statement.subject != _record_ref(amended):
        fail("AMENDMENT_SUBJECT_MISMATCH", "supersedes subject MUST be the amended agreement")
    if statement.objects != (_record_ref(previous),):
        fail("AMENDMENT_TARGET_MISMATCH", "core amendment supersedes exactly one previous agreement")
    return {
        "amended": record_identity_text(amended),
        "previous": record_identity_text(previous),
        "relationship": record_identity_text(relationship),
        "relation": "supersedes",
        "effective_amendment": "NOT_EVALUATED",
        "requires_new_formation_evidence": True,
    }


def evaluate_supersession(target: RecordV1, relationships: Iterable[RecordV1]) -> dict[str, Any]:
    validate_market_record(target)
    if target.type != TYPE_AGREEMENT:
        fail("AGREEMENT_REQUIRED", "supersession evaluation here targets MarketAgreement")
    target_ref = _record_ref(target)
    successors: set[EvidenceRefV1] = set()
    relationship_ids: list[str] = []
    for relationship in relationships:
        try:
            statement = parse_relationship_record(relationship)
        except (ConformanceError, UnsupportedFeatureError) as exc:
            fail("INVALID_OLP_RELATIONSHIP", f"invalid OLP relationship: {exc}")
        if statement.relation_type != "supersedes" or target_ref not in statement.objects:
            continue
        if statement.subject is None or statement.subject.kind != EvidenceKind.RECORD:
            fail("SUPERSESSION_SUBJECT_REQUIRED", "supersedes relationship requires a Record subject")
        successors.add(statement.subject)
        relationship_ids.append(record_identity_text(relationship))
    ordered = sorted(successors, key=lambda ref: ref.canonical_bytes())
    return {
        "target": record_identity_text(target),
        "successors": [_identity_text_from_digest(ref.identity_digest) for ref in ordered],
        "relationship_records": sorted(relationship_ids),
        "successor_count": len(ordered),
        "conflict": "MULTIPLE_SUCCESSORS" if len(ordered) > 1 else "NONE",
        "canonical_successor": None,
        "authority": "NOT_EVALUATED",
    }
def evaluate_acceptance_withdrawal_coexistence(
    proposal: RecordV1,
    response_event: RecordV1,
    withdrawal: Sequence[Any],
    *,
    evaluation_time: str | None = None,
) -> dict[str, Any]:
    """Preserve a response/withdrawal race without inventing latest-wins."""
    response = validate_proposal_response_event(response_event, proposal)
    withdrawal_result = validate_withdrawal_statement(
        withdrawal,
        proposal,
        evaluation_time=evaluation_time,
    )
    return {
        "proposal": record_identity_text(proposal),
        "response_evidence": response,
        "withdrawal_evidence": withdrawal_result["marketplace_event"],
        "chronology": "NOT_ESTABLISHED",
        "authority": "NOT_EVALUATED",
        "canonical_winner": None,
    }
