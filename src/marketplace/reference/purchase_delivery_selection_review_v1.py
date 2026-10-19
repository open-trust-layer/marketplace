"""L3-A reference adapter to check that proposed delivery selection matches a purchase.

This is an unselected, source-only domain reference review method. It never
publishes a purchase, acknowledges assent, assigns a carrier, starts shipping,
verifies OLP proofs or authorizes settlement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text

from marketplace.application.delivery_selection_v1 import (
    DeliverySelectionDraft,
    DeliverySelectionError,
    SELLER_DELIVERY_COMMITMENT,
    plan_delivery_selection,
)
from marketplace.reference.record_v1 import TYPE_AGREEMENT, validate_market_record

_ERROR: Final = "Marketplace purchase delivery selection review invalid"


class PurchaseDeliverySelectionError(ValueError):
    """Review rejection that does not echo purchase or delivery contents."""

    def __init__(self, code: str) -> None:
        super().__init__(_ERROR)
        self.code = code


@dataclass(frozen=True, slots=True)
class PurchaseDeliverySelectionReview:
    """Identity-only, proposal-only result, not consent or execution authority."""

    purchase_agreement_id: str
    purchase_delivery_commitment_id: str
    seller_principal: str
    proposed_delivery_executor: str
    delivery_mode: str
    distinct_logistics_agreement_required: bool
    state: str = "PROPOSAL_ONLY"
    consent_verified: bool = False
    dispatch_authorized: bool = False
    settlement_authorized: bool = False
    goods_fulfilled: bool = False


def _fail(code: str) -> None:
    raise PurchaseDeliverySelectionError(code) from None


def review_purchase_delivery_selection(
    *, delivery_draft: object, purchase_agreement: object
) -> PurchaseDeliverySelectionReview:
    """Require explicit delivery proposal consistent with one existing purchase.

    The caller must independently establish agreement assent, identities,
    authorization, selected review method and later consent. No sensitive terms
    or private locations are read or projected by this function.
    """
    if type(delivery_draft) is not DeliverySelectionDraft:
        _fail("DELIVERY_DRAFT_REQUIRED")
    try:
        plan = plan_delivery_selection(delivery_draft)
    except DeliverySelectionError:
        _fail("DELIVERY_DRAFT_INVALID")
    if type(purchase_agreement) is not RecordV1 or purchase_agreement.type != TYPE_AGREEMENT:
        _fail("PURCHASE_AGREEMENT_REQUIRED")
    try:
        validate_market_record(purchase_agreement)
        purchase_id = record_identity_text(purchase_agreement)
    except Exception:
        _fail("PURCHASE_AGREEMENT_INVALID")

    seller = delivery_draft.seller_principal
    buyer = delivery_draft.buyer_principal
    principals = tuple(x["principal"] for x in purchase_agreement.content["parties"])
    # Initial seller-to-buyer profile only; any ambiguous/multiparty case
    # needs a separately specified method instead of guessing the recipient.
    if len(principals) != 2 or set(principals) != {seller, buyer}:
        _fail("PURCHASE_PARTIES_MISMATCH")

    matches = [
        entry for entry in purchase_agreement.content["commitments"]
        if entry["id"] == SELLER_DELIVERY_COMMITMENT
    ]
    if len(matches) != 1:
        _fail("PURCHASE_SELLER_DELIVERY_MISSING")
    if matches[0]["party"]["principal"] != seller:
        _fail("PURCHASE_SELLER_DELIVERY_ACTOR_MISMATCH")

    # The purchase seller retains its original goods delivery obligation;
    # an outside executor is never silently made a party to this purchase.
    if plan.seller_product_commitment_principal != seller:
        _fail("PURCHASE_DELIVERY_PLAN_MISMATCH")
    return PurchaseDeliverySelectionReview(
        purchase_agreement_id=purchase_id,
        purchase_delivery_commitment_id=SELLER_DELIVERY_COMMITMENT,
        seller_principal=seller,
        proposed_delivery_executor=plan.proposed_executor_principal,
        delivery_mode=plan.mode,
        distinct_logistics_agreement_required=plan.distinct_delivery_service_agreement_required,
    )


__all__ = [
    "PurchaseDeliverySelectionError",
    "PurchaseDeliverySelectionReview",
    "review_purchase_delivery_selection",
]
