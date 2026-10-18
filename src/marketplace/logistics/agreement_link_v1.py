"""L1 read-only link check for a separate logistics MarketAgreement.

This profile adds NO Marketplace/OLP record type and performs NO side effects.
It does not determine assent, authority, performance, payment, or legal eligibility.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text
from olp.evidence import record_ref

from marketplace.reference.record_v1 import (
    BASE,
    TYPE_AGREEMENT,
    validate_commitment_ref,
    validate_market_record,
)

PROFILE_DELIVERY_V1: Final = f"{BASE}/profile/logistics-delivery-v1"
ACTION_TRANSPORT: Final = f"{BASE}/action/logistics-transport"
TERM_PURCHASE_COMMITMENT: Final = f"{BASE}/term/logistics-purchase-commitment"
_ERROR: Final = "Marketplace logistics agreement link invalid"


class LogisticsAgreementLinkError(ValueError):
    """Stable fail-closed result without leaking record bodies or personal data."""

    def __init__(self, code: str) -> None:
        super().__init__(_ERROR)
        self.code = code


@dataclass(frozen=True)
class DeliveryAgreementLink:
    """Identity-only projection; not a publication or evidence of assent."""

    purchase_agreement_id: str
    purchase_commitment_id: str
    delivery_agreement_id: str
    carrier_commitment_id: str
    carrier_principal: str


def _fail(code: str) -> None:
    raise LogisticsAgreementLinkError(code) from None


def _agreement(value: object) -> RecordV1:
    if type(value) is not RecordV1 or value.type != TYPE_AGREEMENT:
        _fail("LOGISTICS_AGREEMENT_REQUIRED")
    try:
        validate_market_record(value)
    except Exception:
        _fail("LOGISTICS_AGREEMENT_INVALID")
    return value


def inspect_delivery_agreement_link(
    *, purchase_agreement: object, delivery_agreement: object
) -> DeliveryAgreementLink:
    """Validate a single transport commitment linked to an exact purchase commitment.

    Callers separately verify proofs/assent, authority, policy, private disclosures,
    legal courier eligibility and settlement readiness. No network or storage access.
    """

    purchase = _agreement(purchase_agreement)
    delivery = _agreement(delivery_agreement)
    try:
        purchase_id = record_identity_text(purchase)
        delivery_id = record_identity_text(delivery)
    except Exception:
        _fail("LOGISTICS_IDENTITY_INVALID")
    if purchase_id == delivery_id:
        _fail("LOGISTICS_SELF_REFERENCE")
    if PROFILE_DELIVERY_V1 not in delivery.profiles:
        _fail("LOGISTICS_PROFILE_REQUIRED")

    expected_ref = record_ref(purchase).to_value()
    sources = delivery.content.get("source_records", ())
    if not isinstance(sources, tuple) or expected_ref not in sources:
        _fail("LOGISTICS_PURCHASE_SOURCE_MISSING")

    terms = delivery.content.get("terms")
    if not isinstance(terms, Mapping) or set(terms) != {TERM_PURCHASE_COMMITMENT}:
        _fail("LOGISTICS_LINK_TERMS_INVALID")
    link = terms[TERM_PURCHASE_COMMITMENT]
    if not isinstance(link, Mapping) or set(link) != {"record", "id"}:
        _fail("LOGISTICS_TARGET_INVALID")
    try:
        validate_commitment_ref(link, "logistics.purchase_commitment")
    except Exception:
        _fail("LOGISTICS_TARGET_INVALID")
    if link["record"] != expected_ref:
        _fail("LOGISTICS_PURCHASE_MISMATCH")

    commitment_id = link["id"]
    matches = [
        c for c in purchase.content["commitments"]
        if c["id"] == commitment_id
    ]
    if len(matches) != 1:
        _fail("LOGISTICS_PURCHASE_COMMITMENT_MISSING")
    # L1 seller-managed and third-party transport both require the purchase
    # performing party to be a named party to the separate delivery agreement.
    seller = matches[0]["party"]["principal"]
    principals = {party["principal"] for party in delivery.content["parties"]}
    if seller not in principals:
        _fail("LOGISTICS_SELLER_NOT_PARTY")

    transport = [
        c for c in delivery.content["commitments"]
        if c["action"]["id"] == ACTION_TRANSPORT
    ]
    if len(transport) != 1:
        _fail("LOGISTICS_TRANSPORT_COMMITMENT_REQUIRED")
    carrier = transport[0]
    if carrier["party"]["principal"] not in principals:
        _fail("LOGISTICS_CARRIER_NOT_PARTY")

    return DeliveryAgreementLink(
        purchase_agreement_id=purchase_id,
        purchase_commitment_id=commitment_id,
        delivery_agreement_id=delivery_id,
        carrier_commitment_id=carrier["id"],
        carrier_principal=carrier["party"]["principal"],
    )


__all__ = [
    "ACTION_TRANSPORT",
    "DeliveryAgreementLink",
    "LogisticsAgreementLinkError",
    "PROFILE_DELIVERY_V1",
    "TERM_PURCHASE_COMMITMENT",
    "inspect_delivery_agreement_link",
]
