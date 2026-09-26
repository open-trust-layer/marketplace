from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tools import marketplace_localhost as localhost


class ProductAgreementAssentLocalhostPreflightTests(unittest.TestCase):
    def _graph(self, *, initialized: bool = False):
        store = Mock(name="store")
        coordination = SimpleNamespace(_store=store, _initialized=initialized)
        plan = SimpleNamespace(host=localhost.LOCALHOST_HOST, port=18446)
        launch = SimpleNamespace(
            services=SimpleNamespace(coordination=coordination),
            plan=plan,
        )
        return SimpleNamespace(store=store, launch=launch)

    def test_preflight_composes_exact_graph_without_initialization_or_server(self) -> None:
        application = Mock(name="application")
        authenticated_plan = Mock(name="authenticated_plan")
        graph = self._graph()
        provider = Mock(name="provider")

        with (
            patch.object(
                localhost,
                "_validate_authentication_provisioning_directory",
                return_value="/synthetic/provisioning",
            ),
            patch.object(
                localhost,
                "_load_authentication_provisioning",
                return_value=Mock(name="provisioning"),
            ),
            patch.object(
                localhost,
                "_compose_authentication_runtime_inputs",
                return_value=Mock(name="runtime_inputs"),
            ),
            patch.object(
                localhost,
                "_real_environment_getter",
                return_value=Mock(name="getenv"),
            ),
            patch.object(
                localhost,
                "_read_postgres_dsn",
                return_value="postgresql://synthetic",
            ),
            patch.object(
                localhost,
                "_real_asset_reader",
                return_value=Mock(name="asset_reader"),
            ),
            patch.object(
                localhost,
                "_load_web_assets",
                return_value=(b"index", b"app", b"styles"),
            ),
            patch.object(localhost, "_load_auth_web_modules", return_value=()),
            patch.object(
                localhost,
                "_build_psycopg_connection_factory",
                return_value=Mock(name="connection_factory"),
            ),
            patch.object(
                localhost,
                "_build_authenticated_postgres_plan",
                return_value=authenticated_plan,
            ),
            patch.object(
                localhost,
                "_validate_authenticated_plan_before_initialize",
                return_value=application,
            ) as validate_plan,
            patch.object(
                localhost,
                "_build_agreement_assent_postgres_graph",
                return_value=graph,
            ) as build_graph,
            patch.object(
                localhost,
                "_real_uvicorn_provider",
                return_value=provider,
            ) as uvicorn_provider,
            patch.object(
                localhost,
                "_initialize_agreement_assent_coordination",
            ) as initialize_agreement,
            patch.object(
                localhost,
                "_run_agreement_assent_foreground",
            ) as run_server,
        ):
            result = localhost._preflight_agreement_assent_authenticated_localhost(
                18446,
                "/synthetic/provisioning",
            )

        self.assertIs(result, graph)
        validate_plan.assert_called_once_with(authenticated_plan)
        self.assertEqual(build_graph.call_count, 1)
        application.initialize.assert_not_called()
        initialize_agreement.assert_not_called()
        uvicorn_provider.assert_not_called()
        run_server.assert_not_called()

    def test_preflight_rejects_already_initialized_coordination(self) -> None:
        graph = self._graph(initialized=True)
        with (
            patch.object(
                localhost,
                "_validate_authentication_provisioning_directory",
                return_value="/synthetic/provisioning",
            ),
            patch.object(localhost, "_load_authentication_provisioning", return_value=Mock()),
            patch.object(localhost, "_compose_authentication_runtime_inputs", return_value=Mock()),
            patch.object(localhost, "_real_environment_getter", return_value=Mock()),
            patch.object(localhost, "_read_postgres_dsn", return_value="postgresql://synthetic"),
            patch.object(localhost, "_real_asset_reader", return_value=Mock()),
            patch.object(localhost, "_load_web_assets", return_value=(b"index", b"app", b"styles")),
            patch.object(localhost, "_load_auth_web_modules", return_value=()),
            patch.object(localhost, "_build_psycopg_connection_factory", return_value=Mock()),
            patch.object(localhost, "_build_authenticated_postgres_plan", return_value=Mock()),
            patch.object(localhost, "_validate_authenticated_plan_before_initialize", return_value=Mock()),
            patch.object(localhost, "_build_agreement_assent_postgres_graph", return_value=graph),
        ):
            with self.assertRaises(localhost.MarketplaceLocalhostBootstrapError) as caught:
                localhost._preflight_agreement_assent_authenticated_localhost(
                    18446,
                    "/synthetic/provisioning",
                )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_LOCALHOST_PREFLIGHT_FAILED",
        )

    def test_preflight_mode_is_mutually_exclusive_with_execution(self) -> None:
        parser = localhost._parser()
        args = parser.parse_args(
            [
                "--port",
                "18446",
                "--preflight-agreement-assent-localhost",
                "--authentication-provisioning-directory",
                "/synthetic/provisioning",
            ]
        )
        self.assertTrue(args.preflight_agreement_assent_localhost)
        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "--port",
                    "18446",
                    "--preflight-agreement-assent-localhost",
                    "--execute-agreement-assent-localhost",
                    localhost.AGREEMENT_ASSENT_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                ]
            )


if __name__ == "__main__":
    unittest.main()
