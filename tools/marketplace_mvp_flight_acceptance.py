"""Deterministic local product-flight acceptance over reviewed Marketplace semantics.

This tool composes existing listing, discovery, proposal, lifecycle, agreement
formation, and fulfillment helpers into one bounded two-user MVP journey.
It performs no network, filesystem persistence, database, settlement, or deployment.
"""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TOOLS = ROOT / "tools"
for path in (SRC, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from olp import RecordV1, create_proof
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text
from olp.evidence import record_ref
from olp.model.verification import ResolvedVerificationMethod

from marketplace.application import ExactDecimal, LocalMarketplaceApplication, ProductListingDraft, UNIT_ITEM
from marketplace.application.mvp import MarketplaceMvpFlightResult
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.reference.matching_v1 import evaluate_discovery, evaluate_match
from marketplace.reference.product_listing_v1 import (
    ACTION_SELL,
    PRODUCT_LISTING_PROFILE,
    build_product_listing_record,
)
from marketplace.reference.proposal_v1 import build_buyer_request_proposal_record
from marketplace.runtime import create_in_memory_runtime
from marketplace_record_v1 import BASE, CORE_PROFILE, TYPE_AGREEMENT, TYPE_EVENT, validate_market_record
from marketplace_lifecycle_v1 import (
    AssentEvidence,
    EVENT_PROPOSAL_ACCEPTANCE,
    FORMATION_PROFILE,
    evaluate_agreement_formation,
    validate_proposal_response_event,
)
from marketplace_fulfillment_v1 import (
    EVENT_COMMITMENT_ACCEPTANCE,
    EVENT_COMMITMENT_COMPLETION,
    EVENT_COMMITMENT_PERFORMANCE,
    FULFILLMENT_METHOD_CORE,
    OUTCOME_PERFORMANCE_CLAIMED_COMPLETE,
    EventEvidence,
    evaluate_commitment_fulfillment,
)


ACTION_BUY = f"{BASE}/action/buy"
COMMITMENT_ID = "seller-delivery"
SOURCE = "urn:open-layer-marketplace:mvp-flight"
STATES = ("CREATED", "PUBLISHED", "DISCOVERED", "ACCEPTED", "COMPLETED")
COMPLETED_AT = "2026-09-11T18:00:02Z"


class MarketplaceMvpFlightError(RuntimeError):
    """Stable flight failure without input/key reflection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class _CloseOnlyExpiryHandle:
    __slots__ = ()

    def cancel(self) -> None:
        return None


class _CloseOnlyExpiryScheduler:
    __slots__ = ()

    def schedule(self, _delay_seconds: float, _callback) -> _CloseOnlyExpiryHandle:
        return _CloseOnlyExpiryHandle()


def _public_bytes(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def _local_identity(key: Ed25519PrivateKey) -> tuple[str, str, bytes]:
    public_key = _public_bytes(key)
    principal = f"urn:open-layer-marketplace:mvp:identity:{sha256(public_key).hexdigest()}"
    return principal, f"{principal}#key-1", public_key


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_plain(item) for item in value)
    return value


def _sort_set(values: tuple[object, ...]) -> tuple[object, ...]:
    return tuple(sorted(values, key=olp_encode))


def _record(record_type: str, content: dict[str, object], profiles: tuple[str, ...] = (CORE_PROFILE,)) -> RecordV1:
    record = RecordV1(
        envelope_version=1,
        type=record_type,
        content=content,
        profiles=profiles,
    )
    validate_market_record(record)
    return record


def _proposal_acceptance(seller_principal: str, proposal: RecordV1) -> RecordV1:
    event = _record(
        TYPE_EVENT,
        {
            "version": 1,
            "issuer": {"principal": seller_principal},
            "event": EVENT_PROPOSAL_ACCEPTANCE,
            "related_records": (record_ref(proposal).to_value(),),
        },
    )
    if validate_proposal_response_event(event, proposal) != "ACCEPTANCE_ASSERTED":
        raise MarketplaceMvpFlightError("PROPOSAL_ACCEPTANCE_INVALID", "proposal acceptance did not validate")
    return event


def _agreement(
    *,
    seller_principal: str,
    buyer_principal: str,
    listing: RecordV1,
    proposal: RecordV1,
    acceptance: RecordV1,
) -> RecordV1:
    subjects = tuple(_plain(item) for item in listing.content["subjects"])
    seller_party = {"principal": seller_principal}
    buyer_party = {"principal": buyer_principal}
    commitment = {
        "id": COMMITMENT_ID,
        "party": seller_party,
        "action": {"id": ACTION_SELL},
        "subjects": subjects,
    }
    return _record(
        TYPE_AGREEMENT,
        {
            "version": 1,
            "parties": _sort_set((seller_party, buyer_party)),
            "subjects": subjects,
            "actions": _sort_set(({"id": ACTION_SELL}, {"id": ACTION_BUY})),
            "terms": _plain(listing.content["terms"]),
            "commitments": (commitment,),
            "source_records": _sort_set(
                (
                    record_ref(listing).to_value(),
                    record_ref(proposal).to_value(),
                    record_ref(acceptance).to_value(),
                )
            ),
        },
        (CORE_PROFILE, FORMATION_PROFILE),
    )


def _fulfillment_event(
    *,
    issuer: str,
    event_type: str,
    agreement: RecordV1,
    outcome: dict[str, object] | None = None,
) -> RecordV1:
    content: dict[str, object] = {
        "version": 1,
        "issuer": {"principal": issuer},
        "event": event_type,
        "commitment_refs": (
            {"record": record_ref(agreement).to_value(), "id": COMMITMENT_ID},
        ),
    }
    if outcome is not None:
        content["outcome"] = outcome
    return _record(TYPE_EVENT, content)


def run_marketplace_mvp_flight_acceptance() -> MarketplaceMvpFlightResult:
    """Execute one deterministic two-user local Marketplace product journey."""
    seller_key = Ed25519PrivateKey.from_private_bytes(bytes([0x31]) * 32)
    buyer_key = Ed25519PrivateKey.from_private_bytes(bytes([0x42]) * 32)
    seller_principal, seller_method, seller_public = _local_identity(seller_key)
    buyer_principal, buyer_method, buyer_public = _local_identity(buyer_key)

    listing = build_product_listing_record(
        ProductListingDraft(
            seller_principal=seller_principal,
            subject_uri="urn:open-layer-marketplace:mvp:item:city-bicycle",
            title="City bicycle",
            description="Deterministic local MVP flight listing.",
            consideration=ExactDecimal(12500, 2),
            currency_code="EUR",
            quantity=ExactDecimal(1, 0),
            unit_uri=UNIT_ITEM,
            latitude_e6=52_090_700,
            longitude_e6=5_121_400,
        )
    )

    runtime = create_in_memory_runtime(
        validate_record=validate_market_record,
        record_identity_text=record_identity_text,
        evaluate_discovery=evaluate_discovery,
        evaluate_match=evaluate_match,
        scheduler=_CloseOnlyExpiryScheduler(),
    )
    with runtime:
        app = LocalMarketplaceApplication(node=runtime.node, discovery=runtime.discovery, source=SOURCE)

        listing_published = app.publish(listing)
        stored_listing = app.get(listing_published.record_id)
        listing_integrity_verified = (
            type(stored_listing) is RecordV1
            and record_identity_text(stored_listing) == listing_published.record_id
        )
        if not listing_integrity_verified:
            raise MarketplaceMvpFlightError("LISTING_INTEGRITY_INVALID", "published listing identity did not replay")

        discovery = app.search(
            {
                "version": 1,
                "profiles_all": [PRODUCT_LISTING_PROFILE],
                "action_ids_any": [ACTION_SELL],
                "subject_uris_any": ["urn:open-layer-marketplace:mvp:item:city-bicycle"],
            },
            completeness="PARTIAL_SOURCE",
            freshness="FRESH",
            max_records=8,
        )
        if discovery.record_ids != (listing_published.record_id,):
            raise MarketplaceMvpFlightError("DISCOVERY_INVALID", "buyer did not discover the exact listing")

        proposal = build_buyer_request_proposal_record(
            BuyerRequestProposalDraft(
                parent_record_id=listing_published.record_id,
                buyer_principal=buyer_principal,
                subject_uri="urn:open-layer-marketplace:mvp:item:city-bicycle",
                action_uri=ACTION_BUY,
            )
        )
        proposal_published = app.publish(proposal)

        proposal_acceptance = _proposal_acceptance(seller_principal, proposal)
        proposal_acceptance_published = app.publish(proposal_acceptance)

        agreement = _agreement(
            seller_principal=seller_principal,
            buyer_principal=buyer_principal,
            listing=listing,
            proposal=proposal,
            acceptance=proposal_acceptance,
        )
        seller_proof = create_proof(
            agreement,
            proof_purpose="assertion",
            verification_method=seller_method,
            private_key=seller_key,
            created="2026-09-11T18:00:00Z",
        )
        buyer_proof = create_proof(
            agreement,
            proof_purpose="assertion",
            verification_method=buyer_method,
            private_key=buyer_key,
            created="2026-09-11T18:00:01Z",
        )
        formation = evaluate_agreement_formation(
            agreement,
            (
                AssentEvidence(
                    seller_principal,
                    seller_proof,
                    ResolvedVerificationMethod(seller_method, "Ed25519", seller_public),
                    True,
                ),
                AssentEvidence(
                    buyer_principal,
                    buyer_proof,
                    ResolvedVerificationMethod(buyer_method, "Ed25519", buyer_public),
                    True,
                ),
            ),
        )
        if formation["formation_evidence"] != "EVIDENCE_SUFFICIENT_FOR_PROFILE":
            raise MarketplaceMvpFlightError("AGREEMENT_FORMATION_INVALID", "agreement assent was incomplete")
        agreement_published = app.publish(agreement)

        performance = _fulfillment_event(
            issuer=seller_principal,
            event_type=EVENT_COMMITMENT_PERFORMANCE,
            agreement=agreement,
            outcome={"type": OUTCOME_PERFORMANCE_CLAIMED_COMPLETE},
        )
        fulfillment_acceptance = _fulfillment_event(
            issuer=buyer_principal,
            event_type=EVENT_COMMITMENT_ACCEPTANCE,
            agreement=agreement,
        )
        completion = _fulfillment_event(
            issuer=seller_principal,
            event_type=EVENT_COMMITMENT_COMPLETION,
            agreement=agreement,
        )
        performance_published = app.publish(performance)
        fulfillment_acceptance_published = app.publish(fulfillment_acceptance)
        completion_published = app.publish(completion)

        fulfillment = evaluate_commitment_fulfillment(
            agreement,
            COMMITMENT_ID,
            (
                EventEvidence(performance, True, True),
                EventEvidence(fulfillment_acceptance, True, True),
                EventEvidence(completion, True, True),
            ),
            method=FULFILLMENT_METHOD_CORE,
            require_acceptance=True,
        )
        if fulfillment["conclusion"] != "FULFILLED_UNDER_METHOD":
            raise MarketplaceMvpFlightError("FULFILLMENT_INVALID", "completion evidence was insufficient")

        return MarketplaceMvpFlightResult(
            seller_principal=seller_principal,
            buyer_principal=buyer_principal,
            listing_record_id=listing_published.record_id,
            proposal_record_id=proposal_published.record_id,
            proposal_acceptance_record_id=proposal_acceptance_published.record_id,
            agreement_record_id=agreement_published.record_id,
            performance_record_id=performance_published.record_id,
            fulfillment_acceptance_record_id=fulfillment_acceptance_published.record_id,
            completion_record_id=completion_published.record_id,
            listing_integrity_verified=True,
            agreement_formation=formation["formation_evidence"],
            fulfillment_conclusion=fulfillment["conclusion"],
            states=STATES,
            final_state="COMPLETED",
            completed_at=COMPLETED_AT,
            universal_truth=bool(fulfillment["universal_truth"]),
            payment_or_settlement_evaluated=bool(fulfillment["payment_or_settlement_evaluated"]),
        )


def main() -> int:
    result = run_marketplace_mvp_flight_acceptance()
    print(
        json.dumps(
            {
                "profile": "MARKETPLACE_MVP_FLIGHT_ACCEPTANCE_V1",
                "states": list(result.states),
                "final_state": result.final_state,
                "completed_at": result.completed_at,
                "seller_principal": result.seller_principal,
                "buyer_principal": result.buyer_principal,
                "listing_record_id": result.listing_record_id,
                "agreement_record_id": result.agreement_record_id,
                "listing_integrity_verified": result.listing_integrity_verified,
                "agreement_formation": result.agreement_formation,
                "fulfillment_conclusion": result.fulfillment_conclusion,
                "audit_record_ids": list(result.audit_record_ids),
                "universal_truth": result.universal_truth,
                "payment_or_settlement_evaluated": result.payment_or_settlement_evaluated,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
