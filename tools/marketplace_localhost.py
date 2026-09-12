"""Explicit repo-only localhost bootstrap for the reviewed Marketplace M17 stack.

Import, help, and dry-run are external-I/O inert. The existing M17.2B live path
requires its exact opt-in; the M17.5Y authenticated path requires a separate exact
opt-in and provisioning preflight. This is not a production deployment/service entry point.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Final

from marketplace.application.asgi import MarketplaceAsgiHttpAdapter
from marketplace.application.composition import MarketplaceApplicationComposition
from marketplace.application.http import MAX_APPLICATION_HTTP_RESPONSE_BYTES
from marketplace.application.launch import MarketplaceApplicationLaunchPlan
from marketplace.application.runtime_server import (
    EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
    run_marketplace_application_foreground,
)
from marketplace.reference.postgres_application_v1 import (
    build_reference_postgres_marketplace_application_launch_plan,
)


LOCALHOST_EXECUTION_OPT_IN: Final = "EXECUTE_MARKETPLACE_LOCALHOST_MVP_V1"
AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN: Final = (
    "EXECUTE_AUTHENTICATED_MARKETPLACE_LOCALHOST_MVP_V1"
)
LOCALHOST_HOST: Final = "127.0.0.1"
MIN_LOCALHOST_PORT: Final = 1024
MAX_LOCALHOST_PORT: Final = 65535
POSTGRES_DSN_ENV: Final = "MARKETPLACE_POSTGRES_DSN"
MAX_POSTGRES_DSN_CHARS: Final = 8192
_INDEX_ASSET: Final = "web/index.html"
_APP_JS_ASSET: Final = "web/app.js"
_STYLES_ASSET: Final = "web/styles.css"
_ALLOWED_ASSETS: Final = frozenset((_INDEX_ASSET, _APP_JS_ASSET, _STYLES_ASSET))


class MarketplaceLocalhostBootstrapError(RuntimeError):
    """Stable bootstrap failure that does not reflect provider, path, or secret text."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _validate_port(port: int) -> int:
    if type(port) is not int or port < MIN_LOCALHOST_PORT or port > MAX_LOCALHOST_PORT:
        raise MarketplaceLocalhostBootstrapError("M17_2B_PORT_INVALID")
    return port


def _validate_execution_opt_in(value: object) -> None:
    if type(value) is not str or value != LOCALHOST_EXECUTION_OPT_IN:
        raise MarketplaceLocalhostBootstrapError("M17_2B_EXECUTION_OPT_IN_REQUIRED")


def _validate_authenticated_execution_opt_in(value: object) -> None:
    if type(value) is not str or value != AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN:
        raise MarketplaceLocalhostBootstrapError("M17_5Y_EXECUTION_OPT_IN_REQUIRED")


def _validate_authentication_provisioning_directory(value: object) -> str:
    if type(value) is not str or not value or "\x00" in value:
        raise MarketplaceLocalhostBootstrapError("M17_5Y_PROVISIONING_DIRECTORY_INVALID")
    if not Path(value).is_absolute():
        raise MarketplaceLocalhostBootstrapError("M17_5Y_PROVISIONING_DIRECTORY_INVALID")
    return value


def _load_authentication_provisioning(
    directory: str,
    *,
    importer: Callable[[str], object] = importlib.import_module,
):
    try:
        module = importer("marketplace.application.auth_startup_provisioning")
        loader = getattr(module, "load_marketplace_authentication_startup_provisioning")
        if not callable(loader):
            raise TypeError("loader")
        return loader(directory=directory)
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_5Y_PROVISIONING_FAILED") from None


def _compose_authentication_runtime_inputs(
    *, importer: Callable[[str], object] = importlib.import_module
):
    try:
        module = importer("marketplace.application.auth_runtime_inputs")
        composer = getattr(module, "compose_marketplace_authentication_runtime_inputs")
        if not callable(composer):
            raise TypeError("composer")
        return composer()
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_5Y_RUNTIME_INPUTS_FAILED") from None


def _build_authenticated_postgres_plan(
    *,
    connection_factory: object,
    clock: Callable[[], datetime],
    host: str,
    port: int,
    index_html: bytes,
    app_js: bytes,
    styles_css: bytes,
    provisioning: object,
    runtime_inputs: object,
    importer: Callable[[str], object] = importlib.import_module,
):
    try:
        module = importer("marketplace.reference.auth_postgres_application_v1")
        builder = getattr(
            module,
            "build_reference_authenticated_postgres_marketplace_launch_plan",
        )
        if not callable(builder):
            raise TypeError("builder")
        return builder(
            connection_factory=connection_factory,
            clock=clock,
            host=host,
            port=port,
            index_html=index_html,
            app_js=app_js,
            styles_css=styles_css,
            provisioning=provisioning,
            runtime_inputs=runtime_inputs,
        )
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_5Y_COMPOSITION_FAILED") from None


