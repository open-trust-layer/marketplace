from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from marketplace.application.auth_launch import MarketplaceAuthenticatedLoopbackLaunchPlan
from marketplace.application.launch import MarketplaceApplicationLaunchPlan
from marketplace.reference.auth_postgres_application_v1 import (
    PROFILE_NAME,
    build_reference_authenticated_postgres_marketplace_launch_plan,
)
from tests.test_m17_5o_auth_static_composition import AT_TIME
from tests.test_m17_5t_auth_startup_composition import _provisioning, _runtime_inputs

MODULE = "marketplace.reference.auth_postgres_application_v1"
HOST = "127.0.0.1"
PORT = 8443
INDEX_HTML = b"<html></html>"
APP_JS = b"console.log('marketplace')"
STYLES_CSS = b"body{display:block}"


class MarketplaceReferenceAuthenticatedPostgresApplicationTests(unittest.TestCase):
    def test_exact_existing_builders_receive_inputs_without_rewriting(self) -> None:
        connection_factory = Mock(name="connection_factory")
        clock = Mock(name="postgres_clock")
        provisioning = _provisioning()
        runtime_inputs = _runtime_inputs()
        application_plan = Mock(spec=MarketplaceApplicationLaunchPlan)
        authenticated_plan = Mock(spec=MarketplaceAuthenticatedLoopbackLaunchPlan)

        with (
            patch(
                f"{MODULE}.build_reference_postgres_marketplace_application_launch_plan",
                return_value=application_plan,
            ) as postgres_builder,
            patch(
                f"{MODULE}.build_reference_authenticated_marketplace_launch_plan",
                return_value=authenticated_plan,
            ) as auth_builder,
        ):
            result = build_reference_authenticated_postgres_marketplace_launch_plan(
                connection_factory=connection_factory,
                clock=clock,
                host=HOST,
                port=PORT,
                index_html=INDEX_HTML,
                app_js=APP_JS,
                styles_css=STYLES_CSS,
                provisioning=provisioning,
                runtime_inputs=runtime_inputs,
            )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATED_POSTGRES_APPLICATION_V1",
        )
        self.assertIs(result, authenticated_plan)
        postgres_builder.assert_called_once_with(
            connection_factory=connection_factory,
            clock=clock,
            host=HOST,
            port=PORT,
            index_html=INDEX_HTML,
            app_js=APP_JS,
            styles_css=STYLES_CSS,
        )
        auth_builder.assert_called_once_with(
            application_plan=application_plan,
            provisioning=provisioning,
            runtime_inputs=runtime_inputs,
        )
        connection_factory.assert_not_called()
        clock.assert_not_called()

    def test_real_composition_is_inert(self) -> None:
        connection_factory = Mock(side_effect=AssertionError("database connected"))
        clock = Mock(side_effect=AssertionError("PostgreSQL clock consumed"))
        provisioning = _provisioning()
        runtime_inputs = _runtime_inputs()
        auth_clock = Mock(return_value=AT_TIME * 1_000_000_000)

        with patch("marketplace.application.auth_runtime_inputs._time_ns", auth_clock):
            result = build_reference_authenticated_postgres_marketplace_launch_plan(
                connection_factory=connection_factory,
                clock=clock,
                host=HOST,
                port=PORT,
                index_html=INDEX_HTML,
                app_js=APP_JS,
                styles_css=STYLES_CSS,
                provisioning=provisioning,
                runtime_inputs=runtime_inputs,
            )

        self.assertIs(type(result), MarketplaceAuthenticatedLoopbackLaunchPlan)
        self.assertEqual(result.host, HOST)
        self.assertEqual(result.port, PORT)
        self.assertIs(result.startup.asgi.runtime_inputs, runtime_inputs)
        connection_factory.assert_not_called()
        clock.assert_not_called()
        auth_clock.assert_called_once_with()

    def test_postgres_builder_failure_stops_before_authentication_composition(self) -> None:
        connection_factory = Mock(name="connection_factory")
        clock = Mock(name="postgres_clock")
        provisioning = _provisioning()
        runtime_inputs = _runtime_inputs()
        failure = ValueError("postgres plan rejected")

        with (
            patch(
                f"{MODULE}.build_reference_postgres_marketplace_application_launch_plan",
                side_effect=failure,
            ) as postgres_builder,
            patch(
                f"{MODULE}.build_reference_authenticated_marketplace_launch_plan"
            ) as auth_builder,
        ):
            with self.assertRaisesRegex(ValueError, "postgres plan rejected"):
                build_reference_authenticated_postgres_marketplace_launch_plan(
                    connection_factory=connection_factory,
                    clock=clock,
                    host=HOST,
                    port=PORT,
                    index_html=INDEX_HTML,
                    app_js=APP_JS,
                    styles_css=STYLES_CSS,
                    provisioning=provisioning,
                    runtime_inputs=runtime_inputs,
                )

        postgres_builder.assert_called_once()
        auth_builder.assert_not_called()
        connection_factory.assert_not_called()
        clock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
