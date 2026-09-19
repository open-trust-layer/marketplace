from __future__ import annotations

import unittest

from marketplace.application.agreement_assent import (
    AgreementAssentError,
    AgreementAssentSigningPreparation,
    MarketplaceAgreementAssentProofService,
)
from marketplace.application.agreement_candidate import AgreementCandidateBuildResult
from marketplace.application.auth_verification_method_snapshot import (
    AuthenticationVerificationMethodEvidence,
    MarketplaceAuthenticationVerificationMethodSnapshot,
)


AGREEMENT_ID = "r1_agreement-test"
LISTING_ID = "r1_listing-test"
PROPOSAL_ID = "r1_proposal-test"
ACCEPTANCE_ID = "r1_acceptance-test"
PRINCIPAL = "urn:marketplace:test:buyer"
OTHER_PRINCIPAL = "urn:marketplace:test:other"
METHOD = "urn:marketplace:test:key-1"
PUBLIC_KEY = b"\x11" * 32
SIGNATURE = b"\x22" * 64


def _candidate(record: object | None = None) -> AgreementCandidateBuildResult:
    return AgreementCandidateBuildResult(
        record=object() if record is None else record,
        record_id=AGREEMENT_ID,
        listing_record_id=LISTING_ID,
        proposal_record_id=PROPOSAL_ID,
        acceptance_record_id=ACCEPTANCE_ID,
    )


def _snapshot(principal: str = PRINCIPAL) -> MarketplaceAuthenticationVerificationMethodSnapshot:
    return MarketplaceAuthenticationVerificationMethodSnapshot(
        [
            AuthenticationVerificationMethodEvidence(
                verification_method=METHOD,
                controller_principal=principal,
                public_key=PUBLIC_KEY,
                valid_from=100,
                valid_until=300,
            )
        ]
    )


class ProductAgreementAssentApplicationTests(unittest.TestCase):
    def service(self, *, snapshot=None, signing_input=None, proof=None):
        accepted_proof = object() if proof is None else proof
        return (
            MarketplaceAgreementAssentProofService(
                verification_methods=snapshot or _snapshot(),
                record_identity=lambda _record: AGREEMENT_ID,
                build_signing_input=signing_input
                or (lambda _record, _method: b"signing-input"),
                build_verified_proof=lambda *_args: accepted_proof,
            ),
            accepted_proof,
        )

    def test_prepare_and_finalize_bind_trusted_principal_method_and_candidate(self) -> None:
        calls = []
        accepted_proof = object()
        service = MarketplaceAgreementAssentProofService(
            verification_methods=_snapshot(),
            record_identity=lambda _record: AGREEMENT_ID,
            build_signing_input=lambda _record, _method: b"signing-input",
            build_verified_proof=lambda *args: calls.append(args) or accepted_proof,
        )
        candidate = _candidate()
        preparation = service.prepare(
            candidate=candidate,
            principal=PRINCIPAL,
            verification_method=METHOD,
            at_time=200,
        )
        self.assertEqual(preparation.agreement_record_id, AGREEMENT_ID)
        self.assertEqual(preparation.signing_input, b"signing-input")

        result = service.finalize(
            candidate=candidate,
            preparation=preparation,
            signature=SIGNATURE,
            at_time=200,
        )
        self.assertEqual(result.agreement_record_id, AGREEMENT_ID)
        self.assertEqual(result.principal, PRINCIPAL)
        self.assertEqual(result.verification_method, METHOD)
        self.assertIs(result.proof, accepted_proof)
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0],
            (candidate.record, METHOD, PUBLIC_KEY, SIGNATURE),
        )

    def test_untrusted_principal_method_binding_fails_closed(self) -> None:
        service, _ = self.service(snapshot=_snapshot(OTHER_PRINCIPAL))
        with self.assertRaises(AgreementAssentError) as caught:
            service.prepare(
                candidate=_candidate(),
                principal=PRINCIPAL,
                verification_method=METHOD,
                at_time=200,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_PRINCIPAL_MISMATCH",
        )

    def test_method_outside_validity_window_is_not_accepted(self) -> None:
        service, _ = self.service()
        with self.assertRaises(AgreementAssentError) as caught:
            service.prepare(
                candidate=_candidate(),
                principal=PRINCIPAL,
                verification_method=METHOD,
                at_time=300,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_PRINCIPAL_MISMATCH",
        )

    def test_candidate_identity_mismatch_is_rejected_before_signing_input(self) -> None:
        calls = []
        service = MarketplaceAgreementAssentProofService(
            verification_methods=_snapshot(),
            record_identity=lambda _record: "r1_other",
            build_signing_input=lambda *_args: calls.append(True) or b"unexpected",
            build_verified_proof=lambda *_args: object(),
        )
        with self.assertRaises(AgreementAssentError) as caught:
            service.prepare(
                candidate=_candidate(),
                principal=PRINCIPAL,
                verification_method=METHOD,
                at_time=200,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_IDENTITY_MISMATCH",
        )
        self.assertEqual(calls, [])

    def test_finalize_rebuilds_and_rejects_mutated_preparation(self) -> None:
        service, _ = self.service()
        hostile = AgreementAssentSigningPreparation(
            agreement_record_id=AGREEMENT_ID,
            principal=PRINCIPAL,
            verification_method=METHOD,
            signing_input=b"different-input",
        )
        with self.assertRaises(AgreementAssentError) as caught:
            service.finalize(
                candidate=_candidate(),
                preparation=hostile,
                signature=SIGNATURE,
                at_time=200,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_PREPARATION_INVALID",
        )

    def test_signature_length_is_rejected_before_evidence_builder(self) -> None:
        calls = []
        service = MarketplaceAgreementAssentProofService(
            verification_methods=_snapshot(),
            record_identity=lambda _record: AGREEMENT_ID,
            build_signing_input=lambda _record, _method: b"signing-input",
            build_verified_proof=lambda *_args: calls.append(True),
        )
        preparation = service.prepare(
            candidate=_candidate(),
            principal=PRINCIPAL,
            verification_method=METHOD,
            at_time=200,
        )
        with self.assertRaises(AgreementAssentError) as caught:
            service.finalize(
                candidate=_candidate(),
                preparation=preparation,
                signature=b"\x00" * 63,
                at_time=200,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_SIGNATURE_INVALID",
        )
        self.assertEqual(calls, [])

    def test_evidence_builder_failure_is_stable_and_non_reflective(self) -> None:
        def fail(*_args):
            raise RuntimeError("sensitive proof detail")

        service = MarketplaceAgreementAssentProofService(
            verification_methods=_snapshot(),
            record_identity=lambda _record: AGREEMENT_ID,
            build_signing_input=lambda _record, _method: b"signing-input",
            build_verified_proof=fail,
        )
        preparation = service.prepare(
            candidate=_candidate(),
            principal=PRINCIPAL,
            verification_method=METHOD,
            at_time=200,
        )
        with self.assertRaises(AgreementAssentError) as caught:
            service.finalize(
                candidate=_candidate(),
                preparation=preparation,
                signature=SIGNATURE,
                at_time=200,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_VERIFICATION_FAILED",
        )
        self.assertNotIn("sensitive proof detail", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