def _validate_authenticated_plan_before_initialize(
    plan: object,
    *,
    importer: Callable[[str], object] = importlib.import_module,
) -> MarketplaceApplicationComposition:
    try:
        runtime_module = importer("marketplace.application.auth_runtime_server")
        validator = getattr(runtime_module, "_validate_plan")
        if not callable(validator):
            raise TypeError("validator")
        validator(plan)
        application = plan.startup.http.application
        if type(application) is not MarketplaceApplicationComposition:
            raise TypeError("application")
        return application
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_5Y_LAUNCH_PLAN_INVALID") from None


def _run_authenticated_foreground(
    *,
    plan: object,
    provider: object,
    importer: Callable[[str], object] = importlib.import_module,
) -> None:
    try:
        module = importer("marketplace.application.auth_runtime_server")
        runner = getattr(module, "run_marketplace_authenticated_application_foreground")
        token = getattr(module, "EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER")
        if not callable(runner) or type(token) is not str:
            raise TypeError("runtime")
        runner(plan=plan, provider=provider, execute_token=token)
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_5Y_LOOPBACK_SERVER_FAILED") from None


def _load_mvp_flight_runner(
    *, importer: Callable[[str], object] = importlib.import_module
):
    module_name = (
        "tools.marketplace_mvp_flight_acceptance"
        if __package__
        else "marketplace_mvp_flight_acceptance"
    )
    try:
        module = importer(module_name)
        runner = getattr(module, "run_marketplace_mvp_flight_acceptance")
    except Exception:
        raise MarketplaceLocalhostBootstrapError("MVP_FLIGHT_RUNNER_UNAVAILABLE") from None
    if not callable(runner):
        raise MarketplaceLocalhostBootstrapError("MVP_FLIGHT_RUNNER_INVALID")
    return runner


def _real_environment_getter() -> Callable[[str], str | None]:
    import os

    return os.environ.get


def _read_postgres_dsn(getenv: Callable[[str], str | None]) -> str:
    if not callable(getenv):
        raise MarketplaceLocalhostBootstrapError("M17_2B_ENVIRONMENT_PROVIDER_INVALID")
    try:
        value = getenv(POSTGRES_DSN_ENV)
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_2B_POSTGRES_DSN_UNAVAILABLE") from None
    if type(value) is not str or not value or len(value) > MAX_POSTGRES_DSN_CHARS:
        raise MarketplaceLocalhostBootstrapError("M17_2B_POSTGRES_DSN_INVALID")
    if "\x00" in value or "\r" in value or "\n" in value:
        raise MarketplaceLocalhostBootstrapError("M17_2B_POSTGRES_DSN_INVALID")
    return value


def _real_asset_reader() -> Callable[[str], bytes]:
    try:
        repository_root = Path(__file__).resolve(strict=True).parents[1]
        declared_web_root = repository_root / "web"
        if declared_web_root.is_symlink():
            raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_BOUNDARY_INVALID")
        web_root = declared_web_root.resolve(strict=True)
        if not web_root.is_dir():
            raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_BOUNDARY_INVALID")
    except MarketplaceLocalhostBootstrapError:
        raise
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_BOUNDARY_INVALID") from None

    def read(relative_path: str) -> bytes:
        if type(relative_path) is not str or relative_path not in _ALLOWED_ASSETS:
            raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_PATH_INVALID")
        candidate = repository_root / relative_path
        try:
            if candidate.is_symlink():
                raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_BOUNDARY_INVALID")
            resolved = candidate.resolve(strict=True)
            if resolved.parent != web_root or not resolved.is_file():
                raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_BOUNDARY_INVALID")
            before_size = resolved.stat().st_size
            if before_size <= 0 or before_size > MAX_APPLICATION_HTTP_RESPONSE_BYTES:
                raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_SIZE_INVALID")
            data = resolved.read_bytes()
            after_size = resolved.stat().st_size
        except MarketplaceLocalhostBootstrapError:
            raise
        except Exception:
            raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_READ_FAILED") from None
        if after_size != before_size or len(data) != after_size:
            raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_CHANGED_DURING_READ")
        if type(data) is not bytes or not data or len(data) > MAX_APPLICATION_HTTP_RESPONSE_BYTES:
            raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_SIZE_INVALID")
        return data

    return read


