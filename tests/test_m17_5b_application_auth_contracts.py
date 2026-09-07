from __future__ import annotations

import unittest

from marketplace.application.auth import (
    AUTH_CHALLENGE_BYTES,
    AUTH_CHALLENGE_MAX_AGE_SECONDS,
    AUTH_PROOF_DOMAIN,
    AUTH_SESSION_ABSOLUTE_SECONDS,
    AUTH_SESSION_IDLE_SECONDS,
    AUTH_SESSION_TOKEN_BYTES,
    ApplicationAuthError,
    AuthenticatedProductListingAuthoringService,
    AuthenticatedProposalAuthoringService,
    MarketplaceApplicationAuthService,
    VerifiedAuthenticationProof,
)
from marketplace.application.authoring import ProductListingAuthoringFields
from marketplace.application.proposal import BuyerRequestProposalDraft


class BindingVerifier:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.calls: list[tuple[str, str, int]] = []

    def verify(self, *, principal: str, verification_method: str, at_time: int) -> bool:
        self.calls.append((principal, verification_method, at_time))
        return self.allowed


class FakeProductWriter:
    def __init__(self) -> None:
        self.calls: list[ProductListingAuthoringFields] = []

    def create_product_listing(self, fields: ProductListingAuthoringFields):
        self.calls.append(fields)
        return "product-ok"


class FakeProposalWriter:
    def __init__(self) -> None:
        self.calls: list[BuyerRequestProposalDraft] = []

    def create_buyer_request_proposal(self, draft: BuyerRequestProposalDraft):
        self.calls.append(draft)
        return "proposal-ok"


