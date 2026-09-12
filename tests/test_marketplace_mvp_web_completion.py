from __future__ import annotations

import json
from pathlib import Path
import unittest

from marketplace.application.http import (
    ApplicationHttpRequest,
    MarketplaceApplicationHttpAdapter,
)
from marketplace.application.mvp import MarketplaceMvpFlightResult
from marketplace.application.postgres_state import ApplicationStatePutResult, StoreDisposition


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"


def _result() -> MarketplaceMvpFlightResult:
    ids = tuple(f"r1_demo_{index}" for index in range(7))
    return MarketplaceMvpFlightResult(
        seller_principal="urn:demo:seller",
        buyer_principal="urn:demo:buyer",
        listing_record_id=ids[0],
        proposal_record_id=ids[1],
        proposal_acceptance_record_id=ids[2],
        agreement_record_id=ids[3],
        performance_record_id=ids[4],
        fulfillment_acceptance_record_id=ids[5],
        completion_record_id=ids[6],
        listing_integrity_verified=True,
        agreement_formation="EVIDENCE_SUFFICIENT_FOR_PROFILE",
        fulfillment_conclusion="FULFILLED_UNDER_METHOD",
        states=("CREATED", "PUBLISHED", "DISCOVERED", "ACCEPTED", "COMPLETED"),
        final_state="COMPLETED",
        completed_at="2026-09-11T18:00:02Z",
        universal_truth=False,
        payment_or_settlement_evaluated=False,
    )


def _adapter(*, runner=None) -> MarketplaceApplicationHttpAdapter:
    return MarketplaceApplicationHttpAdapter(
        api=object(),
        decode_record_json=lambda body: json.loads(body.decode("utf-8")),
        encode_record_json=lambda record: json.dumps(record).encode("utf-8"),
        create_product_listing=lambda _fields: ApplicationStatePutResult(StoreDisposition.STORED, 1),
        create_proposal=lambda _draft: ApplicationStatePutResult(StoreDisposition.STORED, 2),
        run_mvp_flight=runner,
    )


def _request(method: str = "POST", *, query=(), content_type=None, body=b"") -> ApplicationHttpRequest:
    return ApplicationHttpRequest(method, "/api/mvp-flight", query, content_type, body)


class MarketplaceMvpWebCompletionTests(unittest.TestCase):
    def test_result_document_is_bounded_user_visible_evidence(self):
        document = _result().to_document()
        self.assertEqual(document["profile"], "MARKETPLACE_MVP_FLIGHT_ACCEPTANCE_V1")
        self.assertEqual(document["final_state"], "COMPLETED")
        self.assertEqual(document["participants"], {"seller": "urn:demo:seller", "buyer": "urn:demo:buyer"})
        self.assertEqual(document["verification"]["agreement_formation"], "EVIDENCE_SUFFICIENT_FOR_PROFILE")
        self.assertEqual(document["verification"]["fulfillment_conclusion"], "FULFILLED_UNDER_METHOD")
        self.assertFalse(document["verification"]["universal_truth"])
        self.assertFalse(document["verification"]["payment_or_settlement_evaluated"])
        self.assertEqual(len(document["audit_record_ids"]), 7)

    def test_http_route_runs_exact_injected_flight_once(self):
        calls: list[str] = []

        def runner():
            calls.append("run")
            return _result()

        response = _adapter(runner=runner).handle(_request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, ["run"])
        document = json.loads(response.body.decode("utf-8"))
        self.assertEqual(document["final_state"], "COMPLETED")

    def test_route_is_unavailable_without_explicit_runner(self):
        response = _adapter().handle(_request())
        self.assertEqual(response.status_code, 503)
        document = json.loads(response.body.decode("utf-8"))
        self.assertEqual(document["error"]["code"], "MVP_FLIGHT_UNAVAILABLE")

    def test_malformed_request_fails_before_runner(self):
        calls: list[str] = []

        def runner():
            calls.append("run")
            return _result()

        adapter = _adapter(runner=runner)
        cases = (
            _request(method="GET"),
            _request(query=(("unexpected", "1"),)),
            _request(content_type="application/json", body=b"{}"),
        )
        for request in cases:
            with self.subTest(request=request):
                response = adapter.handle(request)
                self.assertIn(response.status_code, (400, 405))
        self.assertEqual(calls, [])

    def test_runner_failure_is_stable_and_nonreflective(self):
        hostile = "SECRET-MVP-RUNNER-DETAIL"

        def runner():
            raise RuntimeError(hostile)

        response = _adapter(runner=runner).handle(_request())
        self.assertEqual(response.status_code, 500)
        text = response.body.decode("utf-8")
        self.assertIn("MVP_FLIGHT_FAILED", text)
        self.assertNotIn(hostile, text)

    def test_web_surface_exposes_completion_evidence_without_browser_protocol_logic(self):
        index = INDEX.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        localhost = LOCALHOST.read_text(encoding="utf-8")
        for marker in ('id="run-mvp-flight"', 'id="mvp-flight-final"', 'id="mvp-flight-audit"'):
            self.assertIn(marker, index)
        for marker in ('"/api/mvp-flight"', "reviewedMvpFlightDocument", "renderMvpFlight"):
            self.assertIn(marker, app)
        self.assertIn("run_marketplace_mvp_flight", localhost)
        self.assertNotIn("create_proof", app)
        self.assertNotIn("Ed25519", app)
        self.assertNotIn("localStorage", app)
