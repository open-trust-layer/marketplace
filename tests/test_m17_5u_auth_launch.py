from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import patch

from marketplace.application.auth_asgi_composition import (
    MarketplaceAuthenticatedAsgiComposition,
)
from marketplace.application.auth_launch import (
    PROFILE_NAME,
    MarketplaceAuthenticatedLoopbackLaunchPlan,
    MarketplaceAuthenticatedLoopbackLaunchPlanError,
    build_marketplace_authenticated_loopback_launch_plan,
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


ERROR_MESSAGE = "authenticated Marketplace loopback launch plan failed"


class _StringSubclass(str):
    pass


class _IntegerSubclass(int):
    pass


def _corrupt_asgi_http(startup: MarketplaceAuthenticatedStartupComposition):
    corrupted = object.__new__(MarketplaceAuthenticatedAsgiComposition)
    object.__setattr__(corrupted, "http", object())
    object.__setattr__(corrupted, "runtime_inputs", startup.asgi.runtime_inputs)
    object.__setattr__(corrupted, "asgi", startup.asgi.asgi)
    result = object.__new__(MarketplaceAuthenticatedStartupComposition)
    object.__setattr__(result, "authentication", startup.authentication)
    object.__setattr__(result, "http", startup.http)
    object.__setattr__(result, "asgi", corrupted)
    return result


class MarketplaceAuthenticatedLoopbackLaunchPlanTests(unittest.TestCase):
    def test_profile_exact_identity_and_frozen_plan(self) -> None:
        startup, _application, _provisioning, _runtime_inputs = _compose()
        result = build_marketplace_authenticated_loopback_launch_plan(
            host=LOOPBACK_LAUNCH_HOST,
            port=8443,
            startup=startup,
        )
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_LOOPBACK_LAUNCH_PLAN_V1",
        )
        self.assertIs(type(result), MarketplaceAuthenticatedLoopbackLaunchPlan)
        self.assertEqual(result.host, "127.0.0.1")
        self.assertEqual(result.port, 8443)
        self.assertIs(result.startup, startup)
        self.assertIs(result.asgi, startup.asgi.asgi)
        self.assertIs(result.startup.asgi.http, result.startup.http)
        self.assertIs(result.startup.http.authentication, result.startup.authentication)
        with self.assertRaises(FrozenInstanceError):
            result.port = 9000  # type: ignore[misc,assignment]

    def test_existing_exact_port_bounds_are_accepted(self) -> None:
        startup, _application, _provisioning, _runtime_inputs = _compose()
        for port in (MIN_LAUNCH_PORT, MAX_LAUNCH_PORT):
            with self.subTest(port=port):
                result = build_marketplace_authenticated_loopback_launch_plan(
                    host=LOOPBACK_LAUNCH_HOST,
                    port=port,
                    startup=startup,
                )
                self.assertEqual(result.port, port)

    def test_host_port_and_startup_are_exact(self) -> None:
        startup, _application, _provisioning, _runtime_inputs = _compose()
        cases = (
            {"host": "0.0.0.0"},
            {"host": "::1"},
            {"host": "localhost"},
            {"host": _StringSubclass(LOOPBACK_LAUNCH_HOST)},
            {"port": 0},
            {"port": MAX_LAUNCH_PORT + 1},
            {"port": True},
            {"port": _IntegerSubclass(8443)},
            {"startup": object()},
        )
        for changes in cases:
            kwargs = {
                "host": LOOPBACK_LAUNCH_HOST,
                "port": 8443,
                "startup": startup,
            }
            kwargs.update(changes)
            with self.subTest(changes=changes):
                with self.assertRaises(
                    MarketplaceAuthenticatedLoopbackLaunchPlanError
                ) as caught:
                    build_marketplace_authenticated_loopback_launch_plan(
                        **kwargs  # type: ignore[arg-type]
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)

    def test_plan_creation_consumes_no_runtime_or_provisioning_sources(self) -> None:
        startup, _application, _provisioning, _runtime_inputs = _compose()
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
            ) as load_provisioning,
            patch(
                "marketplace.application.composition."
                "MarketplaceApplicationComposition.initialize",
                side_effect=AssertionError("application initialized"),
            ) as initialize,
            patch("socket.socket", side_effect=AssertionError("socket used")) as socket,
        ):
            result = build_marketplace_authenticated_loopback_launch_plan(
                host=LOOPBACK_LAUNCH_HOST,
                port=8443,
                startup=startup,
            )
        self.assertIs(result.asgi, startup.asgi.asgi)
        clock.assert_not_called()
        material.assert_not_called()
        load_provisioning.assert_not_called()
        initialize.assert_not_called()
        socket.assert_not_called()

    def test_corrupted_startup_graph_fails_closed(self) -> None:
        startup, _application, _provisioning, _runtime_inputs = _compose()
        corrupted = _corrupt_asgi_http(startup)
        with self.assertRaises(
            MarketplaceAuthenticatedLoopbackLaunchPlanError
        ) as caught:
            build_marketplace_authenticated_loopback_launch_plan(
                host=LOOPBACK_LAUNCH_HOST,
                port=8443,
                startup=corrupted,
            )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)

    def test_direct_plan_construction_cannot_substitute_asgi(self) -> None:
        startup, _application, _provisioning, _runtime_inputs = _compose()
        with self.assertRaises(MarketplaceAuthenticatedLoopbackLaunchPlanError):
            MarketplaceAuthenticatedLoopbackLaunchPlan(
                host=LOOPBACK_LAUNCH_HOST,
                port=8443,
                startup=startup,
                asgi=object(),  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
