from __future__ import annotations

from dataclasses import replace
import hashlib
import unittest

from olp.encoding.proof_identity import proof_identity
from olp.encoding.record_identity import record_identity_text

from marketplace.application.agreement_assent import VerifiedAgreementAssent
from marketplace.application.agreement_assent_coordination import PreparedAgreementAssent
from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.reference.agreement_assent_coordination_v1 import (
    AgreementAssentCoordinationProfileError,
    build_prepared_product_agreement_assent,
    decode_prepared_product_agreement_assent_proof,
)
from marketplace.reference.agreement_assent_v1 import (
    VerifiedAgreementAssentProof,
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


def verified() -> VerifiedAgreementAssent:
    record = agreement()
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


class ProductAgreementAssentCoordinationReferenceTests(unittest.TestCase):
    def test_verified_proof_serializes_deterministically_and_round_trips(self) -> None:
        value = verified()
        first = build_prepared_product_agreement_assent(value)
        second = build_prepared_product_agreement_assent(value)
        self.assertEqual(first, second)
        self.assertEqual(first.agreement_record_id, value.agreement_record_id)
        self.assertEqual(first.principal, BUYER)
        self.assertEqual(first.verification_method, METHOD)
        self.assertEqual(len(first.proof_identity), 32)
        self.assertLess(len(first.proof_bytes), 16 * 1024)
        self.assertEqual(
            first.proof_identity.hex(),
            "ad8e7af0541a35dbbeafa981297df6a3a057acbcd16321c8091ab83585a4833b",
        )
        decoded = decode_prepared_product_agreement_assent_proof(first)
        self.assertEqual(proof_identity(decoded), first.proof_identity)
        self.assertEqual(decoded.proofValue, SIGNATURE)
        self.assertEqual(decoded.verificationMethod, METHOD)
        self.assertEqual(decoded, value.proof.proof)

    def test_serialized_bytes_are_canonical_transport_json(self) -> None:
        prepared = build_prepared_product_agreement_assent(verified())
        self.assertTrue(prepared.proof_bytes.startswith(b'{"olp":1,"payload":'))
        self.assertIn(b'"type":"proof"', prepared.proof_bytes)
        self.assertNotIn(b" ", prepared.proof_bytes)
        self.assertNotIn(b"\n", prepared.proof_bytes)
        self.assertEqual(
            hashlib.sha256(prepared.proof_bytes).hexdigest(),
            hashlib.sha256(
                build_prepared_product_agreement_assent(verified()).proof_bytes
            ).hexdigest(),
        )

    def test_tampered_transport_bytes_fail_closed(self) -> None:
        original = build_prepared_product_agreement_assent(verified())
        hostile = PreparedAgreementAssent(
            original.agreement_record_id,
            original.principal,
            original.verification_method,
            original.proof_identity,
            original.proof_bytes[:-1] + b"!",
        )
        with self.assertRaises(AgreementAssentCoordinationProfileError) as caught:
            decode_prepared_product_agreement_assent_proof(hostile)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_SERIALIZATION_INVALID",
        )

    def test_proof_identity_mismatch_fails_closed(self) -> None:
        original = build_prepared_product_agreement_assent(verified())
        hostile = PreparedAgreementAssent(
            original.agreement_record_id,
            original.principal,
            original.verification_method,
            b"\x00" * 32,
            original.proof_bytes,
        )
        with self.assertRaises(AgreementAssentCoordinationProfileError) as caught:
            decode_prepared_product_agreement_assent_proof(hostile)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_PROOF_IDENTITY_MISMATCH",
        )

    def test_verification_method_binding_is_rechecked_on_decode(self) -> None:
        original = build_prepared_product_agreement_assent(verified())
        hostile = PreparedAgreementAssent(
            original.agreement_record_id,
            original.principal,
            "urn:example:olp:other-key",
            original.proof_identity,
            original.proof_bytes,
        )
        with self.assertRaises(AgreementAssentCoordinationProfileError) as caught:
            decode_prepared_product_agreement_assent_proof(hostile)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_PROOF_PROFILE_MISMATCH",
        )

    def test_reference_preparer_requires_exact_verified_proof_result(self) -> None:
        value = VerifiedAgreementAssent(
            agreement_record_id=record_identity_text(agreement()),
            principal=BUYER,
            verification_method=METHOD,
            proof=object(),
        )
        with self.assertRaises(AgreementAssentCoordinationProfileError) as caught:
            build_prepared_product_agreement_assent(value)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_VERIFIED_RESULT_INVALID",
        )
    def test_optional_proof_metadata_is_outside_first_coordination_profile(self) -> None:
        value = verified()
        widened = VerifiedAgreementAssentProof(
            proof=replace(
                value.proof.proof,
                domain="https://example.invalid/agreement",
            ),
            resolved_method=value.proof.resolved_method,
        )
        hostile = VerifiedAgreementAssent(
            agreement_record_id=value.agreement_record_id,
            principal=value.principal,
            verification_method=value.verification_method,
            proof=widened,
        )
        with self.assertRaises(AgreementAssentCoordinationProfileError) as caught:
            build_prepared_product_agreement_assent(hostile)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_PROOF_PROFILE_MISMATCH",
        )


if __name__ == "__main__":
    unittest.main()
