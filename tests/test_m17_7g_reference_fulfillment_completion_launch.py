from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.agreement_assent_launch import (
    MarketplaceAgreementAssentLoopbackLaunchPlan,
)
from marketplace.application.agreement_assent_startup_composition import (
    MarketplaceAgreementAssentStartupComposition,
)
from marketplace.application.agreement_publication_http_composition import (
    MarketplaceAgreementPublicationHttpComposition,
)
from marketplace.application.auth_runtime_inputs import (
    MarketplaceAuthenticationRuntimeInputs,
)
from marketplace.application.composition import MarketplaceApplicationComposition
from marketplace.application.fulfillment_completion_asgi_composition import (
    MarketplaceFulfillmentCompletionAsgiComposition,
)
from marketplace.application.fulfillment_completion_http_composition import (
    MarketplaceFulfillmentCompletionHttpComposition,
)
from marketplace.application.fulfillment_completion_launch import (
    MarketplaceFulfillmentCompletionLoopbackLaunchPlan,
)
from marketplace.application.fulfillment_completion_startup_composition import (
    MarketplaceFulfillmentCompletionStartupComposition,
)
from marketplace.application.state import MarketplaceApplicationStateService
from marketplace.reference.agreement_assent_application_v1 import (
    MarketplaceReferenceAgreementAssentServices,
)
from marketplace.reference.agreement_assent_launch_v1 import (
    MarketplaceReferenceAgreementAssentLaunch,
)
from marketplace.reference.agreement_assent_postgres_v1 import (
    MarketplaceReferenceAgreementAssentPostgres,
)
from marketplace.reference.fulfillment_completion_evidence_v1 import (
    build_claimed_complete_performance_event,
    build_commitment_acceptance_event,
    build_commitment_completion_event,
    fulfillment_event_target,
)
from marketplace.reference.fulfillment_completion_launch_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceFulfillmentCompletionLaunch,
    MarketplaceReferenceFulfillmentCompletionLaunchError,
    build_reference_fulfillment_completion_launch,
)


def _agreement_graph():
    state = object.__new__(MarketplaceApplicationStateService)
    application = object.__new__(MarketplaceApplicationComposition)
    object.__setattr__(application, "state", state)

    services = object.__new__(MarketplaceReferenceAgreementAssentServices)
    object.__setattr__(services, "application", application)

    runtime_inputs = object.__new__(MarketplaceAuthenticationRuntimeInputs)
    agreement_startup = object.__new__(MarketplaceAgreementAssentStartupComposition)
    object.__setattr__(agreement_startup, "runtime_inputs", runtime_inputs)

    agreement_plan = object.__new__(MarketplaceAgreementAssentLoopbackLaunchPlan)
    object.__setattr__(agreement_plan, "host", "127.0.0.1")
    object.__setattr__(agreement_plan, "port", 18080)

    launch = object.__new__(MarketplaceReferenceAgreementAssentLaunch)
    object.__setattr__(launch, "services", services)
    object.__setattr__(launch, "startup", agreement_startup)
    object.__setattr__(launch, "plan", agreement_plan)

    graph = object.__new__(MarketplaceReferenceAgreementAssentPostgres)
    object.__setattr__(graph, "launch", launch)
    return graph, state, agreement_startup, runtime_inputs, agreement_plan


