from __future__ import annotations

import json
import unittest
from unittest.mock import call, patch

from marketplace.application.auth import MarketplaceApplicationAuthService
from marketplace.application.auth_material import (
    MarketplaceCredentialMaterialSource,
    MarketplaceCredentialMaterialSourceError,
    PROFILE_NAME,
)
from marketplace.application.auth_session_http import MarketplaceAuthenticationSessionHttpAdapter
from marketplace.application.http import ApplicationHttpRequest


PRINCIPAL = "did:example:alice"
METHOD = "did:example:alice#key-1"
CHALLENGE = bytes(range(32))
TOKEN = bytes(range(32, 64))


class AllowBinding:
    def verify(self, *, principal: str, verification_method: str, at_time: int) -> bool:
        return principal == PRINCIPAL and verification_method == METHOD and at_time >= 0


class NeverProofVerifier:
    def verify(self, proof_document: object):
        raise AssertionError("proof verifier must not run for challenge material failure")


def challenge_request() -> ApplicationHttpRequest:
    body = json.dumps(
        {"principal": PRINCIPAL, "verification_method": METHOD},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return ApplicationHttpRequest(
        "POST",
        "/api/auth/challenges",
        (),
        "application/json",
        body,
    )


def decode(response) -> dict[str, object]:
    return json.loads(response.body.decode("utf-8"))


class M17AuthMaterialTests(unittest.TestCase):
    def test_profile_and_source_are_exact_and_stateless(self):
        source = MarketplaceCredentialMaterialSource()
        self.assertEqual(PROFILE_NAME, "MARKETPLACE_APPLICATION_CREDENTIAL_MATERIAL_SOURCE_V1")
        self.assertEqual(MarketplaceCredentialMaterialSource.__slots__, ())
        self.assertFalse(hasattr(source, "__dict__"))

    def test_challenge_and_session_material_use_fresh_exact_32_byte_calls(self):
        source = MarketplaceCredentialMaterialSource()
        with patch(
            "marketplace.application.auth_material._token_bytes",
            side_effect=[CHALLENGE, TOKEN],
        ) as generator:
            self.assertEqual(source.challenge_bytes(), CHALLENGE)
            self.assertEqual(source.session_token_bytes(), TOKEN)
        self.assertEqual(generator.call_args_list, [call(32), call(32)])

    def test_malformed_generator_results_fail_closed_without_material_reflection(self):
        source = MarketplaceCredentialMaterialSource()
        malformed = (bytearray(32), b"x" * 31, b"y" * 33)
        for value in malformed:
            with self.subTest(value_type=type(value).__name__, value_length=len(value)):
                with patch("marketplace.application.auth_material._token_bytes", return_value=value):
                    with self.assertRaises(MarketplaceCredentialMaterialSourceError) as raised:
                        source.challenge_bytes()
                self.assertEqual(
                    str(raised.exception),
                    "credential material source returned invalid material",
                )
                self.assertNotIn(repr(value), str(raised.exception))

    def test_underlying_csprng_exception_propagates_without_retry_or_fallback(self):
        class EntropyFailure(RuntimeError):
            pass

        failure = EntropyFailure("synthetic provider detail")
        source = MarketplaceCredentialMaterialSource()
        with patch(
            "marketplace.application.auth_material._token_bytes",
            side_effect=failure,
        ) as generator:
            with self.assertRaises(EntropyFailure) as raised:
                source.session_token_bytes()
        self.assertIs(raised.exception, failure)
        generator.assert_called_once_with(32)

    def test_existing_http_boundary_maps_csprng_failure_to_stable_non_reflective_error(self):
        class EntropyFailure(RuntimeError):
            pass

        source = MarketplaceCredentialMaterialSource()
        auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
        adapter = MarketplaceAuthenticationSessionHttpAdapter(
            auth=auth,
            material_source=source,
            proof_verifier=NeverProofVerifier(),
        )
        with patch(
            "marketplace.application.auth_material._token_bytes",
            side_effect=EntropyFailure("synthetic provider detail must not escape"),
        ) as generator:
            response = adapter.handle(
                challenge_request(),
                session_token=None,
                session_invalid=False,
                now=100,
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(decode(response)["error"]["code"], "AUTH_MATERIAL_UNAVAILABLE")
        self.assertNotIn(b"synthetic provider detail", response.body)
        generator.assert_called_once_with(32)


if __name__ == "__main__":
    unittest.main()
