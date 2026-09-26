from __future__ import annotations

from dataclasses import replace
import inspect
from pathlib import Path
import unittest

from marketplace.application.agreement_assent import (
    AgreementAssentError,
    MarketplaceAgreementAssentProofService,
)
from marketplace.application.agreement_candidate import AgreementCandidateBuildResult
from marketplace.application.auth_verification_method_snapshot import (
    AuthenticationVerificationMethodEvidence,
    MarketplaceAuthenticationVerificationMethodSnapshot,
)
from marketplace.reference.agreement_assent_v1 import (
    AGREEMENT_ASSENT_PROOF_PURPOSE,
    build_product_agreement_assent_signing_input,
    build_verified_product_agreement_assent_proof,
)


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SOURCE = (
    ROOT / "src" / "marketplace" / "reference" / "agreement_assent_v1.py"
)

AGREEMENT = "r1_" + "A" * 43
PRINCIPAL = "urn:marketplace:test:buyer"
METHOD = "urn:marketplace:test:buyer-key"
PUBLIC_KEY = b"\x11" * 32
SIGNATURE = b"\x22" * 64


def candidate() -> AgreementCandidateBuildResult:
    return AgreementCandidateBuildResult(
        record=object(),
        record_id=AGREEMENT,
        listing_record_id="r1_" + "L" * 43,
        proposal_record_id="r1_" + "P" * 43,
        acceptance_record_id="r1_" + "C" * 43,
    )


def service() -> MarketplaceAgreementAssentProofService:
    snapshot = MarketplaceAuthenticationVerificationMethodSnapshot(
        [
            AuthenticationVerificationMethodEvidence(
                verification_method=METHOD,
                controller_principal=PRINCIPAL,
                public_key=PUBLIC_KEY,
                valid_from=100,
                valid_until=300,
            )
        ]
    )
    return MarketplaceAgreementAssentProofService(
        verification_methods=snapshot,
        record_identity=lambda _record: AGREEMENT,
        build_signing_input=lambda _record, _method: b"reviewed-signing-input",
        build_verified_proof=lambda *_args: object(),
    )


class ProductAgreementAssentAuthorityContractTests(unittest.TestCase):
    def test_application_callers_cannot_supply_public_key_or_attribution(self) -> None:
        for operation in (
            MarketplaceAgreementAssentProofService.prepare,
            MarketplaceAgreementAssentProofService.finalize,
        ):
            parameters = inspect.signature(operation).parameters
            for forbidden in (
                "public_key",
                "publicKey",
                "attribution",
                "attribution_accepted",
                "trusted",
                "proof_purpose",
            ):
                with self.subTest(operation=operation.__name__, forbidden=forbidden):
                    self.assertNotIn(forbidden, parameters)

    def test_reference_proof_purpose_is_fixed_and_not_caller_controlled(self) -> None:
        self.assertEqual(AGREEMENT_ASSENT_PROOF_PURPOSE, "assertion")
        for operation in (
            build_product_agreement_assent_signing_input,
            build_verified_product_agreement_assent_proof,
        ):
            parameters = inspect.signature(operation).parameters
            self.assertNotIn("proof_purpose", parameters)
            self.assertNotIn("expected_purpose", parameters)

        source = REFERENCE_SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            "proof_purpose=AGREEMENT_ASSENT_PROOF_PURPOSE",
            source,
        )
        self.assertIn(
            "expected_purpose=AGREEMENT_ASSENT_PROOF_PURPOSE",
            source,
        )

    def test_one_byte_preparation_mutation_is_rejected_before_proof_builder(self) -> None:
        proof_calls: list[object] = []
        reviewed = service()
        reviewed._build_verified_proof = lambda *_args: proof_calls.append(object())
        original = reviewed.prepare(
            candidate=candidate(),
            principal=PRINCIPAL,
            verification_method=METHOD,
            at_time=200,
        )
        hostile_bytes = bytearray(original.signing_input)
        hostile_bytes[-1] ^= 1
        hostile = replace(original, signing_input=bytes(hostile_bytes))

        with self.assertRaises(AgreementAssentError) as caught:
            reviewed.finalize(
                candidate=candidate(),
                preparation=hostile,
                signature=SIGNATURE,
                at_time=200,
            )

        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_PREPARATION_INVALID",
        )
        self.assertEqual(proof_calls, [])

    def test_public_key_is_selected_only_from_trusted_snapshot(self) -> None:
        calls: list[tuple[object, ...]] = []
        reviewed = service()
        reviewed._build_verified_proof = lambda *args: calls.append(args) or object()
        preparation = reviewed.prepare(
            candidate=candidate(),
            principal=PRINCIPAL,
            verification_method=METHOD,
            at_time=200,
        )
        reviewed.finalize(
            candidate=candidate(),
            preparation=preparation,
            signature=SIGNATURE,
            at_time=200,
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], METHOD)
        self.assertEqual(calls[0][2], PUBLIC_KEY)
        self.assertEqual(calls[0][3], SIGNATURE)


if __name__ == "__main__":
    unittest.main()
