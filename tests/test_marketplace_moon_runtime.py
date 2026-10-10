from __future__ import annotations

import asyncio
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from marketplace.application.moon_runtime import (
    MarketplaceMoonHeartbeatLease,
    MarketplaceMoonHeartbeatServerProvider,
    marketplace_moon_heartbeat_from_env,
    wrap_marketplace_server_provider_from_env,
)


class _FakeLease:
    def __init__(self) -> None:
        self.events: list[str] = []

    def ensure_started(self) -> None:
        self.events.append("started")

    def close(self) -> None:
        self.events.append("closed")


class _RequestingProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str, int]] = []

    def run(self, *, application: object, host: str, port: int) -> None:
        self.calls.append((application, host, port))

        async def exercise() -> None:
            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(_message):
                return None

            await application(  # type: ignore[operator]
                {"type": "http", "method": "GET", "path": "/"},
                receive,
                send,
            )

        asyncio.run(exercise())




class _LifespanOnlyProvider:
    def run(self, *, application: object, host: str, port: int) -> None:
        del host, port

        async def exercise() -> None:
            received = False

            async def receive():
                nonlocal received
                if received:
                    return {"type": "lifespan.shutdown"}
                received = True
                return {"type": "lifespan.startup"}

            async def send(_message):
                return None

            await application(  # type: ignore[operator]
                {"type": "lifespan"},
                receive,
                send,
            )

        asyncio.run(exercise())


class _FailBeforeRequestProvider:
    def run(self, *, application: object, host: str, port: int) -> None:
        del application, host, port
        raise RuntimeError("synthetic bind failure")


async def _asgi_application(scope, receive, send) -> None:
    del scope, receive
    await send({"type": "http.response.start", "status": 204, "headers": []})
    await send({"type": "http.response.body", "body": b""})


def _http_response_application(
    *, status: int, final_body: bool = True, raise_after: bool = False,
):
    async def application(scope, receive, send) -> None:
        del scope, receive
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({
            "type": "http.response.body",
            "body": b"",
            "more_body": not final_body,
        })
        if raise_after:
            raise RuntimeError("synthetic application failure")

    return application


class _SendFailureProvider:
    def run(self, *, application: object, host: str, port: int) -> None:
        del host, port

        async def exercise() -> None:
            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def reject_send(_message):
                raise RuntimeError("synthetic transport failure")

            await application(  # type: ignore[operator]
                {"type": "http", "method": "GET", "path": "/"},
                receive,
                reject_send,
            )

        asyncio.run(exercise())


