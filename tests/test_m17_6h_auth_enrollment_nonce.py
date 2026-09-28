from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import base64
import hashlib
import unittest

from marketplace.application.auth_enrollment_coordination import (
    AUTH_ENROLLMENT_NONCE_BYTES,
)
from marketplace.application.auth_enrollment_nonce import (
    AUTH_ENROLLMENT_NONCE_MAX_AGE_SECONDS,
    AUTH_MAX_OUTSTANDING_ENROLLMENT_NONCES,
    AUTH_MAX_OUTSTANDING_ENROLLMENT_NONCES_PER_BINDING,
    AuthenticationEnrollmentNonceError,
    MarketplaceAuthenticationEnrollmentNonceAuthority,
    PROFILE_NAME,
)
from marketplace.application.auth_verification_method_evidence import (
    AUTH_EVIDENCE_MAX_LEASE_SECONDS,
)


AUTHORITY = "https://authority.example/auth-enrollment"
PRINCIPAL = "did:example:alice"
METHOD = "did:example:alice#key-1"
KEY_BYTES = bytes(range(32))
PAYLOAD = base64.urlsafe_b64encode(KEY_BYTES).rstrip(b"=").decode("ascii")
PUBLIC_KEY = "mkp1_" + PAYLOAD
LEASE_SECONDS = 600
NONCE = b"n" * AUTH_ENROLLMENT_NONCE_BYTES


class SequenceMaterialSource:
    def __init__(self, values: list[object]) -> None:
        self.values = list(values)
        self.calls = 0

    def enrollment_nonce_bytes(self):
        self.calls += 1
        if not self.values:
            raise RuntimeError("sensitive material-source exhaustion")
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


def issue(
    authority: MarketplaceAuthenticationEnrollmentNonceAuthority,
    *,
    principal: str = PRINCIPAL,
    verification_method: str = METHOD,
    public_key: str = PUBLIC_KEY,
    authority_uri: str = AUTHORITY,
    lease_seconds: int = LEASE_SECONDS,
    now: int = 100,
):
    return authority.issue_authentication_enrollment_nonce(
        principal=principal,
        verification_method=verification_method,
        public_key=public_key,
        authority=authority_uri,
        evidence_lease_seconds=lease_seconds,
        now=now,
    )


def consume(
    authority: MarketplaceAuthenticationEnrollmentNonceAuthority,
    nonce: bytes,
    *,
    principal: str = PRINCIPAL,
    verification_method: str = METHOD,
    public_key: str = PUBLIC_KEY,
    authority_uri: str = AUTHORITY,
    issued_at: int = 101,
    expires_at: int = 701,
) -> bool:
    return authority.consume_authentication_enrollment_nonce(
        nonce=nonce,
        principal=principal,
        verification_method=verification_method,
        public_key=public_key,
        authority=authority_uri,
        issued_at=issued_at,
        expires_at=expires_at,
    )


