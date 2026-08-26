from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from marketplace.runtime.network_policy import (
    FederationEgressPolicy,
    FederationEndpointAuthorization,
    FederationNetworkPolicyError,
    authorize_federation_endpoint,
    canonicalize_federation_endpoint,
    validate_endpoint_authorization,
    validate_resolved_addresses,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("src/marketplace/runtime/network_policy.py")


class FederationNetworkPolicyTests(unittest.TestCase):
    def policy(self, **changes) -> FederationEgressPolicy:
        values = {
            "policy_id": "https://open-trust-layer.github.io/marketplace/policy/egress-v1",
            "policy_version": 1,
            "allowed_hosts": ("federation.example.com",),
        }
        values.update(changes)
        return FederationEgressPolicy(**values)

    def authorization(self, **changes) -> FederationEndpointAuthorization:
        values = {
            "endpoint": "https://federation.example.com/federation/v1",
            "allowed_operations": (
                "https://open-trust-layer.github.io/marketplace/semantics/v1/federation/operation/snapshot-v1",
                "https://open-trust-layer.github.io/marketplace/semantics/v1/federation/operation/sync-v1",
            ),
            "authorization_id": "egress-auth-001",
            "issued_at_epoch": 1_000,
            "expires_at_epoch": 1_120,
            "policy": self.policy(),
        }
        values.update(changes)
        return authorize_federation_endpoint(**values)

    def assert_policy_error(self, code: str, function, *args, **kwargs) -> FederationNetworkPolicyError:
        with self.assertRaises(FederationNetworkPolicyError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_https_endpoint_is_canonicalized_and_exactly_allowlisted(self):
        endpoint = canonicalize_federation_endpoint(
            "HTTPS://FEDERATION.EXAMPLE.COM:443/federation/v1",
            self.policy(),
        )
        self.assertEqual(endpoint.url, "https://federation.example.com/federation/v1")
        self.assertEqual(endpoint.hostname, "federation.example.com")
        self.assertEqual(endpoint.port, 443)
        self.assertEqual(endpoint.path, "/federation/v1")

    def test_nondefault_port_requires_explicit_policy(self):
        self.assert_policy_error(
            "PORT_NOT_ALLOWLISTED",
            canonicalize_federation_endpoint,
            "https://federation.example.com:8443/federation/v1",
            self.policy(),
        )
        endpoint = canonicalize_federation_endpoint(
            "https://federation.example.com:8443/federation/v1",
            self.policy(allowed_ports=(443, 8443)),
        )
        self.assertEqual(endpoint.url, "https://federation.example.com:8443/federation/v1")

    def test_endpoint_rejects_scheme_userinfo_query_fragment_and_unallowlisted_host(self):
        cases = (
            ("HTTPS_REQUIRED", "http://federation.example.com/federation/v1"),
            ("USERINFO_FORBIDDEN", "https://token@federation.example.com/federation/v1"),
            ("QUERY_FORBIDDEN", "https://federation.example.com/federation/v1?token=x"),
            ("FRAGMENT_FORBIDDEN", "https://federation.example.com/federation/v1#fragment"),
            ("HOST_NOT_ALLOWLISTED", "https://attacker.example.com/federation/v1"),
        )
        for code, endpoint in cases:
            with self.subTest(endpoint=endpoint):
                self.assert_policy_error(code, canonicalize_federation_endpoint, endpoint, self.policy())

    def test_host_allowlist_cannot_be_bypassed_by_trailing_dot_encoding_unicode_or_ip_literal(self):
        cases = (
            ("AMBIGUOUS_HOSTNAME", "https://federation.example.com./federation/v1"),
            ("AMBIGUOUS_HOSTNAME", "https://federation%2eexample.com/federation/v1"),
            ("NON_ASCII_TEXT", "https://federatiön.example.com/federation/v1"),
            ("IP_LITERAL_FORBIDDEN", "https://127.0.0.1/federation/v1"),
            ("IP_LITERAL_FORBIDDEN", "https://[::1]/federation/v1"),
        )
        for code, endpoint in cases:
            with self.subTest(endpoint=endpoint):
                policy = self.policy(allowed_hosts=("federation.example.com",))
                self.assert_policy_error(code, canonicalize_federation_endpoint, endpoint, policy)

    def test_allowlist_itself_must_be_canonical_and_cannot_use_idna(self):
        with self.assertRaises(FederationNetworkPolicyError) as uppercase:
            self.policy(allowed_hosts=("Federation.example.com",))
        self.assertEqual(uppercase.exception.code, "NONCANONICAL_ALLOWLIST_HOST")
        with self.assertRaises(FederationNetworkPolicyError) as idna:
            self.policy(allowed_hosts=("xn--e1afmkfd.example",))
        self.assertEqual(idna.exception.code, "IDNA_HOST_FORBIDDEN")
        with self.assertRaises(ValueError):
            self.policy(allowed_hosts=("z.example.com", "a.example.com"))

    def test_path_is_ascii_bounded_and_rejects_traversal_or_ambiguous_encodings(self):
        cases = (
            ("PATH_TRAVERSAL", "https://federation.example.com/a/../b"),
            ("AMBIGUOUS_PATH", "https://federation.example.com/a/%2e%2e/b"),
            ("AMBIGUOUS_PATH", "https://federation.example.com/a//b"),
            ("NON_ASCII_TEXT", "https://federation.example.com/féd"),
        )
        for code, endpoint in cases:
            with self.subTest(endpoint=endpoint):
                self.assert_policy_error(code, canonicalize_federation_endpoint, endpoint, self.policy())

    def test_authorization_binds_endpoint_operations_policy_and_short_validity_window(self):
        authorization = self.authorization()
        self.assertEqual(authorization.path_mode, "EXACT")
        self.assertEqual(authorization.policy_version, 1)
        self.assertFalse(authorization.establishes_marketplace_authorization)
        self.assertFalse(authorization.establishes_agreement)
        self.assertFalse(authorization.establishes_trust)
        endpoint = validate_endpoint_authorization(
            authorization,
            endpoint="https://FEDERATION.EXAMPLE.COM/federation/v1",
            operation=authorization.allowed_operations[0],
            now_epoch=1_050,
            policy=self.policy(),
        )
        self.assertEqual(endpoint.url, authorization.canonical_endpoint)

    def test_authorization_rejects_wrong_endpoint_operation_policy_and_authority_escalation(self):
        authorization = self.authorization()
        self.assert_policy_error(
            "AUTHORIZATION_ENDPOINT_MISMATCH",
            validate_endpoint_authorization,
            authorization,
            endpoint="https://federation.example.com/other",
            operation=authorization.allowed_operations[0],
            now_epoch=1_050,
            policy=self.policy(),
        )
        self.assert_policy_error(
            "OPERATION_NOT_AUTHORIZED",
            validate_endpoint_authorization,
            authorization,
            endpoint=authorization.canonical_endpoint,
            operation="https://example.com/unapproved-operation",
            now_epoch=1_050,
            policy=self.policy(),
        )
        self.assert_policy_error(
            "AUTHORIZATION_POLICY_MISMATCH",
            validate_endpoint_authorization,
            authorization,
            endpoint=authorization.canonical_endpoint,
            operation=authorization.allowed_operations[0],
            now_epoch=1_050,
            policy=self.policy(policy_version=2),
        )
        escalated = replace(authorization, establishes_marketplace_authorization=True)
        self.assert_policy_error(
            "AUTHORIZATION_AUTHORITY_ESCALATION",
            validate_endpoint_authorization,
            escalated,
            endpoint=authorization.canonical_endpoint,
            operation=authorization.allowed_operations[0],
            now_epoch=1_050,
            policy=self.policy(),
        )

    def test_authorization_fails_closed_before_issuance_at_expiry_and_when_window_is_too_long(self):
        authorization = self.authorization()
        self.assert_policy_error(
            "AUTHORIZATION_NOT_YET_VALID",
            validate_endpoint_authorization,
            authorization,
            endpoint=authorization.canonical_endpoint,
            operation=authorization.allowed_operations[0],
            now_epoch=999,
            policy=self.policy(),
        )
        self.assert_policy_error(
            "AUTHORIZATION_EXPIRED",
            validate_endpoint_authorization,
            authorization,
            endpoint=authorization.canonical_endpoint,
            operation=authorization.allowed_operations[0],
            now_epoch=1_120,
            policy=self.policy(),
        )
        self.assert_policy_error(
            "AUTHORIZATION_WINDOW_TOO_LONG",
            authorize_federation_endpoint,
            endpoint=authorization.canonical_endpoint,
            allowed_operations=authorization.allowed_operations,
            authorization_id="too-long",
            issued_at_epoch=1_000,
            expires_at_epoch=1_301,
            policy=self.policy(),
        )

    def test_global_unicast_ipv4_and_ipv6_resolver_results_are_canonicalized(self):
        result = validate_resolved_addresses(
            "FEDERATION.EXAMPLE.COM",
            ("2606:4700:4700::1111", "1.1.1.1", "1.1.1.1"),
        )
        self.assertEqual(result.hostname, "federation.example.com")
        self.assertEqual(result.addresses, ("1.1.1.1", "2606:4700:4700::1111"))
        self.assertFalse(result.dns_was_performed)
        self.assertFalse(result.safe_forever)

    def test_private_loopback_linklocal_multicast_unspecified_and_reserved_addresses_fail_closed(self):
        unsafe = (
            "127.0.0.1",
            "10.0.0.1",
            "169.254.169.254",
            "0.0.0.0",
            "224.0.0.1",
            "240.0.0.1",
            "::1",
            "fc00::1",
            "fe80::1",
            "::",
            "ff02::1",
            "2001:db8::1",
        )
        for address in unsafe:
            with self.subTest(address=address):
                self.assert_policy_error(
                    "UNSAFE_RESOLVED_ADDRESS",
                    validate_resolved_addresses,
                    "federation.example.com",
                    (address,),
                )

    def test_ipv4_mapped_ipv6_cannot_bypass_ipv4_policy(self):
        self.assert_policy_error(
            "IPV4_MAPPED_IPV6_FORBIDDEN",
            validate_resolved_addresses,
            "federation.example.com",
            ("::ffff:127.0.0.1",),
        )

    def test_resolver_results_are_bounded_without_exhausting_untrusted_iterable(self):
        consumed: list[int] = []

        def values():
            for index in range(10):
                consumed.append(index)
                yield "1.1.1.1"

        self.assert_policy_error(
            "RESOLVED_ADDRESS_LIMIT_EXCEEDED",
            validate_resolved_addresses,
            "federation.example.com",
            values(),
            max_addresses=2,
        )
        self.assertEqual(consumed, [0, 1, 2])

    def test_m25_module_has_no_dns_network_tls_process_environment_or_credential_access(self):
        source = (REPO_ROOT / TARGET).read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=str(TARGET))
        forbidden_modules = {
            "aiohttp",
            "ftplib",
            "http.client",
            "httpx",
            "netrc",
            "os",
            "requests",
            "smtplib",
            "socket",
            "ssl",
            "subprocess",
            "urllib.request",
            "websockets",
        }
        found: set[str] = set()
        dynamic_calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_modules or any(alias.name.startswith(name + ".") for name in forbidden_modules):
                        found.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module in forbidden_modules or any(node.module.startswith(name + ".") for name in forbidden_modules):
                    found.add(node.module)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"__import__", "eval", "exec"}:
                dynamic_calls.add(node.func.id)
        self.assertEqual(found, set())
        self.assertEqual(dynamic_calls, set())


if __name__ == "__main__":
    unittest.main()
