from __future__ import annotations

import unittest
from unittest.mock import call, patch

from marketplace.application.auth_enrollment_coordination import (
    AUTH_ENROLLMENT_NONCE_BYTES,
)
from marketplace.reference.auth_enrollment_nonce_material_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAuthenticationEnrollmentNonceMaterialError,
    MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource,
)


NONCE = bytes(range(AUTH_ENROLLMENT_NONCE_BYTES))
ERROR_MESSAGE = "reference authentication enrollment nonce material failed"


class M176PReferenceAuthenticationEnrollmentNonceMaterialTests(unittest.TestCase):
    def test_profile_source_and_exact_existing_size_are_frozen(self) -> None:
        source = MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource()
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_NONCE_MATERIAL_V1",
        )
        self.assertEqual(AUTH_ENROLLMENT_NONCE_BYTES, 32)
        self.assertEqual(
            MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource.__slots__,
            (),
        )
        self.assertFalse(hasattr(source, "__dict__"))

    def test_constructor_and_import_consume_no_entropy(self) -> None:
        with patch(
            "marketplace.reference.auth_enrollment_nonce_material_v1._token_bytes",
            side_effect=AssertionError("entropy consumed"),
        ) as generator:
            source = MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource()
            self.assertIs(
                type(source),
                MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource,
            )
        generator.assert_not_called()

    def test_explicit_call_uses_one_exact_csprng_call(self) -> None:
        source = MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource()
        with patch(
            "marketplace.reference.auth_enrollment_nonce_material_v1._token_bytes",
            return_value=NONCE,
        ) as generator:
            result = source.enrollment_nonce_bytes()
        self.assertEqual(result, NONCE)
        self.assertIs(type(result), bytes)
        self.assertEqual(generator.call_args_list, [call(32)])

    def test_malformed_material_fails_stably_without_reflection(self) -> None:
        source = MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource()
        malformed = (
            bytearray(NONCE),
            b"x" * 31,
            b"y" * 33,
        )
        for value in malformed:
            with self.subTest(value_type=type(value).__name__, length=len(value)):
                with patch(
                    "marketplace.reference.auth_enrollment_nonce_material_v1._token_bytes",
                    return_value=value,
                ) as generator:
                    with self.assertRaises(
                        MarketplaceReferenceAuthenticationEnrollmentNonceMaterialError
                    ) as caught:
                        source.enrollment_nonce_bytes()
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                self.assertNotIn(repr(value), str(caught.exception))
                generator.assert_called_once_with(32)

    def test_csprng_failure_is_stable_not_retried_and_not_reflected(self) -> None:
        source = MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource()
        with patch(
            "marketplace.reference.auth_enrollment_nonce_material_v1._token_bytes",
            side_effect=RuntimeError("synthetic entropy provider detail"),
        ) as generator:
            with self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentNonceMaterialError
            ) as caught:
                source.enrollment_nonce_bytes()
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("synthetic entropy provider detail", str(caught.exception))
        generator.assert_called_once_with(32)


if __name__ == "__main__":
    unittest.main()
