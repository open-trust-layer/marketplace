from __future__ import annotations

import contextlib
import io
import pathlib
import types
import unittest
from unittest.mock import Mock, patch

import tools.marketplace_localhost as tool


PROVISIONING_DIRECTORY = str(pathlib.Path.cwd() / "synthetic-auth")
PORT = 18080


class _Application:
    def __init__(self, events: list[str], *, fail: bool = False) -> None:
        self._events = events
        self._fail = fail

    def initialize(self):
        self._events.append("initialize")
        if self._fail:
            raise RuntimeError("SECRET-DB-DETAIL")
        return object()


class MarketplaceAuthenticatedLocalhostBootstrapTests(unittest.TestCase):
    def test_authenticated_mode_requires_exact_token_before_external_providers(self):
        stderr = io.StringIO()
        with (
            patch.object(tool, "_load_authentication_provisioning") as provisioning,
            patch.object(tool, "_compose_authentication_runtime_inputs") as runtime_inputs,
            patch.object(tool, "_real_environment_getter") as environment,
            patch.object(tool, "_real_asset_reader") as assets,
            patch.object(tool, "_build_psycopg_connection_factory") as postgres,
            patch.object(tool, "_real_uvicorn_provider") as server,
        ):
            with contextlib.redirect_stderr(stderr):
                code = tool.main(
                    [
                        "--port",
                        str(PORT),
                        "--execute-authenticated-localhost",
                        "execute",
                        "--authentication-provisioning-directory",
                        PROVISIONING_DIRECTORY,
                    ]
                )
        self.assertEqual(code, 2)
        self.assertEqual(stderr.getvalue().strip(), "M17_5Y_EXECUTION_OPT_IN_REQUIRED")
        provisioning.assert_not_called()
        runtime_inputs.assert_not_called()
        environment.assert_not_called()
        assets.assert_not_called()
        postgres.assert_not_called()
        server.assert_not_called()

    def test_missing_or_relative_provisioning_directory_fails_before_external_providers(self):
        cases = (None, "relative/auth")
        for directory in cases:
            with self.subTest(directory=directory):
                stderr = io.StringIO()
                with (
                    patch.object(tool, "_load_authentication_provisioning") as provisioning,
                    patch.object(tool, "_compose_authentication_runtime_inputs") as runtime_inputs,
                    patch.object(tool, "_real_environment_getter") as environment,
                    patch.object(tool, "_real_asset_reader") as assets,
                ):
                    argv = [
                        "--port",
                        str(PORT),
                        "--execute-authenticated-localhost",
                        tool.AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                    ]
                    if directory is not None:
                        argv += ["--authentication-provisioning-directory", directory]
                    with contextlib.redirect_stderr(stderr):
                        code = tool.main(argv)
                self.assertEqual(code, 2)
                self.assertEqual(
                    stderr.getvalue().strip(),
                    "M17_5Y_PROVISIONING_DIRECTORY_INVALID",
                )
                provisioning.assert_not_called()
                runtime_inputs.assert_not_called()
                environment.assert_not_called()
                assets.assert_not_called()

    def test_dry_run_and_existing_unauthenticated_mode_do_not_select_auth_path(self):
        with patch.object(tool, "_execute_authenticated_localhost") as authenticated:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = tool.main(["--port", str(PORT), "--dry-run"])
            self.assertEqual(code, 0)
            self.assertIn("M17_2B_DRY_RUN_READY", stdout.getvalue())
            authenticated.assert_not_called()

        with (
            patch.object(tool, "_execute_localhost") as unauthenticated,
            patch.object(tool, "_execute_authenticated_localhost") as authenticated,
        ):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = tool.main(
                    [
                        "--port",
                        str(PORT),
                        "--execute-localhost",
                        tool.LOCALHOST_EXECUTION_OPT_IN,
                    ]
                )
            self.assertEqual(code, 0)
            unauthenticated.assert_called_once_with(PORT, tool.LOCALHOST_EXECUTION_OPT_IN)
            authenticated.assert_not_called()
            self.assertIn("M17_2B_LOCALHOST_FOREGROUND_COMPLETE", stdout.getvalue())

    def test_authenticated_provisioning_flag_is_rejected_outside_authenticated_mode(self):
        modes = (
            ["--port", str(PORT), "--dry-run"],
            [
                "--port",
                str(PORT),
                "--execute-localhost",
                tool.LOCALHOST_EXECUTION_OPT_IN,
            ],
        )
        for argv in modes:
            with self.subTest(mode=argv[2]):
                stderr = io.StringIO()
                with (
                    patch.object(tool, "_execute_localhost") as unauthenticated,
                    patch.object(tool, "_execute_authenticated_localhost") as authenticated,
                ):
                    with contextlib.redirect_stderr(stderr):
                        code = tool.main(
                            argv
                            + [
                                "--authentication-provisioning-directory",
                                PROVISIONING_DIRECTORY,
                            ]
                        )
                self.assertEqual(code, 2)
                self.assertEqual(
                    stderr.getvalue().strip(),
                    "M17_5Y_PROVISIONING_DIRECTORY_MODE_INVALID",
                )
                unauthenticated.assert_not_called()
                authenticated.assert_not_called()
    def test_authenticated_execute_orders_reviewed_boundaries_once(self):
        events: list[str] = []
        provisioning = object()
        runtime_inputs = object()
        connection_factory = Mock(name="connection_factory")
        plan = object()
        application = _Application(events)
        provider = object()

        def load_provisioning(directory: str):
            events.append("provisioning")
            self.assertEqual(directory, PROVISIONING_DIRECTORY)
            return provisioning

        def compose_runtime_inputs():
            events.append("runtime-inputs")
            return runtime_inputs

        def environment_provider():
            events.append("environment-provider")

            def getenv(name: str):
                events.append("dsn")
                self.assertEqual(name, tool.POSTGRES_DSN_ENV)
                return "postgresql://SECRET"

            return getenv

        def asset_provider():
            events.append("asset-provider")
            values = {
                "web/index.html": b"index",
                "web/app.js": b"app",
                "web/styles.css": b"css",
            }

            def read(path: str):
                events.append(path)
                return values[path]

            return read

        def build_postgres_factory(dsn: str):
            events.append("postgres-provider")
            self.assertEqual(dsn, "postgresql://SECRET")
            return connection_factory

        def build_plan(**kwargs):
            events.append("plan")
            self.assertIs(kwargs["connection_factory"], connection_factory)
            self.assertIs(kwargs["clock"], tool._utc_clock)
            self.assertEqual(kwargs["host"], tool.LOCALHOST_HOST)
            self.assertEqual(kwargs["port"], PORT)
            self.assertEqual(kwargs["index_html"], b"index")
            self.assertEqual(kwargs["app_js"], b"app")
            self.assertEqual(kwargs["styles_css"], b"css")
            self.assertIs(kwargs["provisioning"], provisioning)
            self.assertIs(kwargs["runtime_inputs"], runtime_inputs)
            return plan

        def validate(candidate):
            events.append("validate-plan")
            self.assertIs(candidate, plan)
            return application

        def server_provider():
            events.append("server-provider")
            return provider

        def run_authenticated(**kwargs):
            events.append("server")
            self.assertIs(kwargs["plan"], plan)
            self.assertIs(kwargs["provider"], provider)

        with (
            patch.object(tool, "_load_authentication_provisioning", side_effect=load_provisioning),
            patch.object(tool, "_compose_authentication_runtime_inputs", side_effect=compose_runtime_inputs),
            patch.object(tool, "_real_environment_getter", side_effect=environment_provider),
            patch.object(tool, "_real_asset_reader", side_effect=asset_provider),
            patch.object(tool, "_build_psycopg_connection_factory", side_effect=build_postgres_factory),
            patch.object(tool, "_build_authenticated_postgres_plan", side_effect=build_plan),
            patch.object(tool, "_validate_authenticated_plan_before_initialize", side_effect=validate),
            patch.object(tool, "_real_uvicorn_provider", side_effect=server_provider),
            patch.object(tool, "_run_authenticated_foreground", side_effect=run_authenticated),
        ):
            tool._execute_authenticated_localhost(
                PORT,
                tool.AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                PROVISIONING_DIRECTORY,
            )

        self.assertEqual(
            events,
            [
                "provisioning",
                "runtime-inputs",
                "environment-provider",
                "dsn",
                "asset-provider",
                "web/index.html",
                "web/app.js",
                "web/styles.css",
                "postgres-provider",
                "plan",
                "validate-plan",
                "server-provider",
                "initialize",
                "server",
            ],
        )
        connection_factory.assert_not_called()

    def test_provisioning_failure_is_nonreflective_and_stops_later_authority(self):
        secret = "SECRET-PROVISIONING-DETAIL"
        module = types.SimpleNamespace(
            load_marketplace_authentication_startup_provisioning=Mock(
                side_effect=RuntimeError(secret)
            )
        )
        with self.assertRaises(tool.MarketplaceLocalhostBootstrapError) as caught:
            tool._load_authentication_provisioning(
                PROVISIONING_DIRECTORY,
                importer=lambda name: module,
            )
        self.assertEqual(caught.exception.code, "M17_5Y_PROVISIONING_FAILED")
        self.assertNotIn(secret, str(caught.exception))

    def test_runtime_inputs_failure_is_nonreflective(self):
        secret = "SECRET-RUNTIME-INPUT-DETAIL"
        module = types.SimpleNamespace(
            compose_marketplace_authentication_runtime_inputs=Mock(
                side_effect=RuntimeError(secret)
            )
        )
        with self.assertRaises(tool.MarketplaceLocalhostBootstrapError) as caught:
            tool._compose_authentication_runtime_inputs(importer=lambda name: module)
        self.assertEqual(caught.exception.code, "M17_5Y_RUNTIME_INPUTS_FAILED")
        self.assertNotIn(secret, str(caught.exception))

    def test_authenticated_runtime_helper_uses_exact_m17_5v_token_once(self):
        calls: list[dict[str, object]] = []
        plan = object()
        provider = object()

        def run(**kwargs):
            calls.append(kwargs)

        module = types.SimpleNamespace(
            run_marketplace_authenticated_application_foreground=run,
            EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER=(
                "EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER"
            ),
        )
        tool._run_authenticated_foreground(
            plan=plan,
            provider=provider,
            importer=lambda name: module,
        )
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["plan"], plan)
        self.assertIs(calls[0]["provider"], provider)
        self.assertEqual(
            calls[0]["execute_token"],
            "EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER",
        )

    def test_invalid_authenticated_plan_stops_before_provider_and_initialization(self):
        plan = object()
        with (
            patch.object(tool, "_load_authentication_provisioning", return_value=object()),
            patch.object(tool, "_compose_authentication_runtime_inputs", return_value=object()),
            patch.object(tool, "_real_environment_getter", return_value=lambda name: "postgresql://synthetic"),
            patch.object(
                tool,
                "_real_asset_reader",
                return_value=lambda path: {
                    "web/index.html": b"index",
                    "web/app.js": b"app",
                    "web/styles.css": b"css",
                }[path],
            ),
            patch.object(tool, "_build_psycopg_connection_factory", return_value=Mock()),
            patch.object(tool, "_build_authenticated_postgres_plan", return_value=plan),
            patch.object(
                tool,
                "_validate_authenticated_plan_before_initialize",
                side_effect=tool.MarketplaceLocalhostBootstrapError(
                    "M17_5Y_LAUNCH_PLAN_INVALID"
                ),
            ),
            patch.object(tool, "_real_uvicorn_provider") as provider,
            patch.object(tool, "_run_authenticated_foreground") as run_server,
        ):
            with self.assertRaises(tool.MarketplaceLocalhostBootstrapError) as caught:
                tool._execute_authenticated_localhost(
                    PORT,
                    tool.AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                    PROVISIONING_DIRECTORY,
                )
        self.assertEqual(caught.exception.code, "M17_5Y_LAUNCH_PLAN_INVALID")
        provider.assert_not_called()
        run_server.assert_not_called()

    def test_initialization_failure_is_nonreflective_and_prevents_server(self):
        events: list[str] = []
        application = _Application(events, fail=True)
        run_server = Mock()
        stderr = io.StringIO()
        with (
            patch.object(tool, "_load_authentication_provisioning", return_value=object()),
            patch.object(tool, "_compose_authentication_runtime_inputs", return_value=object()),
            patch.object(tool, "_real_environment_getter", return_value=lambda name: "postgresql://synthetic"),
            patch.object(
                tool,
                "_real_asset_reader",
                return_value=lambda path: {
                    "web/index.html": b"index",
                    "web/app.js": b"app",
                    "web/styles.css": b"css",
                }[path],
            ),
            patch.object(tool, "_build_psycopg_connection_factory", return_value=Mock()),
            patch.object(tool, "_build_authenticated_postgres_plan", return_value=object()),
            patch.object(
                tool,
                "_validate_authenticated_plan_before_initialize",
                return_value=application,
            ),
            patch.object(tool, "_real_uvicorn_provider", return_value=object()),
            patch.object(tool, "_run_authenticated_foreground", run_server),
        ):
            with contextlib.redirect_stderr(stderr):
                code = tool.main(
                    [
                        "--port",
                        str(PORT),
                        "--execute-authenticated-localhost",
                        tool.AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN,
                        "--authentication-provisioning-directory",
                        PROVISIONING_DIRECTORY,
                    ]
                )
        self.assertEqual(code, 1)
        self.assertEqual(
            stderr.getvalue().strip(),
            "M17_5Y_DATABASE_INITIALIZATION_FAILED",
        )
        self.assertNotIn("SECRET-DB-DETAIL", stderr.getvalue())
        self.assertEqual(events, ["initialize"])
        run_server.assert_not_called()

    def test_authenticated_server_failure_is_nonreflective_and_not_retried(self):
        secret = "SECRET-SERVER-DETAIL"
        module = types.SimpleNamespace(
            run_marketplace_authenticated_application_foreground=Mock(
                side_effect=RuntimeError(secret)
            ),
            EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER=(
                "EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER"
            ),
        )
        with self.assertRaises(tool.MarketplaceLocalhostBootstrapError) as caught:
            tool._run_authenticated_foreground(
                plan=object(),
                provider=object(),
                importer=lambda name: module,
            )
        self.assertEqual(caught.exception.code, "M17_5Y_LOOPBACK_SERVER_FAILED")
        self.assertNotIn(secret, str(caught.exception))
        module.run_marketplace_authenticated_application_foreground.assert_called_once()


if __name__ == "__main__":
    unittest.main()
