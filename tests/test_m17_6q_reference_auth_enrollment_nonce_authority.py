from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from marketplace.reference.auth_enrollment_nonce_authority_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAuthenticationEnrollmentNonceAuthority,
    MarketplaceReferenceAuthenticationEnrollmentNonceAuthorityError,
    build_reference_authentication_enrollment_nonce_authority,
)
from marketplace.reference.auth_enrollment_nonce_material_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource,
)


ERROR_MESSAGE = (
    "reference authentication enrollment nonce authority composition failed"
)


def _forged_graph(
    *,
    material_source: object,
    nonce_authority: object,
) -> MarketplaceReferenceAuthenticationEnrollmentNonceAuthority:
    return MarketplaceReferenceAuthenticationEnrollmentNonceAuthority(
        material_source=material_source,  # type: ignore[arg-type]
        nonce_authority=nonce_authority,  # type: ignore[arg-type]
    )


class M176QReferenceAuthenticationEnrollmentNonceAuthorityTests(unittest.TestCase):
    def test_profile_and_exact_p_to_h_graph_are_frozen(self) -> None:
        result = build_reference_authentication_enrollment_nonce_authority()

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_NONCE_AUTHORITY_V1",
        )
        self.assertIs(
            type(result),
            MarketplaceReferenceAuthenticationEnrollmentNonceAuthority,
        )
        self.assertIs(
            type(result.material_source),
            MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource,
        )
        self.assertIs(
            type(result.nonce_authority),
            MarketplaceAuthenticationEnrollmentNonceAuthority,
        )
        self.assertIs(
            result.nonce_authority._nonce_bytes.__self__,
            result.material_source,
        )
        self.assertEqual(result.nonce_authority._outstanding, {})
        self.assertEqual(result.nonce_authority._spent, {})

    def test_construction_consumes_zero_entropy(self) -> None:
        with patch(
            "marketplace.reference.auth_enrollment_nonce_material_v1._token_bytes",
            side_effect=AssertionError("entropy consumed during composition"),
        ) as entropy:
            result = build_reference_authentication_enrollment_nonce_authority()

        self.assertIs(
            result.nonce_authority._nonce_bytes.__self__,
            result.material_source,
        )
        entropy.assert_not_called()

    def test_construction_does_not_issue_or_consume_nonce(self) -> None:
        with (
            patch.object(
                MarketplaceAuthenticationEnrollmentNonceAuthority,
                "issue_authentication_enrollment_nonce",
                side_effect=AssertionError("nonce issued during composition"),
            ) as issue,
            patch.object(
                MarketplaceAuthenticationEnrollmentNonceAuthority,
                "consume_authentication_enrollment_nonce",
                side_effect=AssertionError("nonce consumed during composition"),
            ) as consume,
        ):
            result = build_reference_authentication_enrollment_nonce_authority()

        self.assertEqual(result.nonce_authority._outstanding, {})
        self.assertEqual(result.nonce_authority._spent, {})
        issue.assert_not_called()
        consume.assert_not_called()

    def test_wrong_source_or_authority_fails_stably(self) -> None:
        valid = build_reference_authentication_enrollment_nonce_authority()
        cases = (
            (object(), valid.nonce_authority),
            (valid.material_source, object()),
        )
        for source, authority in cases:
            with self.subTest(source=type(source).__name__, authority=type(authority).__name__):
                with self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentNonceAuthorityError
                ) as caught:
                    _forged_graph(
                        material_source=source,
                        nonce_authority=authority,
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)

    def test_cross_bound_source_and_nonempty_state_fail_stably(self) -> None:
        first = build_reference_authentication_enrollment_nonce_authority()
        second = build_reference_authentication_enrollment_nonce_authority()

        with self.assertRaises(
            MarketplaceReferenceAuthenticationEnrollmentNonceAuthorityError
        ) as caught:
            _forged_graph(
                material_source=first.material_source,
                nonce_authority=second.nonce_authority,
            )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)

        first.nonce_authority._outstanding[b"x" * 32] = object()  # type: ignore[assignment]
        with self.assertRaises(
            MarketplaceReferenceAuthenticationEnrollmentNonceAuthorityError
        ) as caught:
            _forged_graph(
                material_source=first.material_source,
                nonce_authority=first.nonce_authority,
            )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)


if __name__ == "__main__":
    unittest.main()
