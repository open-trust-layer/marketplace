from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import patch

from marketplace.application.auth_enrollment_asgi_composition import (
    compose_marketplace_authentication_enrollment_asgi as _compose_k,
)
from marketplace.application.auth_enrollment_http_composition import (
    compose_marketplace_authentication_enrollment_http as _compose_j,
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
from marketplace.application.auth_runtime_inputs import (
    compose_marketplace_authentication_runtime_inputs,
)
from tests.test_m17_5t_auth_startup_composition import _compose as _compose_startup
from tests.test_m17_6i_auth_enrollment_http import (
    AUTHORITY,
    LEASE_SECONDS,
    NONCE,
    RecordingAttestor,
    RecordingPolicy,
    SequenceMaterialSource,
)


MODULE = "marketplace.application.auth_enrollment_startup_composition"


def _inputs():
    startup, _application, _provisioning, runtime_inputs = _compose_startup()
    nonce_source = SequenceMaterialSource([NONCE])
    nonce_authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
        material_source=nonce_source
    )
    policy = RecordingPolicy()
    attestor = RecordingAttestor()
    return (
        startup,
        runtime_inputs,
        nonce_source,
        nonce_authority,
        policy,
        attestor,
    )


def _compose():
    startup, runtime_inputs, nonce_source, nonce_authority, policy, attestor = _inputs()
    result = compose_marketplace_authentication_enrollment_startup(
        authenticated_startup=startup,
        runtime_inputs=runtime_inputs,
        nonce_authority=nonce_authority,
        policy=policy,
        attestor=attestor,
        authority=AUTHORITY,
        evidence_lease_seconds=LEASE_SECONDS,
    )
    return result, startup, runtime_inputs, nonce_source, nonce_authority, policy, attestor


