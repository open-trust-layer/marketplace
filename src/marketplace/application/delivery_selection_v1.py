"""Proposal-only physical delivery responsibility, outside OLP evidence semantics.

This pure application adapter selects a proposed delivery executor. It never
assigns a courier, publishes an Agreement, dispatches, records performance,
handles addresses, invokes a network service, or authorizes payment.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


SELLER_DELIVERY = "seller_delivery"
INDEPENDENT_COURIER = "independent_courier"
PARTNER_CARRIER = "partner_carrier"
SELLER_DELIVERY_COMMITMENT = "seller-delivery"

_MODES = frozenset((SELLER_DELIVERY, INDEPENDENT_COURIER, PARTNER_CARRIER))
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_MAX_PRINCIPAL_BYTES = 2048


class DeliverySelectionError(ValueError):
    """Bounded, identity-free review failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _principal(value: object, *, role: str) -> str:
    if type(value) is not str:
        raise DeliverySelectionError("DELIVERY_PRINCIPAL_INVALID")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise DeliverySelectionError("DELIVERY_PRINCIPAL_INVALID") from None
    if not (1 <= len(encoded) <= _MAX_PRINCIPAL_BYTES) or _URI_RE.fullmatch(value) is None:
        raise DeliverySelectionError("DELIVERY_PRINCIPAL_INVALID")
    return value


@dataclass(frozen=True, slots=True)
class DeliverySelectionDraft:
    """Explicit proposed mode and principals, not an Agreement or assignment."""

    mode: str
    seller_principal: str
    buyer_principal: str
    proposed_provider_principal: str | None = None

    def __post_init__(self) -> None:
        if type(self.mode) is not str or self.mode not in _MODES:
            raise DeliverySelectionError("DELIVERY_MODE_UNSUPPORTED")
        seller = _principal(self.seller_principal, role="seller")
        buyer = _principal(self.buyer_principal, role="buyer")
        if seller == buyer:
            raise DeliverySelectionError("DELIVERY_PARTIES_NOT_DISTINCT")
        provider = self.proposed_provider_principal
        if self.mode == SELLER_DELIVERY:
            if provider is not None:
                raise DeliverySelectionError("DELIVERY_SELLER_MODE_PROVIDER_FORBIDDEN")
        else:
            provider = _principal(provider, role="provider")
            if provider in (seller, buyer):
                raise DeliverySelectionError("DELIVERY_THIRD_PARTY_NOT_DISTINCT")


@dataclass(frozen=True, slots=True)
class DeliverySelectionPlan:
    """Non-authoritative read-model only; no contract, payment or fulfillment."""

    mode: str
    proposed_executor_principal: str
    seller_product_commitment_principal: str
    seller_product_commitment_id: str
    distinct_delivery_service_agreement_required: bool
    quote_and_consent_required: bool
    state: str = "PROPOSAL_ONLY"
    dispatch_authorized: bool = False
    payment_authorized: bool = False
    seller_delivery_fulfilled: bool = False


def plan_delivery_selection(draft: object) -> DeliverySelectionPlan:
    """Review explicit actor choice, preserving separate product obligations.

    Seller delivery still requires an actual Agreement and independently
    acceptable performance evidence. Third-party delivery additionally needs a
    distinct, consented service Agreement, not an implicit subcontract.
    """
    if type(draft) is not DeliverySelectionDraft:
        raise DeliverySelectionError("DELIVERY_DRAFT_INVALID")
    reviewed = DeliverySelectionDraft(
        mode=draft.mode,
        seller_principal=draft.seller_principal,
        buyer_principal=draft.buyer_principal,
        proposed_provider_principal=draft.proposed_provider_principal,
    )
    external = reviewed.mode != SELLER_DELIVERY
    return DeliverySelectionPlan(
        mode=reviewed.mode,
        proposed_executor_principal=(
            reviewed.proposed_provider_principal if external
            else reviewed.seller_principal
        ),
        seller_product_commitment_principal=reviewed.seller_principal,
        seller_product_commitment_id=SELLER_DELIVERY_COMMITMENT,
        distinct_delivery_service_agreement_required=external,
        quote_and_consent_required=True,
    )


__all__ = [
    "DeliverySelectionDraft",
    "DeliverySelectionError",
    "DeliverySelectionPlan",
    "INDEPENDENT_COURIER",
    "PARTNER_CARRIER",
    "SELLER_DELIVERY",
    "SELLER_DELIVERY_COMMITMENT",
    "plan_delivery_selection",
]
