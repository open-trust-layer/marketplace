from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import patch

from marketplace.application.agreement_assent_launch import (
    PROFILE_NAME,
    MarketplaceAgreementAssentLoopbackLaunchPlan,
    MarketplaceAgreementAssentLoopbackLaunchPlanError,
    build_marketplace_agreement_assent_loopback_launch_plan,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from marketplace.application.launch import (
    LOOPBACK_LAUNCH_HOST,
    MAX_LAUNCH_PORT,
    MIN_LAUNCH_PORT,
)
from tests.test_product_agreement_assent_startup_composition import _compose


class _StringSubclass(str):
    pass


class _IntegerSubclass(int):
    pass


class ProductAgreementAssentLoopbackLaunchTests(unittest.TestCase):
    def test_profile_exact_identity_and_frozen_plan(self) -> None:
        startup, authenticated_startup, _runtime_inputs = _compose()
        result = build_marketplace_agreement_assent_loopback_launch_plan(
            host=LOOPBACK_LAUNCH_HOST,
            port=8443,
            startup=startup,
        )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_AGREEMENT_ASSENT_LOOPBACK_LAUNCH_PLAN_V1",
        )
        self.assertIs(type(result), MarketplaceAgreementAssentLoopbackLaunchPlan)
        self.assertEqual(result.host, LOOPBACK_LAUNCH_HOST)
        self.assertEqual(result.port, 8443)
        self.assertIs(result.startup, startup)
        self.assertIs(result.asgi, startup.agreement_asgi.asgi)
        self.assertIs(
            result.asgi._marketplace_http,
            startup.agreement_http.assent_http,
        )
        self.assertIs(
            result.asgi._auth_http,
            authenticated_startup.http.session_http,
        )
        with self.assertRaises(FrozenInstanceError):
            result.port = 8444  # type: ignore[misc,assignment]

    def test_exact_existing_port_bounds_are_accepted(self) -> None:
        startup, _authenticated_startup, _runtime_inputs = _compose()
        for port in (MIN_LAUNCH_PORT, MAX_LAUNCH_PORT):
            with self.subTest(port=port):
                result = build_marketplace_agreement_assent_loopback_launch_plan(
                    host=LOOPBACK_LAUNCH_HOST,
                    port=port,
                    startup=startup,
                )
                self.assertEqual(result.port, port)

    def test_host_port_and_startup_are_exact(self) -> None:
        startup, _authenticated_startup, _runtime_inputs = _compose()
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
                    MarketplaceAgreementAssentLoopbackLaunchPlanError
                ):
                    build_marketplace_agreement_assent_loopback_launch_plan(
                        **kwargs  # type: ignore[arg-type]
                    )

    def test_plan_creation_consumes_no_runtime_or_request_authority(self) -> None:
        startup, _authenticated_startup, _runtime_inputs = _compose()
        with (
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                side_effect=AssertionError("clock consumed"),
            ) as clock,
            patch(
                "marketplace.application.auth_material._token_bytes",
                side_effect=AssertionError("material consumed"),
            ) as material,
            patch.object(
                MarketplaceSessionEstablishmentAsgiHttpAdapter,
                "__call__",
                side_effect=AssertionError("request handled"),
            ) as request,
            patch("socket.socket", side_effect=AssertionError("socket used")) as socket,
        ):
            result = build_marketplace_agreement_assent_loopback_launch_plan(
                host=LOOPBACK_LAUNCH_HOST,
                port=8443,
                startup=startup,
            )

        self.assertIs(result.asgi, startup.agreement_asgi.asgi)
        clock.assert_not_called()
        material.assert_not_called()
        request.assert_not_called()
        socket.assert_not_called()

    def test_direct_plan_construction_cannot_substitute_asgi(self) -> None:
        startup, _authenticated_startup, _runtime_inputs = _compose()
        with self.assertRaises(MarketplaceAgreementAssentLoopbackLaunchPlanError):
            MarketplaceAgreementAssentLoopbackLaunchPlan(
                host=LOOPBACK_LAUNCH_HOST,
                port=8443,
                startup=startup,
                asgi=object(),  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
