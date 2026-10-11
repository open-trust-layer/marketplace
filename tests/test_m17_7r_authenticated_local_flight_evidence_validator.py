from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import stat
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from tools.marketplace_authenticated_local_flight_evidence import (
    AuthenticatedLocalFlightEvidenceError,
    MAX_EVIDENCE_BYTES,
    MAX_SAFE_INTEGER,
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

    def test_javascript_safe_integer_bounds_match_browser_projection(self) -> None:
        # The Web producer uses Number.isSafeInteger for every numeric field.
        valid = valid_evidence()
        valid["ci_run_number"] = MAX_SAFE_INTEGER
        publication = valid["agreement_publication"]
        completion = valid["completion"]
        assert type(publication) is dict and type(completion) is dict
        publication["change_seq"] = MAX_SAFE_INTEGER
        completion["change_seq"] = MAX_SAFE_INTEGER
        validate_authenticated_local_flight_evidence(valid)

        invalid_ci = (0, -1, MAX_SAFE_INTEGER + 1, 1.0, True, "1")
        for bad in invalid_ci:
            with self.subTest(field="ci_run_number", value=bad):
                record = valid_evidence()
                record["ci_run_number"] = bad
                self.assert_code(record, "EVIDENCE_CI_RUN_INVALID")

        invalid_sequence = (0, -1, MAX_SAFE_INTEGER + 1, 1.0, True, "1")
        for field in ("agreement_publication", "completion"):
            for bad in invalid_sequence:
                with self.subTest(field=field, value=bad):
                    record = valid_evidence()
                    nested = record[field]
                    assert type(nested) is dict
                    nested["change_seq"] = bad
                    self.assert_code(record, "EVIDENCE_CHANGE_SEQ_INVALID")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out-of-range.json"
            record = valid_evidence()
            record["ci_run_number"] = MAX_SAFE_INTEGER + 1
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
                load_authenticated_local_flight_evidence(path)
            self.assertEqual(caught.exception.code, "EVIDENCE_CI_RUN_INVALID")

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


    def test_file_limit_accepts_exact_size_and_rejects_one_extra_byte(self) -> None:
        canonical = json.dumps(valid_evidence()).encode("utf-8")
        self.assertLess(len(canonical), MAX_EVIDENCE_BYTES)
        exact_limit = canonical + b" " * (MAX_EVIDENCE_BYTES - len(canonical))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_bytes(exact_limit)
            self.assertEqual(
                load_authenticated_local_flight_evidence(path)["agreement_record_id"],
                "rid_agreement_01",
            )
            path.write_bytes(exact_limit + b" ")
            with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
                load_authenticated_local_flight_evidence(path)
            self.assertEqual(caught.exception.code, "EVIDENCE_FILE_TOO_LARGE")

    def test_oversized_evidence_never_causes_unbounded_file_read(self) -> None:
        requested: list[int] = []

        class ReadSpy(io.BytesIO):
            def read(self, size: int = -1) -> bytes:
                requested.append(size)
                if size < 0 or size > MAX_EVIDENCE_BYTES + 1:
                    raise AssertionError("unbounded evidence read")
                return super().read(size)

        reader = ReadSpy(b"x" * (MAX_EVIDENCE_BYTES + 4096))
        with patch.object(
            Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFREG)
        ), patch.object(Path, "open", return_value=reader) as mocked_open:
            with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
                load_authenticated_local_flight_evidence("evidence.json")
        mocked_open.assert_called_once_with("rb")
        self.assertEqual(requested, [MAX_EVIDENCE_BYTES + 1])
        self.assertEqual(caught.exception.code, "EVIDENCE_FILE_TOO_LARGE")

    def test_evidence_read_failure_is_stable_without_path_reflection(self) -> None:
        with patch.object(
            Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFREG)
        ), patch.object(Path, "open", side_effect=OSError("sensitive path")):
            with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
                load_authenticated_local_flight_evidence("secret-evidence.json")
        self.assertEqual(caught.exception.code, "EVIDENCE_FILE_UNAVAILABLE")
        self.assertNotIn("sensitive path", str(caught.exception))
        self.assertNotIn("secret-evidence.json", str(caught.exception))

    def test_malformed_path_metadata_valueerror_is_stable_and_does_not_open(self) -> None:
        # pathlib may raise ValueError (for example from an embedded NUL)
        # rather than OSError. Path names and exception text stay private.
        with patch.object(
            Path, "lstat", side_effect=ValueError("private filename metadata")
        ), patch.object(
            Path, "open", side_effect=AssertionError("must not open")
        ) as opened:
            with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
                load_authenticated_local_flight_evidence("sensitive-evidence.json")
        self.assertEqual(caught.exception.code, "EVIDENCE_FILE_UNAVAILABLE")
        self.assertNotIn("private filename", str(caught.exception))
        self.assertNotIn("sensitive-evidence.json", str(caught.exception))
        opened.assert_not_called()

    def test_malformed_path_open_valueerror_has_stable_cli_failure(self) -> None:
        with patch.object(
            Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFREG)
        ), patch.object(
            Path, "open", side_effect=ValueError("secret local path")
        ):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(main(["private-evidence.json"]), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue().strip(), "status=FAIL code=EVIDENCE_FILE_UNAVAILABLE")
        self.assertNotIn("secret local path", stderr.getvalue())
        self.assertNotIn("private-evidence.json", stderr.getvalue())

    def test_nonregular_evidence_refused_without_opening_path(self) -> None:
        # Pure metadata mocks work on Windows where symlink/FIFO creation
        # often needs elevated privileges. No input path is opened.
        for kind in (stat.S_IFLNK, stat.S_IFDIR, stat.S_IFIFO, stat.S_IFCHR):
            with self.subTest(kind=kind):
                with patch.object(
                    Path, "lstat", return_value=SimpleNamespace(st_mode=kind)
                ), patch.object(
                    Path, "open", side_effect=AssertionError("must not open")
                ) as opened:
                    with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
                        load_authenticated_local_flight_evidence("sensitive-evidence.json")
                self.assertEqual(caught.exception.code, "EVIDENCE_FILE_UNAVAILABLE")
                self.assertNotIn("sensitive-evidence.json", str(caught.exception))
                opened.assert_not_called()

    def test_evidence_metadata_error_fails_closed_without_open(self) -> None:
        with patch.object(
            Path, "lstat", side_effect=OSError("private-raw-path")
        ), patch.object(
            Path, "open", side_effect=AssertionError("must not open")
        ) as opened:
            with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
                load_authenticated_local_flight_evidence("sensitive-evidence.json")
        self.assertEqual(caught.exception.code, "EVIDENCE_FILE_UNAVAILABLE")
        self.assertNotIn("private-raw-path", str(caught.exception))
        opened.assert_not_called()

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

    def test_deeply_nested_json_under_file_limit_fails_with_stable_cli_code(self) -> None:
        # A byte-bounded file can still exceed the JSON parser's nesting depth.
        payload = "[" * 10_000 + "0" + "]" * 10_000
        self.assertLess(len(payload.encode("utf-8")), MAX_EVIDENCE_BYTES)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private-auth-evidence.json"
            path.write_text(payload, encoding="utf-8")
            with self.assertRaises(AuthenticatedLocalFlightEvidenceError) as caught:
                load_authenticated_local_flight_evidence(path)
            self.assertEqual(caught.exception.code, "EVIDENCE_JSON_INVALID")
            self.assertNotIn(str(path), str(caught.exception))

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(main([str(path)]), 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(stderr.getvalue().strip(), "status=FAIL code=EVIDENCE_JSON_INVALID")
            self.assertNotIn(str(path), stderr.getvalue())

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
