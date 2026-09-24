from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from marketplace.application.http import ApplicationHttpRequest, ApplicationHttpResponse
from marketplace.application.site_host import MarketplaceSiteHostAdapter
from marketplace.reference.auth_postgres_application_v1 import build_reference_authenticated_postgres_marketplace_launch_plan
import tools.marketplace_localhost as localhost

ROOT = Path(__file__).resolve().parents[1]
AUTH_MODULES = (
    ("/client_session.js", b"client-session"),
    ("/auth_establishment.js", b"auth-establishment"),
    ("/auth_ed25519_proof_provider.js", b"auth-proof"),
    ("/auth_ed25519_key_creation.js", b"auth-key-creation"),
    ("/agreement_ed25519_assent_provider.js", b"agreement-assent"),
    ("/agreement_assent_client.js", b"agreement-assent-client"),
    ("/auth_bootstrap.js", b"auth-bootstrap"),
)


class _Api:
    def __init__(self) -> None:
        self.calls: list[ApplicationHttpRequest] = []

    def handle(self, request: ApplicationHttpRequest) -> ApplicationHttpResponse:
        self.calls.append(request)
        return ApplicationHttpResponse(204, "No Content", (), b"")


def _host(*, modules=()) -> tuple[MarketplaceSiteHostAdapter, _Api]:
    api = _Api()
    return MarketplaceSiteHostAdapter(
        application_http=api,
        index_html=b"index",
        app_js=b"app",
        styles_css=b"css",
        web_modules=modules,
    ), api


class ProductAuthWebModuleDeliveryTests(unittest.TestCase):
    def test_default_site_does_not_expose_auth_modules(self) -> None:
        host, api = _host()
        for path, _ in AUTH_MODULES:
            response = host.handle(ApplicationHttpRequest("GET", path, (), None, b""))
            self.assertEqual(response.status_code, 404)
        self.assertEqual(api.calls, [])

    def test_explicit_modules_are_exact_same_origin_static_assets(self) -> None:
        host, api = _host(modules=AUTH_MODULES)
        for path, body in AUTH_MODULES:
            response = host.handle(ApplicationHttpRequest("GET", path, (), None, b""))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.body, body)
            self.assertIn(("Content-Type", "text/javascript; charset=utf-8"), response.headers)
        self.assertEqual(api.calls, [])

    def test_module_delivery_is_exact_allowlist_and_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            _host(modules=(("/not-reviewed.js", b"x"),))
        with self.assertRaises(ValueError):
            _host(modules=(("/client_session.js", b"a"), ("/client_session.js", b"b")))
        with self.assertRaises(TypeError):
            _host(modules=(("/client_session.js", "not-bytes"),))

    def test_authenticated_loader_reads_only_exact_reviewed_sources(self) -> None:
        reads: list[str] = []
        values = {relative: route.encode("ascii") for route, relative in localhost._AUTH_WEB_MODULE_ASSETS}
        def reader(path: str) -> bytes:
            reads.append(path)
            return values[path]
        modules = localhost._load_auth_web_modules(reader)
        self.assertEqual(reads, [relative for _, relative in localhost._AUTH_WEB_MODULE_ASSETS])
        self.assertEqual(modules, tuple((route, values[relative]) for route, relative in localhost._AUTH_WEB_MODULE_ASSETS))

    def test_normal_web_asset_loader_does_not_read_auth_modules(self) -> None:
        reads: list[str] = []
        values = {
            "web/index.html": b"index",
            "web/app.js": b"app",
            "web/styles.css": b"css",
        }
        def reader(path: str) -> bytes:
            reads.append(path)
            return values[path]
        self.assertEqual(localhost._load_web_assets(reader), (b"index", b"app", b"css"))
        self.assertEqual(reads, ["web/index.html", "web/app.js", "web/styles.css"])

    def test_active_page_selects_only_bootstrap_on_explicit_action(self) -> None:
        index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        bootstrap = (ROOT / "web" / "auth_bootstrap.js").read_text(encoding="utf-8")
        self.assertNotIn("auth_bootstrap.js", index)
        self.assertEqual(app.count('import("./auth_bootstrap.js")'), 1)
        lower_auth_modules = tuple(
            path for path, _ in AUTH_MODULES
            if path not in {
                "/auth_bootstrap.js",
                "/agreement_ed25519_assent_provider.js",
                "/agreement_assent_client.js",
            }
        )
        for path in lower_auth_modules:
            marker = path.removeprefix("/")
            self.assertNotIn(marker, index)
            self.assertNotIn(marker, app)
            self.assertIn(f'./{marker}', bootstrap)
        for assent_marker in (
            "agreement_ed25519_assent_provider.js",
            "agreement_assent_client.js",
        ):
            self.assertNotIn(assent_marker, index)
            self.assertNotIn(assent_marker, app)
            self.assertEqual(bootstrap.count(f'./{assent_marker}'), 1)

    def test_authenticated_reference_builder_forwards_nonempty_module_bundle_only(self) -> None:
        modules = AUTH_MODULES
        base_plan = object()
        auth_plan = object()
        with (
            patch("marketplace.reference.auth_postgres_application_v1.build_reference_postgres_marketplace_application_launch_plan", return_value=base_plan) as base,
            patch("marketplace.reference.auth_postgres_application_v1.build_reference_authenticated_marketplace_launch_plan", return_value=auth_plan),
        ):
            result = build_reference_authenticated_postgres_marketplace_launch_plan(
                connection_factory=Mock(), clock=Mock(), host="127.0.0.1", port=8443,
                index_html=b"index", app_js=b"app", styles_css=b"css",
                web_modules=modules, provisioning=Mock(), runtime_inputs=Mock(),
            )
        self.assertIs(result, auth_plan)
        self.assertEqual(base.call_args.kwargs["web_modules"], modules)


if __name__ == "__main__":
    unittest.main()
