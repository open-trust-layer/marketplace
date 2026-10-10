from __future__ import annotations

import json
import unittest

from marketplace.application.auth import (
    AuthenticatedProductListingAuthoringService,
    AuthenticatedProposalAcceptanceAuthoringService,
    AuthenticatedProposalAuthoringService,
)
from marketplace.application.auth_http import MarketplaceAuthenticatedApplicationHttpAdapter
from marketplace.application.http import ApplicationHttpRequest, MarketplaceApplicationHttpAdapter
from marketplace.application.proposal_acceptance_resolution import (
    MarketplaceProposalAcceptanceResolutionService,
)
from marketplace.application.state import MarketplaceApplicationStateService
from tests.test_m17_5c_bearer_session_transport import (
    PRINCIPAL,
    TOKEN,
    FakeApi,
    RecordingListingAuthoring,
    RecordingProposalAuthoring,
    decode_record,
    encode_record,
    make_active_auth,
)
from tests.test_product_proposal_acceptance_authoring import (
    ACCEPTANCE_ID,
    LISTING_ID,
    OTHER,
    PROPOSAL_ID,
    FakeStore,
    listing,
    make_service,
)




def make_resolution_service():
    source = {
        PROPOSAL_ID: {"kind": "proposal", "issuer": "did:example:buyer"},
        LISTING_ID: {"kind": "listing"},
        ACCEPTANCE_ID: {
            "kind": "acceptance",
            "issuer": PRINCIPAL,
            "proposal": PROPOSAL_ID,
        },
    }
    store = FakeStore(source)

    def prepare(record):
        from marketplace.application.postgres_state import PreparedApplicationRecord
        return PreparedApplicationRecord(ACCEPTANCE_ID, b"acceptance")

    def decode(data):
        return source[data.decode("ascii")]

    state = MarketplaceApplicationStateService(
        store=store,
        prepare_record=prepare,
        decode_record=decode,
    )
    state.initialize()
    resolver = MarketplaceProposalAcceptanceResolutionService(
        state=state,
        is_proposal_record=lambda record: record.get("kind") == "proposal",
        proposal_parent_ids=lambda record: (LISTING_ID,),
        extract_product_listing=lambda record: listing(PRINCIPAL),
        record_principal=lambda record: record["issuer"],
        build_acceptance_record=lambda seller, proposal_id: {
            "kind": "acceptance",
            "issuer": seller,
            "proposal": proposal_id,
        },
        acceptance_proposal_id=lambda record: record["proposal"],
        record_identity=lambda record: ACCEPTANCE_ID,
    )
    return resolver

