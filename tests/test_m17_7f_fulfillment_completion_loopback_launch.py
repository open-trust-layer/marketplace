from __future__ import annotations

import unittest

from marketplace.application.agreement_assent_startup_composition import (
    MarketplaceAgreementAssentStartupComposition,
)
from marketplace.application.auth_http_composition import (
    MarketplaceAuthenticatedHttpComposition,
)
from marketplace.application.auth_runtime_inputs import (
    MarketplaceAuthenticationRuntimeInputs,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from marketplace.application.auth_session_http import (
    MarketplaceAuthenticationSessionHttpAdapter,
)
from marketplace.application.auth_startup_composition import (
    MarketplaceAuthenticatedStartupComposition,
)
from marketplace.application.fulfillment_completion_asgi_composition import (
    MarketplaceFulfillmentCompletionAsgiComposition,
)
from marketplace.application.fulfillment_completion_http import (
    MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter,
)
from marketplace.application.fulfillment_completion_http_composition import (
    MarketplaceFulfillmentCompletionHttpComposition,
)
from marketplace.application.fulfillment_completion_launch import (
    PROFILE_NAME,
    MarketplaceFulfillmentCompletionLoopbackLaunchPlan,
    MarketplaceFulfillmentCompletionLoopbackLaunchPlanError,
    build_marketplace_fulfillment_completion_loopback_launch_plan,
)
from marketplace.application.fulfillment_completion_startup_composition import (
    MarketplaceFulfillmentCompletionStartupComposition,
)
from marketplace.application.launch import (
    LOOPBACK_LAUNCH_HOST,
    MAX_LAUNCH_PORT,
    MIN_LAUNCH_PORT,
)


def _startup():
    runtime_inputs = object.__new__(MarketplaceAuthenticationRuntimeInputs)

    session_http = object.__new__(MarketplaceAuthenticationSessionHttpAdapter)
    authenticated_http = object.__new__(MarketplaceAuthenticatedHttpComposition)
    object.__setattr__(authenticated_http, "session_http", session_http)

    authenticated_startup = object.__new__(MarketplaceAuthenticatedStartupComposition)
    object.__setattr__(authenticated_startup, "http", authenticated_http)

    agreement_startup = object.__new__(MarketplaceAgreementAssentStartupComposition)
    object.__setattr__(agreement_startup, "authenticated_startup", authenticated_startup)

    fulfillment_adapter = object.__new__(
        MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter
    )
    fulfillment_http = object.__new__(
        MarketplaceFulfillmentCompletionHttpComposition
    )
    object.__setattr__(fulfillment_http, "fulfillment_http", fulfillment_adapter)

    asgi = object.__new__(MarketplaceSessionEstablishmentAsgiHttpAdapter)
    object.__setattr__(asgi, "_marketplace_http", fulfillment_adapter)
    object.__setattr__(asgi, "_auth_http", session_http)

    fulfillment_asgi = object.__new__(
        MarketplaceFulfillmentCompletionAsgiComposition
    )
    object.__setattr__(fulfillment_asgi, "fulfillment_http", fulfillment_http)
    object.__setattr__(fulfillment_asgi, "runtime_inputs", runtime_inputs)
    object.__setattr__(fulfillment_asgi, "asgi", asgi)

    startup = object.__new__(MarketplaceFulfillmentCompletionStartupComposition)
    object.__setattr__(startup, "agreement_startup", agreement_startup)
    object.__setattr__(startup, "runtime_inputs", runtime_inputs)
    object.__setattr__(startup, "fulfillment_http", fulfillment_http)
    object.__setattr__(startup, "fulfillment_asgi", fulfillment_asgi)
    return startup, asgi


class M177FFulfillmentCompletionLoopbackLaunchTests(unittest.TestCase):
    def test_profile_and_exact_loopback_plan(self) -> None:
        startup, asgi = _startup()
        plan = build_marketplace_fulfillment_completion_loopback_launch_plan(
            host=LOOPBACK_LAUNCH_HOST,
            port=MIN_LAUNCH_PORT,
            startup=startup,
        )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_FULFILLMENT_COMPLETION_LOOPBACK_LAUNCH_PLAN_V1",
        )
        self.assertIs(type(plan), MarketplaceFulfillmentCompletionLoopbackLaunchPlan)
        self.assertEqual(plan.host, LOOPBACK_LAUNCH_HOST)
        self.assertEqual(plan.port, MIN_LAUNCH_PORT)
        self.assertIs(plan.startup, startup)
        self.assertIs(plan.asgi, asgi)

    def test_non_loopback_host_and_invalid_ports_fail_closed(self) -> None:
        startup, _ = _startup()
        cases = (
            ("0.0.0.0", MIN_LAUNCH_PORT),
            ("localhost", MIN_LAUNCH_PORT),
            (LOOPBACK_LAUNCH_HOST, MIN_LAUNCH_PORT - 1),
            (LOOPBACK_LAUNCH_HOST, MAX_LAUNCH_PORT + 1),
            (LOOPBACK_LAUNCH_HOST, True),
        )
        for host, port in cases:
            with self.subTest(host=host, port=port):
                with self.assertRaises(
                    MarketplaceFulfillmentCompletionLoopbackLaunchPlanError
                ):
                    build_marketplace_fulfillment_completion_loopback_launch_plan(
                        host=host,
                        port=port,  # type: ignore[arg-type]
                        startup=startup,
                    )

    def test_wrong_startup_type_fails_closed(self) -> None:
        with self.assertRaises(
            MarketplaceFulfillmentCompletionLoopbackLaunchPlanError
        ):
            build_marketplace_fulfillment_completion_loopback_launch_plan(
                host=LOOPBACK_LAUNCH_HOST,
                port=MIN_LAUNCH_PORT,
                startup=object(),  # type: ignore[arg-type]
            )

    def test_tampered_asgi_binding_fails_closed(self) -> None:
        startup, _ = _startup()
        object.__setattr__(
            startup.fulfillment_asgi.asgi,
            "_marketplace_http",
            object(),
        )
        with self.assertRaises(
            MarketplaceFulfillmentCompletionLoopbackLaunchPlanError
        ):
            build_marketplace_fulfillment_completion_loopback_launch_plan(
                host=LOOPBACK_LAUNCH_HOST,
                port=MIN_LAUNCH_PORT,
                startup=startup,
            )


if __name__ == "__main__":
    unittest.main()
