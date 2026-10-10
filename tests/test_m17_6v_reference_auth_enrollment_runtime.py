from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from marketplace.application.auth_enrollment_runtime_server import (
    EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER,
    run_marketplace_authentication_enrollment_foreground as _run_n,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from marketplace.reference.auth_enrollment_approval_policy_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy,
)
from marketplace.reference.auth_enrollment_attestor_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
)
from marketplace.reference.auth_enrollment_launch_policy_nonce_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
)
from marketplace.reference.auth_enrollment_runtime_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAuthenticationEnrollmentForegroundRuntimeError,
    run_reference_authentication_enrollment_foreground,
)
from tests.test_m17_6u_reference_auth_enrollment_launch_policy_nonce_ed25519 import (
    _build as _build_u,
)


MODULE = "marketplace.reference.auth_enrollment_runtime_v1"
ERROR_MESSAGE = "reference authentication enrollment foreground runtime failed"


class _StringSubclass(str):
    pass


class _ProviderProbe:
    def __init__(self, *, fail: bool = False) -> None:
        self.inspections = 0
        self.calls: list[tuple[object, str, int]] = []
        self.fail = fail

    @property
    def run(self):
        self.inspections += 1

        def invoke(*, application: object, host: str, port: int) -> None:
            self.calls.append((application, host, port))
            if self.fail:
                raise RuntimeError("provider secret detail")

        return invoke


def _reference():
    result, authenticated, bindings = _build_u()
    return result, authenticated, bindings


def _forged_reference(
    source: MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
    *,
    authenticated_plan: object | None = None,
    bindings: object | None = None,
    attestor: object | None = None,
    authority: object | None = None,
    evidence_lease_seconds: object | None = None,
    launch: object | None = None,
):
    result = object.__new__(
        MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519
    )
    object.__setattr__(
        result,
        "authenticated_plan",
        source.authenticated_plan
        if authenticated_plan is None
        else authenticated_plan,
    )
    object.__setattr__(
        result,
        "bindings",
        source.bindings if bindings is None else bindings,
    )
    object.__setattr__(
        result,
        "attestor",
        source.attestor if attestor is None else attestor,
    )
    object.__setattr__(
        result,
        "authority",
        source.authority if authority is None else authority,
    )
    object.__setattr__(
        result,
        "evidence_lease_seconds",
        source.evidence_lease_seconds
        if evidence_lease_seconds is None
        else evidence_lease_seconds,
    )
    object.__setattr__(
        result,
        "launch",
        source.launch if launch is None else launch,
    )
    return result


