from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tools import marketplace_localhost as localhost


class ProductAgreementAssentLocalhostLifecycleTests(unittest.TestCase):
    def test_exact_lifecycle_orders_both_initializations_before_server(self) -> None:
        events: list[str] = []
        application = Mock(name="application")
        application.initialize.side_effect = lambda: events.append("application")
        authenticated_plan = Mock(name="authenticated_plan")
        graph = SimpleNamespace(launch=SimpleNamespace(plan=Mock(name="agreement_plan")))
        provider = Mock(name="provider")

        replacements = {
            "_validate_authentication_provisioning_directory": Mock(
                return_value="/synthetic/provisioning"
            ),
            "_load_authentication_provisioning": Mock(return_value=Mock()),
            "_compose_authentication_runtime_inputs": Mock(return_value=Mock()),
            "_real_environment_getter": Mock(return_value=Mock()),
            "_read_postgres_dsn": Mock(return_value="synthetic-dsn"),
            "_real_asset_reader": Mock(return_value=Mock()),
            "_load_web_assets": Mock(return_value=(b"index", b"app", b"styles")),
            "_load_auth_web_modules": Mock(return_value=()),
            "_build_psycopg_connection_factory": Mock(return_value=Mock()),
            "_build_authenticated_postgres_plan": Mock(return_value=authenticated_plan),
            "_validate_authenticated_plan_before_initialize": Mock(
                return_value=application
            ),
            "_build_agreement_assent_postgres_graph": Mock(return_value=graph),
            "_real_uvicorn_provider": Mock(return_value=provider),
            "_initialize_agreement_assent_coordination": Mock(
                side_effect=lambda value: events.append("agreement")
            ),
            "_run_agreement_assent_foreground": Mock(
                side_effect=lambda value, provider: events.append("server")
            ),
        }

        with patch.multiple(localhost, **replacements):
            localhost._execute_agreement_assent_authenticated_localhost(
                18446,
                localhost.AGREEMENT_ASSENT_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                "/synthetic/provisioning",
            )

        self.assertEqual(events, ["application", "agreement", "server"])
        replacements["_initialize_agreement_assent_coordination"].assert_called_once_with(
            graph
        )
        replacements["_run_agreement_assent_foreground"].assert_called_once_with(
            graph,
            provider=provider,
        )

    def test_base_initialization_failure_blocks_agreement_and_server(self) -> None:
        application = Mock(name="application")
        application.initialize.side_effect = RuntimeError("provider detail")
        authenticated_plan = Mock(name="authenticated_plan")
        graph = SimpleNamespace(launch=SimpleNamespace(plan=Mock(name="agreement_plan")))

        initialize_agreement = Mock(name="initialize_agreement")
        run_server = Mock(name="run_server")
        replacements = {
            "_validate_authentication_provisioning_directory": Mock(
                return_value="/synthetic/provisioning"
            ),
            "_load_authentication_provisioning": Mock(return_value=Mock()),
            "_compose_authentication_runtime_inputs": Mock(return_value=Mock()),
            "_real_environment_getter": Mock(return_value=Mock()),
            "_read_postgres_dsn": Mock(return_value="synthetic-dsn"),
            "_real_asset_reader": Mock(return_value=Mock()),
            "_load_web_assets": Mock(return_value=(b"index", b"app", b"styles")),
            "_load_auth_web_modules": Mock(return_value=()),
            "_build_psycopg_connection_factory": Mock(return_value=Mock()),
            "_build_authenticated_postgres_plan": Mock(return_value=authenticated_plan),
            "_validate_authenticated_plan_before_initialize": Mock(
                return_value=application
            ),
            "_build_agreement_assent_postgres_graph": Mock(return_value=graph),
            "_real_uvicorn_provider": Mock(return_value=Mock()),
            "_initialize_agreement_assent_coordination": initialize_agreement,
            "_run_agreement_assent_foreground": run_server,
        }

        with patch.multiple(localhost, **replacements):
            with self.assertRaises(localhost.MarketplaceLocalhostBootstrapError) as caught:
                localhost._execute_agreement_assent_authenticated_localhost(
                    18446,
                    localhost.AGREEMENT_ASSENT_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                    "/synthetic/provisioning",
                )

        self.assertEqual(
            caught.exception.code,
            "M17_5Y_DATABASE_INITIALIZATION_FAILED",
        )
        self.assertNotIn("provider detail", str(caught.exception))
        initialize_agreement.assert_not_called()
        run_server.assert_not_called()

    def test_agreement_initialization_failure_blocks_server(self) -> None:
        application = Mock(name="application")
        authenticated_plan = Mock(name="authenticated_plan")
        graph = SimpleNamespace(launch=SimpleNamespace(plan=Mock(name="agreement_plan")))

        run_server = Mock(name="run_server")
        replacements = {
            "_validate_authentication_provisioning_directory": Mock(
                return_value="/synthetic/provisioning"
            ),
            "_load_authentication_provisioning": Mock(return_value=Mock()),
            "_compose_authentication_runtime_inputs": Mock(return_value=Mock()),
            "_real_environment_getter": Mock(return_value=Mock()),
            "_read_postgres_dsn": Mock(return_value="synthetic-dsn"),
            "_real_asset_reader": Mock(return_value=Mock()),
            "_load_web_assets": Mock(return_value=(b"index", b"app", b"styles")),
            "_load_auth_web_modules": Mock(return_value=()),
            "_build_psycopg_connection_factory": Mock(return_value=Mock()),
            "_build_authenticated_postgres_plan": Mock(return_value=authenticated_plan),
            "_validate_authenticated_plan_before_initialize": Mock(
                return_value=application
            ),
            "_build_agreement_assent_postgres_graph": Mock(return_value=graph),
            "_real_uvicorn_provider": Mock(return_value=Mock()),
            "_initialize_agreement_assent_coordination": Mock(
                side_effect=localhost.MarketplaceLocalhostBootstrapError(
                    "AGREEMENT_ASSENT_DATABASE_INITIALIZATION_FAILED"
                )
            ),
            "_run_agreement_assent_foreground": run_server,
        }

        with patch.multiple(localhost, **replacements):
            with self.assertRaises(localhost.MarketplaceLocalhostBootstrapError) as caught:
                localhost._execute_agreement_assent_authenticated_localhost(
                    18446,
                    localhost.AGREEMENT_ASSENT_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                    "/synthetic/provisioning",
                )

        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_DATABASE_INITIALIZATION_FAILED",
        )
        run_server.assert_not_called()


if __name__ == "__main__":
    unittest.main()
