from __future__ import annotations

import math
import unittest

from marketplace.runtime.page_hydration import (
    BoundedFederationPageHydrator,
    FederationPageHydrationError,
    PageHydrationLimits,
    _finite_clock_value,
)
from marketplace.runtime.record_retrieval import RetrievedRecordTransportResult


EXPECTED_ID = "r1_" + ("A" * 43)


def valid_result(**overrides):
    values = {
        "expected_record_identity": EXPECTED_ID,
        "response_envelope": ("OLP-TRANSPORT", 1, "record", {}),
        "http_status": 200,
        "response_body_bytes": 1,
        "selected_address": "1.1.1.1",
        "tls_server_hostname": "records.example.com",
    }
    values.update(overrides)
    return RetrievedRecordTransportResult(**values)


class PageHydrationHardeningTests(unittest.TestCase):
    def test_limits_reject_nonfinite_time_budget(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    PageHydrationLimits(total_timeout_seconds=value)

    def test_clock_values_must_be_finite_non_boolean_numbers(self):
        for value in (True, False, "1", None, float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(FederationPageHydrationError) as caught:
                    _finite_clock_value(value)
                self.assertEqual(caught.exception.code, "INVALID_MONOTONIC_CLOCK")
        self.assertEqual(_finite_clock_value(0), 0.0)
        self.assertTrue(math.isfinite(_finite_clock_value(1.25)))

    def test_boolean_connection_attempt_cannot_impersonate_integer_one(self):
        with self.assertRaises(FederationPageHydrationError) as caught:
            BoundedFederationPageHydrator._validate_transport_result(
                valid_result(connection_attempts=True),
                expected_record_identity=EXPECTED_ID,
            )
        self.assertEqual(caught.exception.code, "RETRIEVAL_ATTEMPT_INVARIANT")

    def test_boolean_redirect_or_retry_cannot_impersonate_integer_zero(self):
        for field in ("redirects_followed", "retries_performed"):
            with self.subTest(field=field):
                with self.assertRaises(FederationPageHydrationError) as caught:
                    BoundedFederationPageHydrator._validate_transport_result(
                        valid_result(**{field: False}),
                        expected_record_identity=EXPECTED_ID,
                    )
                self.assertEqual(caught.exception.code, "RETRIEVAL_REPLAY_INVARIANT")

    def test_boolean_http_status_cannot_impersonate_integer_status(self):
        with self.assertRaises(FederationPageHydrationError) as caught:
            BoundedFederationPageHydrator._validate_transport_result(
                valid_result(http_status=True),
                expected_record_identity=EXPECTED_ID,
            )
        self.assertEqual(caught.exception.code, "INVALID_RETRIEVAL_RESULT")

    def test_boolean_envelope_version_cannot_impersonate_integer_one(self):
        with self.assertRaises(FederationPageHydrationError) as caught:
            BoundedFederationPageHydrator._validate_transport_result(
                valid_result(response_envelope=("OLP-TRANSPORT", True, "record", {})),
                expected_record_identity=EXPECTED_ID,
            )
        self.assertEqual(caught.exception.code, "INVALID_RETRIEVAL_RESULT")


if __name__ == "__main__":
    unittest.main()
