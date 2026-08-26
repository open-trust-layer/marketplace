from __future__ import annotations

import unittest

from olp import RecordV1

import marketplace_matching_v1 as tool_matching
import marketplace_record_v1 as tool_record
from marketplace.reference import matching_v1 as package_matching
from marketplace.reference import record_v1 as package_record


class ReferenceAdapterParityTests(unittest.TestCase):
    def intent(self, *, principal: str, action: str) -> RecordV1:
        return RecordV1.from_mapping(
            {
                "envelope_version": 1,
                "type": package_record.TYPE_INTENT,
                "content": {
                    "version": 1,
                    "issuer": {"principal": principal},
                    "subjects": [{"uri": "urn:example:item:m22"}],
                    "action": {"id": action},
                    "terms": {},
                },
                "profiles": [package_record.CORE_PROFILE],
            }
        )

    def test_m3_tool_path_reexports_packaged_single_source(self):
        self.assertIs(tool_record.validate_market_record, package_record.validate_market_record)
        self.assertIs(tool_record.MarketplaceConformanceError, package_record.MarketplaceConformanceError)
        self.assertIs(tool_record.STRUCTURE_VALIDATORS, package_record.STRUCTURE_VALIDATORS)
        self.assertEqual(tool_record.BASE, package_record.BASE)
        self.assertEqual(tool_record.TYPE_INTENT, package_record.TYPE_INTENT)

    def test_m5_tool_path_reexports_packaged_single_source(self):
        self.assertIs(tool_matching.evaluate_discovery, package_matching.evaluate_discovery)
        self.assertIs(tool_matching.evaluate_match, package_matching.evaluate_match)
        self.assertIs(tool_matching.verify_index_entry, package_matching.verify_index_entry)
        self.assertIs(tool_matching.merge_federated_views, package_matching.merge_federated_views)
        self.assertIs(tool_matching.bind_cursor, package_matching.bind_cursor)
        self.assertEqual(tool_matching.DEFAULT_MATCH_METHOD, package_matching.DEFAULT_MATCH_METHOD)

    def test_packaged_validator_and_tool_wrapper_reject_with_same_error_type(self):
        invalid = RecordV1.from_mapping(
            {
                "envelope_version": 1,
                "type": package_record.TYPE_INTENT,
                "content": {
                    "version": 1,
                    "issuer": {"principal": "did:example:alice"},
                    "subjects": [{"uri": "urn:example:item:m22"}],
                    "action": {"id": "https://example.test/actions/buy"},
                    "terms": {},
                },
                "profiles": [],
            }
        )
        with self.assertRaises(package_record.MarketplaceConformanceError) as packaged:
            package_record.validate_market_record(invalid)
        with self.assertRaises(tool_record.MarketplaceConformanceError) as wrapper:
            tool_record.validate_market_record(invalid)
        self.assertEqual(packaged.exception.code, wrapper.exception.code)
        self.assertEqual(str(packaged.exception), str(wrapper.exception))

    def test_packaged_discovery_matches_wrapper_result_exactly(self):
        sell = self.intent(
            principal="did:example:bob",
            action="https://example.test/actions/sell",
        )
        kwargs = {
            "source": "urn:example:source:m22",
            "completeness": "COMPLETE_FOR_DECLARED_SOURCE",
            "freshness": "FRESH",
            "max_records": 8,
        }
        query = {"version": 1, "action_ids_any": ["https://example.test/actions/sell"]}
        packaged = package_matching.evaluate_discovery((sell,), query, **kwargs)
        wrapper = tool_matching.evaluate_discovery((sell,), query, **kwargs)
        self.assertEqual(packaged, wrapper)
        self.assertEqual(packaged["global_completeness"], "UNKNOWN")
        self.assertFalse(packaged["absence_is_negative_evidence"])

    def test_packaged_match_matches_wrapper_and_never_creates_agreement(self):
        buy = self.intent(
            principal="did:example:alice",
            action="https://example.test/actions/buy",
        )
        sell = self.intent(
            principal="did:example:bob",
            action="https://example.test/actions/sell",
        )
        kwargs = {
            "method": "https://example.test/method/exact-v1",
            "base_status": "SATISFIED",
            "observations": (),
            "evidence_completeness": "COMPLETE_FOR_METHOD_INPUTS",
        }
        packaged = package_matching.evaluate_match(buy, sell, **kwargs)
        wrapper = tool_matching.evaluate_match(buy, sell, **kwargs)
        self.assertEqual(packaged, wrapper)
        self.assertEqual(packaged["conclusion"], "COMPATIBLE_UNDER_METHOD")
        self.assertFalse(packaged["protocol_truth"])
        self.assertFalse(packaged["creates_agreement"])


if __name__ == "__main__":
    unittest.main()
