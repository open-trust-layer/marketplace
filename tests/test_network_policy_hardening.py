from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from marketplace.runtime.network_policy import (
    FederationEgressPolicy,
    FederationNetworkPolicyError,
    authorize_federation_endpoint,
    validate_endpoint_authorization,
    validate_resolved_addresses,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("src/marketplace/runtime/network_policy.py")


class FederationNetworkPolicyHardeningTests(unittest.TestCase):
    def policy(self) -> FederationEgressPolicy:
        return FederationEgressPolicy(
            policy_id="https://open-trust-layer.github.io/marketplace/policy/egress-v1",
            policy_version=1,
            allowed_hosts=("federation.example.com",),
        )

    def authorization(self):
        return authorize_federation_endpoint(
            endpoint="https://federation.example.com/federation/v1",
            allowed_operations=(
                "https://open-trust-layer.github.io/marketplace/semantics/v1/federation/operation/snapshot-v1",
            ),
            authorization_id="egress-auth-hardening",
            issued_at_epoch=1_000,
            expires_at_epoch=1_120,
            policy=self.policy(),
        )

    def assert_policy_error(self, code: str, function, *args, **kwargs) -> None:
        with self.assertRaises(FederationNetworkPolicyError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_ipv6_transition_and_translation_forms_are_rejected_before_use(self):
        unsafe = (
            "64:ff9b::7f00:1",
            "64:ff9b::808:808",
            "64:ff9b:1::808:808",
            "2002:0808:0808::",
            "2001:0000:4136:e378:8000:63bf:3fff:fdd2",
        )
        for address in unsafe:
            with self.subTest(address=address):
                self.assert_policy_error(
                    "IPV6_TRANSITION_FORBIDDEN",
                    validate_resolved_addresses,
                    "federation.example.com",
                    (address,),
                )

    def test_fabricated_authorization_rejects_non_integer_times_explicitly(self):
        authorization = self.authorization()
        for changed in (
            replace(authorization, issued_at_epoch="1000"),
            replace(authorization, expires_at_epoch=None),
        ):
            with self.subTest(changed=changed):
                self.assert_policy_error(
                    "INVALID_AUTHORIZATION_TIME",
                    validate_endpoint_authorization,
                    changed,
                    endpoint=authorization.canonical_endpoint,
                    operation=authorization.allowed_operations[0],
                    now_epoch=1_050,
                    policy=self.policy(),
                )

    def test_fabricated_authorization_requires_negative_authority_flags_to_be_exact_false(self):
        authorization = self.authorization()
        for changed in (
            replace(authorization, establishes_trust=0),
            replace(authorization, establishes_agreement=None),
            replace(authorization, establishes_marketplace_authorization="false"),
        ):
            with self.subTest(changed=changed):
                self.assert_policy_error(
                    "AUTHORIZATION_AUTHORITY_ESCALATION",
                    validate_endpoint_authorization,
                    changed,
                    endpoint=authorization.canonical_endpoint,
                    operation=authorization.allowed_operations[0],
                    now_epoch=1_050,
                    policy=self.policy(),
                )

    def test_fabricated_authorization_operation_collection_must_remain_canonical_tuple(self):
        authorization = self.authorization()
        malformed = replace(authorization, allowed_operations=list(authorization.allowed_operations))
        self.assert_policy_error(
            "INVALID_AUTHORIZATION",
            validate_endpoint_authorization,
            malformed,
            endpoint=authorization.canonical_endpoint,
            operation=authorization.allowed_operations[0],
            now_epoch=1_050,
            policy=self.policy(),
        )

    def test_m25_module_uses_exact_reviewed_import_surface_and_no_dynamic_file_execution(self):
        source = (REPO_ROOT / TARGET).read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=str(TARGET))
        imported: set[str] = set()
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"__import__", "eval", "exec", "open", "compile"}:
                    calls.add(node.func.id)
        self.assertEqual(
            imported,
            {
                "__future__",
                "ipaddress",
                "re",
                "collections.abc",
                "dataclasses",
                "typing",
                "urllib.parse",
            },
        )
        self.assertEqual(calls, set())


if __name__ == "__main__":
    unittest.main()