class M176VReferenceAuthenticationEnrollmentRuntimeTests(unittest.TestCase):
    def test_profile_and_single_exact_n_delegation(self) -> None:
        reference, _, _ = _reference()
        provider = _ProviderProbe()
        expected_plan = reference.launch.launch.plan

        result = run_reference_authentication_enrollment_foreground(
            reference=reference,
            provider=provider,
            execute_token=(
                EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
            ),
        )

        self.assertIsNone(result)
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_FOREGROUND_RUNTIME_V1",
        )
        self.assertEqual(provider.inspections, 1)
        self.assertEqual(
            provider.calls,
            [(expected_plan.asgi, expected_plan.host, expected_plan.port)],
        )

    def test_wrapper_passes_exact_plan_provider_and_token_to_n_once(self) -> None:
        reference, _, _ = _reference()
        provider = _ProviderProbe()
        token = EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER

        with patch(
            f"{MODULE}.run_marketplace_authentication_enrollment_foreground",
            wraps=_run_n,
        ) as run_n:
            run_reference_authentication_enrollment_foreground(
                reference=reference,
                provider=provider,
                execute_token=token,
            )

        self.assertEqual(run_n.call_count, 1)
        self.assertIs(run_n.call_args.kwargs["plan"], reference.launch.launch.plan)
        self.assertIs(run_n.call_args.kwargs["provider"], provider)
        self.assertIs(run_n.call_args.kwargs["execute_token"], token)

    def test_wrong_token_fails_before_n_or_provider(self) -> None:
        reference, _, _ = _reference()
        bad_tokens = (
            "",
            "EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER",
            _StringSubclass(
                EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
            ),
            object(),
        )
        for token in bad_tokens:
            provider = _ProviderProbe()
            with self.subTest(kind=type(token).__name__):
                with patch(
                    f"{MODULE}.run_marketplace_authentication_enrollment_foreground"
                ) as run_n:
                    with self.assertRaises(
                        MarketplaceReferenceAuthenticationEnrollmentForegroundRuntimeError
                    ) as caught:
                        run_reference_authentication_enrollment_foreground(
                            reference=reference,
                            provider=provider,
                            execute_token=token,  # type: ignore[arg-type]
                        )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                run_n.assert_not_called()
                self.assertEqual(provider.inspections, 0)
                self.assertEqual(provider.calls, [])

    def test_cross_bound_reference_fails_before_n_or_provider(self) -> None:
        reference, _, _ = _reference()
        other, _, _ = _reference()
        invalid = (
            object(),
            _forged_reference(reference, authenticated_plan=other.authenticated_plan),
            _forged_reference(reference, bindings=other.bindings),
            _forged_reference(reference, attestor=other.attestor),
            _forged_reference(reference, authority="https://wrong.example/"),
            _forged_reference(
                reference,
                evidence_lease_seconds=reference.evidence_lease_seconds + 1,
            ),
            _forged_reference(reference, launch=other.launch),
        )
        token = EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER

        for value in invalid:
            provider = _ProviderProbe()
            with self.subTest(kind=type(value).__name__):
                with patch(
                    f"{MODULE}.run_marketplace_authentication_enrollment_foreground"
                ) as run_n:
                    with self.assertRaises(
                        MarketplaceReferenceAuthenticationEnrollmentForegroundRuntimeError
                    ):
                        run_reference_authentication_enrollment_foreground(
                            reference=value,  # type: ignore[arg-type]
                            provider=provider,
                            execute_token=token,
                        )
                run_n.assert_not_called()
                self.assertEqual(provider.inspections, 0)

    def test_validation_consumes_no_enrollment_authority_before_n(self) -> None:
        reference, _, _ = _reference()
        provider = _ProviderProbe()
        token = EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER

        with (
            patch.object(
                MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
                "attest_authentication_enrollment",
                side_effect=AssertionError("attestation used"),
            ) as attest,
            patch(
                "marketplace.reference.auth_enrollment_nonce_material_v1._token_bytes",
                side_effect=AssertionError("entropy used"),
            ) as entropy,
            patch.object(
                MarketplaceAuthenticationEnrollmentNonceAuthority,
                "issue_authentication_enrollment_nonce",
                side_effect=AssertionError("nonce issued"),
            ) as issue_nonce,
            patch.object(
                MarketplaceAuthenticationEnrollmentNonceAuthority,
                "consume_authentication_enrollment_nonce",
                side_effect=AssertionError("nonce consumed"),
            ) as consume_nonce,
            patch.object(
                MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy,
                "approve_authentication_enrollment",
                side_effect=AssertionError("policy used"),
            ) as policy,
            patch.object(
                MarketplaceSessionEstablishmentAsgiHttpAdapter,
                "__call__",
                side_effect=AssertionError("request handled"),
            ) as request,
            patch("socket.socket", side_effect=AssertionError("socket used")) as socket,
            patch(
                f"{MODULE}.run_marketplace_authentication_enrollment_foreground"
            ) as run_n,
        ):
            run_reference_authentication_enrollment_foreground(
                reference=reference,
                provider=provider,
                execute_token=token,
            )

        attest.assert_not_called()
        entropy.assert_not_called()
        issue_nonce.assert_not_called()
        consume_nonce.assert_not_called()
        policy.assert_not_called()
        request.assert_not_called()
        socket.assert_not_called()
        self.assertEqual(run_n.call_count, 1)
        self.assertEqual(provider.inspections, 0)
        self.assertEqual(provider.calls, [])

    def test_n_or_provider_failure_collapses_to_stable_v_error(self) -> None:
        reference, _, _ = _reference()
        token = EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER

        with patch(
            f"{MODULE}.run_marketplace_authentication_enrollment_foreground",
            side_effect=RuntimeError("nested provider detail"),
        ):
            with self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentForegroundRuntimeError
            ) as caught:
                run_reference_authentication_enrollment_foreground(
                    reference=reference,
                    provider=_ProviderProbe(),
                    execute_token=token,
                )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("nested provider detail", str(caught.exception))

        provider = _ProviderProbe(fail=True)
        with self.assertRaises(
            MarketplaceReferenceAuthenticationEnrollmentForegroundRuntimeError
        ) as caught:
            run_reference_authentication_enrollment_foreground(
                reference=reference,
                provider=provider,
                execute_token=token,
            )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("provider secret detail", str(caught.exception))
        self.assertEqual(provider.inspections, 1)
        self.assertEqual(len(provider.calls), 1)


if __name__ == "__main__":
    unittest.main()
