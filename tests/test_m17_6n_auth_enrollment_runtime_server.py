from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.auth_enrollment_launch import (
    MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan,
    build_marketplace_authentication_enrollment_loopback_launch_plan,
)
from marketplace.application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from marketplace.application.auth_enrollment_runtime_server import (
    EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER,
    PROFILE_NAME,
    MarketplaceAuthenticationEnrollmentLocalRuntimeError,
    run_marketplace_authentication_enrollment_foreground,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from marketplace.application.launch import (
    LOOPBACK_LAUNCH_HOST,
    MAX_LAUNCH_PORT,
    MIN_LAUNCH_PORT,
)
from tests.test_m17_6l_auth_enrollment_startup_composition import _compose


ERROR_MESSAGE = "authentication enrollment loopback runtime failed"


class _StringSubclass(str):
    pass


class _IntegerSubclass(int):
    pass


class _ProviderProbe:
    def __init__(self, *, fail: bool = False, expose_callable: bool = True) -> None:
        self.inspections = 0
        self.calls: list[tuple[object, str, int]] = []
        self.fail = fail
        self.expose_callable = expose_callable

    @property
    def run(self):
        self.inspections += 1
        if not self.expose_callable:
            return None

        def invoke(*, application: object, host: str, port: int) -> None:
            self.calls.append((application, host, port))
            if self.fail:
                raise ValueError("provider secret detail")

        return invoke


class _ExplodingProvider:
    @property
    def run(self):
        raise ValueError("provider inspection secret")


def _plan(port: int = 8443):
    startup, authenticated_startup, runtime_inputs, nonce_source, nonce_authority, policy, attestor = _compose()
    plan = build_marketplace_authentication_enrollment_loopback_launch_plan(
        host=LOOPBACK_LAUNCH_HOST,
        port=port,
        startup=startup,
    )
    return (
        plan,
        authenticated_startup,
        runtime_inputs,
        nonce_source,
        nonce_authority,
        policy,
        attestor,
    )


def _forged_plan(
    source: MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan,
    *,
    host: object | None = None,
    port: object | None = None,
    startup: object | None = None,
    asgi: object | None = None,
) -> MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan:
    result = object.__new__(MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan)
    object.__setattr__(result, "host", source.host if host is None else host)
    object.__setattr__(result, "port", source.port if port is None else port)
    object.__setattr__(
        result,
        "startup",
        source.startup if startup is None else startup,
    )
    object.__setattr__(result, "asgi", source.asgi if asgi is None else asgi)
    return result


class M176NAuthenticationEnrollmentRuntimeServerTests(unittest.TestCase):
    def test_profile_token_and_single_provider_delegation(self) -> None:
        plan, *_ = _plan()
        provider = _ProviderProbe()

        result = run_marketplace_authentication_enrollment_foreground(
            plan=plan,
            provider=provider,
            execute_token=(
                EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
            ),
        )

        self.assertIsNone(result)
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_FOREGROUND_RUNTIME_V1",
        )
        self.assertEqual(
            EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER,
            "EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER",
        )
        self.assertEqual(provider.inspections, 1)
        self.assertEqual(provider.calls, [(plan.asgi, plan.host, plan.port)])

    def test_wrong_token_fails_before_provider_inspection(self) -> None:
        plan, *_ = _plan()
        tokens = (
            "",
            "EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER",
            _StringSubclass(
                EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
            ),
            object(),
        )
        for token in tokens:
            provider = _ProviderProbe()
            with self.subTest(token=type(token).__name__):
                with self.assertRaises(
                    MarketplaceAuthenticationEnrollmentLocalRuntimeError
                ) as caught:
                    run_marketplace_authentication_enrollment_foreground(
                        plan=plan,
                        provider=provider,
                        execute_token=token,  # type: ignore[arg-type]
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                self.assertEqual(provider.inspections, 0)
                self.assertEqual(provider.calls, [])

    def test_invalid_plan_fails_before_provider_inspection(self) -> None:
        valid, *_ = _plan()
        invalid_plans = (
            object(),
            _forged_plan(valid, host="0.0.0.0"),
            _forged_plan(valid, host=_StringSubclass(LOOPBACK_LAUNCH_HOST)),
            _forged_plan(valid, port=True),
            _forged_plan(valid, port=_IntegerSubclass(8443)),
            _forged_plan(valid, port=MIN_LAUNCH_PORT - 1),
            _forged_plan(valid, port=MAX_LAUNCH_PORT + 1),
            _forged_plan(valid, startup=object()),
            _forged_plan(valid, asgi=object()),
        )
        for invalid in invalid_plans:
            provider = _ProviderProbe()
            with self.subTest(invalid=type(invalid).__name__):
                with self.assertRaises(
                    MarketplaceAuthenticationEnrollmentLocalRuntimeError
                ) as caught:
                    run_marketplace_authentication_enrollment_foreground(
                        plan=invalid,  # type: ignore[arg-type]
                        provider=provider,
                        execute_token=(
                            EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
                        ),
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                self.assertEqual(provider.inspections, 0)
                self.assertEqual(provider.calls, [])

    def test_cross_bound_or_corrupted_graph_fails_before_provider_inspection(self) -> None:
        plan, *_ = _plan()
        other, *_ = _plan(port=8444)

        cross_bound = _forged_plan(plan, asgi=other.asgi)
        for invalid in (cross_bound,):
            provider = _ProviderProbe()
            with self.assertRaises(
                MarketplaceAuthenticationEnrollmentLocalRuntimeError
            ):
                run_marketplace_authentication_enrollment_foreground(
                    plan=invalid,
                    provider=provider,
                    execute_token=(
                        EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
                    ),
                )
            self.assertEqual(provider.inspections, 0)
            self.assertEqual(provider.calls, [])

        corrupted, *_ = _plan()
        object.__setattr__(corrupted.asgi, "_enrollment_http", object())
        provider = _ProviderProbe()
        with self.assertRaises(MarketplaceAuthenticationEnrollmentLocalRuntimeError):
            run_marketplace_authentication_enrollment_foreground(
                plan=corrupted,
                provider=provider,
                execute_token=(
                    EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
                ),
            )
        self.assertEqual(provider.inspections, 0)
        self.assertEqual(provider.calls, [])

    def test_corrupted_clock_owner_fails_before_provider_inspection(self) -> None:
        plan, *_ = _plan()
        object.__setattr__(plan.asgi, "_now", lambda: 100)
        provider = _ProviderProbe()
        with self.assertRaises(MarketplaceAuthenticationEnrollmentLocalRuntimeError):
            run_marketplace_authentication_enrollment_foreground(
                plan=plan,
                provider=provider,
                execute_token=(
                    EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
                ),
            )
        self.assertEqual(provider.inspections, 0)
        self.assertEqual(provider.calls, [])

    def test_provider_shape_and_failure_are_stable_and_not_retried(self) -> None:
        plan, *_ = _plan()

        missing = _ProviderProbe(expose_callable=False)
        with self.assertRaises(
            MarketplaceAuthenticationEnrollmentLocalRuntimeError
        ) as caught:
            run_marketplace_authentication_enrollment_foreground(
                plan=plan,
                provider=missing,
                execute_token=(
                    EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
                ),
            )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertEqual(missing.inspections, 1)
        self.assertEqual(missing.calls, [])

        exploding = _ExplodingProvider()
        with self.assertRaises(
            MarketplaceAuthenticationEnrollmentLocalRuntimeError
        ) as caught:
            run_marketplace_authentication_enrollment_foreground(
                plan=plan,
                provider=exploding,
                execute_token=(
                    EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
                ),
            )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("provider inspection secret", str(caught.exception))

        failing = _ProviderProbe(fail=True)
        with self.assertRaises(
            MarketplaceAuthenticationEnrollmentLocalRuntimeError
        ) as caught:
            run_marketplace_authentication_enrollment_foreground(
                plan=plan,
                provider=failing,
                execute_token=(
                    EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
                ),
            )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("provider secret detail", str(caught.exception))
        self.assertEqual(failing.inspections, 1)
        self.assertEqual(len(failing.calls), 1)

    def test_execution_seam_consumes_no_other_authority_before_provider_call(self) -> None:
        plan, _authenticated_startup, _runtime_inputs, nonce_source, _nonce_authority, policy, attestor = _plan()
        provider = _ProviderProbe()
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
            patch(
                "marketplace.application.auth_startup_provisioning."
                "load_marketplace_authentication_startup_provisioning",
                side_effect=AssertionError("provisioning consumed"),
            ) as provisioning,
            patch(
                "marketplace.application.composition."
                "MarketplaceApplicationComposition.initialize",
                side_effect=AssertionError("application initialized"),
            ) as initialize,
            patch.object(
                MarketplaceSessionEstablishmentAsgiHttpAdapter,
                "__call__",
                side_effect=AssertionError("request handled"),
            ) as request,
            patch("socket.socket", side_effect=AssertionError("socket used")) as socket,
        ):
            run_marketplace_authentication_enrollment_foreground(
                plan=plan,
                provider=provider,
                execute_token=(
                    EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
                ),
            )

        self.assertEqual(provider.inspections, 1)
        self.assertEqual(provider.calls, [(plan.asgi, plan.host, plan.port)])
        clock.assert_not_called()
        material.assert_not_called()
        issue_nonce.assert_not_called()
        consume_nonce.assert_not_called()
        provisioning.assert_not_called()
        initialize.assert_not_called()
        request.assert_not_called()
        socket.assert_not_called()
        self.assertEqual(nonce_source.calls, 0)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)


if __name__ == "__main__":
    unittest.main()
