from __future__ import annotations

from pathlib import Path
import unittest

from marketplace.application.agreement_assent import (
    AgreementAssentError,
    MarketplaceAgreementAssentProofService,
)
from marketplace.application.agreement_assent_coordination import (
    MemoryAgreementAssentCoordinationStore,
    MarketplaceAgreementAssentCoordinationService,
    PreparedAgreementAssent,
)
from marketplace.application.agreement_candidate import AgreementCandidateBuildResult
from marketplace.application.auth_proof_profile import (
    AuthenticationProofSigningRequest,
    make_marketplace_authentication_proof,
)
from marketplace.application.auth_verification_method_snapshot import (
    AuthenticationVerificationMethodEvidence,
    MarketplaceAuthenticationVerificationMethodSnapshot,
)


ROOT = Path(__file__).resolve().parents[1]
APPLICATION = ROOT / "src" / "marketplace" / "application"
REFERENCE = ROOT / "src" / "marketplace" / "reference"

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


def authentication_proof():
    return make_marketplace_authentication_proof(
        AuthenticationProofSigningRequest(
            verification_method=METHOD,
            challenge=b"\x33" * 32,
        ),
        b"\x44" * 64,
    )


def proof_service(proof_calls: list[tuple[object, ...]]):
    methods = MarketplaceAuthenticationVerificationMethodSnapshot(
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
        verification_methods=methods,
        record_identity=lambda _record: AGREEMENT,
        build_signing_input=lambda _record, _method: b"agreement-proof-input",
        build_verified_proof=lambda *args: proof_calls.append(args) or object(),
    )


class ProductAgreementAssentAuthenticationProofNonReuseTests(unittest.TestCase):
    def test_authentication_proof_cannot_be_relabelled_as_signing_preparation(self) -> None:
        proof_calls: list[tuple[object, ...]] = []
        service = proof_service(proof_calls)

        with self.assertRaises(AgreementAssentError) as caught:
            service.finalize(
                candidate=candidate(),
                preparation=authentication_proof(),
                signature=SIGNATURE,
                at_time=200,
            )

        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_PREPARATION_INVALID",
        )
        self.assertEqual(proof_calls, [])

    def test_authentication_proof_cannot_enter_verified_assent_coordination(self) -> None:
        store = MemoryAgreementAssentCoordinationStore(clock=lambda: 200)
        preparer_calls: list[object] = []
        coordination = MarketplaceAgreementAssentCoordinationService(
            store=store,
            prepare_verified_assent=lambda value: (
                preparer_calls.append(value)
                or PreparedAgreementAssent(
                    agreement_record_id=AGREEMENT,
                    principal=PRINCIPAL,
                    verification_method=METHOD,
                    proof_identity=b"\x55" * 32,
                    proof_bytes=b"unexpected",
                )
            ),
        )
        coordination.initialize()

        with self.assertRaises(TypeError):
            coordination.accept(authentication_proof())

        self.assertEqual(preparer_calls, [])
        self.assertEqual(coordination.for_agreement(AGREEMENT), ())

    def test_agreement_assent_python_stack_has_no_authentication_proof_conversion(self) -> None:
        assent_sources = tuple(sorted(APPLICATION.glob("agreement_assent*.py"))) + tuple(
            sorted(REFERENCE.glob("agreement_assent*.py"))
        )
        self.assertGreater(len(assent_sources), 0)

        forbidden = (
            "auth_proof_profile",
            "MarketplaceAuthenticationProof",
            "AuthenticationProofSigningRequest",
            "build_marketplace_auth_transcript",
            "make_marketplace_authentication_proof",
            "decode_marketplace_authentication_proof_json",
        )
        for path in assent_sources:
            source = path.read_text(encoding="utf-8")
            for marker in forbidden:
                with self.subTest(path=path.name, marker=marker):
                    self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
