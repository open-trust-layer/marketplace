from __future__ import annotations

import contextlib
import io
import types
import unittest
from unittest.mock import Mock, patch

import tools.marketplace_localhost as tool


class M177HFulfillmentCompletionLocalhostBootstrapTests(unittest.TestCase):
    def test_exact_execution_opt_in_is_separate_and_fail_closed(self) -> None:
        tool._validate_fulfillment_completion_authenticated_execution_opt_in(
            tool.FULFILLMENT_COMPLETION_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN
        )
        for value in (None, "", "execute", tool.AGREEMENT_ASSENT_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN):
            with self.subTest(value=value):
                with self.assertRaises(tool.MarketplaceLocalhostBootstrapError) as caught:
                    tool._validate_fulfillment_completion_authenticated_execution_opt_in(
                        value
                    )
                self.assertEqual(
                    caught.exception.code,
                    "FULFILLMENT_COMPLETION_LOCALHOST_EXECUTION_OPT_IN_REQUIRED",
                )

    def test_reference_builder_is_lazy_and_exact(self) -> None:
        graph = object()
        reference = object()
        calls = []

        def builder(*, agreement_graph):
            calls.append(agreement_graph)
            return reference

        module = types.SimpleNamespace(
            build_reference_fulfillment_completion_launch=builder
        )
        result = tool._build_fulfillment_completion_reference(
            agreement_graph=graph,
            importer=lambda name: module
            if name == "marketplace.reference.fulfillment_completion_launch_v1"
            else None,
        )
        self.assertIs(result, reference)
        self.assertEqual(calls, [graph])

    def test_preflight_composes_exact_graph_without_initialization_or_server(self) -> None:
        application = types.SimpleNamespace(state=object(), initialize=Mock())
        agreement_startup = object()
        graph = types.SimpleNamespace(
            launch=types.SimpleNamespace(startup=agreement_startup),
        )
        reference = types.SimpleNamespace(
            agreement_graph=graph,
            plan=types.SimpleNamespace(host=tool.LOCALHOST_HOST, port=18080),
            startup=types.SimpleNamespace(agreement_startup=agreement_startup),
            agreement_publication=types.SimpleNamespace(_state=application.state),
            fulfillment_publication=types.SimpleNamespace(_state=application.state),
        )

        with (
            patch.object(
                tool,
                "_compose_agreement_assent_authenticated_localhost",
                return_value=(application, graph),
            ) as compose,
            patch.object(
                tool,
                "_build_fulfillment_completion_reference",
                return_value=reference,
            ) as build,
            patch.object(
                tool,
                "_initialize_agreement_assent_coordination",
            ) as initialize_coordination,
            patch.object(
                tool,
                "_run_fulfillment_completion_foreground",
            ) as run_server,
        ):
            result = tool._preflight_fulfillment_completion_authenticated_localhost(
                18080,
                r"C:\marketplace-auth",
            )

        self.assertIs(result, reference)
        compose.assert_called_once_with(18080, r"C:\marketplace-auth")
        build.assert_called_once_with(agreement_graph=graph)
        application.initialize.assert_not_called()
        initialize_coordination.assert_not_called()
        run_server.assert_not_called()

    def test_live_execution_initializes_application_then_coordination_then_runtime(self) -> None:
        events = []
        application = types.SimpleNamespace(
            initialize=lambda: events.append("application.initialize"),
        )
        graph = object()
        reference = object()
        provider = object()

        with (
            patch.object(
                tool,
                "_validate_fulfillment_completion_authenticated_execution_opt_in",
            ) as validate_token,
            patch.object(
                tool,
                "_compose_fulfillment_completion_authenticated_localhost",
                return_value=(application, graph, reference),
            ) as compose,
            patch.object(
                tool,
                "_real_uvicorn_provider",
                return_value=object(),
            ),
            patch.object(
                tool,
                "_wrap_marketplace_provider_with_moon_heartbeat",
                return_value=provider,
            ),
            patch.object(
                tool,
                "_initialize_agreement_assent_coordination",
                side_effect=lambda value: events.append(("coordination.initialize", value)),
            ),
            patch.object(
                tool,
                "_run_fulfillment_completion_foreground",
                side_effect=lambda value, *, provider: events.append(
                    ("runtime.run", value, provider)
                ),
            ),
        ):
            tool._execute_fulfillment_completion_authenticated_localhost(
                18080,
                tool.FULFILLMENT_COMPLETION_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                r"C:\marketplace-auth",
            )

        validate_token.assert_called_once_with(
            tool.FULFILLMENT_COMPLETION_AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN
        )
        compose.assert_called_once_with(18080, r"C:\marketplace-auth")
        self.assertEqual(
            events,
            [
                "application.initialize",
                ("coordination.initialize", graph),
                ("runtime.run", reference, provider),
            ],
        )

    def test_main_preflight_accepts_authenticated_provisioning_mode(self) -> None:
        stdout = io.StringIO()
        with patch.object(
            tool,
            "_preflight_fulfillment_completion_authenticated_localhost",
            return_value=object(),
        ) as preflight:
            with contextlib.redirect_stdout(stdout):
                code = tool.main(
                    [
                        "--port",
                        "18080",
                        "--preflight-fulfillment-completion-localhost",
                        "--authentication-provisioning-directory",
                        r"C:\marketplace-auth",
                    ]
                )

        self.assertEqual(code, 0)
        preflight.assert_called_once_with(18080, r"C:\marketplace-auth")
        self.assertIn(
            "FULFILLMENT_COMPLETION_AUTHENTICATED_LOCALHOST_PREFLIGHT_READY",
            stdout.getvalue(),
        )
        self.assertIn("server_invoked=false", stdout.getvalue())

    def test_main_bad_execution_token_fails_before_composition(self) -> None:
        stderr = io.StringIO()
        with patch.object(
            tool,
            "_compose_fulfillment_completion_authenticated_localhost",
        ) as compose:
            with contextlib.redirect_stderr(stderr):
                code = tool.main(
                    [
                        "--port",
                        "18080",
                        "--execute-fulfillment-completion-localhost",
                        "execute",
                        "--authentication-provisioning-directory",
                        r"C:\marketplace-auth",
                    ]
                )

        self.assertEqual(code, 2)
        compose.assert_not_called()
        self.assertEqual(
            stderr.getvalue().strip(),
            "FULFILLMENT_COMPLETION_LOCALHOST_EXECUTION_OPT_IN_REQUIRED",
        )


if __name__ == "__main__":
    unittest.main()
