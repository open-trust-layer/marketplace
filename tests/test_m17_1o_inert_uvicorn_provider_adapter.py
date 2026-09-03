from __future__ import annotations

from pathlib import Path
import tomllib
import unittest
from unittest.mock import patch

from marketplace.application.uvicorn_provider import (
    UVICORN_DISTRIBUTION,
    UVICORN_VERSION,
    UvicornLoopbackServerProvider,
)


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
SOURCE = ROOT / "src" / "marketplace" / "application" / "uvicorn_provider.py"


class FakeUvicornModule:
    def __init__(self, *, failure: BaseException | None = None) -> None:
        self.failure = failure
        self.calls: list[tuple[object, dict[str, object]]] = []

    def run(self, application: object, **kwargs: object) -> None:
        self.calls.append((application, kwargs))
        if self.failure is not None:
            raise self.failure


async def fake_asgi(scope, receive, send):
    raise AssertionError("fake ASGI application must never execute in unit tests")


class M17InertUvicornProviderAdapterTests(unittest.TestCase):
    def test_optional_dependency_is_exact_minimal_uvicorn_pin(self):
        parsed = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        project = parsed["project"]
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(
            project["optional-dependencies"]["local-server"],
            ["uvicorn==0.52.4"],
        )
        self.assertNotIn("uvicorn[standard]", PYPROJECT.read_text(encoding="utf-8").lower())
        self.assertEqual(UVICORN_DISTRIBUTION, "uvicorn")
        self.assertEqual(UVICORN_VERSION, "0.52.4")

    def test_provider_import_is_lazy_and_delegates_once_with_locked_surface(self):
        fake = FakeUvicornModule()
        provider = UvicornLoopbackServerProvider()

        with patch("marketplace.application.uvicorn_provider.import_module", return_value=fake) as loader:
            provider.run(application=fake_asgi, host="127.0.0.1", port=8080)

        loader.assert_called_once_with("uvicorn")
        self.assertEqual(len(fake.calls), 1)
        application, kwargs = fake.calls[0]
        self.assertIs(application, fake_asgi)
        self.assertEqual(
            kwargs,
            {
                "host": "127.0.0.1",
                "port": 8080,
                "uds": None,
                "fd": None,
                "loop": "asyncio",
                "http": "h11",
                "ws": "none",
                "lifespan": "off",
                "interface": "asgi3",
                "reload": False,
                "workers": 1,
                "env_file": None,
                "log_config": None,
                "log_level": "warning",
                "access_log": False,
                "proxy_headers": False,
                "server_header": False,
                "date_header": False,
                "forwarded_allow_ips": "",
                "root_path": "",
                "limit_concurrency": 32,
                "backlog": 64,
                "timeout_keep_alive": 5,
                "ssl_keyfile": None,
                "ssl_certfile": None,
                "ssl_keyfile_password": None,
                "ssl_ca_certs": None,
                "headers": [],
                "app_dir": None,
                "factory": False,
            },
        )

    def test_invalid_host_port_and_application_fail_before_uvicorn_import(self):
        provider = UvicornLoopbackServerProvider()
        cases = (
            {"application": fake_asgi, "host": "0.0.0.0", "port": 8080},
            {"application": fake_asgi, "host": "localhost", "port": 8080},
            {"application": fake_asgi, "host": b"127.0.0.1", "port": 8080},
            {"application": fake_asgi, "host": "127.0.0.1", "port": True},
            {"application": fake_asgi, "host": "127.0.0.1", "port": 0},
            {"application": fake_asgi, "host": "127.0.0.1", "port": 65536},
            {"application": object(), "host": "127.0.0.1", "port": 8080},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with patch("marketplace.application.uvicorn_provider.import_module") as loader:
                    with self.assertRaises((TypeError, ValueError)):
                        provider.run(**kwargs)
                    loader.assert_not_called()

    def test_missing_or_malformed_uvicorn_fails_without_reflecting_loader_detail(self):
        provider = UvicornLoopbackServerProvider()

        with patch(
            "marketplace.application.uvicorn_provider.import_module",
            side_effect=ImportError("private import detail"),
        ):
            with self.assertRaises(RuntimeError) as caught:
                provider.run(application=fake_asgi, host="127.0.0.1", port=8080)
        self.assertEqual(str(caught.exception), "MARKETPLACE_UVICORN_PROVIDER_UNAVAILABLE")
        self.assertNotIn("private", str(caught.exception))

        malformed = object()
        with patch("marketplace.application.uvicorn_provider.import_module", return_value=malformed):
            with self.assertRaises(RuntimeError) as caught:
                provider.run(application=fake_asgi, host="127.0.0.1", port=8080)
        self.assertEqual(str(caught.exception), "MARKETPLACE_UVICORN_PROVIDER_UNAVAILABLE")

    def test_uvicorn_failure_is_stable_and_not_retried(self):
        fake = FakeUvicornModule(failure=RuntimeError("provider secret detail"))
        provider = UvicornLoopbackServerProvider()
        with patch("marketplace.application.uvicorn_provider.import_module", return_value=fake):
            with self.assertRaises(RuntimeError) as caught:
                provider.run(application=fake_asgi, host="127.0.0.1", port=8080)
        self.assertEqual(str(caught.exception), "MARKETPLACE_UVICORN_PROVIDER_FAILED")
        self.assertEqual(len(fake.calls), 1)
        self.assertNotIn("secret", str(caught.exception))

    def test_source_contains_no_activation_or_unbounded_option_surface(self):
        source = SOURCE.read_text(encoding="utf-8")
        forbidden = (
            "subprocess",
            "socket.",
            "os.environ",
            "uvicorn[standard]",
            "**options",
            "reload=True",
            "proxy_headers=True",
            "workers=None",
        )
        for fragment in forbidden:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
