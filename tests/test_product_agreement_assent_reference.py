from __future__ import annotations

import unittest

from olp.encoding.proof_identity import proof_identity
from olp.encoding.record_identity import record_identity_text

from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.reference.agreement_assent_v1 import (
    AgreementAssentProfileError,
    build_product_agreement_assent_signing_input,
    build_verified_product_agreement_assent_proof,
)
from marketplace.reference.agreement_candidate_v1 import (
    ACTION_BUY,
    build_product_agreement_candidate,
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
EXPECTED_INPUT_HEX = (
    "89694f4c502d50524f4f46017065646473612d656432353531392d763169617373"
    "657274696f6e781a75726e3a6578616d706c653a6f6c703a746573742d6b65792d"
    "31822f582082b4b4fc794b352d80d55a9d10b11afdd682e08265fd2046cf17003b"
    "a7ac3390a0a080"
)
EXPECTED_PROOF_IDENTITY_HEX = (
    "ad8e7af0541a35dbbeafa981297df6a3a057acbcd16321c8091ab83585a4833b"
)


def _records(*, description: str = "Agreement assent cross-runtime vector"):
    listing = build_product_listing_record(
        ProductListingDraft(
            seller_principal=SELLER,
            subject_uri=SUBJECT,
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
            subject_uri=SUBJECT,
            action_uri=ACTION_BUY,
        )
    )
    acceptance = build_proposal_acceptance_record(
        SELLER,
        record_identity_text(proposal),
    )
    agreement = build_product_agreement_candidate(
        listing,
        proposal,
        acceptance,
    )
    return listing, proposal, acceptance, agreement


class ProductAgreementAssentReferenceTests(unittest.TestCase):
    def test_frozen_marketplace_cross_runtime_vector(self) -> None:
        listing, proposal, acceptance, agreement = _records()
        self.assertEqual(
            record_identity_text(listing),
            "r1_ePig7aybee8gTDoLgkGnBtkThAzfnLiBhghnYT7_5oo",
        )
        self.assertEqual(
            record_identity_text(proposal),
            "r1_eK7njvEOxYBo_7xT_CaIjcIJxITw3Jz8o774iPTqoSQ",
        )
        self.assertEqual(
            record_identity_text(acceptance),
            "r1_fAjuCNheWAkbyAQpbm20hZbvku3iocKvynI6FGUUYWg",
        )
        self.assertEqual(
            record_identity_text(agreement),
            "r1_grS0_HlLNS2A1VqdELEa_daC4IJl_SBGzxcAO6esM5A",
        )

        signing_input = build_product_agreement_assent_signing_input(
            agreement,
            METHOD,
        )
        self.assertEqual(len(signing_input), 106)
        self.assertEqual(signing_input.hex(), EXPECTED_INPUT_HEX)

        result = build_verified_product_agreement_assent_proof(
            agreement,
            METHOD,
            PUBLIC_KEY,
            SIGNATURE,
        )
        self.assertEqual(result.proof.proofValue, SIGNATURE)
        self.assertEqual(result.proof.verificationMethod, METHOD)
        self.assertEqual(
            proof_identity(result.proof).hex(),
            EXPECTED_PROOF_IDENTITY_HEX,
        )
        self.assertFalse(hasattr(result, "principal"))
        self.assertFalse(hasattr(result, "attribution_accepted"))

    def test_signature_bit_mutation_fails_closed(self) -> None:
        agreement = _records()[3]
        hostile = bytes([SIGNATURE[0] ^ 1]) + SIGNATURE[1:]
        with self.assertRaises(AgreementAssentProfileError) as caught:
            build_verified_product_agreement_assent_proof(
                agreement,
                METHOD,
                PUBLIC_KEY,
                hostile,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_PROOF_INVALID",
        )

    def test_different_candidate_rejects_frozen_signature(self) -> None:
        agreement = _records(description="Different agreement candidate")[3]
        self.assertNotEqual(
            build_product_agreement_assent_signing_input(
                agreement,
                METHOD,
            ).hex(),
            EXPECTED_INPUT_HEX,
        )
        with self.assertRaises(AgreementAssentProfileError) as caught:
            build_verified_product_agreement_assent_proof(
                agreement,
                METHOD,
                PUBLIC_KEY,
                SIGNATURE,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_PROOF_INVALID",
        )

    def test_wrong_method_rejects_frozen_signature(self) -> None:
        agreement = _records()[3]
        with self.assertRaises(AgreementAssentProfileError) as caught:
            build_verified_product_agreement_assent_proof(
                agreement,
                "urn:example:olp:other-key",
                PUBLIC_KEY,
                SIGNATURE,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_PROOF_INVALID",
        )

    def test_invalid_key_and_signature_lengths_fail_before_crypto(self) -> None:
        agreement = _records()[3]
        with self.assertRaises(AgreementAssentProfileError) as key_error:
            build_verified_product_agreement_assent_proof(
                agreement,
                METHOD,
                PUBLIC_KEY[:-1],
                SIGNATURE,
            )
        self.assertEqual(
            key_error.exception.code,
            "AGREEMENT_ASSENT_METHOD_INVALID",
        )

        with self.assertRaises(AgreementAssentProfileError) as signature_error:
            build_verified_product_agreement_assent_proof(
                agreement,
                METHOD,
                PUBLIC_KEY,
                SIGNATURE[:-1],
            )
        self.assertEqual(
            signature_error.exception.code,
            "AGREEMENT_ASSENT_SIGNATURE_INVALID",
        )


if __name__ == "__main__":
    unittest.main()
