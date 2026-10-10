from __future__ import annotations

import unittest
from unittest.mock import Mock

from tools import marketplace_localhost as localhost


class ProductAgreementAssentLocalhostWiringTests(unittest.TestCase):
    def test_exact_execution_token_is_required(self) -> None:
        localhost._validate_agreement_assent_authenticated_execution_opt_in(
            localhost.AGREEMENT_ASSENT_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN
        )
        for value in ("", "WRONG", object()):
            with self.assertRaises(localhost.MarketplaceLocalhostBootstrapError):
                localhost._validate_agreement_assent_authenticated_execution_opt_in(
                    value
                )

    def test_agreement_helpers_select_exact_reviewed_entry_points(self) -> None:
        graph = Mock(name="graph")
        initialize = Mock(name="initialize")
        init_module = Mock(
            initialize_reference_agreement_assent_coordination=initialize,
            INITIALIZE_ONE_AGREEMENT_ASSENT_COORDINATION="INIT",
        )
        localhost._initialize_agreement_assent_coordination(
            graph,
            importer=lambda name: init_module,
        )
        initialize.assert_called_once_with(graph=graph, execute_token="INIT")

        plan = Mock(name="plan")
        graph.launch.plan = plan
        provider = Mock(name="provider")
        run = Mock(name="run")
        runtime_module = Mock(
            run_marketplace_agreement_assent_foreground=run,
            EXECUTE_ONE_AGREEMENT_ASSENT_MARKETPLACE_LOOPBACK_SERVER="RUN",
        )
        localhost._run_agreement_assent_foreground(
            graph,
            provider=provider,
            importer=lambda name: runtime_module,
        )
        run.assert_called_once_with(
            plan=plan,
            provider=provider,
            execute_token="RUN",
        )

    def test_parser_keeps_agreement_mode_mutually_exclusive(self) -> None:
        parser = localhost._parser()
        args = parser.parse_args(
            [
                "--port",
                "18446",
                "--execute-agreement-assent-localhost",
                localhost.AGREEMENT_ASSENT_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                "--authentication-provisioning-directory",
                "/synthetic/provisioning",
            ]
        )
        self.assertEqual(
            args.execute_agreement_assent_localhost,
            localhost.AGREEMENT_ASSENT_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
        )
        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "--port",
                    "18446",
                    "--execute-agreement-assent-localhost",
                    localhost.AGREEMENT_ASSENT_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                    "--execute-authenticated-localhost",
                    localhost.AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                ]
            )


if __name__ == "__main__":
    unittest.main()
