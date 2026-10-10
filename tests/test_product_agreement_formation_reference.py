from __future__ import annotations

import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from olp import create_proof
from olp.encoding.record_identity import record_identity_text
from olp.model.verification import ResolvedVerificationMethod

from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.reference.agreement_candidate_v1 import (
    ACTION_BUY,
    build_product_agreement_candidate,
)
from marketplace.reference.agreement_formation_v1 import (
    AssentEvidence,
    evaluate_product_agreement_formation,
)
from marketplace.reference.product_listing_v1 import build_product_listing_record
from marketplace.reference.proposal_acceptance_v1 import build_proposal_acceptance_record
from marketplace.reference.proposal_v1 import build_buyer_request_proposal_record


SELLER = "urn:marketplace:test:seller"
BUYER = "urn:marketplace:test:buyer"
SUBJECT = "urn:marketplace:test:item:bicycle"


def _public_bytes(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes_raw()


def _agreement():
    listing = build_product_listing_record(
        ProductListingDraft(
            seller_principal=SELLER,
            subject_uri=SUBJECT,
            title="Bicycle",
            description="Formation evaluation test item",
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
    acceptance = build_proposal_acceptance_record(SELLER, record_identity_text(proposal))
    return build_product_agreement_candidate(listing, proposal, acceptance)


def _evidence(agreement, principal: str, method: str, *, purpose: str = "assertion", accepted: bool = True):
    key = Ed25519PrivateKey.generate()
    proof = create_proof(
        agreement,
        proof_purpose=purpose,
        verification_method=method,
        private_key=key,
        created="2026-09-18T06:00:00Z",
    )
    resolved = ResolvedVerificationMethod(method, "Ed25519", _public_bytes(key))
    return AssentEvidence(principal, proof, resolved, accepted)


class ProductAgreementFormationReferenceTests(unittest.TestCase):
    def test_complete_two_party_assent_is_sufficient_only_for_profile(self) -> None:
        agreement = _agreement()
        result = evaluate_product_agreement_formation(
            agreement,
            (
                _evidence(agreement, SELLER, "did:example:seller#key-1"),
                _evidence(agreement, BUYER, "did:example:buyer#key-1"),
            ),
        )
        self.assertEqual(result["formation_evidence"], "EVIDENCE_SUFFICIENT_FOR_PROFILE")
        self.assertEqual(result["missing_principals"], [])
        self.assertEqual(result["legal_enforceability"], "NOT_EVALUATED")
        self.assertFalse(result["universal_truth"])
        self.assertFalse(result["publishes_agreement"])
        self.assertFalse(result["authorizes_side_effects"])

    def test_missing_buyer_assent_is_incomplete(self) -> None:
        agreement = _agreement()
        result = evaluate_product_agreement_formation(
            agreement,
            (_evidence(agreement, SELLER, "did:example:seller#key-1"),),
        )
        self.assertEqual(result["formation_evidence"], "EVIDENCE_INCOMPLETE")
        self.assertEqual(result["missing_principals"], [BUYER])

    def test_wrong_proof_purpose_does_not_cover_party(self) -> None:
        agreement = _agreement()
        result = evaluate_product_agreement_formation(
            agreement,
            (
                _evidence(agreement, SELLER, "did:example:seller#key-1"),
                _evidence(
                    agreement,
                    BUYER,
                    "did:example:buyer#key-1",
                    purpose="authorization",
                ),
            ),
        )
        self.assertEqual(result["formation_evidence"], "EVIDENCE_INCOMPLETE")
        self.assertEqual(result["missing_principals"], [BUYER])

    def test_rejected_attribution_does_not_cover_party(self) -> None:
        agreement = _agreement()
        result = evaluate_product_agreement_formation(
            agreement,
            (
                _evidence(agreement, SELLER, "did:example:seller#key-1"),
                _evidence(
                    agreement,
                    BUYER,
                    "did:example:buyer#key-1",
                    accepted=False,
                ),
            ),
        )
        self.assertEqual(result["formation_evidence"], "EVIDENCE_INCOMPLETE")
        self.assertEqual(result["missing_principals"], [BUYER])


if __name__ == "__main__":
    unittest.main()