class AuthenticatedProposalAcceptanceHttpTests(unittest.TestCase):
    def make_adapter(self, *, acceptance=True, extractor=None, resolution=False):
        api = FakeApi()
        listing_authoring = RecordingListingAuthoring()
        proposal_authoring = RecordingProposalAuthoring()
        auth = make_active_auth()
        base = MarketplaceApplicationHttpAdapter(
            api=api,
            decode_record_json=decode_record,
            encode_record_json=encode_record,
            create_product_listing=listing_authoring.create_product_listing,
            create_proposal=proposal_authoring.create_buyer_request_proposal,
        )
        guarded_listing = AuthenticatedProductListingAuthoringService(
            auth=auth,
            authoring=listing_authoring,
        )
        guarded_proposal = AuthenticatedProposalAuthoringService(
            auth=auth,
            authoring=proposal_authoring,
        )
        acceptance_store = None
        guarded_acceptance = None
        if acceptance:
            acceptance_authoring, acceptance_store, _ = make_service(extractor=extractor)
            guarded_acceptance = AuthenticatedProposalAcceptanceAuthoringService(
                auth=auth,
                authoring=acceptance_authoring,
            )
        adapter = MarketplaceAuthenticatedApplicationHttpAdapter(
            base=base,
            auth=auth,
            product_listing_authoring=guarded_listing,
            proposal_authoring=guarded_proposal,
            proposal_acceptance_authoring=guarded_acceptance,
            proposal_acceptance_resolution=make_resolution_service() if resolution else None,
            decode_record_json=decode_record,
            create_intent=api.create_intent,
            respond_to_intent=api.respond_to_intent,
            record_principal=lambda record: record["issuer"],
        )
        return adapter, acceptance_store

    @staticmethod
    def request(*, body=b"", content_type=None, query=()):
        return ApplicationHttpRequest(
            "POST",
            f"/api/intents/{PROPOSAL_ID}/acceptance",
            query,
            content_type,
            body,
        )

    @staticmethod
    def document(response):
        return json.loads(response.body.decode("utf-8"))

    @staticmethod
    def resolution_request(*, body=b"", content_type=None, query=()):
        return ApplicationHttpRequest(
            "GET",
            f"/api/intents/{PROPOSAL_ID}/acceptance",
            query,
            content_type,
            body,
        )

    def test_exact_get_resolves_published_acceptance_for_authenticated_party(self):
        adapter, _ = self.make_adapter(resolution=True)
        before = adapter._auth.validate_session(session_token=TOKEN, now=102)
        response = adapter.handle(
            self.resolution_request(),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        after = adapter._auth.validate_session(session_token=TOKEN, now=102)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.document(response),
            {
                "proposal_record_id": PROPOSAL_ID,
                "record_id": ACCEPTANCE_ID,
            },
        )
        self.assertEqual(before.last_used_at, 101)
        self.assertEqual(after.last_used_at, 101)

    def test_resolution_requires_session_and_selected_service(self):
        adapter, _ = self.make_adapter(resolution=True)
        missing = adapter.handle(
            self.resolution_request(),
            session_token=None,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(self.document(missing)["error"]["code"], "AUTH_REQUIRED")

        adapter, _ = self.make_adapter(resolution=False)
        unavailable = adapter.handle(
            self.resolution_request(),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(unavailable.status_code, 503)
        self.assertEqual(
            self.document(unavailable)["error"]["code"],
            "PROPOSAL_ACCEPTANCE_RESOLUTION_UNAVAILABLE",
        )

    def test_resolution_rejects_body_query_or_content_type(self):
        cases = (
            self.resolution_request(body=b"{}"),
            self.resolution_request(content_type="application/json"),
            self.resolution_request(query=(("x", "1"),)),
        )
        for request in cases:
            with self.subTest(request=request):
                adapter, _ = self.make_adapter(resolution=True)
                response = adapter.handle(
                    request,
                    session_token=TOKEN,
                    session_invalid=False,
                    now=102,
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    self.document(response)["error"]["code"],
                    "PROPOSAL_ACCEPTANCE_RESOLUTION_REQUEST_INVALID",
                )

    def test_acceptance_requires_session_before_authoring(self):
        adapter, store = self.make_adapter()
        response = adapter.handle(
            self.request(),
            session_token=None,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.document(response)["error"]["code"], "AUTH_REQUIRED")
        self.assertEqual(store.put_calls, [])

    def test_exact_empty_post_publishes_record_backed_acceptance(self):
        adapter, store = self.make_adapter()
        response = adapter.handle(
            self.request(),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.document(response), {
            "change_seq": 7,
            "disposition": "STORED",
            "record_id": "r-acceptance",
        })
        self.assertEqual(len(store.put_calls), 1)

    def test_acceptance_rejects_body_query_or_content_type_before_authoring(self):
        cases = (
            self.request(body=b"{}"),
            self.request(body=b"{}", content_type="application/json"),
            self.request(query=(("x", "1"),)),
        )
        for request in cases:
            with self.subTest(request=request):
                adapter, store = self.make_adapter()
                response = adapter.handle(
                    request,
                    session_token=TOKEN,
                    session_invalid=False,
                    now=102,
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    self.document(response)["error"]["code"],
                    "PROPOSAL_ACCEPTANCE_REQUEST_INVALID",
                )
                self.assertEqual(store.put_calls, [])

    def test_unselected_acceptance_service_fails_closed(self):
        adapter, _ = self.make_adapter(acceptance=False)
        response = adapter.handle(
            self.request(),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            self.document(response)["error"]["code"],
            "PROPOSAL_ACCEPTANCE_UNAVAILABLE",
        )

    def test_session_principal_must_own_parent_listing(self):
        adapter, store = self.make_adapter(extractor=lambda record: listing(OTHER))
        response = adapter.handle(
            self.request(),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.document(response)["error"]["code"],
            "PROPOSAL_ACCEPTANCE_SELLER_MISMATCH",
        )
        self.assertEqual(store.put_calls, [])


if __name__ == "__main__":
    unittest.main()