class M17ApplicationAuthContractsTests(unittest.TestCase):
    PRINCIPAL = "did:example:alice"
    METHOD = "did:example:alice#key-1"

    def setUp(self) -> None:
        self.binding = BindingVerifier()
        self.auth = MarketplaceApplicationAuthService(principal_binding_verifier=self.binding)
        self.challenge = b"c" * AUTH_CHALLENGE_BYTES
        self.token = b"t" * AUTH_SESSION_TOKEN_BYTES

    def proof(self, **changes) -> VerifiedAuthenticationProof:
        values = {
            "challenge_sha256": __import__("hashlib").sha256(self.challenge).digest(),
            "domain": AUTH_PROOF_DOMAIN,
            "proof_purpose": "assertion",
            "verification_method": self.METHOD,
            "cryptographically_valid": True,
        }
        values.update(changes)
        return VerifiedAuthenticationProof(**values)

    def register(self, now: int = 1_000) -> None:
        self.auth.register_challenge(
            challenge=self.challenge,
            principal=self.PRINCIPAL,
            verification_method=self.METHOD,
            now=now,
        )

    def authenticate(self, now: int = 1_001):
        return self.auth.authenticate_challenge(
            challenge=self.challenge,
            proof=self.proof(),
            session_token=self.token,
            now=now,
        )

    def test_profile_constants_are_exact_reviewed_ceilings(self):
        self.assertEqual(AUTH_CHALLENGE_BYTES, 32)
        self.assertEqual(AUTH_SESSION_TOKEN_BYTES, 32)
        self.assertEqual(AUTH_CHALLENGE_MAX_AGE_SECONDS, 120)
        self.assertEqual(AUTH_SESSION_IDLE_SECONDS, 30 * 60)
        self.assertEqual(AUTH_SESSION_ABSOLUTE_SECONDS, 8 * 60 * 60)

    def test_challenge_registers_digest_only_and_authenticates_once(self):
        self.register()
        session = self.authenticate()
        self.assertEqual(session.principal, self.PRINCIPAL)
        self.assertEqual(session.verification_method, self.METHOD)
        self.assertEqual(self.binding.calls, [(self.PRINCIPAL, self.METHOD, 1_001)])
        with self.assertRaises(ApplicationAuthError) as caught:
            self.authenticate(now=1_002)
        self.assertEqual(caught.exception.code, "AUTH_CHALLENGE_INVALID")

    def test_expired_challenge_fails_closed_and_is_consumed(self):
        self.register(now=1_000)
        with self.assertRaises(ApplicationAuthError) as caught:
            self.authenticate(now=1_000 + AUTH_CHALLENGE_MAX_AGE_SECONDS)
        self.assertEqual(caught.exception.code, "AUTH_CHALLENGE_EXPIRED")
        with self.assertRaises(ApplicationAuthError) as second:
            self.authenticate(now=1_001)
        self.assertEqual(second.exception.code, "AUTH_CHALLENGE_INVALID")

    def test_invalid_proof_consumes_challenge_without_binding_or_session(self):
        self.register()
        with self.assertRaises(ApplicationAuthError) as caught:
            self.auth.authenticate_challenge(
                challenge=self.challenge,
                proof=self.proof(cryptographically_valid=False),
                session_token=self.token,
                now=1_001,
            )
        self.assertEqual(caught.exception.code, "AUTH_PROOF_INVALID")
        self.assertEqual(self.binding.calls, [])
        with self.assertRaises(ApplicationAuthError):
            self.auth.authenticate_session(session_token=self.token, now=1_002)

    def test_domain_purpose_method_or_challenge_mismatch_fails_before_binding(self):
        variants = [
            self.proof(domain="https://wrong.invalid/auth"),
            self.proof(proof_purpose="authorization"),
            self.proof(verification_method="did:example:alice#other"),
            self.proof(challenge_sha256=b"x" * 32),
        ]
        for proof in variants:
            with self.subTest(proof=proof):
                auth = MarketplaceApplicationAuthService(principal_binding_verifier=BindingVerifier())
                auth.register_challenge(
                    challenge=self.challenge,
                    principal=self.PRINCIPAL,
                    verification_method=self.METHOD,
                    now=1_000,
                )
                with self.assertRaises(ApplicationAuthError) as caught:
                    auth.authenticate_challenge(
                        challenge=self.challenge,
                        proof=proof,
                        session_token=self.token,
                        now=1_001,
                    )
                self.assertEqual(caught.exception.code, "AUTH_PROOF_INVALID")

    def test_principal_binding_is_mandatory_and_fail_closed(self):
        denied = MarketplaceApplicationAuthService(
            principal_binding_verifier=BindingVerifier(allowed=False)
        )
        denied.register_challenge(
            challenge=self.challenge,
            principal=self.PRINCIPAL,
            verification_method=self.METHOD,
            now=1_000,
        )
        with self.assertRaises(ApplicationAuthError) as caught:
            denied.authenticate_challenge(
                challenge=self.challenge,
                proof=self.proof(),
                session_token=self.token,
                now=1_001,
            )
        self.assertEqual(caught.exception.code, "AUTH_PRINCIPAL_BINDING_REJECTED")
        with self.assertRaises(TypeError):
            MarketplaceApplicationAuthService(principal_binding_verifier=object())

    def test_session_idle_absolute_expiry_and_revocation_are_terminal(self):
        self.register()
        session = self.authenticate()
        self.assertEqual(session.absolute_expires_at, 1_001 + AUTH_SESSION_ABSOLUTE_SECONDS)
        self.auth.authenticate_session(
            session_token=self.token,
            now=1_001 + AUTH_SESSION_IDLE_SECONDS - 1,
        )
        with self.assertRaises(ApplicationAuthError) as idle:
            self.auth.authenticate_session(
                session_token=self.token,
                now=1_001 + 2 * AUTH_SESSION_IDLE_SECONDS - 1,
            )
        self.assertEqual(idle.exception.code, "AUTH_SESSION_EXPIRED")

        auth2 = MarketplaceApplicationAuthService(principal_binding_verifier=BindingVerifier())
        auth2.register_challenge(
            challenge=self.challenge,
            principal=self.PRINCIPAL,
            verification_method=self.METHOD,
            now=2_000,
        )
        auth2.authenticate_challenge(
            challenge=self.challenge,
            proof=self.proof(),
            session_token=self.token,
            now=2_001,
        )
        auth2.revoke_session(session_token=self.token, now=2_002)
        with self.assertRaises(ApplicationAuthError) as revoked:
            auth2.authenticate_session(session_token=self.token, now=2_003)
        self.assertEqual(revoked.exception.code, "AUTH_SESSION_INVALID")

    def test_absolute_expiry_cannot_be_extended_by_activity(self):
        self.register(now=10)
        self.authenticate(now=11)
        last = 11
        while last + AUTH_SESSION_IDLE_SECONDS - 1 < 11 + AUTH_SESSION_ABSOLUTE_SECONDS:
            last += AUTH_SESSION_IDLE_SECONDS - 1
            self.auth.authenticate_session(session_token=self.token, now=last)
        with self.assertRaises(ApplicationAuthError) as caught:
            self.auth.authenticate_session(
                session_token=self.token,
                now=11 + AUTH_SESSION_ABSOLUTE_SECONDS,
            )
        self.assertEqual(caught.exception.code, "AUTH_SESSION_EXPIRED")

    def test_session_token_is_never_exposed_by_session_view(self):
        self.register()
        view = self.authenticate()
        rendered = repr(view)
        self.assertNotIn(self.token.hex(), rendered)
        self.assertFalse(hasattr(view, "token"))
        self.assertFalse(hasattr(view, "token_digest"))

    def product_fields(self, principal: str) -> ProductListingAuthoringFields:
        return ProductListingAuthoringFields(
            seller_principal=principal,
            subject_uri="urn:sku:test",
            title="Test",
            description="Synthetic",
            consideration_coefficient=1,
            consideration_scale=0,
            currency_code="USD",
            quantity_coefficient=1,
            quantity_scale=0,
            unit_uri="https://open-trust-layer.github.io/marketplace/semantics/v1/unit/item",
            latitude_e6=0,
            longitude_e6=0,
        )

    def proposal(self, principal: str) -> BuyerRequestProposalDraft:
        return BuyerRequestProposalDraft(
            buyer_principal=principal,
            subject_uri="urn:sku:test",
            action_uri="https://open-trust-layer.github.io/marketplace/semantics/v1/action/request",
            parent_record_id="r-parent",
        )

    def test_product_write_guard_blocks_principal_mismatch_before_downstream(self):
        self.register()
        self.authenticate()
        downstream = FakeProductWriter()
        guarded = AuthenticatedProductListingAuthoringService(auth=self.auth, authoring=downstream)
        with self.assertRaises(ApplicationAuthError) as caught:
            guarded.create_product_listing(
                session_token=self.token,
                fields=self.product_fields("did:example:mallory"),
                now=1_002,
            )
        self.assertEqual(caught.exception.code, "AUTH_PRINCIPAL_MISMATCH")
        self.assertEqual(downstream.calls, [])
        self.assertEqual(
            guarded.create_product_listing(
                session_token=self.token,
                fields=self.product_fields(self.PRINCIPAL),
                now=1_003,
            ),
            "product-ok",
        )

    def test_proposal_write_guard_blocks_principal_mismatch_before_downstream(self):
        self.register()
        self.authenticate()
        downstream = FakeProposalWriter()
        guarded = AuthenticatedProposalAuthoringService(auth=self.auth, authoring=downstream)
        with self.assertRaises(ApplicationAuthError) as caught:
            guarded.create_buyer_request_proposal(
                session_token=self.token,
                draft=self.proposal("did:example:mallory"),
                now=1_002,
            )
        self.assertEqual(caught.exception.code, "AUTH_PRINCIPAL_MISMATCH")
        self.assertEqual(downstream.calls, [])
        self.assertEqual(
            guarded.create_buyer_request_proposal(
                session_token=self.token,
                draft=self.proposal(self.PRINCIPAL),
                now=1_003,
            ),
            "proposal-ok",
        )

    def test_raw_token_and_challenge_shapes_are_bounded(self):
        with self.assertRaises(ValueError):
            self.auth.register_challenge(
                challenge=b"short",
                principal=self.PRINCIPAL,
                verification_method=self.METHOD,
                now=1,
            )
        self.register()
        with self.assertRaises(ValueError):
            self.auth.authenticate_challenge(
                challenge=self.challenge,
                proof=self.proof(),
                session_token=b"short",
                now=1_001,
            )


if __name__ == "__main__":
    unittest.main()
