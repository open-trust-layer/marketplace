from __future__ import annotations

import unittest

from olp.encoding.record_identity import record_identity_text

from marketplace.application.agreement_assent import VerifiedAgreementAssent
from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.reference.agreement_assent_coordination_v1 import (
    build_prepared_product_agreement_assent,
)
from marketplace.reference.agreement_assent_formation_v1 import (
    AgreementAssentFormationProfileError,
    build_product_agreement_formation_evidence_from_verified_assent,
    reverify_prepared_product_agreement_assent,
)
from marketplace.reference.agreement_assent_v1 import (
    build_verified_product_agreement_assent_proof,
)
from marketplace.reference.agreement_candidate_v1 import (
    ACTION_BUY,
    build_product_agreement_candidate,
)
from marketplace.reference.agreement_formation_v1 import (
    evaluate_product_agreement_formation,
)
from marketplace.reference.product_listing_v1 import build_product_listing_record
from marketplace.reference.proposal_acceptance_v1 import (
    build_proposal_acceptance_record,
)
from marketplace.reference.proposal_v1 import build_buyer_request_proposal_record


SELLER = "urn:marketplace:test:seller"
BUYER = "urn:marketplace:test:buyer"
SUBJECT = "urn:marketplace:test:item:bicycle"
METHOD = "urn:example:olp:test-key-1"
PUBLIC_KEY = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)
SIGNATURE = bytes.fromhex(
    "796690ef7db0526e6c5c6c1c93ab0157ff5e3d14b2196103f22f39d208f6d590"
    "71528d13f3e5f6b34b14d2ebb04617822dd0962c36d4673aaa456601f5f76b0c"
)


def agreement(
    *,
    subject: str = SUBJECT,
    description: str = "Agreement assent cross-runtime vector",
):
    listing = build_product_listing_record(
        ProductListingDraft(
            seller_principal=SELLER,
            subject_uri=subject,
            title="Bicycle",
            description=description,
            consideration=ExactDecimal(12500, 2),
            currency_code="EUR",
            quantity=ExactDecimal(1, 0),
            unit_uri=UNIT_ITEM,
            latitude_e6=52_090_700,
            longitude_e6=5_121_400,
        )
    )
    proposal = build_buyer_request_proposal_record(
        BuyerRequestProposalDraft(
            parent_record_id=record_identity_text(listing),
            buyer_principal=BUYER,
            subject_uri=subject,
            action_uri=ACTION_BUY,
        )
    )
    acceptance = build_proposal_acceptance_record(
        SELLER,
        record_identity_text(proposal),
    )
    return build_product_agreement_candidate(listing, proposal, acceptance)


def verified(record):
    proof = build_verified_product_agreement_assent_proof(
        record,
        METHOD,
        PUBLIC_KEY,
        SIGNATURE,
    )
    return VerifiedAgreementAssent(
        agreement_record_id=record_identity_text(record),
        principal=BUYER,
        verification_method=METHOD,
        proof=proof,
    )


class ProductAgreementAssentFormationReferenceTests(unittest.TestCase):
    def test_stored_proof_is_reverified_before_formation_projection(self):
        record = agreement()
        original = verified(record)
        prepared = build_prepared_product_agreement_assent(original)
        reverified = reverify_prepared_product_agreement_assent(
            record,
            prepared,
            PUBLIC_KEY,
        )
        current = VerifiedAgreementAssent(
            agreement_record_id=prepared.agreement_record_id,
            principal=prepared.principal,
            verification_method=prepared.verification_method,
            proof=reverified,
        )
        evidence = build_product_agreement_formation_evidence_from_verified_assent(
            current,
            PUBLIC_KEY,
        )
        result = evaluate_product_agreement_formation(record, (evidence,))
        self.assertEqual(result["covered_principals"], [BUYER])
        self.assertEqual(result["missing_principals"], [SELLER])
        self.assertEqual(result["formation_evidence"], "EVIDENCE_INCOMPLETE")

    def test_wrong_current_public_key_rejects_retained_signature(self):
        record = agreement()
        prepared = build_prepared_product_agreement_assent(verified(record))
        with self.assertRaises(AgreementAssentFormationProfileError) as caught:
            reverify_prepared_product_agreement_assent(
                record,
                prepared,
                b"\x44" * 32,
            )
        self.assertEqual(caught.exception.code, "AGREEMENT_ASSENT_PROOF_INVALID")

    def test_other_agreement_binding_is_rejected_before_verification(self):
        record = agreement()
        prepared = build_prepared_product_agreement_assent(verified(record))
        other = agreement(
            subject="urn:marketplace:test:item:other",
            description="Other candidate",
        )
        self.assertNotEqual(
            record_identity_text(other),
            prepared.agreement_record_id,
        )
        with self.assertRaises(AgreementAssentFormationProfileError) as caught:
            reverify_prepared_product_agreement_assent(
                other,
                prepared,
                PUBLIC_KEY,
            )
        self.assertEqual(caught.exception.code, "AGREEMENT_ASSENT_BINDING_MISMATCH")

    def test_formation_projection_requires_current_public_key_match(self):
        record = agreement()
        current = verified(record)
        with self.assertRaises(AgreementAssentFormationProfileError) as caught:
            build_product_agreement_formation_evidence_from_verified_assent(
                current,
                b"\x55" * 32,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_VERIFIED_RESULT_MISMATCH",
        )


if __name__ == "__main__":
    unittest.main()
