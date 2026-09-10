from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.auth_asgi_composition import (
    MarketplaceAuthenticatedAsgiComposition,
)
from marketplace.application.auth_launch import (
    MarketplaceAuthenticatedLoopbackLaunchPlan,
    build_marketplace_authenticated_loopback_launch_plan,
)
from marketplace.application.auth_runtime_server import (
    EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER,
    PROFILE_NAME,
    MarketplaceAuthenticatedLocalRuntimeError,
    run_marketplace_authenticated_application_foreground,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from marketplace.application.auth_startup_composition import (
    MarketplaceAuthenticatedStartupComposition,
)
from marketplace.application.launch import (
    LOOPBACK_LAUNCH_HOST,
    MAX_LAUNCH_PORT,
    MIN_LAUNCH_PORT,
)
from tests.test_m17_5t_auth_startup_composition import _compose


ERROR_MESSAGE = "authenticated Marketplace loopback runtime failed"


class _StringSubclass(str):
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
    startup, application, provisioning, runtime_inputs = _compose()
    plan = build_marketplace_authenticated_loopback_launch_plan(
        host=LOOPBACK_LAUNCH_HOST,
        port=port,
        startup=startup,
    )
    return plan, application, provisioning, runtime_inputs


def _forged_plan(
    source: MarketplaceAuthenticatedLoopbackLaunchPlan,
    *,
    host: object | None = None,
    port: object | None = None,
    startup: object | None = None,
    asgi: object | None = None,
) -> MarketplaceAuthenticatedLoopbackLaunchPlan:
    result = object.__new__(MarketplaceAuthenticatedLoopbackLaunchPlan)
    object.__setattr__(result, "host", source.host if host is None else host)
    object.__setattr__(result, "port", source.port if port is None else port)
    selected_startup = source.startup if startup is None else startup
    object.__setattr__(result, "startup", selected_startup)
    object.__setattr__(result, "asgi", source.asgi if asgi is None else asgi)
    return result


def _corrupt_startup_http(
    startup: MarketplaceAuthenticatedStartupComposition,
) -> MarketplaceAuthenticatedStartupComposition:
    corrupted_asgi = object.__new__(MarketplaceAuthenticatedAsgiComposition)
    object.__setattr__(corrupted_asgi, "http", object())
    object.__setattr__(corrupted_asgi, "runtime_inputs", startup.asgi.runtime_inputs)
    object.__setattr__(corrupted_asgi, "asgi", startup.asgi.asgi)
    result = object.__new__(MarketplaceAuthenticatedStartupComposition)
    object.__setattr__(result, "authentication", startup.authentication)
    object.__setattr__(result, "http", startup.http)
    object.__setattr__(result, "asgi", corrupted_asgi)
    return result


class MarketplaceAuthenticatedRuntimeServerTests(unittest.TestCase):
    def test_profile_token_and_successful_single_delegation(self) -> None:
        plan, _application, _provisioning, _runtime_inputs = _plan()
        provider = _ProviderProbe()
        result = run_marketplace_authenticated_application_foreground(
            plan=plan,
            provider=provider,
            execute_token=EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER,
        )
        self.assertIsNone(result)
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_FOREGROUND_RUNTIME_V1",
        )
        self.assertEqual(
            EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER,
            "EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER",
        )
        self.assertEqual(provider.inspections, 1)
        self.assertEqual(len(provider.calls), 1)
        application, host, port = provider.calls[0]
        self.assertIs(application, plan.asgi)
        self.assertEqual(host, LOOPBACK_LAUNCH_HOST)
        self.assertEqual(port, plan.port)

    def test_wrong_token_fails_before_provider_inspection(self) -> None:
        plan, _application, _provisioning, _runtime_inputs = _plan()
        for token in (
            "",
            "EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER",
            _StringSubclass(EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER),
            object(),
        ):
            provider = _ProviderProbe()
            with self.subTest(token=type(token).__name__):
                with self.assertRaises(
                    MarketplaceAuthenticatedLocalRuntimeError
                ) as caught:
                    run_marketplace_authenticated_application_foreground(
                        plan=plan,
                        provider=provider,
                        execute_token=token,  # type: ignore[arg-type]
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                self.assertEqual(provider.inspections, 0)
                self.assertEqual(provider.calls, [])

    def test_invalid_plan_fails_before_provider_inspection(self) -> None:
        valid, _application, _provisioning, _runtime_inputs = _plan()
        invalid_plans = (
            object(),
            _forged_plan(valid, host="0.0.0.0"),
            _forged_plan(valid, host=_StringSubclass(LOOPBACK_LAUNCH_HOST)),
            _forged_plan(valid, port=True),
            _forged_plan(valid, port=MIN_LAUNCH_PORT - 1),
            _forged_plan(valid, port=MAX_LAUNCH_PORT + 1),
            _forged_plan(valid, startup=object()),
            _forged_plan(valid, asgi=object()),
        )
        for invalid in invalid_plans:
            provider = _ProviderProbe()
            with self.subTest(invalid=type(invalid).__name__):
                with self.assertRaises(
                    MarketplaceAuthenticatedLocalRuntimeError
                ) as caught:
                    run_marketplace_authenticated_application_foreground(
                        plan=invalid,  # type: ignore[arg-type]
                        provider=provider,
                        execute_token=(
                            EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER
                        ),
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                self.assertEqual(provider.inspections, 0)
                self.assertEqual(provider.calls, [])

    def test_corrupt_or_cross_bound_graph_fails_before_provider_inspection(
        self,
    ) -> None:
        plan, _application, _provisioning, _runtime_inputs = _plan()
        other, _app2, _prov2, _inputs2 = _plan(port=8444)
        corrupt_startup = _corrupt_startup_http(plan.startup)
        cases = (
            _forged_plan(plan, startup=corrupt_startup),
            _forged_plan(plan, asgi=other.asgi),
        )
        for invalid in cases:
            provider = _ProviderProbe()
            with self.subTest(asgi=id(invalid.asgi)):
                with self.assertRaises(MarketplaceAuthenticatedLocalRuntimeError):
                    run_marketplace_authenticated_application_foreground(
                        plan=invalid,
                        provider=provider,
                        execute_token=(
                            EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER
                        ),
                    )
                self.assertEqual(provider.inspections, 0)
                self.assertEqual(provider.calls, [])

    def test_deep_authenticated_asgi_binding_is_revalidated(self) -> None:
        plan, _application, _provisioning, _runtime_inputs = _plan()
        corrupted_asgi = object.__new__(MarketplaceSessionEstablishmentAsgiHttpAdapter)
        object.__setattr__(corrupted_asgi, "_site", object())
        object.__setattr__(
            corrupted_asgi,
            "_marketplace_http",
            plan.asgi._marketplace_http,
        )
        object.__setattr__(corrupted_asgi, "_auth_http", plan.asgi._auth_http)
        object.__setattr__(corrupted_asgi, "_now", plan.asgi._now)
        corrupted_r = object.__new__(MarketplaceAuthenticatedAsgiComposition)
        object.__setattr__(corrupted_r, "http", plan.startup.http)
        object.__setattr__(
            corrupted_r,
            "runtime_inputs",
            plan.startup.asgi.runtime_inputs,
        )
        object.__setattr__(corrupted_r, "asgi", corrupted_asgi)
        corrupted_startup = object.__new__(MarketplaceAuthenticatedStartupComposition)
        object.__setattr__(
            corrupted_startup,
            "authentication",
            plan.startup.authentication,
        )
        object.__setattr__(corrupted_startup, "http", plan.startup.http)
        object.__setattr__(corrupted_startup, "asgi", corrupted_r)
        invalid = _forged_plan(
            plan,
            startup=corrupted_startup,
            asgi=corrupted_asgi,
        )
        provider = _ProviderProbe()
        with self.assertRaises(MarketplaceAuthenticatedLocalRuntimeError):
            run_marketplace_authenticated_application_foreground(
                plan=invalid,
                provider=provider,
                execute_token=EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER,
            )
        self.assertEqual(provider.inspections, 0)
        self.assertEqual(provider.calls, [])

    def test_provider_shape_and_failure_are_stable_and_not_retried(self) -> None:
        plan, _application, _provisioning, _runtime_inputs = _plan()
        unavailable = _ProviderProbe(expose_callable=False)
        with self.assertRaises(MarketplaceAuthenticatedLocalRuntimeError) as caught:
            run_marketplace_authenticated_application_foreground(
                plan=plan,
                provider=unavailable,
                execute_token=EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER,
            )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertEqual(unavailable.inspections, 1)
        self.assertEqual(unavailable.calls, [])

        exploding = _ExplodingProvider()
        with self.assertRaises(MarketplaceAuthenticatedLocalRuntimeError) as caught:
            run_marketplace_authenticated_application_foreground(
                plan=plan,
                provider=exploding,
                execute_token=EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER,
            )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("provider inspection secret", str(caught.exception))

        failing = _ProviderProbe(fail=True)
        with self.assertRaises(MarketplaceAuthenticatedLocalRuntimeError) as caught:
            run_marketplace_authenticated_application_foreground(
                plan=plan,
                provider=failing,
                execute_token=EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER,
            )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("provider secret detail", str(caught.exception))
        self.assertEqual(failing.inspections, 1)
        self.assertEqual(len(failing.calls), 1)

    def test_execution_seam_consumes_no_other_runtime_authority(self) -> None:
        plan, _application, _provisioning, _runtime_inputs = _plan()
        provider = _ProviderProbe()
        with (
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                side_effect=AssertionError("clock consumed"),
            ) as clock,
            patch(
                "marketplace.application.auth_material._token_bytes",
                side_effect=AssertionError("material consumed"),
            ) as material,
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
            run_marketplace_authenticated_application_foreground(
                plan=plan,
                provider=provider,
                execute_token=EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER,
            )
        self.assertEqual(len(provider.calls), 1)
        clock.assert_not_called()
        material.assert_not_called()
        provisioning.assert_not_called()
        initialize.assert_not_called()
        request.assert_not_called()
        socket.assert_not_called()


if __name__ == "__main__":
    unittest.main()