from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import Mock, patch

from marketplace.application.auth import (
    AUTH_CHALLENGE_BYTES,
    AUTH_SESSION_TOKEN_BYTES,
)
from marketplace.application.auth_material import MarketplaceCredentialMaterialSource
from marketplace.application.auth_runtime_inputs import (
    PROFILE_NAME,
    MarketplaceAuthenticationRuntimeInputError,
    MarketplaceAuthenticationRuntimeInputs,
    MarketplaceAuthenticationUnixClock,
    compose_marketplace_authentication_runtime_inputs,
)


ERROR_MESSAGE = "authentication runtime input is invalid or unavailable"


class MarketplaceAuthenticationRuntimeInputsTests(unittest.TestCase):
    def test_profile_exact_types_and_immutable_bundle(self) -> None:
        bundle = compose_marketplace_authentication_runtime_inputs()
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_RUNTIME_INPUTS_V1",
        )
        self.assertIs(type(bundle), MarketplaceAuthenticationRuntimeInputs)
        self.assertIs(type(bundle.material_source), MarketplaceCredentialMaterialSource)
        self.assertIs(type(bundle.clock), MarketplaceAuthenticationUnixClock)

        with self.assertRaises(FrozenInstanceError):
            bundle.clock = MarketplaceAuthenticationUnixClock()  # type: ignore[misc]

    def test_composition_consumes_no_runtime_input(self) -> None:
        challenge = Mock(side_effect=AssertionError("challenge called"))
        session = Mock(side_effect=AssertionError("session called"))
        clock = Mock(side_effect=AssertionError("clock called"))
        with (
            patch.object(
                MarketplaceCredentialMaterialSource,
                "challenge_bytes",
                challenge,
            ),
            patch.object(
                MarketplaceCredentialMaterialSource,
                "session_token_bytes",
                session,
            ),
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                clock,
            ),
        ):
            bundle = compose_marketplace_authentication_runtime_inputs()
        self.assertIs(type(bundle.material_source), MarketplaceCredentialMaterialSource)
        self.assertEqual(challenge.call_count, 0)
        self.assertEqual(session.call_count, 0)
        self.assertEqual(clock.call_count, 0)

    def test_clock_maps_nanoseconds_to_whole_unix_seconds(self) -> None:
        clock = MarketplaceAuthenticationUnixClock()
        cases = ((0, 0), (999_999_999, 0), (1_000_000_000, 1), (2_999_999_999, 2))
        for nanoseconds, expected in cases:
            with self.subTest(nanoseconds=nanoseconds):
                with patch(
                    "marketplace.application.auth_runtime_inputs._time_ns",
                    return_value=nanoseconds,
                ):
                    self.assertEqual(clock.now(), expected)

    def test_clock_failures_are_stable_and_non_reflective(self) -> None:
        clock = MarketplaceAuthenticationUnixClock()
        for malformed in (True, -1, "1000000000", None):
            with self.subTest(malformed=malformed):
                with patch(
                    "marketplace.application.auth_runtime_inputs._time_ns",
                    return_value=malformed,
                ):
                    with self.assertRaises(
                        MarketplaceAuthenticationRuntimeInputError
                    ) as caught:
                        clock.now()
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)

        with patch(
            "marketplace.application.auth_runtime_inputs._time_ns",
            side_effect=OSError("synthetic sensitive clock failure"),
        ):
            with self.assertRaises(
                MarketplaceAuthenticationRuntimeInputError
            ) as caught:
                clock.now()
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("sensitive", str(caught.exception))

    def test_existing_material_source_exact_bounds_after_composition(self) -> None:
        challenge = b"c" * AUTH_CHALLENGE_BYTES
        session = b"s" * AUTH_SESSION_TOKEN_BYTES
        with patch(
            "marketplace.application.auth_material._token_bytes",
            side_effect=(challenge, session),
        ) as token_bytes:
            bundle = compose_marketplace_authentication_runtime_inputs()
            self.assertEqual(token_bytes.call_count, 0)
            self.assertEqual(bundle.material_source.challenge_bytes(), challenge)
            self.assertEqual(bundle.material_source.session_token_bytes(), session)
        self.assertEqual(token_bytes.call_count, 2)
        self.assertEqual(len(challenge), 32)
        self.assertEqual(len(session), 32)

    def test_composition_and_bundle_failures_are_non_reflective(self) -> None:
        with patch(
            "marketplace.application.auth_runtime_inputs."
            "MarketplaceCredentialMaterialSource",
            side_effect=RuntimeError("synthetic sensitive constructor failure"),
        ):
            with self.assertRaises(
                MarketplaceAuthenticationRuntimeInputError
            ) as caught:
                compose_marketplace_authentication_runtime_inputs()
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("sensitive", str(caught.exception))

        with self.assertRaises(MarketplaceAuthenticationRuntimeInputError):
            MarketplaceAuthenticationRuntimeInputs(
                material_source=object(),  # type: ignore[arg-type]
                clock=MarketplaceAuthenticationUnixClock(),
            )


if __name__ == "__main__":
    unittest.main()
