from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.auth_enrollment_runtime_server import (
    EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER,
)
from marketplace.application.uvicorn_provider import UvicornLoopbackServerProvider
from marketplace.reference.auth_enrollment_runtime_uvicorn_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAuthenticationEnrollmentUvicornRuntimeError,
    run_reference_authentication_enrollment_uvicorn_foreground,
)
from tests.test_m17_6u_reference_auth_enrollment_launch_policy_nonce_ed25519 import (
    _build as _build_u,
)


MODULE = "marketplace.reference.auth_enrollment_runtime_uvicorn_v1"
ERROR_MESSAGE = "reference authentication enrollment Uvicorn runtime failed"


class _StringSubclass(str):
    pass


class _ProviderSentinel:
    pass


def _reference():
    result, _, _ = _build_u()
    return result


class M176WReferenceAuthenticationEnrollmentRuntimeUvicornTests(
    unittest.TestCase
):
    def test_profile_selects_one_provider_and_delegates_once_to_v(self) -> None:
        reference = _reference()
        provider = _ProviderSentinel()
        token = EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER

        with (
            patch(
                f"{MODULE}.UvicornLoopbackServerProvider",
                return_value=provider,
            ) as build_provider,
            patch(
                f"{MODULE}.run_reference_authentication_enrollment_foreground"
            ) as run_v,
        ):
            result = run_reference_authentication_enrollment_uvicorn_foreground(
                reference=reference,
                execute_token=token,
            )

        self.assertIsNone(result)
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_UVICORN_RUNTIME_V1",
        )
        build_provider.assert_called_once_with()
        run_v.assert_called_once_with(
            reference=reference,
            provider=provider,
            execute_token=token,
        )

    def test_wrong_token_fails_before_provider_construction_or_v(self) -> None:
        reference = _reference()
        invalid = (
            "",
            "EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER",
            _StringSubclass(
                EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
            ),
            object(),
        )
        for token in invalid:
            with self.subTest(kind=type(token).__name__):
                with (
                    patch(f"{MODULE}.UvicornLoopbackServerProvider") as build_provider,
                    patch(
                        f"{MODULE}.run_reference_authentication_enrollment_foreground"
                    ) as run_v,
                    self.assertRaises(
                        MarketplaceReferenceAuthenticationEnrollmentUvicornRuntimeError
                    ) as caught,
                ):
                    run_reference_authentication_enrollment_uvicorn_foreground(
                        reference=reference,
                        execute_token=token,  # type: ignore[arg-type]
                    )

                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                build_provider.assert_not_called()
                run_v.assert_not_called()

    def test_wrong_reference_type_fails_before_provider_construction_or_v(self) -> None:
        token = EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
        with (
            patch(f"{MODULE}.UvicornLoopbackServerProvider") as build_provider,
            patch(
                f"{MODULE}.run_reference_authentication_enrollment_foreground"
            ) as run_v,
            self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentUvicornRuntimeError
            ) as caught,
        ):
            run_reference_authentication_enrollment_uvicorn_foreground(
                reference=object(),  # type: ignore[arg-type]
                execute_token=token,
            )

        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        build_provider.assert_not_called()
        run_v.assert_not_called()

    def test_provider_constructor_failure_is_stable_and_nonreflective(self) -> None:
        reference = _reference()
        token = EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
        with (
            patch(
                f"{MODULE}.UvicornLoopbackServerProvider",
                side_effect=RuntimeError("provider constructor secret"),
            ),
            patch(
                f"{MODULE}.run_reference_authentication_enrollment_foreground"
            ) as run_v,
            self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentUvicornRuntimeError
            ) as caught,
        ):
            run_reference_authentication_enrollment_uvicorn_foreground(
                reference=reference,
                execute_token=token,
            )

        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("constructor secret", str(caught.exception))
        run_v.assert_not_called()

    def test_v_failure_is_stable_nonreflective_and_not_retried(self) -> None:
        reference = _reference()
        provider = _ProviderSentinel()
        token = EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
        with (
            patch(
                f"{MODULE}.UvicornLoopbackServerProvider",
                return_value=provider,
            ) as build_provider,
            patch(
                f"{MODULE}.run_reference_authentication_enrollment_foreground",
                side_effect=RuntimeError("nested runtime secret"),
            ) as run_v,
            self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentUvicornRuntimeError
            ) as caught,
        ):
            run_reference_authentication_enrollment_uvicorn_foreground(
                reference=reference,
                execute_token=token,
            )

        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("nested runtime secret", str(caught.exception))
        build_provider.assert_called_once_with()
        self.assertEqual(run_v.call_count, 1)

    def test_real_provider_constructor_is_inert_before_patched_v(self) -> None:
        reference = _reference()
        token = EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER

        with (
            patch(
                "marketplace.application.uvicorn_provider.import_module",
                side_effect=AssertionError("uvicorn imported"),
            ) as loader,
            patch("socket.socket", side_effect=AssertionError("socket opened")) as socket,
            patch(
                f"{MODULE}.run_reference_authentication_enrollment_foreground"
            ) as run_v,
        ):
            run_reference_authentication_enrollment_uvicorn_foreground(
                reference=reference,
                execute_token=token,
            )

        loader.assert_not_called()
        socket.assert_not_called()
        self.assertEqual(run_v.call_count, 1)
        provider = run_v.call_args.kwargs["provider"]
        self.assertIs(type(provider), UvicornLoopbackServerProvider)
        self.assertIs(run_v.call_args.kwargs["reference"], reference)
        self.assertIs(run_v.call_args.kwargs["execute_token"], token)


if __name__ == "__main__":
    unittest.main()
