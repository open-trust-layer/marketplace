from __future__ import annotations

import base64
import unittest

from marketplace.reference.auth_enrollment_approval_policy_v1 import (
    PROFILE_NAME,
    REFERENCE_AUTH_ENROLLMENT_APPROVAL_MAX_BINDINGS,
    MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
    MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy,
    MarketplaceReferenceAuthenticationEnrollmentApprovalPolicyError,
)


AUTHORITY = "https://authority.example/auth-enrollment"
OTHER_AUTHORITY = "https://other-authority.example/auth-enrollment"
PRINCIPAL = "did:example:alice"
OTHER_PRINCIPAL = "did:example:bob"
METHOD = "did:example:alice#key-1"
OTHER_METHOD = "did:example:alice#key-2"
KEY_BYTES = bytes(range(32))
OTHER_KEY_BYTES = bytes(reversed(range(32)))


def _carrier(raw: bytes) -> str:
    return "mkp1_" + base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


PUBLIC_KEY = _carrier(KEY_BYTES)
OTHER_PUBLIC_KEY = _carrier(OTHER_KEY_BYTES)
ERROR_MESSAGE = "reference authentication enrollment approval policy failed"


def binding(
    *,
    principal: str = PRINCIPAL,
    verification_method: str = METHOD,
    public_key: str = PUBLIC_KEY,
    authority: str = AUTHORITY,
) -> MarketplaceReferenceAuthenticationEnrollmentApprovalBinding:
    return MarketplaceReferenceAuthenticationEnrollmentApprovalBinding(
        principal=principal,
        verification_method=verification_method,
        public_key=public_key,
        authority=authority,
    )


def policy(
    *bindings: MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
) -> MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy:
    if not bindings:
        bindings = (binding(),)
    return MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy(
        bindings=tuple(bindings),
    )


def decision_kwargs() -> dict[str, object]:
    return {
        "principal": PRINCIPAL,
        "verification_method": METHOD,
        "public_key": PUBLIC_KEY,
        "authority": AUTHORITY,
        "issued_at": 100,
        "expires_at": 200,
    }


class M176RReferenceAuthenticationEnrollmentApprovalPolicyTests(unittest.TestCase):
    def test_profile_bound_and_exact_immutable_binding_are_frozen(self) -> None:
        value = binding()

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_APPROVAL_POLICY_V1",
        )
        self.assertEqual(REFERENCE_AUTH_ENROLLMENT_APPROVAL_MAX_BINDINGS, 256)
        self.assertIs(
            type(value),
            MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
        )
        self.assertEqual(value.principal, PRINCIPAL)
        self.assertEqual(value.verification_method, METHOD)
        self.assertEqual(value.public_key, PUBLIC_KEY)
        self.assertEqual(value.authority, AUTHORITY)
        with self.assertRaises((AttributeError, TypeError)):
            value.principal = OTHER_PRINCIPAL  # type: ignore[misc]

    def test_binding_reuses_reviewed_identity_key_and_authority_validation(self) -> None:
        cases = (
            {"principal": "relative"},
            {"verification_method": "relative"},
            {"public_key": PUBLIC_KEY + "="},
            {"authority": "relative"},
            {"principal": True},
            {"verification_method": b"not-text"},
            {"public_key": object()},
            {"authority": None},
        )
        for changes in cases:
            kwargs = {
                "principal": PRINCIPAL,
                "verification_method": METHOD,
                "public_key": PUBLIC_KEY,
                "authority": AUTHORITY,
            }
            kwargs.update(changes)
            with self.subTest(changes=changes):
                with self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentApprovalPolicyError
                ) as caught:
                    MarketplaceReferenceAuthenticationEnrollmentApprovalBinding(
                        **kwargs  # type: ignore[arg-type]
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)

    def test_policy_requires_exact_nonempty_bounded_unique_tuple(self) -> None:
        one = binding()
        with self.assertRaises(
            MarketplaceReferenceAuthenticationEnrollmentApprovalPolicyError
        ):
            MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy(bindings=())

        with self.assertRaises(
            MarketplaceReferenceAuthenticationEnrollmentApprovalPolicyError
        ):
            MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy(
                bindings=[one]  # type: ignore[arg-type]
            )

        with self.assertRaises(
            MarketplaceReferenceAuthenticationEnrollmentApprovalPolicyError
        ):
            MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy(
                bindings=(one, one)
            )

        with self.assertRaises(
            MarketplaceReferenceAuthenticationEnrollmentApprovalPolicyError
        ):
            MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy(
                bindings=(object(),)  # type: ignore[arg-type]
            )

        many = tuple(
            binding(
                verification_method=f"did:example:alice#key-{index}",
            )
            for index in range(REFERENCE_AUTH_ENROLLMENT_APPROVAL_MAX_BINDINGS + 1)
        )
        with self.assertRaises(
            MarketplaceReferenceAuthenticationEnrollmentApprovalPolicyError
        ):
            MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy(bindings=many)

    def test_exact_match_returns_true_and_valid_nonmatches_return_false(self) -> None:
        value = policy(binding())
        kwargs = decision_kwargs()

        self.assertIs(value.approve_authentication_enrollment(**kwargs), True)

        cases = (
            {"principal": OTHER_PRINCIPAL},
            {"verification_method": OTHER_METHOD},
            {"public_key": OTHER_PUBLIC_KEY},
            {"authority": OTHER_AUTHORITY},
        )
        for changes in cases:
            changed = dict(kwargs)
            changed.update(changes)
            with self.subTest(changes=changes):
                self.assertIs(
                    value.approve_authentication_enrollment(
                        **changed  # type: ignore[arg-type]
                    ),
                    False,
                )

    def test_valid_lease_is_not_an_approval_selector(self) -> None:
        value = policy(binding())

        first = decision_kwargs()
        first["issued_at"] = 0
        first["expires_at"] = 1
        second = decision_kwargs()
        second["issued_at"] = 10_000
        second["expires_at"] = 10_100

        self.assertIs(
            value.approve_authentication_enrollment(
                **first  # type: ignore[arg-type]
            ),
            True,
        )
        self.assertIs(
            value.approve_authentication_enrollment(
                **second  # type: ignore[arg-type]
            ),
            True,
        )

    def test_malformed_decision_inputs_fail_with_stable_nonreflective_error(self) -> None:
        value = policy(binding())
        cases = (
            {"principal": "relative"},
            {"verification_method": "relative"},
            {"public_key": "mkp1_bad"},
            {"authority": "relative"},
            {"issued_at": True},
            {"issued_at": -1},
            {"expires_at": 100},
            {"expires_at": 100 + 86401},
        )
        for changes in cases:
            kwargs = decision_kwargs()
            kwargs.update(changes)
            with self.subTest(changes=changes):
                with self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentApprovalPolicyError
                ) as caught:
                    value.approve_authentication_enrollment(
                        **kwargs  # type: ignore[arg-type]
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                self.assertNotIn("relative", str(caught.exception))
                self.assertNotIn("mkp1_bad", str(caught.exception))

    def test_no_prefix_wildcard_or_normalization_semantics(self) -> None:
        value = policy(binding())
        for changes in (
            {"principal": PRINCIPAL + ":child"},
            {"verification_method": METHOD + "-suffix"},
            {"authority": AUTHORITY + "/"},
        ):
            kwargs = decision_kwargs()
            kwargs.update(changes)
            with self.subTest(changes=changes):
                self.assertIs(
                    value.approve_authentication_enrollment(
                        **kwargs  # type: ignore[arg-type]
                    ),
                    False,
                )


if __name__ == "__main__":
    unittest.main()
