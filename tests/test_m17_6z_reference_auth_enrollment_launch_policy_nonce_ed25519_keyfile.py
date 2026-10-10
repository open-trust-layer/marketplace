from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from marketplace.application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
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
from marketplace.reference.auth_enrollment_attestor_keyfile_v1 import (
    AUTH_ENROLLMENT_ED25519_KEY_FILENAME,
    load_reference_authentication_enrollment_ed25519_attestor as _load_x,
)
from marketplace.reference.auth_enrollment_launch_policy_nonce_ed25519_attestor_v1 import (
    build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor as _build_y,
)
from marketplace.reference.auth_enrollment_launch_policy_nonce_ed25519_keyfile_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileCompositionError,
    build_reference_authentication_enrollment_launch_policy_nonce_ed25519_keyfile,
)
from marketplace.reference.auth_enrollment_launch_policy_nonce_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
)
from tests.test_m17_6i_auth_enrollment_http import LEASE_SECONDS
from tests.test_m17_6o_reference_auth_enrollment_launch import _inputs as _o_inputs
from tests.test_m17_6r_reference_auth_enrollment_approval_policy import (
    AUTHORITY,
    binding,
)


MODULE = (
    "marketplace.reference."
    "auth_enrollment_launch_policy_nonce_ed25519_keyfile_v1"
)
PRIVATE_KEY = bytes(range(32))
ERROR_MESSAGE = (
    "reference authentication enrollment Ed25519 keyfile composition failed"
)


def _inputs():
    authenticated, _source, _old_nonce, _old_policy, _old_attestor = _o_inputs()
    return authenticated, (binding(),)


def _write_key(directory: Path) -> None:
    (directory / AUTH_ENROLLMENT_ED25519_KEY_FILENAME).write_bytes(PRIVATE_KEY)


