"""L3-B proposal-to-logistics-Agreement coherence review (offline, unselected).

This adapter cross-checks an explicit third-party delivery proposal against
one separate immutable delivery Agreement. It cannot establish consent,
authorize dispatch, validate OLP proofs, or authorize money movement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from marketplace.application.delivery_selection_v1 import (
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

_ERROR: Final = "Marketplace logistics delivery selection link review invalid"


class DeliverySelectionLinkReviewError(ValueError):
    """Stable, content-free fail-closed reason for local review methods."""

    def __init__(self, code: str) -> None:
        super().__init__(_ERROR)
        self.code = code


@dataclass(frozen=True, slots=True)
class DeliverySelectionLinkReview:
    """Coherent identities only; never verified assent or authority."""

    purchase_agreement_id: str
    purchase_commitment_id: str
    delivery_agreement_id: str
    transport_commitment_id: str
    seller_principal: str
    proposed_provider_principal: str
    delivery_mode: str
    status: str = "CONSISTENT_PROPOSAL_ONLY"
    separate_agreement_required: bool = True
    assent_verified: bool = False
    dispatch_authorized: bool = False
    settlement_authorized: bool = False
    goods_fulfilled: bool = False


def _fail(code: str) -> None:
    raise DeliverySelectionLinkReviewError(code) from None


def review_delivery_selection_link(
    *, delivery_draft: object, purchase_agreement: object,
    delivery_agreement: object,
) -> DeliverySelectionLinkReview:
    """Match a named third-party proposal to an exact L1 logistics link.

    All input Records must be immutable validated OLP records. The caller must
    separately assess signer identity, consent, carrier eligibility, policy,
    proof validity, and private data before any later operational action.
    """
    try:
        proposal = review_purchase_delivery_selection(
            delivery_draft=delivery_draft,
            purchase_agreement=purchase_agreement,
        )
    except PurchaseDeliverySelectionError:
        _fail("PURCHASE_SELECTION_INVALID")

    if (
        proposal.delivery_mode not in (INDEPENDENT_COURIER, PARTNER_CARRIER)
        or not proposal.distinct_logistics_agreement_required
    ):
        _fail("THIRD_PARTY_DELIVERY_REQUIRED")

    try:
        link = inspect_delivery_agreement_link(
            purchase_agreement=purchase_agreement,
            delivery_agreement=delivery_agreement,
        )
    except LogisticsAgreementLinkError:
        _fail("DELIVERY_AGREEMENT_LINK_INVALID")

    # An L1 link may target another commitment from the same purchase.
    # L3-B requires precisely the reviewed seller-delivery commitment.
    if link.purchase_agreement_id != proposal.purchase_agreement_id:
        _fail("PURCHASE_AGREEMENT_MISMATCH")
    if link.purchase_commitment_id != proposal.purchase_delivery_commitment_id:
        _fail("PURCHASE_COMMITMENT_MISMATCH")
    if link.carrier_principal != proposal.proposed_delivery_executor:
        _fail("PROPOSED_PROVIDER_MISMATCH")

    return DeliverySelectionLinkReview(
        purchase_agreement_id=proposal.purchase_agreement_id,
        purchase_commitment_id=proposal.purchase_delivery_commitment_id,
        delivery_agreement_id=link.delivery_agreement_id,
        transport_commitment_id=link.carrier_commitment_id,
        seller_principal=proposal.seller_principal,
        proposed_provider_principal=proposal.proposed_delivery_executor,
        delivery_mode=proposal.delivery_mode,
    )


__all__ = [
    "DeliverySelectionLinkReview",
    "DeliverySelectionLinkReviewError",
    "review_delivery_selection_link",
]
