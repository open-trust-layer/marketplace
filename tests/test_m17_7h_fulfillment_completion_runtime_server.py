from __future__ import annotations

import unittest

from marketplace.application.agreement_assent_startup_composition import (
    MarketplaceAgreementAssentStartupComposition,
)
from marketplace.application.auth_http_composition import (
    MarketplaceAuthenticatedHttpComposition,
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
from marketplace.application.composition import MarketplaceApplicationComposition
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
    MarketplaceFulfillmentCompletionLoopbackLaunchPlan,
)
from marketplace.application.fulfillment_completion_runtime_server import (
    EXECUTE_ONE_FULFILLMENT_COMPLETION_MARKETPLACE_LOOPBACK_SERVER,
    PROFILE_NAME,
    MarketplaceFulfillmentCompletionLocalRuntimeError,
    run_marketplace_fulfillment_completion_foreground,
)
from marketplace.application.fulfillment_completion_startup_composition import (
    MarketplaceFulfillmentCompletionStartupComposition,
)
from marketplace.application.launch import LOOPBACK_LAUNCH_HOST


class Provider:
    def __init__(self) -> None:
        self.calls = []

    def run(self, *, application, host, port) -> None:
        self.calls.append((application, host, port))


def _plan():
    site = object()
    application = object.__new__(MarketplaceApplicationComposition)
    object.__setattr__(application, "site", site)

    session_http = object.__new__(MarketplaceAuthenticationSessionHttpAdapter)
    authenticated_http = object.__new__(MarketplaceAuthenticatedHttpComposition)
    object.__setattr__(authenticated_http, "application", application)
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
    object.__setattr__(asgi, "_site", site)
    object.__setattr__(asgi, "_marketplace_http", fulfillment_adapter)
    object.__setattr__(asgi, "_auth_http", session_http)

    fulfillment_asgi = object.__new__(
        MarketplaceFulfillmentCompletionAsgiComposition
    )
    object.__setattr__(fulfillment_asgi, "asgi", asgi)

    startup = object.__new__(MarketplaceFulfillmentCompletionStartupComposition)
    object.__setattr__(startup, "agreement_startup", agreement_startup)
    object.__setattr__(startup, "fulfillment_http", fulfillment_http)
    object.__setattr__(startup, "fulfillment_asgi", fulfillment_asgi)

    plan = object.__new__(MarketplaceFulfillmentCompletionLoopbackLaunchPlan)
    object.__setattr__(plan, "host", LOOPBACK_LAUNCH_HOST)
    object.__setattr__(plan, "port", 18080)
    object.__setattr__(plan, "startup", startup)
    object.__setattr__(plan, "asgi", asgi)
    return plan, asgi


class M177HFulfillmentCompletionRuntimeServerTests(unittest.TestCase):
    def test_profile_and_exact_execution_delegate_once(self) -> None:
        plan, asgi = _plan()
        provider = Provider()

        run_marketplace_fulfillment_completion_foreground(
            plan=plan,
            provider=provider,
            execute_token=(
                EXECUTE_ONE_FULFILLMENT_COMPLETION_MARKETPLACE_LOOPBACK_SERVER
            ),
        )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_FULFILLMENT_COMPLETION_FOREGROUND_RUNTIME_V1",
        )
        self.assertEqual(
            provider.calls,
            [(asgi, LOOPBACK_LAUNCH_HOST, 18080)],
        )

    def test_wrong_execution_token_fails_before_provider(self) -> None:
        plan, _ = _plan()
        provider = Provider()

        with self.assertRaises(
            MarketplaceFulfillmentCompletionLocalRuntimeError
        ):
            run_marketplace_fulfillment_completion_foreground(
                plan=plan,
                provider=provider,
                execute_token="execute",
            )
        self.assertEqual(provider.calls, [])

    def test_non_loopback_or_tampered_http_binding_fails_before_provider(self) -> None:
        for mutation in ("host", "marketplace_http"):
            with self.subTest(mutation=mutation):
                plan, _ = _plan()
                provider = Provider()
                if mutation == "host":
                    object.__setattr__(plan, "host", "0.0.0.0")
                else:
                    object.__setattr__(plan.asgi, "_marketplace_http", object())

                with self.assertRaises(
                    MarketplaceFulfillmentCompletionLocalRuntimeError
                ):
                    run_marketplace_fulfillment_completion_foreground(
                        plan=plan,
                        provider=provider,
                        execute_token=(
                            EXECUTE_ONE_FULFILLMENT_COMPLETION_MARKETPLACE_LOOPBACK_SERVER
                        ),
                    )
                self.assertEqual(provider.calls, [])


if __name__ == "__main__":
    unittest.main()
