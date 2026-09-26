from __future__ import annotations

from dataclasses import replace
import unittest

from olp import verify_proof
from olp.encoding.record_identity import record_identity_text
from olp.model.verification import ReasonCode, Status

from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.reference.agreement_assent_v1 import (
    AGREEMENT_ASSENT_PROOF_PURPOSE,
    build_verified_product_agreement_assent_proof,
)
from marketplace.reference.agreement_candidate_v1 import (
    ACTION_BUY,
    build_product_agreement_candidate,
)
from marketplace.reference.product_listing_v1 import build_product_listing_record
from marketplace.reference.proposal_acceptance_v1 import build_proposal_acceptance_record
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


def agreement():
    listing = build_product_listing_record(
        ProductListingDraft(
            seller_principal=SELLER,
            subject_uri=SUBJECT,
            title="Bicycle",
            description="Agreement assent cross-runtime vector",
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
            subject_uri=SUBJECT,
            action_uri=ACTION_BUY,
        )
    )
    acceptance = build_proposal_acceptance_record(
        SELLER,
        record_identity_text(proposal),
    )
    return build_product_agreement_candidate(listing, proposal, acceptance)


class ProductAgreementAssentWrongPurposeNegativeTests(unittest.TestCase):
    def test_understood_but_wrong_proof_purpose_is_not_accepted(self) -> None:
        record = agreement()
        verified = build_verified_product_agreement_assent_proof(
            record,
            METHOD,
            PUBLIC_KEY,
            SIGNATURE,
        )
        self.assertEqual(verified.proof.proofPurpose, AGREEMENT_ASSENT_PROOF_PURPOSE)

        hostile = replace(
            verified.proof,
            proofPurpose="authorization",
        )
        result = verify_proof(
            record,
            hostile,
            resolved_method=verified.resolved_method,
            expected_purpose=AGREEMENT_ASSENT_PROOF_PURPOSE,
        )

        self.assertEqual(result.conformance, Status.CONFORMING)
        self.assertEqual(result.purpose_status, Status.MISMATCH)
        self.assertEqual(result.cryptographic_validity, Status.INVALID)
        self.assertTrue(
            any(issue.code == ReasonCode.PURPOSE_MISMATCH for issue in result.errors)
        )

    def test_reference_builder_never_emits_non_assertion_purpose(self) -> None:
        record = agreement()
        verified = build_verified_product_agreement_assent_proof(
            record,
            METHOD,
            PUBLIC_KEY,
            SIGNATURE,
        )
        self.assertEqual(AGREEMENT_ASSENT_PROOF_PURPOSE, "assertion")
        self.assertEqual(verified.proof.proofPurpose, "assertion")


if __name__ == "__main__":
    unittest.main()
