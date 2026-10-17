"""Offline security tests for the exact-target HTTPS/SNI preflight."""
from __future__ import annotations

import socket
import ssl
import unittest
from unittest.mock import MagicMock, patch

from tools import marketplace_canonical_https_preflight as probe


def public_dns(address: str = "168.113.210.63"):
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, 443))]


def fake_dependencies():
    sock = MagicMock()
    sock.__enter__.return_value = sock
    tls = MagicMock()
    tls.__enter__.return_value = tls
    ctx = MagicMock()
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.wrap_socket.return_value = tls
    return sock, ctx


class CanonicalHttpsSniPreflightTests(unittest.TestCase):
    def test_inert_default_does_not_resolve_or_connect(self) -> None:
        with patch.object(probe, "probe_canonical_https_tls", side_effect=AssertionError("network")):
            with patch("builtins.print") as printer:
                self.assertEqual(probe.main([]), 0)
                printer.assert_called_once_with(probe.INERT_STATUS)

    def test_invalid_opt_in_does_not_reflect_or_probe(self) -> None:
        bad = (
            ("--probe-canonical-https", "secret-session-text"),
            ("--probe-canonical-https", probe.EXACT_PROBE_OPT_IN, "--hostname", "localhost"),
            ("--probe-canonical-https", probe.EXACT_PROBE_OPT_IN, "--port", "5432"),
            ("--probe-canonical-https", probe.EXACT_PROBE_OPT_IN + "\n"),
            ("--help",),
        )
        with patch.object(probe, "probe_canonical_https_tls", side_effect=AssertionError("network")):
            for args in bad:
                with self.subTest(args=args), patch("builtins.print") as printer:
                    self.assertEqual(probe.main(args), 2)
                    printer.assert_called_once_with(probe.INVALID_OPT_IN)

    def test_validated_origin_uses_exact_sni_and_numeric_public_ipv4(self) -> None:
        sock, ctx = fake_dependencies()
        resolver = MagicMock(return_value=public_dns())
        factory = MagicMock(return_value=sock)
        context_factory = MagicMock(return_value=ctx)
        result = probe.probe_canonical_https_tls(
            resolver=resolver, socket_factory=factory, context_factory=context_factory,
        )
        self.assertEqual(result, probe.SUCCESS_STATUS)
        resolver.assert_called_once_with(
            probe.CANONICAL_HOST, 443, socket.AF_INET,
            socket.SOCK_STREAM, socket.IPPROTO_TCP,
        )
        factory.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        sock.settimeout.assert_called_once_with(5.0)
        sock.connect.assert_called_once_with(("168.113.210.63", 443))
        ctx.wrap_socket.assert_called_once_with(sock, server_hostname=probe.CANONICAL_HOST)

    def test_rejects_private_dns_and_bad_resolutions_before_socket(self) -> None:
        bad = (
            public_dns("127.0.0.1"), public_dns("10.1.2.3"),
            public_dns("192.168.1.1"), public_dns("169.254.1.1"),
            public_dns("0.0.0.0"), public_dns("255.255.255.255"),
            public_dns("999.1.2.3"), public_dns("1.1.1.1") + public_dns("127.0.0.1"),
            public_dns("1.1.1.1") * 9,
            [(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("::1", 443, 0, 0))],
            [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("1.1.1.1", 80))],
            [], "not-a-list",
        )
        _, ctx = fake_dependencies()
        for dns in bad:
            with self.subTest(dns=dns):
                factory = MagicMock(side_effect=AssertionError("unsafe socket"))
                result = probe.probe_canonical_https_tls(
                    resolver=lambda *_args: dns,
                    socket_factory=factory,
                    context_factory=lambda _purpose: ctx,
                )
                self.assertIn(result, {
                    "status=BLOCKED_DNS_UNSAFE", "status=BLOCKED_DNS_UNAVAILABLE",
                })
                factory.assert_not_called()

    def test_broken_certificate_or_tls_does_not_claim_health(self) -> None:
        cases = (
            (ssl.SSLCertVerificationError("super-secret-cert-path"), "status=BLOCKED_TLS_CERTIFICATE"),
            (ssl.SSLError("very-secret-certificate-details"), "status=BLOCKED_TLS_HANDSHAKE"),
            (TimeoutError("sensitive timeout"), "status=BLOCKED_TLS_TIMEOUT"),
            (ConnectionRefusedError("secret transport"), "status=BLOCKED_TLS_TRANSPORT"),
        )
        for exception, expected in cases:
            with self.subTest(expected=expected):
                sock, ctx = fake_dependencies()
                if isinstance(exception, ConnectionRefusedError):
                    sock.connect.side_effect = exception
                else:
                    ctx.wrap_socket.side_effect = exception
                result = probe.probe_canonical_https_tls(
                    resolver=lambda *_: public_dns(),
                    socket_factory=lambda *_: sock,
                    context_factory=lambda _: ctx,
                )
                self.assertEqual(result, expected)
                self.assertNotIn("secret", result)

    def test_unsafe_ssl_configuration_never_opens_socket(self) -> None:
        for changes in (
            {"check_hostname": False},
            {"verify_mode": ssl.CERT_NONE},
            {"minimum_version": ssl.TLSVersion.TLSv1_1},
        ):
            with self.subTest(changes=changes):
                _, ctx = fake_dependencies()
                for key, value in changes.items():
                    setattr(ctx, key, value)
                sock_factory = MagicMock(side_effect=AssertionError("network"))
                result = probe.probe_canonical_https_tls(
                    resolver=MagicMock(side_effect=AssertionError("DNS")),
                    socket_factory=sock_factory,
                    context_factory=lambda _: ctx,
                )
                self.assertEqual(result, "status=BLOCKED_TLS_CONFIGURATION")
                sock_factory.assert_not_called()

    def test_dns_resolution_errors_are_redacted(self) -> None:
        _, ctx = fake_dependencies()
        value = probe.probe_canonical_https_tls(
            resolver=MagicMock(side_effect=socket.gaierror("private-internal-dns")),
            socket_factory=MagicMock(side_effect=AssertionError("network")),
            context_factory=lambda _: ctx,
        )
        self.assertEqual(value, "status=BLOCKED_DNS_UNAVAILABLE")

    def test_manual_opt_in_returns_stable_exit_codes(self) -> None:
        with patch.object(probe, "probe_canonical_https_tls", return_value=probe.SUCCESS_STATUS):
            with patch("builtins.print") as printer:
                code = probe.main(["--probe-canonical-https", probe.EXACT_PROBE_OPT_IN])
                self.assertEqual(code, 0)
                printer.assert_called_once_with(probe.SUCCESS_STATUS)
        with patch.object(probe, "probe_canonical_https_tls", return_value="status=BLOCKED_TLS_HANDSHAKE"):
            with patch("builtins.print") as printer:
                code = probe.main(["--probe-canonical-https", probe.EXACT_PROBE_OPT_IN])
                self.assertEqual(code, 3)
                printer.assert_called_once_with("status=BLOCKED_TLS_HANDSHAKE")


if __name__ == "__main__":
    unittest.main()