class M176LAuthenticationEnrollmentStartupCompositionTests(unittest.TestCase):
    def test_profile_exact_identity_and_frozen_overlay(self) -> None:
        result, startup, runtime_inputs, _source, nonce_authority, policy, attestor = _compose()
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_STARTUP_COMPOSITION_V1",
        )
        self.assertIs(type(result), MarketplaceAuthenticationEnrollmentStartupComposition)
        self.assertIs(result.authenticated_startup, startup)
        self.assertIs(result.runtime_inputs, runtime_inputs)
        self.assertIs(result.enrollment_http.http, startup.http)
        self.assertIs(result.enrollment_http.nonce_authority, nonce_authority)
        self.assertIs(result.enrollment_http.policy, policy)
        self.assertIs(result.enrollment_http.attestor, attestor)
        self.assertEqual(result.enrollment_http.authority, AUTHORITY)
        self.assertEqual(result.enrollment_http.evidence_lease_seconds, LEASE_SECONDS)
        self.assertIs(result.enrollment_asgi.enrollment, result.enrollment_http)
        self.assertIs(result.enrollment_asgi.runtime_inputs, runtime_inputs)
        self.assertIs(
            result.enrollment_asgi.asgi._enrollment_http,
            result.enrollment_http.enrollment_http,
        )
        with self.assertRaises(FrozenInstanceError):
            result.runtime_inputs = object()  # type: ignore[misc,assignment]

    def test_overlay_calls_j_then_k_once_with_exact_existing_graph(self) -> None:
        startup, runtime_inputs, _source, nonce_authority, policy, attestor = _inputs()
        with (
            patch(f"{MODULE}.compose_marketplace_authentication_enrollment_http", wraps=_compose_j) as j,
            patch(f"{MODULE}.compose_marketplace_authentication_enrollment_asgi", wraps=_compose_k) as k,
        ):
            result = compose_marketplace_authentication_enrollment_startup(
                authenticated_startup=startup,
                runtime_inputs=runtime_inputs,
                nonce_authority=nonce_authority,
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )
        self.assertEqual(j.call_count, 1)
        self.assertEqual(k.call_count, 1)
        self.assertIs(j.call_args.kwargs["http"], startup.http)
        self.assertIs(j.call_args.kwargs["nonce_authority"], nonce_authority)
        self.assertIs(j.call_args.kwargs["policy"], policy)
        self.assertIs(j.call_args.kwargs["attestor"], attestor)
        self.assertIs(k.call_args.kwargs["enrollment"], result.enrollment_http)
        self.assertIs(k.call_args.kwargs["runtime_inputs"], runtime_inputs)

    def test_overlay_consumes_no_new_clock_material_nonce_policy_or_attestor(self) -> None:
        startup, runtime_inputs, nonce_source, nonce_authority, policy, attestor = _inputs()
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
                nonce_authority,
                "issue_authentication_enrollment_nonce",
                side_effect=AssertionError("nonce issued"),
            ) as issue_nonce,
            patch.object(
                nonce_authority,
                "consume_authentication_enrollment_nonce",
                side_effect=AssertionError("nonce consumed"),
            ) as consume_nonce,
        ):
            result = compose_marketplace_authentication_enrollment_startup(
                authenticated_startup=startup,
                runtime_inputs=runtime_inputs,
                nonce_authority=nonce_authority,
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )
        self.assertIs(result.authenticated_startup, startup)
        clock.assert_not_called()
        material.assert_not_called()
        issue_nonce.assert_not_called()
        consume_nonce.assert_not_called()
        self.assertEqual(nonce_source.calls, 0)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_mismatched_runtime_inputs_fail_before_j_or_k(self) -> None:
        startup, _runtime_inputs, nonce_source, nonce_authority, policy, attestor = _inputs()
        other = compose_marketplace_authentication_runtime_inputs()
        with (
            patch(f"{MODULE}.compose_marketplace_authentication_enrollment_http") as j,
            patch(f"{MODULE}.compose_marketplace_authentication_enrollment_asgi") as k,
            self.assertRaises(MarketplaceAuthenticationEnrollmentStartupCompositionError),
        ):
            compose_marketplace_authentication_enrollment_startup(
                authenticated_startup=startup,
                runtime_inputs=other,
                nonce_authority=nonce_authority,
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )
        j.assert_not_called()
        k.assert_not_called()
        self.assertEqual(nonce_source.calls, 0)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_corrupted_base_startup_fails_before_j_or_k(self) -> None:
        startup, runtime_inputs, _source, nonce_authority, policy, attestor = _inputs()
        object.__setattr__(startup.asgi, "http", object())
        with (
            patch(f"{MODULE}.compose_marketplace_authentication_enrollment_http") as j,
            patch(f"{MODULE}.compose_marketplace_authentication_enrollment_asgi") as k,
            self.assertRaises(MarketplaceAuthenticationEnrollmentStartupCompositionError),
        ):
            compose_marketplace_authentication_enrollment_startup(
                authenticated_startup=startup,
                runtime_inputs=runtime_inputs,
                nonce_authority=nonce_authority,
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )
        j.assert_not_called()
        k.assert_not_called()

    def test_invalid_authority_lease_or_collaborator_fails_stably(self) -> None:
        cases = (
            {"authority": "relative"},
            {"evidence_lease_seconds": 0},
            {"policy": object()},
            {"attestor": object()},
        )
        for changes in cases:
            startup, runtime_inputs, _source, nonce_authority, policy, attestor = _inputs()
            kwargs = {
                "authenticated_startup": startup,
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

    def test_base_startup_remains_unchanged_and_launch_unselected(self) -> None:
        result, startup, runtime_inputs, *_ = _compose()
        self.assertIs(startup.asgi.runtime_inputs, runtime_inputs)
        self.assertIsNone(startup.asgi.asgi._enrollment_http)
        self.assertIsNot(result.enrollment_asgi.asgi, startup.asgi.asgi)
        self.assertIsNotNone(result.enrollment_asgi.asgi._enrollment_http)


if __name__ == "__main__":
    unittest.main()