class M176ZReferenceAuthenticationEnrollmentEd25519KeyfileCompositionTests(
    unittest.TestCase
):
    def test_profile_and_real_x_to_y_to_u_integration(self) -> None:
        authenticated, bindings = _inputs()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_key(root)
            result = (
                build_reference_authentication_enrollment_launch_policy_nonce_ed25519_keyfile(
                    authenticated_plan=authenticated,
                    bindings=bindings,
                    directory=str(root),
                    authority=AUTHORITY,
                    evidence_lease_seconds=LEASE_SECONDS,
                )
            )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_"
            "LAUNCH_POLICY_NONCE_ED25519_KEYFILE_V1",
        )
        self.assertIs(
            type(result),
            MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
        )
        self.assertIs(
            type(result.attestor),
            MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
        )
        self.assertIs(result.authenticated_plan, authenticated)
        self.assertIs(result.bindings, bindings)
        self.assertIs(result.launch.attestor, result.attestor)
        self.assertIs(result.launch.launch.attestor, result.attestor)
        self.assertEqual(result.authority, AUTHORITY)
        self.assertEqual(result.evidence_lease_seconds, LEASE_SECONDS)
        self.assertFalse(hasattr(result, "private_key_bytes"))
        self.assertFalse(hasattr(result, "_private_key_bytes"))

    def test_calls_x_once_then_y_once_with_exact_values(self) -> None:
        authenticated, bindings = _inputs()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_key(root)
            with (
                patch(
                    f"{MODULE}.load_reference_authentication_enrollment_ed25519_attestor",
                    wraps=_load_x,
                ) as load_x,
                patch(
                    f"{MODULE}."
                    "build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor",
                    wraps=_build_y,
                ) as build_y,
            ):
                result = (
                    build_reference_authentication_enrollment_launch_policy_nonce_ed25519_keyfile(
                        authenticated_plan=authenticated,
                        bindings=bindings,
                        directory=str(root),
                        authority=AUTHORITY,
                        evidence_lease_seconds=LEASE_SECONDS,
                    )
                )

        load_x.assert_called_once_with(directory=str(root))
        self.assertEqual(build_y.call_count, 1)
        self.assertIs(build_y.call_args.kwargs["authenticated_plan"], authenticated)
        self.assertIs(build_y.call_args.kwargs["bindings"], bindings)
        self.assertIs(
            build_y.call_args.kwargs["attestor"],
            result.attestor,
        )
        self.assertEqual(build_y.call_args.kwargs["authority"], AUTHORITY)
        self.assertEqual(
            build_y.call_args.kwargs["evidence_lease_seconds"],
            LEASE_SECONDS,
        )

    def test_x_failure_collapses_and_y_is_not_called(self) -> None:
        authenticated, bindings = _inputs()
        with (
            patch(
                f"{MODULE}.load_reference_authentication_enrollment_ed25519_attestor",
                side_effect=RuntimeError("sensitive path detail"),
            ),
            patch(
                f"{MODULE}."
                "build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor"
            ) as build_y,
            self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileCompositionError
            ) as caught,
        ):
            build_reference_authentication_enrollment_launch_policy_nonce_ed25519_keyfile(
                authenticated_plan=authenticated,
                bindings=bindings,
                directory="/sensitive/key/path",
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("sensitive path detail", str(caught.exception))
        self.assertNotIn("/sensitive/key/path", str(caught.exception))
        build_y.assert_not_called()

    def test_y_failure_collapses_without_reflection(self) -> None:
        authenticated, bindings = _inputs()
        attestor = MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor(
            private_key_bytes=PRIVATE_KEY
        )
        with (
            patch(
                f"{MODULE}.load_reference_authentication_enrollment_ed25519_attestor",
                return_value=attestor,
            ),
            patch(
                f"{MODULE}."
                "build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor",
                side_effect=RuntimeError("nested Y detail"),
            ),
            self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileCompositionError
            ) as caught,
        ):
            build_reference_authentication_enrollment_launch_policy_nonce_ed25519_keyfile(
                authenticated_plan=authenticated,
                bindings=bindings,
                directory="/synthetic",
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("nested Y detail", str(caught.exception))

    def test_wrong_y_result_type_fails_closed(self) -> None:
        authenticated, bindings = _inputs()
        attestor = MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor(
            private_key_bytes=PRIVATE_KEY
        )
        with (
            patch(
                f"{MODULE}.load_reference_authentication_enrollment_ed25519_attestor",
                return_value=attestor,
            ),
            patch(
                f"{MODULE}."
                "build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor",
                return_value=object(),
            ),
            self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileCompositionError
            ) as caught,
        ):
            build_reference_authentication_enrollment_launch_policy_nonce_ed25519_keyfile(
                authenticated_plan=authenticated,
                bindings=bindings,
                directory="/synthetic",
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

        self.assertEqual(str(caught.exception), ERROR_MESSAGE)

    def test_composition_does_not_consume_enrollment_authority_or_runtime(self) -> None:
        authenticated, bindings = _inputs()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_key(root)
            with (
                patch.object(
                    MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
                    "attest_authentication_enrollment",
                    side_effect=AssertionError("attestation used"),
                ) as attest,
                patch(
                    "marketplace.reference.auth_enrollment_nonce_material_v1._token_bytes",
                    side_effect=AssertionError("entropy consumed"),
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
                    side_effect=AssertionError("policy decision"),
                ) as decide,
                patch.object(
                    MarketplaceSessionEstablishmentAsgiHttpAdapter,
                    "__call__",
                    side_effect=AssertionError("request handled"),
                ) as request,
                patch(
                    "marketplace.application.auth_enrollment_runtime_server."
                    "run_marketplace_authentication_enrollment_foreground",
                    side_effect=AssertionError("runtime executed"),
                ) as runtime,
                patch(
                    "marketplace.application.uvicorn_provider."
                    "UvicornLoopbackServerProvider.run",
                    side_effect=AssertionError("provider invoked"),
                ) as provider,
                patch("socket.socket", side_effect=AssertionError("socket used")) as socket,
            ):
                result = (
                    build_reference_authentication_enrollment_launch_policy_nonce_ed25519_keyfile(
                        authenticated_plan=authenticated,
                        bindings=bindings,
                        directory=str(root),
                        authority=AUTHORITY,
                        evidence_lease_seconds=LEASE_SECONDS,
                    )
                )

        attest.assert_not_called()
        entropy.assert_not_called()
        issue_nonce.assert_not_called()
        consume_nonce.assert_not_called()
        decide.assert_not_called()
        request.assert_not_called()
        runtime.assert_not_called()
        provider.assert_not_called()
        socket.assert_not_called()
        self.assertEqual(result.launch.nonce.nonce_authority._outstanding, {})
        self.assertEqual(result.launch.nonce.nonce_authority._spent, {})


if __name__ == "__main__":
    unittest.main()
