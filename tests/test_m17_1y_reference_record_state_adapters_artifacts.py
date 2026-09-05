from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "src" / "marketplace" / "reference" / "application_record_v1.py"
FACTORY = ROOT / "src" / "marketplace" / "reference" / "application_v1.py"
REFERENCE_INIT = ROOT / "src" / "marketplace" / "reference" / "__init__.py"
APPLICATION = ROOT / "src" / "marketplace" / "application"
DOC = ROOT / "docs" / "m17-1y-reference-record-state-adapters.md"


class M17ReferenceRecordStateAdapterArtifactsTests(unittest.TestCase):
    def test_reference_state_adapter_exists_and_exports_exact_four_semantics(self):
        self.assertTrue(ADAPTER.is_file())
        text = ADAPTER.read_text(encoding="utf-8-sig")
        for marker in (
            "def prepare_marketplace_application_record(",
            "def decode_marketplace_application_record(",
            "def marketplace_response_parent_ids(",
            "def is_marketplace_intent_record(",
            "market_record_transport_payload",
            "make_record_transport_envelope",
            "encode_transport_envelope_json",
            "decode_transport_envelope_json",
            "record_identity_text",
            "PreparedApplicationRecord",
        ):
            self.assertIn(marker, text)

    def test_reference_launch_factory_fixes_state_semantics_but_leaves_raw_json_injected(self):
        text = FACTORY.read_text(encoding="utf-8-sig")
        for marker in (
            "prepare_record=prepare_marketplace_application_record",
            "decode_record=decode_marketplace_application_record",
            "response_parent_ids=marketplace_response_parent_ids",
            "is_intent_record=is_marketplace_intent_record",
            "decode_record_json: RecordJsonDecoder",
            "encode_record_json: RecordJsonEncoder",
        ):
            self.assertIn(marker, text)
        signature = text.split("def build_reference_marketplace_application_launch_plan(", 1)[1].split(") -> MarketplaceApplicationLaunchPlan:", 1)[0]
        for removed in (
            "prepare_record: RecordPreparer",
            "decode_record: RecordDecoder",
            "response_parent_ids: ResponseParentExtractor",
            "is_intent_record: IntentRecordPredicate",
        ):
            self.assertNotIn(removed, signature)

    def test_state_adapter_is_inert_and_does_not_choose_runtime_resources(self):
        text = ADAPTER.read_text(encoding="utf-8-sig")
        for forbidden in (
            "PostgresApplicationStateStore",
            "PostgresIntentQuery",
            "connection_factory=",
            "run_marketplace_application_foreground",
            "UvicornLoopbackServerProvider",
            "open(",
            "Path(",
            "os.environ",
            "getenv(",
            "socket.",
            "subprocess",
        ):
            self.assertNotIn(forbidden, text)

    def test_application_layer_still_does_not_import_reference_layer(self):
        for path in APPLICATION.glob("*.py"):
            text = path.read_text(encoding="utf-8-sig")
            self.assertNotIn("marketplace.reference", text, path.name)
            self.assertNotIn("from ..reference", text, path.name)
            self.assertNotIn("from marketplace.reference", text, path.name)

    def test_reference_package_exports_state_adapters(self):
        text = REFERENCE_INIT.read_text(encoding="utf-8-sig")
        for marker in (
            "prepare_marketplace_application_record",
            "decode_marketplace_application_record",
            "marketplace_response_parent_ids",
            "is_marketplace_intent_record",
         ):
            self.assertIn(marker, text)

    def test_document_preserves_wire_and_runtime_authority_boundaries(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8-sig")
        for marker in (
            "canonical application-record state adapters",
            "raw Record JSON remains caller-injected",
            "no runtime activation",
            "no PostgreSQL connection",
            "no filesystem asset loading",
            "merge remains a separate exact-head governance boundary",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
