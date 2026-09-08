from __future__ import annotations

import base64
from dataclasses import FrozenInstanceError
import json
import unittest

from marketplace.application.auth import MarketplaceApplicationAuthService
from marketplace.application.auth_proof_profile import (
    AuthenticationProofSigningRequest,
    make_marketplace_authentication_proof,
)
from marketplace.application.auth_session_http import MarketplaceAuthenticationSessionHttpAdapter
from marketplace.application.auth_verification_method_snapshot import (
    AUTH_VERIFICATION_METHOD_MAX_ENTRIES,
    AUTH_VERIFICATION_METHOD_URI_MAX_BYTES,
    AUTH_VERIFICATION_PUBLIC_KEY_BYTES,
    AuthenticationVerificationMethodEvidence,
    AuthenticationVerificationMethodSnapshotError,
    MarketplaceAuthenticationVerificationMethodSnapshot,
    PROFILE_NAME,
)
from marketplace.application.auth_verifier_ed25519 import MarketplaceEd25519AuthenticationProofVerifier
from marketplace.application.http import ApplicationHttpRequest


PRINCIPAL = "did:example:alice"
OTHER_PRINCIPAL = "did:example:bob"
METHOD = "did:example:alice#key-1"
CHALLENGE = bytes(range(32))
TOKEN = bytes(range(32, 64))
TEST_PUBLIC_KEY = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)
EXPECTED_SIGNATURE = bytes.fromhex(
    "85fb0e24d5b1bf54ae397e1028a6e2db690e67d8eaa279fcd2e39cfe17240030"
    "206b3eda21574888fde8b0b6d331cba53438e660b3e17bb9d481ce06179ed505"
)


class MaterialSource:
    def challenge_bytes(self) -> bytes:
        return CHALLENGE

    def session_token_bytes(self) -> bytes:
        return TOKEN


def request(method: str, path: str, document: object | None = None) -> ApplicationHttpRequest:
    if document is None:
        return ApplicationHttpRequest(method, path, (), None, b"")
    body = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return ApplicationHttpRequest(method, path, (), "application/json", body)


def decode(response) -> dict[str, object]:
    return json.loads(response.body.decode("utf-8"))


def proof_document() -> dict[str, object]:
    signing_request = AuthenticationProofSigningRequest(
        verification_method=METHOD,
        challenge=CHALLENGE,
    )
    return make_marketplace_authentication_proof(
        signing_request,
        EXPECTED_SIGNATURE,
    ).to_document()


def entry(
    *,
    method: str = METHOD,
    controller: str = PRINCIPAL,
    public_key: bytes = TEST_PUBLIC_KEY,
    valid_from: int | None = None,
    valid_until: int | None = None,
) -> AuthenticationVerificationMethodEvidence:
    return AuthenticationVerificationMethodEvidence(
        verification_method=method,
        controller_principal=controller,
        public_key=public_key,
        valid_from=valid_from,
        valid_until=valid_until,
    )


def make_adapter(
    *,
    key_source: object,
    binding_verifier: object,
) -> MarketplaceAuthenticationSessionHttpAdapter:
    auth = MarketplaceApplicationAuthService(
        principal_binding_verifier=binding_verifier,
    )
    verifier = MarketplaceEd25519AuthenticationProofVerifier(
        key_source=key_source,
    )
    return MarketplaceAuthenticationSessionHttpAdapter(
        auth=auth,
        material_source=MaterialSource(),
        proof_verifier=verifier,
    )


def establish(
    adapter: MarketplaceAuthenticationSessionHttpAdapter,
    *,
    principal: str = PRINCIPAL,
    now: int = 100,
):
    challenge_response = adapter.handle(
        request(
            "POST",
            "/api/auth/challenges",
            {"principal": principal, "verification_method": METHOD},
        ),
        session_token=None,
        session_invalid=False,
        now=now,
    )
    assert challenge_response.status_code == 201
    session_response = adapter.handle(
        request(
            "POST",
            "/api/auth/sessions",
            {
                "challenge": decode(challenge_response)["challenge"],
                "proof": proof_document(),
            },
        ),
        session_token=None,
        session_invalid=False,
        now=now + 1,
    )
    return session_response


