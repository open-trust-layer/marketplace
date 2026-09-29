from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.auth_enrollment_launch import (
    build_marketplace_authentication_enrollment_loopback_launch_plan as _build_m,
)
from marketplace.application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from marketplace.application.auth_enrollment_startup_composition import (
    compose_marketplace_authentication_enrollment_startup as _compose_l,
)
from marketplace.application.auth_launch import (
    MarketplaceAuthenticatedLoopbackLaunchPlan,
    build_marketplace_authenticated_loopback_launch_plan,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from marketplace.application.launch import LOOPBACK_LAUNCH_HOST
from marketplace.reference.auth_enrollment_launch_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAuthenticationEnrollmentLaunch,
    MarketplaceReferenceAuthenticationEnrollmentLaunchError,
    build_reference_authentication_enrollment_launch,
)
from tests.test_m17_5t_auth_startup_composition import _compose as _compose_authenticated
from tests.test_m17_6i_auth_enrollment_http import (
    AUTHORITY,
    LEASE_SECONDS,
    NONCE,
    RecordingAttestor,
    RecordingPolicy,
    SequenceMaterialSource,
)


MODULE = "marketplace.reference.auth_enrollment_launch_v1"
PORT = 18443
ERROR_MESSAGE = "reference authentication enrollment launch composition failed"


def _inputs():
    startup, _application, _provisioning, _runtime_inputs = _compose_authenticated()
    authenticated_plan = build_marketplace_authenticated_loopback_launch_plan(
        host=LOOPBACK_LAUNCH_HOST,
        port=PORT,
        startup=startup,
    )
    nonce_source = SequenceMaterialSource([NONCE])
    nonce_authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
        material_source=nonce_source
    )
    policy = RecordingPolicy()
    attestor = RecordingAttestor()
    return (
        authenticated_plan,
        nonce_source,
        nonce_authority,
        policy,
        attestor,
    )


def _build():
    authenticated_plan, nonce_source, nonce_authority, policy, attestor = _inputs()
    result = build_reference_authentication_enrollment_launch(
        authenticated_plan=authenticated_plan,
        nonce_authority=nonce_authority,
        policy=policy,
        attestor=attestor,
        authority=AUTHORITY,
        evidence_lease_seconds=LEASE_SECONDS,
    )
    return result, authenticated_plan, nonce_source, nonce_authority, policy, attestor


def _forged_authenticated_plan(
    source: MarketplaceAuthenticatedLoopbackLaunchPlan,
    *,
    asgi: object,
) -> MarketplaceAuthenticatedLoopbackLaunchPlan:
    result = object.__new__(MarketplaceAuthenticatedLoopbackLaunchPlan)
    object.__setattr__(result, "host", source.host)
    object.__setattr__(result, "port", source.port)
    object.__setattr__(result, "startup", source.startup)
    object.__setattr__(result, "asgi", asgi)
    return result


