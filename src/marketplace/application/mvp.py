"""Bounded result contract for the local Marketplace MVP product flight."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


MVP_FLIGHT_PROFILE: Final = "MARKETPLACE_MVP_FLIGHT_ACCEPTANCE_V1"
_MAX_TEXT_CHARS: Final = 4096
_MAX_RECORD_ID_CHARS: Final = 512
_MAX_STATES: Final = 16
_MAX_AUDIT_RECORDS: Final = 32


def _require_text(value: object, label: str, *, maximum: int = _MAX_TEXT_CHARS) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise ValueError(f"{label} must be bounded non-empty exact text")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{label} contains control characters")
    return value


def _require_record_id(value: object, label: str) -> str:
    return _require_text(value, label, maximum=_MAX_RECORD_ID_CHARS)


@dataclass(frozen=True, slots=True)
class MarketplaceMvpFlightResult:
    seller_principal: str
    buyer_principal: str
    listing_record_id: str
    proposal_record_id: str
    proposal_acceptance_record_id: str
    agreement_record_id: str
    performance_record_id: str
    fulfillment_acceptance_record_id: str
    completion_record_id: str
    listing_integrity_verified: bool
    agreement_formation: str
    fulfillment_conclusion: str
    states: tuple[str, ...]
    final_state: str
    completed_at: str
    universal_truth: bool
    payment_or_settlement_evaluated: bool

    def __post_init__(self) -> None:
        _require_text(self.seller_principal, "seller_principal")
        _require_text(self.buyer_principal, "buyer_principal")
        if self.seller_principal == self.buyer_principal:
            raise ValueError("MVP flight participants must be distinct")
        for label, value in (
            ("listing_record_id", self.listing_record_id),
            ("proposal_record_id", self.proposal_record_id),
            ("proposal_acceptance_record_id", self.proposal_acceptance_record_id),
            ("agreement_record_id", self.agreement_record_id),
            ("performance_record_id", self.performance_record_id),
            ("fulfillment_acceptance_record_id", self.fulfillment_acceptance_record_id),
            ("completion_record_id", self.completion_record_id),
        ):
            _require_record_id(value, label)
        if type(self.listing_integrity_verified) is not bool:
            raise TypeError("listing_integrity_verified must be exact bool")
        if type(self.universal_truth) is not bool:
            raise TypeError("universal_truth must be exact bool")
        if type(self.payment_or_settlement_evaluated) is not bool:
            raise TypeError("payment_or_settlement_evaluated must be exact bool")
        _require_text(self.agreement_formation, "agreement_formation")
        _require_text(self.fulfillment_conclusion, "fulfillment_conclusion")
        _require_text(self.final_state, "final_state")
        _require_text(self.completed_at, "completed_at", maximum=128)
        if type(self.states) is not tuple or not self.states or len(self.states) > _MAX_STATES:
            raise TypeError("states must be a bounded exact tuple")
        for state in self.states:
            _require_text(state, "state", maximum=64)
        if self.final_state != self.states[-1]:
            raise ValueError("final_state must equal the last lifecycle state")

    @property
    def audit_record_ids(self) -> tuple[str, ...]:
        values = (
            self.listing_record_id,
            self.proposal_record_id,
            self.proposal_acceptance_record_id,
            self.agreement_record_id,
            self.performance_record_id,
            self.fulfillment_acceptance_record_id,
            self.completion_record_id,
        )
        if len(values) > _MAX_AUDIT_RECORDS or len(set(values)) != len(values):
            raise ValueError("audit record identities must be bounded and unique")
        return values

    def to_document(self) -> dict[str, object]:
        return {
            "profile": MVP_FLIGHT_PROFILE,
            "participants": {
                "seller": self.seller_principal,
                "buyer": self.buyer_principal,
            },
            "states": list(self.states),
            "final_state": self.final_state,
            "completed_at": self.completed_at,
            "records": {
                "listing": self.listing_record_id,
                "proposal": self.proposal_record_id,
                "proposal_acceptance": self.proposal_acceptance_record_id,
                "agreement": self.agreement_record_id,
                "performance": self.performance_record_id,
                "fulfillment_acceptance": self.fulfillment_acceptance_record_id,
                "completion": self.completion_record_id,
            },
            "verification": {
                "listing_integrity_verified": self.listing_integrity_verified,
                "agreement_formation": self.agreement_formation,
                "fulfillment_conclusion": self.fulfillment_conclusion,
                "universal_truth": self.universal_truth,
                "payment_or_settlement_evaluated": self.payment_or_settlement_evaluated,
            },
            "audit_record_ids": list(self.audit_record_ids),
        }


__all__ = [
    "MVP_FLIGHT_PROFILE",
    "MarketplaceMvpFlightResult",
]
