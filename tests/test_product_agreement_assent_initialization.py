from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import Mock, patch

from marketplace.application.agreement_assent_coordination import (
    AgreementAssentExpiryResult,
    MarketplaceAgreementAssentCoordinationService,
)
from marketplace.application.auth_launch import (
    build_marketplace_authenticated_loopback_launch_plan,
)
from marketplace.application.launch import LOOPBACK_LAUNCH_HOST
from marketplace.reference.agreement_assent_initialization_v1 import (
    INITIALIZE_ONE_AGREEMENT_ASSENT_COORDINATION,
    PROFILE_NAME,
    MarketplaceReferenceAgreementAssentInitializationError,
    initialize_reference_agreement_assent_coordination,
)
from marketplace.reference.agreement_assent_postgres_v1 import (
    build_reference_agreement_assent_postgres,
)
from tests.test_m17_5t_auth_startup_composition import _compose


PORT = 18445


def _graph():
    startup, _application, _provisioning, _runtime_inputs = _compose()
    authenticated = build_marketplace_authenticated_loopback_launch_plan(
        host=LOOPBACK_LAUNCH_HOST,
        port=PORT,
        startup=startup,
    )
    return build_reference_agreement_assent_postgres(
        authenticated_plan=authenticated,
        connection_factory=Mock(name="connection_factory"),
        clock=Mock(
            name="clock",
            return_value=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    )


class ProductAgreementAssentInitializationTests(unittest.TestCase):
    def test_profile_exact_token_and_single_initialization(self) -> None:
        graph = _graph()
        coordination = graph.launch.services.coordination
        calls = 0

        def initialize(self):
            nonlocal calls
            calls += 1
            self._initialized = True
            return AgreementAssentExpiryResult(())

        with patch.object(
            MarketplaceAgreementAssentCoordinationService,
            "initialize",
            initialize,
        ):
            result = initialize_reference_agreement_assent_coordination(
                graph=graph,
                execute_token=INITIALIZE_ONE_AGREEMENT_ASSENT_COORDINATION,
            )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AGREEMENT_ASSENT_COORDINATION_INITIALIZATION_V1",
        )
        self.assertIs(type(result), AgreementAssentExpiryResult)
        self.assertEqual(result.expired_keys, ())
        self.assertEqual(calls, 1)
        self.assertTrue(coordination._initialized)

    def test_wrong_token_fails_before_initialization(self) -> None:
        graph = _graph()
        with patch.object(
            MarketplaceAgreementAssentCoordinationService,
            "initialize",
        ) as initialize:
            for token in ("", "INITIALIZE_COORDINATION", object()):
                with self.subTest(token=type(token).__name__):
                    with self.assertRaises(
                        MarketplaceReferenceAgreementAssentInitializationError
                    ):
                        initialize_reference_agreement_assent_coordination(
                            graph=graph,
                            execute_token=token,  # type: ignore[arg-type]
                        )
            initialize.assert_not_called()

    def test_already_initialized_graph_fails_before_second_call(self) -> None:
        graph = _graph()
        coordination = graph.launch.services.coordination
        coordination._initialized = True

        with patch.object(
            MarketplaceAgreementAssentCoordinationService,
            "initialize",
        ) as initialize:
            with self.assertRaises(
                MarketplaceReferenceAgreementAssentInitializationError
            ):
                initialize_reference_agreement_assent_coordination(
                    graph=graph,
                    execute_token=INITIALIZE_ONE_AGREEMENT_ASSENT_COORDINATION,
                )
        initialize.assert_not_called()

    def test_underlying_failure_is_nonreflective_and_not_retried(self) -> None:
        graph = _graph()
        secret = "SECRET-POSTGRES-DETAIL"
        with patch.object(
            MarketplaceAgreementAssentCoordinationService,
            "initialize",
            side_effect=RuntimeError(secret),
        ) as initialize:
            with self.assertRaises(
                MarketplaceReferenceAgreementAssentInitializationError
            ) as caught:
                initialize_reference_agreement_assent_coordination(
                    graph=graph,
                    execute_token=INITIALIZE_ONE_AGREEMENT_ASSENT_COORDINATION,
                )
        self.assertEqual(initialize.call_count, 1)
        self.assertNotIn(secret, str(caught.exception))
        self.assertFalse(graph.launch.services.coordination._initialized)

    def test_invalid_graph_fails_before_any_initialization(self) -> None:
        with patch.object(
            MarketplaceAgreementAssentCoordinationService,
            "initialize",
        ) as initialize:
            with self.assertRaises(
                MarketplaceReferenceAgreementAssentInitializationError
            ):
                initialize_reference_agreement_assent_coordination(
                    graph=object(),  # type: ignore[arg-type]
                    execute_token=INITIALIZE_ONE_AGREEMENT_ASSENT_COORDINATION,
                )
        initialize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
