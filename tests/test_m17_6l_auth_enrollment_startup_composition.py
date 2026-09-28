from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.auth_enrollment_asgi_composition import (
    MarketplaceAuthenticationEnrollmentAsgiComposition,
)
from marketplace.application.auth_enrollment_http_composition import (
    MarketplaceAuthenticationEnrollmentHttpComposition,
)
from marketplace.application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from marketplace.application.auth_enrollment_startup_composition import (
    MarketplaceAuthenticationEnrollmentStartupComposition,
    MarketplaceAuthenticationEnrollmentStartupCompositionError,
    PROFILE_NAME,
    compose_marketplace_authentication_enrollment_startup,
)
from marketplace.application.auth_startup_composition import (
    MarketplaceAuthenticatedStartupComposition,
)
from tests.test_m17_5t_auth_startup_composition import _compose as _compose_auth_startup
from tests.test_m17_6i_auth_enrollment_http import (
    AUTHORITY,
    LEASE_SECONDS,
    NONCE,
    RecordingAttestor,
    RecordingPolicy,
    SequenceMaterialSource,
)


def _inputs():
    authenticated_startup, _application, _provisioning, runtime_inputs = (
        _compose_auth_startup()
    )
    nonce_source = SequenceMaterialSource([NONCE])
    nonce_authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
        material_source=nonce_source
    )
    policy = RecordingPolicy()
    attestor = RecordingAttestor()
    return (
        authenticated_startup,
        runtime_inputs,
        nonce_source,
        nonce_authority,
        policy,
        attestor,
    )


def _compose():
    (
        authenticated_startup,
        runtime_inputs,
        nonce_source,
        nonce_authority,
        policy,
        attestor,
    ) = _inputs()
    result = compose_marketplace_authentication_enrollment_startup(
        authenticated_startup=authenticated_startup,
        runtime_inputs=runtime_inputs,
        nonce_authority=nonce_authority,
        policy=policy,
        attestor=attestor,
        authority=AUTHORITY,
        evidence_lease_seconds=LEASE_SECONDS,
    )
    return result, nonce_source, policy, attestor


def _corrupted_startup(
    first: MarketplaceAuthenticatedStartupComposition,
    second: MarketplaceAuthenticatedStartupComposition,
) -> MarketplaceAuthenticatedStartupComposition:
    corrupted = object.__new__(MarketplaceAuthenticatedStartupComposition)
    object.__setattr__(corrupted, "authentication", first.authentication)
    object.__setattr__(corrupted, "http", first.http)
    object.__setattr__(corrupted, "asgi", second.asgi)
    return corrupted


