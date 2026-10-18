"""Offline L1 logistics linking: deterministic positive, negative and privacy guards."""
from __future__ import annotations

import unittest

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text
from olp.evidence import record_ref

from marketplace.logistics.agreement_link_v1 import (
    ACTION_TRANSPORT,
    PROFILE_DELIVERY_V1,
    TERM_PURCHASE_COMMITMENT,
    LogisticsAgreementLinkError,
    inspect_delivery_agreement_link,
)
from marketplace.reference.record_v1 import (
    BASE,
    CORE_PROFILE,
    TYPE_AGREEMENT,
    validate_market_record,
)

SELLER = "did:example:seller"
BUYER = "did:example:buyer"
COURIER = "did:example:courier"
SALE = f"{BASE}/action/sell"
ITEM = {"uri": "urn:example:item:widget"}
DELIVERY_COMMITMENT = "seller-delivery"
COURIER_COMMITMENT = "courier-transport"


def canonical(items):
    return sorted(items, key=olp_encode)


def make_record(content, *, profiles=(CORE_PROFILE,)):
    record = RecordV1.from_mapping({
        "envelope_version": 1,
        "type": TYPE_AGREEMENT,
        "content": content,
        "profiles": canonical(profiles),
    })
    validate_market_record(record)
    return record


def purchase():
    return make_record({
        "version": 1,
        "parties": canonical([{"principal": SELLER}, {"principal": BUYER}]),
        "subjects": [ITEM],
        "actions": [{"id": SALE}],
        "terms": {},
        "commitments": [{
            "id": DELIVERY_COMMITMENT,
            "party": {"principal": SELLER},
            "action": {"id": SALE},
            "subjects": [ITEM],
        }],
    })


def delivery(source, *, carrier=COURIER):
    return make_record({
        "version": 1,
        "parties": canonical([{"principal": principal} for principal in {SELLER, carrier}]),
        "subjects": [ITEM],
        "actions": [{"id": ACTION_TRANSPORT}],
        "terms": {TERM_PURCHASE_COMMITMENT: {
            "record": record_ref(source).to_value(),
            "id": DELIVERY_COMMITMENT,
        }},
        "source_records": [record_ref(source).to_value()],
        "commitments": [{
            "id": COURIER_COMMITMENT,
            "party": {"principal": carrier},
            "action": {"id": ACTION_TRANSPORT},
            "subjects": [ITEM],
        }],
    }, profiles=(CORE_PROFILE, PROFILE_DELIVERY_V1))


def changed(source, **overrides):
    content = dict(source.content)
    content.update(overrides)
    return make_record(content, profiles=source.profiles)


class LogisticsL1AgreementLinkTests(unittest.TestCase):
    def assert_rejected(self, source, delivery_agreement, code):
        with self.assertRaises(LogisticsAgreementLinkError) as caught:
            inspect_delivery_agreement_link(
                purchase_agreement=source,
                delivery_agreement=delivery_agreement,
            )
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), "Marketplace logistics agreement link invalid")

    def test_courier_delivery_is_a_distinct_linked_agreement(self):
        source = purchase()
        other = delivery(source)
        link = inspect_delivery_agreement_link(
            purchase_agreement=source,
            delivery_agreement=other,
        )
        self.assertEqual(link.purchase_agreement_id, record_identity_text(source))
        self.assertEqual(link.delivery_agreement_id, record_identity_text(other))
        self.assertNotEqual(link.purchase_agreement_id, link.delivery_agreement_id)
        self.assertEqual(link.purchase_commitment_id, DELIVERY_COMMITMENT)
        self.assertEqual(link.carrier_commitment_id, COURIER_COMMITMENT)
        self.assertEqual(link.carrier_principal, COURIER)
        self.assertEqual(source.content["terms"], {})
        self.assertNotIn("location", other.content)
        self.assertNotIn("address", other.content)
        self.assertNotIn("payment", other.content)

    def test_self_delivery_preserves_seller_as_carrier(self):
        source = purchase()
        link = inspect_delivery_agreement_link(
            purchase_agreement=source,
            delivery_agreement=delivery(source, carrier=SELLER),
        )
        self.assertEqual(link.carrier_principal, SELLER)

    def test_wrong_or_missing_link_prohibited(self):
        source = purchase()
        other = delivery(source)
        term = dict(other.content["terms"])
        term[TERM_PURCHASE_COMMITMENT] = {
            "record": record_ref(source).to_value(),
            "id": "nonexistent",
        }
        self.assert_rejected(
            source, changed(other, terms=term), "LOGISTICS_PURCHASE_COMMITMENT_MISSING"
        )
        self.assert_rejected(
            source, changed(other, terms={}), "LOGISTICS_LINK_TERMS_INVALID"
        )
        self.assert_rejected(
            source, changed(other, source_records=()),
            "LOGISTICS_PURCHASE_SOURCE_MISSING",
        )
        self.assert_rejected(
            source,
            changed(other, terms={TERM_PURCHASE_COMMITMENT: {"id": DELIVERY_COMMITMENT}}),
            "LOGISTICS_TARGET_INVALID",
        )

    def test_mismatched_agreement_ref_is_not_silently_rebound(self):
        source = purchase()
        another = make_record({
            **dict(source.content),
            "terms": {f"{BASE}/term/test-distinct-source": 1},
        })
        other = delivery(source)
        self.assert_rejected(
            another, other, "LOGISTICS_PURCHASE_SOURCE_MISSING"
        )

    def test_transport_and_role_are_required(self):
        source = purchase()
        other = delivery(source)
        unrelated = f"{BASE}/action/unrelated"
        self.assert_rejected(
            source,
            changed(other, actions=({"id": unrelated},), commitments=({
                "id": COURIER_COMMITMENT,
                "party": {"principal": COURIER},
                "action": {"id": unrelated},
                "subjects": (ITEM,),
            },)),
            "LOGISTICS_TRANSPORT_COMMITMENT_REQUIRED",
        )
        self.assert_rejected(
            source, changed(other, parties=({"principal": COURIER},)),
            "LOGISTICS_SELLER_NOT_PARTY",
        )

    def test_wrong_record_type_and_missing_profile_fail_closed(self):
        source = purchase()
        other = delivery(source)
        self.assert_rejected(source, source, "LOGISTICS_SELF_REFERENCE")
        self.assert_rejected(
            source, make_record(dict(other.content)),
            "LOGISTICS_PROFILE_REQUIRED",
        )
        self.assert_rejected(
            object(), other, "LOGISTICS_AGREEMENT_REQUIRED"
        )

    def test_identity_only_no_public_personal_delivery_terms(self):
        source = purchase()
        other = delivery(source)
        private_term = f"{BASE}/term/logistics-recipient-address"
        terms = dict(other.content["terms"])
        terms[private_term] = "sensitive test address"
        self.assert_rejected(
            source, changed(other, terms=terms), "LOGISTICS_LINK_TERMS_INVALID"
        )


if __name__ == "__main__":
    unittest.main()