def _load_web_assets(reader: Callable[[str], bytes]) -> tuple[bytes, bytes, bytes]:
    if not callable(reader):
        raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_PROVIDER_INVALID")
    try:
        index_html = reader(_INDEX_ASSET)
        app_js = reader(_APP_JS_ASSET)
        styles_css = reader(_STYLES_ASSET)
    except MarketplaceLocalhostBootstrapError:
        raise
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_READ_FAILED") from None
    for value in (index_html, app_js, styles_css):
        if type(value) is not bytes or not value or len(value) > MAX_APPLICATION_HTTP_RESPONSE_BYTES:
            raise MarketplaceLocalhostBootstrapError("M17_2B_WEB_ASSET_SIZE_INVALID")
    return index_html, app_js, styles_css


def _build_psycopg_connection_factory(
    dsn: str,
    *,
    importer: Callable[[str], object] = importlib.import_module,
):
    if type(dsn) is not str or not dsn or len(dsn) > MAX_POSTGRES_DSN_CHARS:
        raise MarketplaceLocalhostBootstrapError("M17_2B_POSTGRES_DSN_INVALID")
    try:
        module = importer("psycopg")
        connect = getattr(module, "connect")
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_2B_POSTGRES_PROVIDER_UNAVAILABLE") from None
    if not callable(connect):
        raise MarketplaceLocalhostBootstrapError("M17_2B_POSTGRES_PROVIDER_INVALID")

    def connection_factory():
        return connect(dsn)

    return connection_factory


def _utc_clock() -> datetime:
    return datetime.now(timezone.utc)


def _real_uvicorn_provider(*, importer: Callable[[str], object] = importlib.import_module):
    try:
        module = importer("marketplace.application.uvicorn_provider")
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_2B_SERVER_PROVIDER_UNAVAILABLE") from None
    try:
        provider_type = getattr(module, "UvicornLoopbackServerProvider")
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_2B_SERVER_PROVIDER_INVALID") from None
    if type(provider_type) is not type:
        raise MarketplaceLocalhostBootstrapError("M17_2B_SERVER_PROVIDER_INVALID")
    try:
        provider = provider_type()
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_2B_SERVER_PROVIDER_INVALID") from None
    if type(provider) is not provider_type:
        raise MarketplaceLocalhostBootstrapError("M17_2B_SERVER_PROVIDER_INVALID")
    try:
        run = provider.run
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_2B_SERVER_PROVIDER_INVALID") from None
    if not callable(run):
        raise MarketplaceLocalhostBootstrapError("M17_2B_SERVER_PROVIDER_INVALID")
    return provider


def _validate_plan_before_initialize(plan: object) -> MarketplaceApplicationLaunchPlan:
    if type(plan) is not MarketplaceApplicationLaunchPlan:
        raise MarketplaceLocalhostBootstrapError("M17_2B_LAUNCH_PLAN_INVALID")
    if type(plan.composition) is not MarketplaceApplicationComposition:
        raise MarketplaceLocalhostBootstrapError("M17_2B_LAUNCH_PLAN_INVALID")
    if type(plan.asgi) is not MarketplaceAsgiHttpAdapter:
        raise MarketplaceLocalhostBootstrapError("M17_2B_LAUNCH_PLAN_INVALID")
    if plan.host != LOCALHOST_HOST or type(plan.port) is not int:
        raise MarketplaceLocalhostBootstrapError("M17_2B_LAUNCH_PLAN_INVALID")
    if plan.port < MIN_LOCALHOST_PORT or plan.port > MAX_LOCALHOST_PORT:
        raise MarketplaceLocalhostBootstrapError("M17_2B_LAUNCH_PLAN_INVALID")
    if plan.asgi._site is not plan.composition.site:
        raise MarketplaceLocalhostBootstrapError("M17_2B_LAUNCH_PLAN_INVALID")
    return plan


def _execute_localhost(port: int, execution_opt_in: object) -> None:
    validated_port = _validate_port(port)
    _validate_execution_opt_in(execution_opt_in)
    mvp_flight_runner = _load_mvp_flight_runner()

    getenv = _real_environment_getter()
    dsn = _read_postgres_dsn(getenv)
    asset_reader = _real_asset_reader()
    index_html, app_js, styles_css = _load_web_assets(asset_reader)
    connection_factory = _build_psycopg_connection_factory(dsn)

    try:
        plan = build_reference_postgres_marketplace_application_launch_plan(
            connection_factory=connection_factory,
            clock=_utc_clock,
            host=LOCALHOST_HOST,
            port=validated_port,
            run_mvp_flight=mvp_flight_runner,
            index_html=index_html,
            app_js=app_js,
            styles_css=styles_css,
        )
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_2B_COMPOSITION_FAILED") from None
    plan = _validate_plan_before_initialize(plan)

    provider = _real_uvicorn_provider()
    try:
        plan.composition.initialize()
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_2B_DATABASE_INITIALIZATION_FAILED") from None

    try:
        run_marketplace_application_foreground(
            plan=plan,
            provider=provider,
            execute_token=EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
        )
    except Exception:
        raise MarketplaceLocalhostBootstrapError("M17_2B_LOOPBACK_SERVER_FAILED") from None