class M176OReferenceAuthenticationEnrollmentLaunchTests(unittest.TestCase):
    def test_profile_and_exact_graph_selection(self) -> None:
        result, authenticated, _source, nonce_authority, policy, attestor = _build()

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_V1",
        )
        self.assertIs(
            type(result),
            MarketplaceReferenceAuthenticationEnrollmentLaunch,
        )
        self.assertIs(result.authenticated_plan, authenticated)
        self.assertIs(result.nonce_authority, nonce_authority)
        self.assertIs(result.policy, policy)
        self.assertIs(result.attestor, attestor)
        self.assertEqual(result.authority, AUTHORITY)
        self.assertEqual(result.evidence_lease_seconds, LEASE_SECONDS)
        self.assertIs(result.startup.authenticated_startup, authenticated.startup)
        self.assertIs(
            result.startup.runtime_inputs,
            authenticated.startup.asgi.runtime_inputs,
        )
        self.assertIs(
            result.startup.enrollment_http.nonce_authority,
            nonce_authority,
        )
        self.assertIs(result.startup.enrollment_http.policy, policy)
        self.assertIs(result.startup.enrollment_http.attestor, attestor)
        self.assertEqual(result.startup.enrollment_http.authority, AUTHORITY)
        self.assertEqual(
            result.startup.enrollment_http.evidence_lease_seconds,
            LEASE_SECONDS,
        )
        self.assertIs(result.plan.startup, result.startup)
        self.assertEqual(result.plan.host, authenticated.host)
        self.assertEqual(result.plan.port, authenticated.port)
        self.assertIs(result.plan.asgi, result.startup.enrollment_asgi.asgi)
        self.assertIsNone(authenticated.asgi._enrollment_http)
        self.assertIsNot(result.plan.asgi, authenticated.asgi)

    def test_selection_composes_l_then_m_once_with_exact_existing_graph(self) -> None:
        authenticated, _source, nonce_authority, policy, attestor = _inputs()

        with (
            patch(
                f"{MODULE}.compose_marketplace_authentication_enrollment_startup",
                wraps=_compose_l,
            ) as compose_l,
            patch(
                f"{MODULE}.build_marketplace_authentication_enrollment_loopback_launch_plan",
                wraps=_build_m,
            ) as build_m,
        ):
            result = build_reference_authentication_enrollment_launch(
                authenticated_plan=authenticated,
                nonce_authority=nonce_authority,
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

        self.assertEqual(compose_l.call_count, 1)
        self.assertEqual(build_m.call_count, 1)
        self.assertIs(
            compose_l.call_args.kwargs["authenticated_startup"],
            authenticated.startup,
        )
        self.assertIs(
            compose_l.call_args.kwargs["runtime_inputs"],
            authenticated.startup.asgi.runtime_inputs,
        )
        self.assertIs(compose_l.call_args.kwargs["nonce_authority"], nonce_authority)
        self.assertIs(compose_l.call_args.kwargs["policy"], policy)
        self.assertIs(compose_l.call_args.kwargs["attestor"], attestor)
        self.assertEqual(compose_l.call_args.kwargs["authority"], AUTHORITY)
        self.assertEqual(
            compose_l.call_args.kwargs["evidence_lease_seconds"],
            LEASE_SECONDS,
        )
        self.assertEqual(build_m.call_args.kwargs["host"], authenticated.host)
        self.assertEqual(build_m.call_args.kwargs["port"], authenticated.port)
        self.assertIs(build_m.call_args.kwargs["startup"], result.startup)

    def test_selection_consumes_no_enrollment_runtime_or_provider_authority(self) -> None:
        authenticated, nonce_source, nonce_authority, policy, attestor = _inputs()

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
            result = build_reference_authentication_enrollment_launch(
                authenticated_plan=authenticated,
                nonce_authority=nonce_authority,
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

        self.assertIs(result.plan.asgi, result.startup.enrollment_asgi.asgi)
        self.assertIsNone(authenticated.asgi._enrollment_http)
        clock.assert_not_called()
        material.assert_not_called()
        issue_nonce.assert_not_called()
        consume_nonce.assert_not_called()
        request.assert_not_called()
        runtime.assert_not_called()
        provider.assert_not_called()
        socket.assert_not_called()
        self.assertEqual(nonce_source.calls, 0)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_invalid_or_cross_bound_authenticated_plan_fails_closed(self) -> None:
        authenticated, _source, nonce_authority, policy, attestor = _inputs()
        other, *_ = _inputs()
        invalid_plans = (
            object(),
            _forged_authenticated_plan(authenticated, asgi=other.asgi),
        )
        for invalid in invalid_plans:
            with self.subTest(invalid=type(invalid).__name__):
                with self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentLaunchError
                ) as caught:
                    build_reference_authentication_enrollment_launch(
                        authenticated_plan=invalid,  # type: ignore[arg-type]
                        nonce_authority=nonce_authority,
                        policy=policy,
                        attestor=attestor,
                        authority=AUTHORITY,
                        evidence_lease_seconds=LEASE_SECONDS,
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)

    def test_invalid_nonce_policy_or_attestor_fails_stably(self) -> None:
        cases = (
            {"nonce_authority": object()},
            {"policy": object()},
            {"attestor": object()},
        )
        for changes in cases:
            authenticated, _source, nonce_authority, policy, attestor = _inputs()
            kwargs = {
                "authenticated_plan": authenticated,
                "nonce_authority": nonce_authority,
                "policy": policy,
                "attestor": attestor,
                "authority": AUTHORITY,
                "evidence_lease_seconds": LEASE_SECONDS,
            }
            kwargs.update(changes)
            with self.subTest(changes=tuple(changes)):
                with self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentLaunchError
                ) as caught:
                    build_reference_authentication_enrollment_launch(
                        **kwargs  # type: ignore[arg-type]
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)


if __name__ == "__main__":
    unittest.main()