class M17AuthVerificationMethodSnapshotTests(unittest.TestCase):
    def test_profile_and_exact_capacity_constants(self):
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_VERIFICATION_METHOD_SNAPSHOT_V1",
        )
        self.assertEqual(AUTH_VERIFICATION_METHOD_MAX_ENTRIES, 256)
        self.assertEqual(AUTH_VERIFICATION_METHOD_URI_MAX_BYTES, 2048)
        self.assertEqual(AUTH_VERIFICATION_PUBLIC_KEY_BYTES, 32)

    def test_entry_requires_exact_bounded_uris_and_preserves_spelling(self):
        method = "did:example:Alice#Key-1"
        evidence = entry(method=method)
        snapshot = MarketplaceAuthenticationVerificationMethodSnapshot([evidence])
        self.assertEqual(snapshot.verification_key_bytes(method), TEST_PUBLIC_KEY)
        with self.assertRaises(AuthenticationVerificationMethodSnapshotError):
            snapshot.verification_key_bytes(method.lower())

        for invalid in (
            "",
            "relative/path",
            "did:example:bad value",
            "x:" + "a" * 2047,
        ):
            with self.subTest(invalid=invalid[:32]):
                with self.assertRaises(AuthenticationVerificationMethodSnapshotError):
                    entry(method=invalid)

    def test_public_key_requires_exact_32_byte_bytes(self):
        for value in (
            bytearray(TEST_PUBLIC_KEY),
            TEST_PUBLIC_KEY[:-1],
            TEST_PUBLIC_KEY + b"\x00",
        ):
            with self.subTest(value_type=type(value).__name__, value_length=len(value)):
                with self.assertRaises(AuthenticationVerificationMethodSnapshotError):
                    AuthenticationVerificationMethodEvidence(
                        verification_method=METHOD,
                        controller_principal=PRINCIPAL,
                        public_key=value,  # type: ignore[arg-type]
                    )

    def test_validity_times_are_exact_non_boolean_non_negative_and_ordered(self):
        for invalid in (True, -1, 1.5):
            with self.subTest(invalid=invalid):
                with self.assertRaises(AuthenticationVerificationMethodSnapshotError):
                    entry(valid_from=invalid)  # type: ignore[arg-type]
                with self.assertRaises(AuthenticationVerificationMethodSnapshotError):
                    entry(valid_until=invalid)  # type: ignore[arg-type]
        with self.assertRaises(AuthenticationVerificationMethodSnapshotError):
            entry(valid_from=100, valid_until=100)
        with self.assertRaises(AuthenticationVerificationMethodSnapshotError):
            entry(valid_from=101, valid_until=100)

    def test_capacity_duplicate_method_and_input_shape_fail_closed(self):
        full = [
            entry(method=f"did:example:controller#key-{index}")
            for index in range(AUTH_VERIFICATION_METHOD_MAX_ENTRIES)
        ]
        MarketplaceAuthenticationVerificationMethodSnapshot(full)
        with self.assertRaises(AuthenticationVerificationMethodSnapshotError):
            MarketplaceAuthenticationVerificationMethodSnapshot(
                full + [entry(method="did:example:overflow#key")]
            )
        with self.assertRaises(AuthenticationVerificationMethodSnapshotError):
            MarketplaceAuthenticationVerificationMethodSnapshot(
                [entry(), entry(controller=OTHER_PRINCIPAL)]
            )
        with self.assertRaises(AuthenticationVerificationMethodSnapshotError):
            MarketplaceAuthenticationVerificationMethodSnapshot(set())  # type: ignore[arg-type]

    def test_snapshot_copies_input_and_has_no_mutation_surface(self):
        source = [entry()]
        snapshot = MarketplaceAuthenticationVerificationMethodSnapshot(source)
        source.clear()
        source.append(entry(method="did:example:bob#key-2", controller=OTHER_PRINCIPAL))
        self.assertEqual(snapshot.verification_key_bytes(METHOD), TEST_PUBLIC_KEY)
        with self.assertRaises(AuthenticationVerificationMethodSnapshotError):
            snapshot.verification_key_bytes("did:example:bob#key-2")
        for name in ("add", "update", "delete", "refresh", "reload"):
            self.assertFalse(hasattr(snapshot, name), name)
        with self.assertRaises(FrozenInstanceError):
            snapshot._entries = {}  # type: ignore[misc,assignment]
        self.assertEqual(snapshot.verification_key_bytes(METHOD), TEST_PUBLIC_KEY)

    def test_binding_uses_explicit_controller_and_half_open_validity_only(self):
        snapshot = MarketplaceAuthenticationVerificationMethodSnapshot(
            [entry(controller=OTHER_PRINCIPAL, valid_from=100, valid_until=200)]
        )
        self.assertFalse(
            snapshot.verify(
                principal=PRINCIPAL,
                verification_method=METHOD,
                at_time=100,
            )
        )
        self.assertTrue(
            snapshot.verify(
                principal=OTHER_PRINCIPAL,
                verification_method=METHOD,
                at_time=100,
            )
        )
        self.assertTrue(
            snapshot.verify(
                principal=OTHER_PRINCIPAL,
                verification_method=METHOD,
                at_time=199,
            )
        )
        self.assertFalse(
            snapshot.verify(
                principal=OTHER_PRINCIPAL,
                verification_method=METHOD,
                at_time=200,
            )
        )

    def test_uri_spelling_never_infers_controller_ownership(self):
        snapshot = MarketplaceAuthenticationVerificationMethodSnapshot(
            [entry(controller=OTHER_PRINCIPAL)]
        )
        self.assertFalse(
            snapshot.verify(
                principal=PRINCIPAL,
                verification_method=METHOD,
                at_time=100,
            )
        )
        self.assertTrue(
            snapshot.verify(
                principal=OTHER_PRINCIPAL,
                verification_method=METHOD,
                at_time=100,
            )
        )

    def test_missing_lookup_is_non_reflective_and_has_no_fallback(self):
        snapshot = MarketplaceAuthenticationVerificationMethodSnapshot([])
        missing = "did:example:secret#key-9"
        with self.assertRaises(AuthenticationVerificationMethodSnapshotError) as caught:
            snapshot.verification_key_bytes(missing)
        self.assertNotIn(missing, str(caught.exception))

    def test_same_snapshot_instance_completes_frozen_in_process_authentication(self):
        snapshot = MarketplaceAuthenticationVerificationMethodSnapshot(
            [entry(valid_from=100, valid_until=200)]
        )
        adapter = make_adapter(
            key_source=snapshot,
            binding_verifier=snapshot,
        )
        response = establish(adapter)
        self.assertEqual(response.status_code, 201)
        document = decode(response)
        self.assertEqual(document["principal"], PRINCIPAL)
        self.assertEqual(document["verification_method"], METHOD)
        expected_token = "mkt1_" + base64.urlsafe_b64encode(TOKEN).rstrip(b"=").decode("ascii")
        self.assertEqual(document["session_token"], expected_token)

    def test_shared_snapshot_rejects_valid_signature_for_controller_or_time_policy(self):
        cases = (
            entry(controller=OTHER_PRINCIPAL),
            entry(valid_from=102),
            entry(valid_until=101),
        )
        for evidence in cases:
            with self.subTest(evidence=evidence):
                snapshot = MarketplaceAuthenticationVerificationMethodSnapshot([evidence])
                verifier = MarketplaceEd25519AuthenticationProofVerifier(key_source=snapshot)
                self.assertTrue(verifier.verify(proof_document()).cryptographically_valid)
                adapter = make_adapter(
                    key_source=snapshot,
                    binding_verifier=snapshot,
                )
                response = establish(adapter)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(
                    decode(response)["error"]["code"],
                    "AUTH_PRINCIPAL_BINDING_REJECTED",
                )

    def test_missing_method_maps_to_existing_verifier_unavailable(self):
        snapshot = MarketplaceAuthenticationVerificationMethodSnapshot([])
        adapter = make_adapter(
            key_source=snapshot,
            binding_verifier=snapshot,
        )
        response = establish(adapter)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            decode(response)["error"]["code"],
            "AUTH_PROOF_VERIFIER_UNAVAILABLE",
        )
        self.assertNotIn(b"did:example", response.body)

    def test_missing_binding_maps_to_existing_binding_unavailable(self):
        key_snapshot = MarketplaceAuthenticationVerificationMethodSnapshot([entry()])
        binding_snapshot = MarketplaceAuthenticationVerificationMethodSnapshot([])
        adapter = make_adapter(
            key_source=key_snapshot,
            binding_verifier=binding_snapshot,
        )
        response = establish(adapter)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            decode(response)["error"]["code"],
            "AUTH_PRINCIPAL_BINDING_UNAVAILABLE",
        )
        self.assertNotIn(b"did:example", response.body)

    def test_binding_arguments_fail_closed_without_boolean_coercion(self):
        snapshot = MarketplaceAuthenticationVerificationMethodSnapshot([entry()])
        for invalid_time in (True, -1, 1.5):
            with self.subTest(invalid_time=invalid_time):
                with self.assertRaises(AuthenticationVerificationMethodSnapshotError):
                    snapshot.verify(
                        principal=PRINCIPAL,
                        verification_method=METHOD,
                        at_time=invalid_time,  # type: ignore[arg-type]
                    )


if __name__ == "__main__":
    unittest.main()
