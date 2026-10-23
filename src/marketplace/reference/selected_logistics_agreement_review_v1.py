"""L3-B inert cross-check between a delivery proposal and an L1 logistics Agreement.

This function composes existing L3-A purchase review and L1 Agreement-link
validation. Identity consistency is NOT assent, authorization or fulfillment.
No I/O, proof verification, dispatch, network requests, payment or persistence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from marketplace.application.delivery_selection_v1 import (
    DeliverySelectionDraft,
    INDEPENDENT_COURIER,
    PARTNER_CARRIER,
)
from marketplace.logistics.agreement_link_v1 import (
    LogisticsAgreementLinkError,
    inspect_delivery_agreement_link,
)
from marketplace.reference.purchase_delivery_selection_review_v1 import (
    PurchaseDeliverySelectionError,
    review_purchase_delivery_selection,
)

_ERROR: Final = "Marketplace logistics selection link invalid"


class SelectedLogisticsLinkError(ValueError):
    """Content-free fail-closed error, never reflecting participant records."""

    def __init__(self, code: str) -> None:
        super().__init__(_ERROR)
        self.code = code


@dataclass(frozen=True, slots=True)
class SelectedLogisticsLinkReview:
    """Exact identity match only; an Agreement record does not prove assent."""

    purchase_agreement_id: str
    purchase_commitment_id: str
    delivery_agreement_id: str
    delivery_commitment_id: str
    proposed_transport_principal: str
    delivery_mode: str
    status: str = "IDENTITY_MATCH_ONLY"
    consent_verified: bool = False
    attribution_verified: bool = False
    carrier_eligible: bool = False
    dispatch_authorized: bool = False
    settlement_authorized: bool = False
    goods_fulfilled: bool = False


def _fail(code: str) -> None:
    raise SelectedLogisticsLinkError(code) from None


def review_selected_logistics_agreement(
    *,
    delivery_draft: object,
    purchase_agreement: object,
    delivery_agreement: object,
) -> SelectedLogisticsLinkReview:
    """Compare an explicitly proposed external transporter with exact L1 link.

    A caller still needs independent proofs, explicit party assent, permission,
    role eligibility, privacy rules and relevant legal/contractual review before
    selecting this profile for use or performing any external action.
    """
    if type(delivery_draft) is not DeliverySelectionDraft:
        _fail("LOGISTICS_SELECTION_DRAFT_REQUIRED")
    try:
        purchase_review = review_purchase_delivery_selection(
            delivery_draft=delivery_draft,
            purchase_agreement=purchase_agreement,
        )
    except PurchaseDeliverySelectionError:
        _fail("LOGISTICS_SELECTION_PURCHASE_INVALID")

    # This narrow cross-check is only applicable where a separate transport
    # Agreement is required. Seller delivery remains an independent proposal.
    if purchase_review.delivery_mode not in (INDEPENDENT_COURIER, PARTNER_CARRIER):
        _fail("LOGISTICS_SELECTION_THIRD_PARTY_REQUIRED")
    if not purchase_review.distinct_logistics_agreement_required:
        _fail("LOGISTICS_SELECTION_SEPARATE_AGREEMENT_REQUIRED")

    try:
        link = inspect_delivery_agreement_link(
            purchase_agreement=purchase_agreement,
            delivery_agreement=delivery_agreement,
        )
    except LogisticsAgreementLinkError:
        _fail("LOGISTICS_SELECTION_LINK_INVALID")

    if (link.purchase_agreement_id != purchase_review.purchase_agreement_id
            or link.purchase_commitment_id != purchase_review.purchase_delivery_commitment_id):
        _fail("LOGISTICS_SELECTION_PURCHASE_TARGET_MISMATCH")
    if link.carrier_principal != purchase_review.proposed_delivery_executor:
        _fail("LOGISTICS_SELECTION_TRANSPORTER_MISMATCH")

    return SelectedLogisticsLinkReview(
        purchase_agreement_id=link.purchase_agreement_id,
        purchase_commitment_id=link.purchase_commitment_id,
        delivery_agreement_id=link.delivery_agreement_id,
        delivery_commitment_id=link.carrier_commitment_id,
        proposed_transport_principal=link.carrier_principal,
        delivery_mode=purchase_review.delivery_mode,
    )


__all__ = [
    "SelectedLogisticsLinkError",
    "SelectedLogisticsLinkReview",
    "review_selected_logistics_agreement",
]
