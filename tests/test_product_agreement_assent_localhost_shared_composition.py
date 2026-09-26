from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tools import marketplace_localhost as localhost


class ProductAgreementAssentLocalhostSharedCompositionTests(unittest.TestCase):
    def test_preflight_and_execution_delegate_to_same_composition_helper(self) -> None:
        application = Mock(name="application")
        graph = SimpleNamespace(launch=SimpleNamespace(plan=Mock(name="plan")))
        compose = Mock(return_value=(application, graph))
        provider = Mock(name="provider")

        with (
            patch.object(
                localhost,
                "_compose_agreement_assent_authenticated_localhost",
                compose,
            ),
            patch.object(
                localhost,
                "_real_uvicorn_provider",
                return_value=provider,
            ),
            patch.object(
                localhost,
                "_initialize_agreement_assent_coordination",
            ) as initialize_agreement,
            patch.object(
                localhost,
                "_run_agreement_assent_foreground",
            ) as run_server,
        ):
            preflight_graph = (
                localhost._preflight_agreement_assent_authenticated_localhost(
                    18446,
                    "/synthetic/provisioning",
                )
            )
            localhost._execute_agreement_assent_authenticated_localhost(
                18446,
                localhost.AGREEMENT_ASSENT_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                "/synthetic/provisioning",
            )

        self.assertIs(preflight_graph, graph)
        self.assertEqual(
            compose.call_args_list[0].args,
            (18446, "/synthetic/provisioning"),
        )
        self.assertEqual(
            compose.call_args_list[1].args,
            (18446, "/synthetic/provisioning"),
        )
        application.initialize.assert_called_once_with()
        initialize_agreement.assert_called_once_with(graph)
        run_server.assert_called_once_with(graph, provider=provider)

    def test_wrong_execution_token_blocks_shared_composition(self) -> None:
        compose = Mock(name="compose")
        with patch.object(
            localhost,
            "_compose_agreement_assent_authenticated_localhost",
            compose,
        ):
            with self.assertRaises(localhost.MarketplaceLocalhostBootstrapError) as caught:
                localhost._execute_agreement_assent_authenticated_localhost(
                    18446,
                    "WRONG",
                    "/synthetic/provisioning",
                )

        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_LOCALHOST_EXECUTION_OPT_IN_REQUIRED",
        )
        compose.assert_not_called()

    def test_shared_composition_rejects_mutated_graph_before_return(self) -> None:
        store = Mock(name="store")
        graph = SimpleNamespace(
            store=store,
            launch=SimpleNamespace(
                services=SimpleNamespace(
                    coordination=SimpleNamespace(
                        _store=store,
                        _initialized=True,
                    )
                ),
                plan=SimpleNamespace(
                    host=localhost.LOCALHOST_HOST,
                    port=18446,
                ),
            ),
        )

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
                localhost._compose_agreement_assent_authenticated_localhost(
                    18446,
                    "/synthetic/provisioning",
                )

        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_LOCALHOST_PREFLIGHT_FAILED",
        )


if __name__ == "__main__":
    unittest.main()