class M176LAuthenticationEnrollmentStartupCompositionTests(unittest.TestCase):
    def test_profile_exact_types_and_identity_coherence(self) -> None:
        result, nonce_source, policy, attestor = _compose()
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_STARTUP_COMPOSITION_V1",
        )
        self.assertIs(
            type(result),
            MarketplaceAuthenticationEnrollmentStartupComposition,
        )
        self.assertIs(
            type(result.enrollment_http),
            MarketplaceAuthenticationEnrollmentHttpComposition,
        )
        self.assertIs(
            type(result.enrollment_asgi),
            MarketplaceAuthenticationEnrollmentAsgiComposition,
        )
        self.assertIs(
            result.runtime_inputs,
            result.authenticated_startup.asgi.runtime_inputs,
        )
        self.assertIs(
            result.enrollment_http.http,
            result.authenticated_startup.http,
        )
        self.assertIs(result.enrollment_asgi.enrollment, result.enrollment_http)
        self.assertIs(result.enrollment_asgi.runtime_inputs, result.runtime_inputs)
        self.assertIs(
            result.enrollment_asgi.asgi._site,
            result.authenticated_startup.http.application.site,
        )
        self.assertIs(
            result.enrollment_asgi.asgi._marketplace_http,
            result.authenticated_startup.http.application_http,
        )
        self.assertIs(
            result.enrollment_asgi.asgi._auth_http,
            result.authenticated_startup.http.session_http,
        )
        self.assertIs(
            result.enrollment_asgi.asgi._enrollment_http,
            result.enrollment_http.enrollment_http,
        )
        self.assertEqual(nonce_source.calls, 0)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_overlay_composition_consumes_no_new_runtime_or_enrollment_input(self) -> None:
        (
            authenticated_startup,
            runtime_inputs,
            nonce_source,
            nonce_authority,
            policy,
            attestor,
        ) = _inputs()
        with (
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                side_effect=AssertionError("clock consumed"),
            ) as clock,
            patch(
                "marketplace.application.auth_material._token_bytes",
                side_effect=AssertionError("credential material consumed"),
            ) as material,
            patch.object(
                SequenceMaterialSource,
                "enrollment_nonce_bytes",
                side_effect=AssertionError("nonce material consumed"),
            ) as nonce_material,
        ):
            result = compose_marketplace_authentication_enrollment_startup(
                authenticated_startup=authenticated_startup,
                runtime_inputs=runtime_inputs,
                nonce_authority=nonce_authority,
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )
        self.assertIs(result.authenticated_startup, authenticated_startup)
        clock.assert_not_called()
        material.assert_not_called()
        nonce_material.assert_not_called()
        self.assertEqual(nonce_source.calls, 0)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_mismatched_runtime_inputs_fail_before_j_or_k_construction(self) -> None:
        (
            authenticated_startup,
            _runtime_inputs,
            _nonce_source,
            nonce_authority,
            policy,
            attestor,
        ) = _inputs()
        _other_startup, _a, _p, other_runtime_inputs = _compose_auth_startup()
        with (
            patch(
                "marketplace.application.auth_enrollment_startup_composition."
                "compose_marketplace_authentication_enrollment_http"
            ) as compose_j,
            patch(
                "marketplace.application.auth_enrollment_startup_composition."
                "compose_marketplace_authentication_enrollment_asgi"
            ) as compose_k,
        ):
            with self.assertRaises(
                MarketplaceAuthenticationEnrollmentStartupCompositionError
            ):
                compose_marketplace_authentication_enrollment_startup(
                    authenticated_startup=authenticated_startup,
                    runtime_inputs=other_runtime_inputs,
                    nonce_authority=nonce_authority,
                    policy=policy,
                    attestor=attestor,
                    authority=AUTHORITY,
                    evidence_lease_seconds=LEASE_SECONDS,
                )
        compose_j.assert_not_called()
        compose_k.assert_not_called()

    def test_corrupted_base_startup_fails_before_j_or_k_construction(self) -> None:
        (
            first,
            runtime_inputs,
            _nonce_source,
            nonce_authority,
            policy,
            attestor,
        ) = _inputs()
        second, _a, _p, _r = _compose_auth_startup()
        corrupted = _corrupted_startup(first, second)
        with (
            patch(
                "marketplace.application.auth_enrollment_startup_composition."
                "compose_marketplace_authentication_enrollment_http"
            ) as compose_j,
            patch(
                "marketplace.application.auth_enrollment_startup_composition."
                "compose_marketplace_authentication_enrollment_asgi"
            ) as compose_k,
        ):
            with self.assertRaises(
                MarketplaceAuthenticationEnrollmentStartupCompositionError
            ):
                compose_marketplace_authentication_enrollment_startup(
                    authenticated_startup=corrupted,
                    runtime_inputs=runtime_inputs,
                    nonce_authority=nonce_authority,
                    policy=policy,
                    attestor=attestor,
                    authority=AUTHORITY,
                    evidence_lease_seconds=LEASE_SECONDS,
                )
        compose_j.assert_not_called()
        compose_k.assert_not_called()

    def test_invalid_collaborator_authority_and_lease_fail_stably(self) -> None:
        cases = (
            {"policy": object()},
            {"attestor": object()},
            {"authority": "relative"},
            {"evidence_lease_seconds": 0},
        )
        for changes in cases:
            (
                authenticated_startup,
                runtime_inputs,
                nonce_source,
                nonce_authority,
                policy,
                attestor,
            ) = _inputs()
            kwargs = {
                "authenticated_startup": authenticated_startup,
                "runtime_inputs": runtime_inputs,
                "nonce_authority": nonce_authority,
                "policy": policy,
                "attestor": attestor,
                "authority": AUTHORITY,
                "evidence_lease_seconds": LEASE_SECONDS,
            }
            kwargs.update(changes)
            with self.subTest(changes=changes):
                with self.assertRaises(
                    MarketplaceAuthenticationEnrollmentStartupCompositionError
                ) as caught:
                    compose_marketplace_authentication_enrollment_startup(
                        **kwargs  # type: ignore[arg-type]
                    )
                self.assertEqual(
                    str(caught.exception),
                    "authentication enrollment startup composition failed",
                )
                self.assertEqual(nonce_source.calls, 0)
                self.assertEqual(policy.calls, 0)
                self.assertEqual(attestor.calls, 0)

    def test_base_authenticated_startup_is_not_replaced_or_mutated(self) -> None:
        (
            authenticated_startup,
            runtime_inputs,
            _nonce_source,
            nonce_authority,
            policy,
            attestor,
        ) = _inputs()
        base_authentication = authenticated_startup.authentication
        base_http = authenticated_startup.http
        base_asgi = authenticated_startup.asgi
        result = compose_marketplace_authentication_enrollment_startup(
            authenticated_startup=authenticated_startup,
            runtime_inputs=runtime_inputs,
            nonce_authority=nonce_authority,
            policy=policy,
            attestor=attestor,
            authority=AUTHORITY,
            evidence_lease_seconds=LEASE_SECONDS,
        )
        self.assertIs(result.authenticated_startup, authenticated_startup)
        self.assertIs(authenticated_startup.authentication, base_authentication)
        self.assertIs(authenticated_startup.http, base_http)
        self.assertIs(authenticated_startup.asgi, base_asgi)
        self.assertIsNone(authenticated_startup.asgi.asgi._enrollment_http)


if __name__ == "__main__":
    unittest.main()