def _execute_authenticated_localhost(
    port: int,
    execution_opt_in: object,
    provisioning_directory: object,
) -> None:
    validated_port = _validate_port(port)
    _validate_authenticated_execution_opt_in(execution_opt_in)
    directory = _validate_authentication_provisioning_directory(provisioning_directory)

    provisioning = _load_authentication_provisioning(directory)
    runtime_inputs = _compose_authentication_runtime_inputs()

    getenv = _real_environment_getter()
    dsn = _read_postgres_dsn(getenv)
    asset_reader = _real_asset_reader()
    index_html, app_js, styles_css = _load_web_assets(asset_reader)
    connection_factory = _build_psycopg_connection_factory(dsn)

    plan = _build_authenticated_postgres_plan(
        connection_factory=connection_factory,
        clock=_utc_clock,
        host=LOCALHOST_HOST,
        port=validated_port,
        index_html=index_html,
        app_js=app_js,
        styles_css=styles_css,
        provisioning=provisioning,
        runtime_inputs=runtime_inputs,
    )
    application = _validate_authenticated_plan_before_initialize(plan)
    provider = _real_uvicorn_provider()

    try:
        application.initialize()
    except Exception:
        raise MarketplaceLocalhostBootstrapError(
            "M17_5Y_DATABASE_INITIALIZATION_FAILED"
        ) from None

    _run_authenticated_foreground(plan=plan, provider=provider)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "HIGH-capability repo-only Marketplace localhost bootstrap. Dry-run performs no external I/O; "
            "live execution requires an exact mode-specific opt-in and separate runtime authorization."
        )
    )
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help=f"IPv4 loopback TCP port {MIN_LOCALHOST_PORT}..{MAX_LOCALHOST_PORT}",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="validate bounded localhost metadata only; no environment/filesystem/database/server access",
    )
    mode.add_argument(
        "--execute-localhost",
        metavar="TOKEN",
        help="TOKEN must equal the exact documented M17.2B localhost execution opt-in",
    )
    mode.add_argument(
        "--execute-authenticated-localhost",
        metavar="TOKEN",
        help="TOKEN must equal the exact documented M17.5Y authenticated localhost execution opt-in",
    )
    parser.add_argument(
        "--authentication-provisioning-directory",
        metavar="ABSOLUTE_DIRECTORY",
        help="explicit absolute local directory consumed only by the authenticated M17.5Y mode",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        port = _validate_port(args.port)
    except MarketplaceLocalhostBootstrapError as exc:
        print(exc.code, file=sys.stderr)
        return 2

    if (
        args.execute_authenticated_localhost is None
        and args.authentication_provisioning_directory is not None
    ):
        print("M17_5Y_PROVISIONING_DIRECTORY_MODE_INVALID", file=sys.stderr)
        return 2

    if args.dry_run:
        print(
            "M17_2B_DRY_RUN_READY "
            f"host={LOCALHOST_HOST} port={port} filesystem_invoked=false environment_invoked=false "
            "postgres_invoked=false server_invoked=false"
        )
        return 0

    if args.execute_authenticated_localhost is not None:
        try:
            _execute_authenticated_localhost(
                port,
                args.execute_authenticated_localhost,
                args.authentication_provisioning_directory,
            )
        except MarketplaceLocalhostBootstrapError as exc:
            print(exc.code, file=sys.stderr)
            preflight_codes = {
                "M17_2B_PORT_INVALID",
                "M17_5Y_EXECUTION_OPT_IN_REQUIRED",
                "M17_5Y_PROVISIONING_DIRECTORY_INVALID",
            }
            return 2 if exc.code in preflight_codes else 1
        print(
            "M17_5Y_AUTHENTICATED_LOCALHOST_FOREGROUND_COMPLETE "
            "public_exposure=false production_deployment=false android_runtime=false"
        )
        return 0

    try:
        _execute_localhost(port, args.execute_localhost)
    except MarketplaceLocalhostBootstrapError as exc:
        print(exc.code, file=sys.stderr)
        return 1 if exc.code not in {"M17_2B_EXECUTION_OPT_IN_REQUIRED", "M17_2B_PORT_INVALID"} else 2

    print(
        "M17_2B_LOCALHOST_FOREGROUND_COMPLETE "
        "public_exposure=false production_deployment=false android_runtime=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