def _nested_result(graph, preflight, agreement_publication, fulfillment_publication):
    agreement_http = object.__new__(MarketplaceAgreementPublicationHttpComposition)
    object.__setattr__(agreement_http, "preflight", preflight)
    object.__setattr__(agreement_http, "publication", agreement_publication)

    fulfillment_http = object.__new__(MarketplaceFulfillmentCompletionHttpComposition)
    object.__setattr__(
        fulfillment_http,
        "fulfillment_publication",
        fulfillment_publication,
    )

    marker_asgi = object()
    fulfillment_asgi = object.__new__(MarketplaceFulfillmentCompletionAsgiComposition)
    object.__setattr__(fulfillment_asgi, "asgi", marker_asgi)

    startup = object.__new__(MarketplaceFulfillmentCompletionStartupComposition)
    object.__setattr__(startup, "agreement_startup", graph.launch.startup)
    object.__setattr__(startup, "runtime_inputs", graph.launch.startup.runtime_inputs)
    object.__setattr__(startup, "agreement_publication_http", agreement_http)
    object.__setattr__(startup, "fulfillment_http", fulfillment_http)
    object.__setattr__(startup, "fulfillment_asgi", fulfillment_asgi)

    plan = object.__new__(MarketplaceFulfillmentCompletionLoopbackLaunchPlan)
    object.__setattr__(plan, "host", graph.launch.plan.host)
    object.__setattr__(plan, "port", graph.launch.plan.port)
    object.__setattr__(plan, "startup", startup)
    object.__setattr__(plan, "asgi", marker_asgi)
    return startup, plan


class M177GReferenceFulfillmentCompletionLaunchTests(unittest.TestCase):
    def test_profile_is_exact(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_FULFILLMENT_COMPLETION_LAUNCH_V1",
        )

    def test_reference_builder_reuses_exact_state_and_reference_evidence(self) -> None:
        graph, state, agreement_startup, runtime_inputs, agreement_plan = (
            _agreement_graph()
        )
        captured = {}

        def compose_startup(**kwargs):
            captured["startup_kwargs"] = kwargs
            startup, plan = _nested_result(
                graph,
                kwargs["agreement_publication_preflight"],
                kwargs["agreement_publication"],
                kwargs["fulfillment_publication"],
            )
            captured["plan"] = plan
            return startup

        def build_plan(**kwargs):
            captured["plan_kwargs"] = kwargs
            return captured["plan"]

        with (
            patch(
                "marketplace.reference.fulfillment_completion_launch_v1."
                "compose_marketplace_fulfillment_completion_startup",
                side_effect=compose_startup,
            ),
            patch(
                "marketplace.reference.fulfillment_completion_launch_v1."
                "build_marketplace_fulfillment_completion_loopback_launch_plan",
                side_effect=build_plan,
            ),
        ):
            result = build_reference_fulfillment_completion_launch(
                agreement_graph=graph
            )

        self.assertIs(
            type(result),
            MarketplaceReferenceFulfillmentCompletionLaunch,
        )
        self.assertIs(result.agreement_graph, graph)
        self.assertIs(result.agreement_publication._state, state)
        self.assertIs(result.fulfillment_publication._state, state)
        self.assertIs(
            result.fulfillment_publication._build_claimed_complete_performance,
            build_claimed_complete_performance_event,
        )
        self.assertIs(
            result.fulfillment_publication._build_commitment_acceptance,
            build_commitment_acceptance_event,
        )
        self.assertIs(
            result.fulfillment_publication._build_commitment_completion,
            build_commitment_completion_event,
        )
        self.assertIs(
            result.fulfillment_publication._event_target,
            fulfillment_event_target,
        )
        self.assertIs(
            captured["startup_kwargs"]["agreement_startup"],
            agreement_startup,
        )
        self.assertIs(captured["startup_kwargs"]["runtime_inputs"], runtime_inputs)
        self.assertEqual(captured["plan_kwargs"]["host"], agreement_plan.host)
        self.assertEqual(captured["plan_kwargs"]["port"], agreement_plan.port)
        self.assertIs(captured["plan_kwargs"]["startup"], result.startup)

    def test_wrong_graph_type_fails_before_composition(self) -> None:
        with patch(
            "marketplace.reference.fulfillment_completion_launch_v1."
            "compose_marketplace_fulfillment_completion_startup"
        ) as compose:
            with self.assertRaises(
                MarketplaceReferenceFulfillmentCompletionLaunchError
            ):
                build_reference_fulfillment_completion_launch(
                    agreement_graph=object(),  # type: ignore[arg-type]
                )
        compose.assert_not_called()


if __name__ == "__main__":
    unittest.main()
