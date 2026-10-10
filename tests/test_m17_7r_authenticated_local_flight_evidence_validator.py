from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools.marketplace_authenticated_local_flight_evidence import (
    AuthenticatedLocalFlightEvidenceError,
    PROFILE,
    load_authenticated_local_flight_evidence,
    main,
    render_authenticated_local_flight_evidence,
    validate_authenticated_local_flight_evidence,
)


def valid_evidence() -> dict[str, object]:
    agreement = "rid_agreement_01"
    return {
        "profile": PROFILE,
        "main_commit": "6e299cc7e723bb29cffd7e5b91e51d221e676198",
        "ci_run_number": 958,
        "runtime_host": "127.0.0.1",
        "seller_authenticated": True,
        "buyer_authenticated": True,
        "listing_record_id": "rid_listing_01",
        "proposal_record_id": "rid_proposal_01",
        "acceptance_record_id": "rid_acceptance_01",
        "agreement_record_id": agreement,
        "formation_evidence": "EVIDENCE_SUFFICIENT_FOR_PROFILE",
        "missing_principals": [],
        "agreement_publication": {
            "agreement_record_id": agreement,
            "disposition": "STORED",
            "change_seq": 21,
        },
        "completion": {
            "record_id": "rid_completion_01",
            "agreement_record_id": agreement,
            "commitment_id": "seller-delivery",
            "evidence_kind": "CLAIMED_COMPLETE_PERFORMANCE",
            "disposition": "STORED",
            "change_seq": 22,
        },
        "universal_truth": False,
        "payment_or_settlement_evaluated": False,
        "public_network_exposed": False,
        "public_deployment": False,
    }


