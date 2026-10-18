"""Review-only Caddy Unix snippet must remain exact, inert, and offline."""
from __future__ import annotations

import contextlib
import io
import unittest
from unittest import mock

from marketplace.application.unix_listener import EXACT_FOREGROUND_OPT_IN
from marketplace.application.linux_unix_caddy_peer import MarketplaceLinuxUnixCaddyPeerVerifier
from tools.marketplace_caddy_unix_review_candidate import (
    CANONICAL_HOST,
    EXACT_RENDER_TOKEN,
    INERT_STATUS,
    INVALID_STATUS,
    REVIEW_UNIX_SOCKET_PATH,
    REVIEW_UNIX_UPSTREAM,
    main,
    render_caddy_unix_review_candidate,
)


class CaddyUnixReviewTests(unittest.TestCase):
    def output(self, *args):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = main(args)
        return rc, buffer.getvalue()

    def test_import_and_review_do_not_create_sockets_or_start_server(self):
        with mock.patch("socket.socket", side_effect=AssertionError("socket opened")), \
             mock.patch("subprocess.run", side_effect=AssertionError("command run")), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("command run")):
            self.assertIn(CANONICAL_HOST, render_caddy_unix_review_candidate())

    def test_default_is_inert_with_stable_status(self):
        rc, text = self.output()
        self.assertEqual((rc, text), (0, INERT_STATUS + "\n"))
        self.assertNotIn("reverse_proxy", text)

    def test_single_exact_opt_in_renders_review_only(self):
        rc, text = self.output("--render-candidate", EXACT_RENDER_TOKEN)
        self.assertEqual(rc, 0)
        self.assertEqual(text, render_caddy_unix_review_candidate())
        self.assertTrue(text.startswith("# REVIEW ONLY"))
        self.assertIn(CANONICAL_HOST + " {\n", text)

    def test_invalid_argv_redacted_and_never_renders(self):
        for args in (
            ("--render-candidate",),
            ("--render-candidate", EXACT_RENDER_TOKEN, "--socket-path", "/tmp/evil"),
            ("--render-candidate", EXACT_RENDER_TOKEN, "--host", "attacker.com"),
            ("--render-candidate", EXACT_RENDER_TOKEN.lower()),
            ("--render-candidate", EXACT_RENDER_TOKEN + "\nmalicious"),
            ("--render-candidate", EXACT_RENDER_TOKEN, "--upstream-port", "24081"),
            ("--render-candidate", "RENDER_REVIEW_ONLY_MARKETPLACE_CADDY_CANDIDATE_V1"),
            ("--proxy", "127.0.0.1:80"),
        ):
            with self.subTest(args=args):
                rc, text = self.output(*args)
                self.assertEqual((rc, text), (2, INVALID_STATUS + "\n"))
                self.assertNotIn("attacker.com", text)
                self.assertNotIn("/tmp/evil", text)

    def test_single_vhost_exact_socket_and_no_tcp_fallback(self):
        text = render_caddy_unix_review_candidate()
        self.assertEqual(text.count("reverse_proxy "), 1)
        self.assertIn("reverse_proxy " + REVIEW_UNIX_UPSTREAM, text)
        self.assertEqual(text.count(CANONICAL_HOST), 2)
        self.assertIn("header_up Host " + CANONICAL_HOST + "\\n", text)
        self.assertNotIn("127.0.0.1:", text)
        self.assertNotIn("localhost:", text)
        self.assertNotIn("http://", text)
        self.assertNotIn("https://", text)
        self.assertNotIn("tls internal", text)
        self.assertNotIn("tls_insecure_skip_verify", text)
        self.assertNotIn("0.0.0.0", text)

    def test_socket_path_matches_reviewer_contract(self):
        self.assertEqual(
            REVIEW_UNIX_SOCKET_PATH,
            "/run/moon-marketplace/marketplace-edge.sock",
        )
        self.assertEqual(REVIEW_UNIX_UPSTREAM, "unix/" + REVIEW_UNIX_SOCKET_PATH)
        self.assertTrue(REVIEW_UNIX_SOCKET_PATH.endswith("/marketplace-edge.sock"))
        self.assertEqual(EXACT_FOREGROUND_OPT_IN,
                         "EXECUTE_BOUNDED_MARKETPLACE_UNIX_EDGE_FOREGROUND_V1")

    def test_caddy_upstream_uses_only_http11_with_no_keepalive(self):
        text = render_caddy_unix_review_candidate()
        self.assertIn("transport http {\n", text)
        self.assertIn("versions 1.1\n", text)
        self.assertIn("keepalive off\n", text)
        self.assertIn("compression off\n", text)
        self.assertNotIn("versions 2", text)
        self.assertNotIn("h2c", text)
        self.assertNotIn("proxy_protocol", text)
        self.assertNotIn("trusted_proxies", text)

    def test_default_caddy_forwarded_headers_are_not_removed(self):
        text = render_caddy_unix_review_candidate()
        for name in ("X-Forwarded-Proto", "X-Forwarded-Host", "X-Forwarded-For"):
            self.assertNotIn("header_up -" + name, text)
        for name in (
            "Forwarded", "X-Real-IP", "X-Original-*", "X-Rewrite-URL",
            "X-Scheme", "X-Forwarded-Port", "X-Forwarded-Prefix",
            "X-Forwarded-Scheme", "X-Forwarded-Server",
        ):
            self.assertIn("header_up -" + name, text)

    def test_exact_review_snippet_balances_braces(self):
        text = render_caddy_unix_review_candidate()
        self.assertEqual(text.count("{"), text.count("}"))
        self.assertEqual(text.count("transport http {"), 1)
        self.assertEqual(text.count("reverse_proxy"), 1)

    def test_source_does_not_supply_peer_identity(self):
        text = render_caddy_unix_review_candidate()
        self.assertNotIn("caddy_uid", text)
        self.assertNotIn("caddy_gid", text)
        self.assertNotIn("setuid", text)
        self.assertNotIn("sudo", text)
        self.assertNotIn("systemctl", text)

    def test_render_is_deterministic_and_nondestructive(self):
        with mock.patch("builtins.open", side_effect=AssertionError("file opened")), \
             mock.patch("os.unlink", side_effect=AssertionError("file deleted")), \
             mock.patch("os.chmod", side_effect=AssertionError("chmod attempted")):
            self.assertEqual(render_caddy_unix_review_candidate(),
                             render_caddy_unix_review_candidate())


if __name__ == "__main__":
    unittest.main()