class M176HAuthenticationEnrollmentNonceTests(unittest.TestCase):
    def test_profile_and_bounds_are_exact(self) -> None:
        self.assertEqual(PROFILE_NAME, "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_NONCE_V1")
        self.assertEqual(AUTH_ENROLLMENT_NONCE_BYTES, 32)
        self.assertEqual(AUTH_ENROLLMENT_NONCE_MAX_AGE_SECONDS, 120)
        self.assertEqual(AUTH_MAX_OUTSTANDING_ENROLLMENT_NONCES, 128)
        self.assertEqual(AUTH_MAX_OUTSTANDING_ENROLLMENT_NONCES_PER_BINDING, 4)

    def test_issuance_returns_raw_nonce_but_retains_only_digest_state(self) -> None:
        source = SequenceMaterialSource([NONCE])
        authority = MarketplaceAuthenticationEnrollmentNonceAuthority(material_source=source)
        view = issue(authority)
        self.assertEqual(view.nonce, NONCE)
        self.assertEqual(view.issued_at, 100)
        self.assertEqual(view.expires_at, 220)
        digest = hashlib.sha256(NONCE).digest()
        self.assertIn(digest, authority._outstanding)
        state = authority._outstanding[digest]
        self.assertFalse(hasattr(state, "nonce"))
        self.assertEqual(state.digest, digest)
        self.assertNotEqual(state.digest, NONCE)

    def test_invalid_issue_binding_fails_before_material_source(self) -> None:
        cases = (
            {"principal": "relative"},
            {"verification_method": "relative"},
            {"public_key": "bad"},
            {"authority_uri": "relative"},
            {"lease_seconds": 0},
            {"lease_seconds": AUTH_EVIDENCE_MAX_LEASE_SECONDS + 1},
            {"now": True},
        )
        for changes in cases:
            source = SequenceMaterialSource([NONCE])
            authority = MarketplaceAuthenticationEnrollmentNonceAuthority(material_source=source)
            kwargs = {
                "principal": PRINCIPAL,
                "verification_method": METHOD,
                "public_key": PUBLIC_KEY,
                "authority_uri": AUTHORITY,
                "lease_seconds": LEASE_SECONDS,
                "now": 100,
            }
            kwargs.update(changes)
            with self.subTest(changes=changes):
                with self.assertRaises(AuthenticationEnrollmentNonceError) as caught:
                    issue(authority, **kwargs)
                self.assertEqual(
                    str(caught.exception),
                    "authentication enrollment nonce operation failed",
                )
                self.assertEqual(source.calls, 0)

    def test_material_source_failure_and_malformed_material_are_nonreflective(self) -> None:
        for value in (
            RuntimeError("sensitive material-source detail"),
            b"x" * 31,
            bytearray(b"x" * 32),
        ):
            source = SequenceMaterialSource([value])
            authority = MarketplaceAuthenticationEnrollmentNonceAuthority(material_source=source)
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(AuthenticationEnrollmentNonceError) as caught:
                    issue(authority)
                self.assertEqual(
                    str(caught.exception),
                    "authentication enrollment nonce operation failed",
                )
                self.assertNotIn("sensitive", str(caught.exception))

    def test_exact_binding_and_lease_are_required_and_mismatch_burns_nonce(self) -> None:
        cases = (
            {"principal": "did:example:bob"},
            {"verification_method": "did:example:alice#key-2"},
            {"public_key": "mkp1_" + base64.urlsafe_b64encode(bytes(reversed(range(32)))).rstrip(b"=").decode("ascii")},
            {"authority_uri": "https://authority.example/other"},
            {"expires_at": 702},
            {"issued_at": 99, "expires_at": 699},
        )
        for index, changes in enumerate(cases, start=1):
            nonce = index.to_bytes(32, "big")
            authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
                material_source=SequenceMaterialSource([nonce])
            )
            issue(authority)
            kwargs = {
                "principal": PRINCIPAL,
                "verification_method": METHOD,
                "public_key": PUBLIC_KEY,
                "authority_uri": AUTHORITY,
                "issued_at": 101,
                "expires_at": 701,
            }
            kwargs.update(changes)
            with self.subTest(changes=changes):
                self.assertIs(consume(authority, nonce, **kwargs), False)
                self.assertIs(consume(authority, nonce), False)

    def test_valid_nonce_consumes_exactly_once(self) -> None:
        authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
            material_source=SequenceMaterialSource([NONCE])
        )
        issue(authority)
        self.assertIs(consume(authority, NONCE), True)
        self.assertIs(consume(authority, NONCE), False)

    def test_concurrent_reuse_has_exactly_one_success(self) -> None:
        authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
            material_source=SequenceMaterialSource([NONCE])
        )
        issue(authority)
        with ThreadPoolExecutor(max_workers=16) as executor:
            results = list(executor.map(lambda _i: consume(authority, NONCE), range(32)))
        self.assertEqual(sum(result is True for result in results), 1)
        self.assertEqual(sum(result is False for result in results), 31)

    def test_expired_nonce_is_rejected_and_expiry_frees_material_for_reissue(self) -> None:
        source = SequenceMaterialSource([NONCE, NONCE])
        authority = MarketplaceAuthenticationEnrollmentNonceAuthority(material_source=source)
        first = issue(authority, now=100)
        self.assertEqual(first.expires_at, 220)
        self.assertIs(
            consume(
                authority,
                NONCE,
                issued_at=220,
                expires_at=820,
            ),
            False,
        )
        second = issue(authority, now=220)
        self.assertEqual(second.nonce, NONCE)
        self.assertEqual(second.expires_at, 340)

    def test_duplicate_material_remains_rejected_after_consumption_until_nonce_expiry(self) -> None:
        source = SequenceMaterialSource([NONCE, NONCE, NONCE])
        authority = MarketplaceAuthenticationEnrollmentNonceAuthority(material_source=source)
        issue(authority, now=100)
        self.assertIs(consume(authority, NONCE), True)
        with self.assertRaises(AuthenticationEnrollmentNonceError):
            issue(authority, now=102)
        reissued = issue(authority, now=220)
        self.assertEqual(reissued.nonce, NONCE)

    def test_per_binding_capacity_counts_recently_consumed_slots(self) -> None:
        values = [i.to_bytes(32, "big") for i in range(1, 6)]
        authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
            material_source=SequenceMaterialSource(values)
        )
        issued = [issue(authority, now=100).nonce for _ in range(4)]
        self.assertIs(consume(authority, issued[0]), True)
        with self.assertRaises(AuthenticationEnrollmentNonceError):
            issue(authority, now=101)

    def test_global_capacity_is_bounded(self) -> None:
        values = [i.to_bytes(32, "big") for i in range(1, 130)]
        authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
            material_source=SequenceMaterialSource(values)
        )
        for index in range(AUTH_MAX_OUTSTANDING_ENROLLMENT_NONCES):
            principal = f"did:example:principal-{index}"
            issue(
                authority,
                principal=principal,
                verification_method=principal + "#key-1",
                now=100,
            )
        with self.assertRaises(AuthenticationEnrollmentNonceError):
            issue(
                authority,
                principal="did:example:overflow",
                verification_method="did:example:overflow#key-1",
                now=100,
            )

    def test_malformed_consumption_returns_exact_false_without_state_change(self) -> None:
        authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
            material_source=SequenceMaterialSource([NONCE])
        )
        issue(authority)
        result = authority.consume_authentication_enrollment_nonce(
            nonce=b"x" * 31,
            principal=PRINCIPAL,
            verification_method=METHOD,
            public_key=PUBLIC_KEY,
            authority=AUTHORITY,
            issued_at=101,
            expires_at=701,
        )
        self.assertIs(result, False)
        self.assertIs(consume(authority, NONCE), True)


if __name__ == "__main__":
    unittest.main()