class AuthenticatedLocalFlightEvidenceValidatorTests(unittest.TestCase):
    def assert_code(self, value: object, code: str) -> None:
        with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
            validate_authenticated_local_flight_evidence(value)
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn("rid_", str(caught.exception))

    def test_valid_final_record_is_accepted_and_rendered(self) -> None:
        document = valid_evidence()
        self.assertIs(validate_authenticated_local_flight_evidence(document), document)
        rendered = render_authenticated_local_flight_evidence(document)
        for marker in (
            "status=PASS",
            "runtime_host=127.0.0.1",
            "agreement_record_id=rid_agreement_01",
            "agreement_publication_disposition=STORED",
            "completion_record_id=rid_completion_01",
            "commitment_id=seller-delivery",
            "evidence_kind=CLAIMED_COMPLETE_PERFORMANCE",
            "universal_truth=false",
            "payment_or_settlement_evaluated=false",
            "public_network_exposed=false",
            "public_deployment=false",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, rendered)

    def test_unknown_top_level_field_is_rejected(self) -> None:
        document = valid_evidence()
        document["unexpected"] = "value"
        self.assert_code(document, "EVIDENCE_DOCUMENT_INVALID")

    def test_non_loopback_runtime_is_rejected(self) -> None:
        document = valid_evidence()
        document["runtime_host"] = "localhost"
        self.assert_code(document, "EVIDENCE_RUNTIME_HOST_INVALID")

    def test_authentication_must_cover_both_parties(self) -> None:
        document = valid_evidence()
        document["buyer_authenticated"] = False
        self.assert_code(document, "EVIDENCE_BUYER_AUTH_INVALID")

    def test_formation_must_be_sufficient_with_no_missing_parties(self) -> None:
        document = valid_evidence()
        document["formation_evidence"] = "EVIDENCE_INCOMPLETE"
        self.assert_code(document, "EVIDENCE_FORMATION_INVALID")

        document = valid_evidence()
        document["missing_principals"] = ["did:example:buyer"]
        self.assert_code(document, "EVIDENCE_MISSING_PRINCIPALS_INVALID")

    def test_publication_and_completion_must_reference_exact_agreement(self) -> None:
        document = valid_evidence()
        publication = document["agreement_publication"]
        assert type(publication) is dict
        publication["agreement_record_id"] = "rid_other_01"
        self.assert_code(document, "EVIDENCE_AGREEMENT_MISMATCH")

        document = valid_evidence()
        completion = document["completion"]
        assert type(completion) is dict
        completion["agreement_record_id"] = "rid_other_02"
        self.assert_code(document, "EVIDENCE_AGREEMENT_MISMATCH")

    def test_completion_semantics_are_exact(self) -> None:
        document = valid_evidence()
        completion = document["completion"]
        assert type(completion) is dict
        completion["commitment_id"] = "buyer-payment"
        self.assert_code(document, "EVIDENCE_COMMITMENT_INVALID")

        document = valid_evidence()
        completion = document["completion"]
        assert type(completion) is dict
        completion["evidence_kind"] = "COMMITMENT_COMPLETION"
        self.assert_code(document, "EVIDENCE_KIND_INVALID")

    def test_truth_payment_network_and_deployment_boundaries_are_false(self) -> None:
        cases = (
            ("universal_truth", "EVIDENCE_TRUTH_CLAIM_INVALID"),
            ("payment_or_settlement_evaluated", "EVIDENCE_PAYMENT_BOUNDARY_INVALID"),
            ("public_network_exposed", "EVIDENCE_NETWORK_BOUNDARY_INVALID"),
            ("public_deployment", "EVIDENCE_DEPLOYMENT_BOUNDARY_INVALID"),
        )
        for key, code in cases:
            with self.subTest(key=key):
                document = valid_evidence()
                document[key] = True
                self.assert_code(document, code)

    def test_change_sequence_is_positive_or_null(self) -> None:
        document = valid_evidence()
        publication = document["agreement_publication"]
        assert type(publication) is dict
        publication["change_seq"] = None
        validate_authenticated_local_flight_evidence(document)

        document = valid_evidence()
        completion = document["completion"]
        assert type(completion) is dict
        completion["change_seq"] = 0
        self.assert_code(document, "EVIDENCE_CHANGE_SEQ_INVALID")

    def test_record_identity_shape_is_bounded_and_lifecycle_ids_are_distinct(self) -> None:
        document = valid_evidence()
        document["proposal_record_id"] = "bad/id"
        self.assert_code(document, "EVIDENCE_RECORD_ID_INVALID")

        document = valid_evidence()
        document["acceptance_record_id"] = document["proposal_record_id"]
        self.assert_code(document, "EVIDENCE_RECORD_ID_COLLISION")

        document = valid_evidence()
        completion = document["completion"]
        assert type(completion) is dict
        completion["record_id"] = document["agreement_record_id"]
        self.assert_code(document, "EVIDENCE_RECORD_ID_COLLISION")

    def test_loader_is_bounded_and_main_returns_stable_codes(self) -> None:
        document = valid_evidence()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            loaded = load_authenticated_local_flight_evidence(path)
            self.assertEqual(loaded["agreement_record_id"], "rid_agreement_01")
            success_out = io.StringIO()
            success_err = io.StringIO()
            with redirect_stdout(success_out), redirect_stderr(success_err):
                self.assertEqual(main([str(path)]), 0)
            self.assertIn("status=PASS", success_out.getvalue())
            self.assertEqual(success_err.getvalue(), "")

            path.write_text("{", encoding="utf-8")
            failure_out = io.StringIO()
            failure_err = io.StringIO()
            with redirect_stdout(failure_out), redirect_stderr(failure_err):
                self.assertEqual(main([str(path)]), 1)
            self.assertEqual(failure_out.getvalue(), "")
            self.assertIn("status=FAIL code=EVIDENCE_JSON_INVALID", failure_err.getvalue())


    def test_duplicate_top_level_json_key_rejected_before_mapping_validation(self) -> None:
        document = valid_evidence()
        payload = json.dumps(document)
        marker = '"seller_authenticated": true'
        self.assertEqual(payload.count(marker), 1)
        payload = payload.replace(
            marker,
            '"seller_authenticated": false, "seller_authenticated": true',
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(payload, encoding="utf-8")
            with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
                load_authenticated_local_flight_evidence(path)
            self.assertEqual(caught.exception.code, "EVIDENCE_JSON_DUPLICATE_KEY")
            self.assertNotIn("seller_authenticated", str(caught.exception))

    def test_duplicate_nested_json_key_rejected_without_reflection(self) -> None:
        document = valid_evidence()
        payload = json.dumps(document)
        marker = '"agreement_publication": {"agreement_record_id": "rid_agreement_01", "disposition": "STORED"'
        self.assertIn(marker, payload)
        payload = payload.replace(
            marker,
            '"agreement_publication": {"agreement_record_id": "rid_agreement_01", "disposition": "DUPLICATE", "disposition": "STORED"',
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(payload, encoding="utf-8")
            with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
                load_authenticated_local_flight_evidence(path)
            self.assertEqual(caught.exception.code, "EVIDENCE_JSON_DUPLICATE_KEY")
            self.assertNotIn("rid_agreement_01", str(caught.exception))

    def test_nonstandard_json_numeric_constants_rejected(self) -> None:
        document = valid_evidence()
        canonical = json.dumps(document)
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token), tempfile.TemporaryDirectory() as directory:
                payload = canonical.replace('"ci_run_number": 958', f'"ci_run_number": {token}')
                self.assertNotEqual(payload, canonical)
                path = Path(directory) / "evidence.json"
                path.write_text(payload, encoding="utf-8")
                with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
                    load_authenticated_local_flight_evidence(path)
                self.assertEqual(caught.exception.code, "EVIDENCE_JSON_INVALID")

    def test_excessive_json_integer_returns_stable_invalid_code(self) -> None:
        canonical = json.dumps(valid_evidence())
        payload = canonical.replace(
            '"ci_run_number": 958',
            '"ci_run_number": ' + '9' * 5_000,
        )
        self.assertNotEqual(payload, canonical)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(payload, encoding="utf-8")
            with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
                load_authenticated_local_flight_evidence(path)
            self.assertEqual(caught.exception.code, "EVIDENCE_JSON_INVALID")

    def test_cli_reports_duplicate_key_with_stable_nonsecret_code(self) -> None:
        canonical = json.dumps(valid_evidence())
        payload = canonical.replace(
            '"seller_authenticated": true',
            '"seller_authenticated": false, "seller_authenticated": true',
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(payload, encoding="utf-8")
            success_out = io.StringIO()
            failure_err = io.StringIO()
            with redirect_stdout(success_out), redirect_stderr(failure_err):
                code = main([str(path)])
            self.assertEqual(code, 1)
            self.assertEqual(success_out.getvalue(), "")
            self.assertEqual(failure_err.getvalue().strip(), "status=FAIL code=EVIDENCE_JSON_DUPLICATE_KEY")
            self.assertNotIn(str(path), failure_err.getvalue())

if __name__ == "__main__":
    unittest.main()
