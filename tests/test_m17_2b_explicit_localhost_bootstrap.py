from __future__ import annotations

import ast
import contextlib
import io
import pathlib
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import tools.marketplace_localhost as tool


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/marketplace_localhost.py"


class _Composition:
    def __init__(self, events: list[str], *, fail: str | None = None) -> None:
        self._events = events
        self._fail = fail

    def initialize(self):
        self._events.append("initialize")
        if self._fail is not None:
            raise RuntimeError(self._fail)
        return object()


class _Plan:
    def __init__(self, composition: _Composition) -> None:
        self.composition = composition


class MarketplaceLocalhostBootstrapTests(unittest.TestCase):
    def test_help_is_external_io_inert(self):
        stdout = io.StringIO()
        with patch.object(tool, "_real_environment_getter") as environment_provider, patch.object(
            tool, "_real_asset_reader"
        ) as asset_provider, patch.object(tool, "_build_psycopg_connection_factory") as postgres_provider, patch.object(
            tool, "_real_uvicorn_provider"
        ) as server_provider:
            with contextlib.redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as caught:
                    tool.main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        environment_provider.assert_not_called()
        asset_provider.assert_not_called()
        postgres_provider.assert_not_called()
        server_provider.assert_not_called()
        self.assertIn("separate runtime authorization", stdout.getvalue())

    def test_dry_run_is_external_io_inert(self):
        stdout = io.StringIO()
        with patch.object(tool, "_real_environment_getter") as environment_provider, patch.object(
            tool, "_real_asset_reader"
        ) as asset_provider, patch.object(tool, "_build_psycopg_connection_factory") as postgres_provider, patch.object(
            tool, "_real_uvicorn_provider"
        ) as server_provider, patch.object(
            tool, "build_reference_postgres_marketplace_application_launch_plan"
        ) as plan_builder, patch.object(tool, "run_marketplace_application_foreground") as run_server:
            with contextlib.redirect_stdout(stdout):
                code = tool.main(["--port", "18080", "--dry-run"])
        self.assertEqual(code, 0)
        environment_provider.assert_not_called()
        asset_provider.assert_not_called()
        postgres_provider.assert_not_called()
        server_provider.assert_not_called()
        plan_builder.assert_not_called()
        run_server.assert_not_called()
        self.assertEqual(
            stdout.getvalue().strip(),
            "M17_2B_DRY_RUN_READY host=127.0.0.1 port=18080 filesystem_invoked=false "
            "environment_invoked=false postgres_invoked=false server_invoked=false",
        )

    def test_bad_execution_token_fails_before_every_external_provider(self):
        stderr = io.StringIO()
        with patch.object(tool, "_real_environment_getter") as environment_provider, patch.object(
            tool, "_real_asset_reader"
        ) as asset_provider, patch.object(tool, "_build_psycopg_connection_factory") as postgres_provider, patch.object(
            tool, "_real_uvicorn_provider"
        ) as server_provider:
            with contextlib.redirect_stderr(stderr):
                code = tool.main(["--port", "18080", "--execute-localhost", "execute"])
        self.assertEqual(code, 2)
        environment_provider.assert_not_called()
        asset_provider.assert_not_called()
        postgres_provider.assert_not_called()
        server_provider.assert_not_called()
        self.assertEqual(stderr.getvalue().strip(), "M17_2B_EXECUTION_OPT_IN_REQUIRED")

    def test_port_is_unprivileged_loopback_range_and_fails_before_providers(self):
        for value in (0, 80, 65536):
            with self.subTest(value=value):
                stderr = io.StringIO()
                with patch.object(tool, "_real_environment_getter") as environment_provider:
                    with contextlib.redirect_stderr(stderr):
                        code = tool.main(["--port", str(value), "--dry-run"])
                self.assertEqual(code, 2)
                environment_provider.assert_not_called()
                self.assertEqual(stderr.getvalue().strip(), "M17_2B_PORT_INVALID")

    def test_dsn_source_is_fixed_bounded_and_nonreflective(self):
        calls: list[str] = []
        secret = "postgresql://user:SECRET-PASSWORD@localhost/marketplace"

        def getenv(name: str):
            calls.append(name)
            return secret

        self.assertEqual(tool._read_postgres_dsn(getenv), secret)
        self.assertEqual(calls, [tool.POSTGRES_DSN_ENV])

        hostile = "postgresql://SECRET-LINE\nbreak"
        with self.assertRaises(tool.MarketplaceLocalhostBootstrapError) as caught:
            tool._read_postgres_dsn(lambda _name: hostile)
        self.assertEqual(caught.exception.code, "M17_2B_POSTGRES_DSN_INVALID")
        self.assertNotIn("SECRET-LINE", str(caught.exception))

    def test_web_asset_loader_reads_exact_three_paths_and_bounds_bytes(self):
        calls: list[str] = []
        values = {
            "web/index.html": b"<html></html>",
            "web/app.js": b"export {};",
            "web/styles.css": b"body{}",
        }

        def reader(path: str) -> bytes:
            calls.append(path)
            return values[path]

        self.assertEqual(
            tool._load_web_assets(reader),
            (values["web/index.html"], values["web/app.js"], values["web/styles.css"]),
        )
        self.assertEqual(calls, ["web/index.html", "web/app.js", "web/styles.css"])

        with patch.object(tool, "MAX_APPLICATION_HTTP_RESPONSE_BYTES", 4):
            with self.assertRaises(tool.MarketplaceLocalhostBootstrapError) as caught:
                tool._load_web_assets(lambda _path: b"12345")
        self.assertEqual(caught.exception.code, "M17_2B_WEB_ASSET_SIZE_INVALID")

    def test_psycopg_provider_selection_is_lazy_and_connection_is_later(self):
        calls: list[object] = []
        connection = object()

        def connect(dsn: str):
            calls.append(("connect", dsn))
            return connection

        module = types.SimpleNamespace(connect=connect)

        def importer(name: str):
            calls.append(("import", name))
            return module

        factory = tool._build_psycopg_connection_factory("postgresql://SECRET", importer=importer)
        self.assertEqual(calls, [("import", "psycopg")])
        self.assertIs(factory(), connection)
        self.assertEqual(calls[-1], ("connect", "postgresql://SECRET"))

    def test_uvicorn_adapter_selection_requires_exact_callable_provider(self):
        calls: list[str] = []

        class UvicornLoopbackServerProvider:
            def run(self, *, application: object, host: str, port: int) -> None:
                raise AssertionError("run must not be invoked by provider selection")

        module = types.SimpleNamespace(UvicornLoopbackServerProvider=UvicornLoopbackServerProvider)

        def importer(name: str):
            calls.append(name)
            return module

        provider = tool._real_uvicorn_provider(importer=importer)
        self.assertIs(type(provider), UvicornLoopbackServerProvider)
        self.assertEqual(calls, ["marketplace.application.uvicorn_provider"])

        malformed = types.SimpleNamespace(UvicornLoopbackServerProvider=lambda: object())
        with self.assertRaises(tool.MarketplaceLocalhostBootstrapError) as caught:
            tool._real_uvicorn_provider(importer=lambda _name: malformed)
        self.assertEqual(caught.exception.code, "M17_2B_SERVER_PROVIDER_INVALID")

    def test_preinitialize_validation_accepts_only_exact_m17_2a_plan_graph(self):
        connection_factory = Mock(name="connection_factory")
        clock = Mock(return_value=datetime(2026, 9, 6, tzinfo=timezone.utc))
        plan = tool.build_reference_postgres_marketplace_application_launch_plan(
            connection_factory=connection_factory,
            clock=clock,
            host=tool.LOCALHOST_HOST,
            port=18080,
            index_html=b"index",
            app_js=b"app",
            styles_css=b"css",
        )
        self.assertIs(tool._validate_plan_before_initialize(plan), plan)
        connection_factory.assert_not_called()
        clock.assert_not_called()

        with self.assertRaises(tool.MarketplaceLocalhostBootstrapError) as caught:
            tool._validate_plan_before_initialize(_Plan(_Composition([])))
        self.assertEqual(caught.exception.code, "M17_2B_LAUNCH_PLAN_INVALID")

    def test_execute_reuses_m17_2a_and_initializes_before_server(self):
        events: list[str] = []
        composition = _Composition(events)
        plan = _Plan(composition)
        connection_factory = Mock(name="connection_factory")
        provider = object()

        def getenv(name: str):
            events.append("dsn")
            self.assertEqual(name, tool.POSTGRES_DSN_ENV)
            return "postgresql://SECRET"

        asset_values = {
            "web/index.html": b"index",
            "web/app.js": b"app",
            "web/styles.css": b"css",
        }

        def asset_reader(path: str):
            events.append(path)
            return asset_values[path]

        def build_connection_factory(dsn: str):
            events.append("postgres-provider")
            self.assertEqual(dsn, "postgresql://SECRET")
            return connection_factory

        def build_plan(**kwargs):
            events.append("plan")
            self.assertIs(kwargs["connection_factory"], connection_factory)
            self.assertIs(kwargs["clock"], tool._utc_clock)
            self.assertEqual(kwargs["host"], "127.0.0.1")
            self.assertEqual(kwargs["port"], 18080)
            self.assertEqual(kwargs["index_html"], b"index")
            self.assertEqual(kwargs["app_js"], b"app")
            self.assertEqual(kwargs["styles_css"], b"css")
            return plan

        def validate_plan(candidate):
            events.append("validate-plan")
            self.assertIs(candidate, plan)
            return plan

        def build_server_provider():
            events.append("server-provider")
            return provider

        def run_server(**kwargs):
            events.append("server")
            self.assertIs(kwargs["plan"], plan)
            self.assertIs(kwargs["provider"], provider)
            self.assertEqual(kwargs["execute_token"], tool.EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER)

        with patch.object(tool, "_real_environment_getter", return_value=getenv), patch.object(
            tool, "_real_asset_reader", return_value=asset_reader
        ), patch.object(tool, "_build_psycopg_connection_factory", side_effect=build_connection_factory), patch.object(
            tool, "build_reference_postgres_marketplace_application_launch_plan", side_effect=build_plan
        ), patch.object(tool, "_validate_plan_before_initialize", side_effect=validate_plan), patch.object(
            tool, "_real_uvicorn_provider", side_effect=build_server_provider
        ), patch.object(tool, "run_marketplace_application_foreground", side_effect=run_server):
            tool._execute_localhost(18080, tool.LOCALHOST_EXECUTION_OPT_IN)

        self.assertEqual(
            events,
            [
                "dsn",
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

    def test_initialization_failure_prevents_server_and_reflects_no_provider_text(self):
        stderr = io.StringIO()
        events: list[str] = []
        plan = _Plan(_Composition(events, fail="SECRET-DB-DETAIL"))
        run_server = Mock()

        with patch.object(tool, "_real_environment_getter", return_value=lambda _name: "postgresql://SECRET"), patch.object(
            tool, "_real_asset_reader", return_value=lambda path: {"web/index.html": b"i", "web/app.js": b"j", "web/styles.css": b"c"}[path]
        ), patch.object(tool, "_build_psycopg_connection_factory", return_value=Mock()), patch.object(
            tool, "build_reference_postgres_marketplace_application_launch_plan", return_value=plan
        ), patch.object(tool, "_validate_plan_before_initialize", return_value=plan), patch.object(
            tool, "_real_uvicorn_provider", return_value=object()
        ), patch.object(tool, "run_marketplace_application_foreground", run_server):
            with contextlib.redirect_stderr(stderr):
                code = tool.main(["--port", "18080", "--execute-localhost", tool.LOCALHOST_EXECUTION_OPT_IN])

        self.assertEqual(code, 1)
        run_server.assert_not_called()
        self.assertEqual(stderr.getvalue().strip(), "M17_2B_DATABASE_INITIALIZATION_FAILED")
        self.assertNotIn("SECRET-DB-DETAIL", stderr.getvalue())

    def test_server_failure_is_nonreflective_and_not_retried(self):
        stderr = io.StringIO()
        plan = _Plan(_Composition([]))
        run_server = Mock(side_effect=RuntimeError("SECRET-UVI-DETAIL"))

        with patch.object(tool, "_real_environment_getter", return_value=lambda _name: "postgresql://SECRET"), patch.object(
            tool, "_real_asset_reader", return_value=lambda path: {"web/index.html": b"i", "web/app.js": b"j", "web/styles.css": b"c"}[path]
        ), patch.object(tool, "_build_psycopg_connection_factory", return_value=Mock()), patch.object(
            tool, "build_reference_postgres_marketplace_application_launch_plan", return_value=plan
        ), patch.object(tool, "_validate_plan_before_initialize", return_value=plan), patch.object(
            tool, "_real_uvicorn_provider", return_value=object()
        ), patch.object(tool, "run_marketplace_application_foreground", run_server):
            with contextlib.redirect_stderr(stderr):
                code = tool.main(["--port", "18080", "--execute-localhost", tool.LOCALHOST_EXECUTION_OPT_IN])

        self.assertEqual(code, 1)
        run_server.assert_called_once()
        self.assertEqual(stderr.getvalue().strip(), "M17_2B_LOOPBACK_SERVER_FAILED")
        self.assertNotIn("SECRET-UVI-DETAIL", stderr.getvalue())


class MarketplaceLocalhostBootstrapSourceTests(unittest.TestCase):
    def test_live_provider_imports_are_post_opt_in_helpers_only(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        top_level_imports: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_level_imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_level_imports.add(node.module.split(".")[0])
        self.assertNotIn("os", top_level_imports)
        self.assertNotIn("psycopg", top_level_imports)
        self.assertNotIn("uvicorn", top_level_imports)
        self.assertNotIn("socket", top_level_imports)

        environment_helper = next(
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_real_environment_getter"
        )
        os_imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Import) and any(alias.name == "os" for alias in node.names)
        ]
        self.assertEqual(len(os_imports), 1)
        self.assertIn(os_imports[0], list(ast.walk(environment_helper)))

    def test_source_has_no_background_browser_process_retry_or_public_bind_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        blocked = {"socket", "subprocess", "threading", "multiprocessing", "asyncio", "concurrent", "webbrowser", "logging"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name.split(".")[0] not in blocked for alias in node.names))
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], blocked)
            self.assertNotIsInstance(node, (ast.While, ast.AsyncFor))
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('LOCALHOST_HOST: Final = "127.0.0.1"', source)
        self.assertNotIn("0.0.0.0", source)
        self.assertNotIn("::", source)

    def test_source_reuses_exact_reviewed_composition_and_runtime_boundaries(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("build_reference_postgres_marketplace_application_launch_plan", source)
        self.assertIn("_validate_plan_before_initialize(plan)", source)
        self.assertIn("plan.composition.initialize()", source)
        self.assertIn("run_marketplace_application_foreground", source)
        self.assertIn("EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER", source)
        self.assertIn('importer("psycopg")', source)
        self.assertIn('importer("marketplace.application.uvicorn_provider")', source)


if __name__ == "__main__":
    unittest.main()