class MarketplaceMoonRuntimeTests(unittest.TestCase):
    def test_heartbeat_is_opt_in_and_rejects_ambiguous_configuration(self) -> None:
        self.assertIsNone(marketplace_moon_heartbeat_from_env({}))
        self.assertIsNone(
            marketplace_moon_heartbeat_from_env(
                {"MARKETPLACE_MOON_HEARTBEAT_ENABLED": "0"}
            )
        )
        with self.assertRaisesRegex(ValueError, "must be 0 or 1"):
            marketplace_moon_heartbeat_from_env(
                {"MARKETPLACE_MOON_HEARTBEAT_ENABLED": "yes"}
            )
        with self.assertRaisesRegex(ValueError, "must be absolute"):
            marketplace_moon_heartbeat_from_env(
                {
                    "MARKETPLACE_MOON_HEARTBEAT_ENABLED": "1",
                    "MARKETPLACE_MOON_STATE_ROOT": "relative/state",
                }
            )

    def test_heartbeat_is_lazy_bounded_and_removed_on_close(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            lease = MarketplaceMoonHeartbeatLease(
                state_root=root,
                version="release-test",
                environment="test",
                interval_seconds=60,
                process_id=4242,
            )
            self.assertFalse(lease.path.exists())

            lease.ensure_started()
            self.assertTrue(lease.path.exists())
            payload = json.loads(lease.path.read_text(encoding="utf-8"))
            self.assertEqual(
                set(payload),
                {
                    "moon_version",
                    "service_id",
                    "version",
                    "environment",
                    "instance_id",
                    "process_id",
                    "started_at",
                    "observed_at",
                },
            )
            self.assertEqual(payload["service_id"], "hello-world-marketplace")
            self.assertEqual(payload["version"], "release-test")
            self.assertEqual(payload["environment"], "test")
            self.assertEqual(payload["process_id"], 4242)
            self.assertLess(lease.path.stat().st_size, 4096)

            lease.close()
            self.assertFalse(lease.path.exists())

    def test_write_failure_is_observability_only(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            lease = MarketplaceMoonHeartbeatLease(
                state_root=Path(directory),
                interval_seconds=60,
                process_id=4242,
            )
            with patch(
                "marketplace.application.moon_runtime._write_heartbeat",
                side_effect=OSError("synthetic write failure"),
            ):
                lease.ensure_started()
                lease.close()

    def test_provider_starts_heartbeat_only_after_first_real_asgi_request(self) -> None:
        lease = _FakeLease()
        delegate = _RequestingProvider()
        provider = MarketplaceMoonHeartbeatServerProvider(delegate, lease)  # type: ignore[arg-type]

        provider.run(application=_asgi_application, host="127.0.0.1", port=18080)

        self.assertEqual(lease.events, ["started", "closed"])
        self.assertEqual(len(delegate.calls), 1)

    def test_heartbeat_requires_completed_non_5xx_http_response(self) -> None:
        for status, admitted in ((200, True), (204, True), (404, True),
                                 (499, True), (500, False), (503, False)):
            with self.subTest(status=status):
                lease = _FakeLease()
                provider = MarketplaceMoonHeartbeatServerProvider(
                    _RequestingProvider(),
                    lease,  # type: ignore[arg-type]
                )
                provider.run(
                    application=_http_response_application(status=status),
                    host="127.0.0.1",
                    port=18080,
                )
                self.assertEqual(
                    lease.events,
                    ["started", "closed"] if admitted else ["closed"],
                )

    def test_incomplete_http_stream_does_not_admit_heartbeat(self) -> None:
        lease = _FakeLease()
        provider = MarketplaceMoonHeartbeatServerProvider(
            _RequestingProvider(), lease,  # type: ignore[arg-type]
        )
        provider.run(
            application=_http_response_application(status=200, final_body=False),
            host="127.0.0.1", port=18080,
        )
        self.assertEqual(lease.events, ["closed"])

    def test_app_failure_after_final_body_does_not_admit_heartbeat(self) -> None:
        lease = _FakeLease()
        provider = MarketplaceMoonHeartbeatServerProvider(
            _RequestingProvider(), lease,  # type: ignore[arg-type]
        )
        with self.assertRaisesRegex(RuntimeError, "synthetic application failure"):
            provider.run(
                application=_http_response_application(status=200, raise_after=True),
                host="127.0.0.1", port=18080,
            )
        self.assertEqual(lease.events, ["closed"])

    def test_failed_asgi_send_does_not_admit_heartbeat(self) -> None:
        lease = _FakeLease()
        provider = MarketplaceMoonHeartbeatServerProvider(
            _SendFailureProvider(), lease,  # type: ignore[arg-type]
        )
        with self.assertRaisesRegex(RuntimeError, "synthetic transport failure"):
            provider.run(
                application=_http_response_application(status=200),
                host="127.0.0.1", port=18080,
            )
        self.assertEqual(lease.events, ["closed"])

    def test_lifespan_scope_does_not_admit_runtime_health(self) -> None:
        lease = _FakeLease()
        provider = MarketplaceMoonHeartbeatServerProvider(
            _LifespanOnlyProvider(),
            lease,  # type: ignore[arg-type]
        )

        provider.run(application=_asgi_application, host="127.0.0.1", port=18080)

        self.assertEqual(lease.events, ["closed"])

    def test_provider_bind_failure_never_starts_heartbeat(self) -> None:
        lease = _FakeLease()
        provider = MarketplaceMoonHeartbeatServerProvider(
            _FailBeforeRequestProvider(),
            lease,  # type: ignore[arg-type]
        )

        with self.assertRaisesRegex(RuntimeError, "synthetic bind failure"):
            provider.run(application=_asgi_application, host="127.0.0.1", port=18080)

        self.assertEqual(lease.events, ["closed"])

    def test_disabled_wrapper_preserves_provider_identity(self) -> None:
        provider = _RequestingProvider()
        wrapped = wrap_marketplace_server_provider_from_env(provider, {})
        self.assertIs(wrapped, provider)


if __name__ == "__main__":
    unittest.main()
