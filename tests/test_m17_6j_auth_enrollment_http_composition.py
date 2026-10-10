from __future__ import annotations

import unittest

from marketplace.application.auth_enrollment_http import (
    AUTH_ENROLLMENT_NONCE_ROUTE,
)
from marketplace.application.auth_enrollment_http_composition import (
    PROFILE_NAME,
    MarketplaceAuthenticationEnrollmentHttpCompositionError,
    compose_marketplace_authentication_enrollment_http,
)
from marketplace.application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from tests.test_m17_5p_auth_http_composition import (
    AT_TIME,
    SESSION_TOKEN,
    _compose,
    _establish_session,
)
from tests.test_m17_6i_auth_enrollment_http import (
    AUTHORITY,
    LEASE_SECONDS,
    NONCE,
    RecordingAttestor,
    RecordingPolicy,
    SequenceMaterialSource,
    proposal_document,
    request,
    response_document,
)


def _enrollment_composition(
    *,
    http=None,
    nonce_source=None,
    policy=None,
    attestor=None,
    authority: str = AUTHORITY,
    lease_seconds: int = LEASE_SECONDS,
):
    resolved_http, *_ = _compose() if http is None else (http,)
    source = nonce_source or SequenceMaterialSource([NONCE])
    nonce_authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
        material_source=source
    )
    resolved_policy = policy or RecordingPolicy()
    resolved_attestor = attestor or RecordingAttestor()
    composition = compose_marketplace_authentication_enrollment_http(
        http=resolved_http,
        nonce_authority=nonce_authority,
        policy=resolved_policy,
        attestor=resolved_attestor,
        authority=authority,
        evidence_lease_seconds=lease_seconds,
    )
    return (
        composition,
        resolved_http,
        source,
        nonce_authority,
        resolved_policy,
        resolved_attestor,
    )


class M176JAuthenticationEnrollmentHttpCompositionTests(unittest.TestCase):
    def test_profile_and_stable_type_failure_are_exact(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_COMPOSITION_V1",
        )
        http, *_ = _compose()
        nonce_authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
            material_source=SequenceMaterialSource([NONCE])
        )
        with self.assertRaises(
            MarketplaceAuthenticationEnrollmentHttpCompositionError
        ) as caught:
            compose_marketplace_authentication_enrollment_http(
                http=object(),  # type: ignore[arg-type]
                nonce_authority=nonce_authority,
                policy=RecordingPolicy(),
                attestor=RecordingAttestor(),
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )
        self.assertEqual(
            str(caught.exception),
            "authenticated enrollment HTTP composition failed",
        )

        with self.assertRaises(
            MarketplaceAuthenticationEnrollmentHttpCompositionError
        ):
            compose_marketplace_authentication_enrollment_http(
                http=http,
                nonce_authority=object(),  # type: ignore[arg-type]
                policy=RecordingPolicy(),
                attestor=RecordingAttestor(),
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

    def test_exact_object_graph_is_shared_without_consuming_collaborators(self) -> None:
        composition, http, source, nonce_authority, policy, attestor = (
            _enrollment_composition()
        )

        auth_service = http.authentication.auth_service
        self.assertIs(composition.http, http)
        self.assertIs(composition.nonce_authority, nonce_authority)
        self.assertIs(composition.policy, policy)
        self.assertIs(composition.attestor, attestor)
        self.assertIs(composition.enrollment_http._auth, auth_service)
        self.assertIs(http.application_http._auth, auth_service)
        self.assertIs(http.session_http._auth, auth_service)
        self.assertIs(
            composition.enrollment_http._nonce_authority,
            nonce_authority,
        )
        self.assertIs(composition.enrollment_http._policy, policy)
        self.assertIs(composition.enrollment_http._attestor, attestor)
        self.assertEqual(composition.authority, AUTHORITY)
        self.assertEqual(composition.evidence_lease_seconds, LEASE_SECONDS)
        self.assertEqual(composition.enrollment_http._authority, AUTHORITY)
        self.assertEqual(
            composition.enrollment_http._lease_seconds,
            LEASE_SECONDS,
        )
        self.assertEqual(source.calls, 0)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_invalid_policy_attestor_authority_and_lease_fail_before_nonce_material(self) -> None:
        cases = (
            {"policy": object()},
            {"attestor": object()},
            {"authority": "relative"},
            {"lease_seconds": 0},
        )
        for changes in cases:
            http, *_ = _compose()
            source = SequenceMaterialSource([NONCE])
            nonce_authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
                material_source=source
            )
            kwargs = {
                "http": http,
                "nonce_authority": nonce_authority,
                "policy": RecordingPolicy(),
                "attestor": RecordingAttestor(),
                "authority": AUTHORITY,
                "evidence_lease_seconds": LEASE_SECONDS,
            }
            if "lease_seconds" in changes:
                kwargs["evidence_lease_seconds"] = changes["lease_seconds"]
            else:
                kwargs.update(changes)
            with self.subTest(changes=changes):
                with self.assertRaises(
                    MarketplaceAuthenticationEnrollmentHttpCompositionError
                ):
                    compose_marketplace_authentication_enrollment_http(
                        **kwargs  # type: ignore[arg-type]
                    )
                self.assertEqual(source.calls, 0)

    def test_incoherent_existing_http_auth_graph_is_rejected(self) -> None:
        http, *_ = _compose()
        other_http, *_ = _compose()
        object.__setattr__(
            http.application_http,
            "_auth",
            other_http.authentication.auth_service,
        )
        source = SequenceMaterialSource([NONCE])
        nonce_authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
            material_source=source
        )
        with self.assertRaises(
            MarketplaceAuthenticationEnrollmentHttpCompositionError
        ):
            compose_marketplace_authentication_enrollment_http(
                http=http,
                nonce_authority=nonce_authority,
                policy=RecordingPolicy(),
                attestor=RecordingAttestor(),
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )
        self.assertEqual(source.calls, 0)

    def test_composed_adapter_uses_existing_session_authority_when_later_called(self) -> None:
        composition, http, source, _nonce_authority, policy, attestor = (
            _enrollment_composition()
        )
        _establish_session(http)

        response = composition.enrollment_http.handle(
            request(
                AUTH_ENROLLMENT_NONCE_ROUTE,
                {
                    "profile": (
                        "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1"
                    ),
                    "proposal": proposal_document(),
                },
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=AT_TIME,
        )
        self.assertEqual(response.status_code, 201)
        body = response_document(response)
        self.assertEqual(
            body["type"],
            "MarketplaceAuthenticationEnrollmentNonce",
        )
        self.assertEqual(source.calls, 1)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_constructor_does_not_issue_session_challenge_or_nonce(self) -> None:
        composition, http, source, *_ = _enrollment_composition()
        session_source = http.session_http._challenge_bytes.__self__
        self.assertEqual(session_source.challenge_calls, 0)
        self.assertEqual(session_source.session_calls, 0)
        self.assertEqual(source.calls, 0)
        self.assertEqual(
            len(composition.nonce_authority._outstanding),
            0,
        )
        self.assertEqual(
            len(composition.nonce_authority._spent),
            0,
        )


if __name__ == "__main__":
    unittest.main()
