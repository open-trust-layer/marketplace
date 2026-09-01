"""Deterministic local M74 buy/sell demonstration over reviewed Marketplace surfaces."""
from __future__ import annotations

from dataclasses import dataclass

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text

from ..application import LocalMarketplaceApplication, ProductListingDraft
from ..runtime import create_in_memory_runtime
from .matching_v1 import DEFAULT_MATCH_METHOD, evaluate_discovery, evaluate_match
from .product_listing_v1 import (
    ACTION_SELL,
    CORE_PROFILE,
    PRODUCT_LISTING_PROFILE,
    build_product_listing_record,
    extract_product_listing,
)
from .record_v1 import TYPE_INTENT, validate_market_record
from .web_map_v1 import render_product_listing_record_page


_DEMO_SOURCE = "urn:open-layer-marketplace:demo:local"


class LocalBuySellDemoError(RuntimeError):
    """Stable local-demo failure without external side effects."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class LocalBuySellDemoResult:
    seller_record_id: str
    buyer_record_id: str
    discovered_seller_record_ids: tuple[str, ...]
    match_method: str
    match_conclusion: str
    protocol_truth: bool
    creates_agreement: bool
    discovery_global_completeness: str
    discovery_absence_is_negative_evidence: bool
    seller_listing_html: str


class _CloseOnlyExpiryHandle:
    __slots__ = ()

    def cancel(self) -> None:
        return None


class _CloseOnlyExpiryScheduler:
    __slots__ = ()

    def schedule(self, _delay_seconds: float, _callback) -> _CloseOnlyExpiryHandle:
        # The demo runtime is unconditionally closed before the function returns.
        # Avoiding a background timer therefore shortens, never extends, retention.
        return _CloseOnlyExpiryHandle()


def _build_buyer_record(
    *,
    buyer_principal: object,
    buyer_action_uri: object,
    subject_uri: str,
) -> RecordV1:
    try:
        record = RecordV1.from_mapping(
            {
                "envelope_version": 1,
                "type": TYPE_INTENT,
                "content": {
                    "version": 1,
                    "issuer": {"principal": buyer_principal},
                    "subjects": [{"uri": subject_uri}],
                    "action": {"id": buyer_action_uri},
                    "terms": {},
                },
                "profiles": [CORE_PROFILE],
            }
        )
        validate_market_record(record)
    except Exception as exc:
        raise LocalBuySellDemoError(
            "BUYER_RECORD_INVALID",
            "buyer request could not be materialized as a valid Marketplace intent",
        ) from exc
    return record


def _review_match_result(
    value: object,
    *,
    buyer_record_id: str,
    seller_record_id: str,
) -> tuple[str, bool, bool]:
    if type(value) is not dict:
        raise LocalBuySellDemoError("MATCH_RESULT_INVALID", "match result shape changed")
    if value.get("left") != buyer_record_id or value.get("right") != seller_record_id:
        raise LocalBuySellDemoError("MATCH_RESULT_INVALID", "match result identity binding changed")
    if value.get("method") != DEFAULT_MATCH_METHOD:
        raise LocalBuySellDemoError("MATCH_RESULT_INVALID", "match method binding changed")
    conclusion = value.get("conclusion")
    protocol_truth = value.get("protocol_truth")
    creates_agreement = value.get("creates_agreement")
    if type(conclusion) is not str or not conclusion:
        raise LocalBuySellDemoError("MATCH_RESULT_INVALID", "match conclusion changed")
    if type(protocol_truth) is not bool or type(creates_agreement) is not bool:
        raise LocalBuySellDemoError("MATCH_RESULT_INVALID", "match authority flags changed")
    if protocol_truth or creates_agreement:
        raise LocalBuySellDemoError("MATCH_AUTHORITY_PROMOTION", "demo match cannot create authority")
    if conclusion != "COMPATIBLE_UNDER_METHOD":
        raise LocalBuySellDemoError("DEMO_NOT_COMPATIBLE", "demo pair was not compatible under method")
    return conclusion, protocol_truth, creates_agreement


def run_local_buy_sell_demo(
    *,
    seller_listing: ProductListingDraft,
    buyer_principal: str,
    buyer_action_uri: str,
) -> LocalBuySellDemoResult:
    """Run one bounded local seller-discovery and buyer/seller match demonstration."""
    seller_record = build_product_listing_record(seller_listing)
    reviewed_seller = extract_product_listing(seller_record)
    buyer_record = _build_buyer_record(
        buyer_principal=buyer_principal,
        buyer_action_uri=buyer_action_uri,
        subject_uri=reviewed_seller.subject_uri,
    )
    seller_listing_html = render_product_listing_record_page((seller_record,))

    runtime = create_in_memory_runtime(
        validate_record=validate_market_record,
        record_identity_text=record_identity_text,
        evaluate_discovery=evaluate_discovery,
        evaluate_match=evaluate_match,
        scheduler=_CloseOnlyExpiryScheduler(),
    )
    with runtime:
        app = LocalMarketplaceApplication(
            node=runtime.node,
            discovery=runtime.discovery,
            source=_DEMO_SOURCE,
        )
        seller_published = app.publish(seller_record)
        buyer_published = app.publish(buyer_record)
        discovery = app.search(
            {
                "version": 1,
                "profiles_all": [PRODUCT_LISTING_PROFILE],
                "action_ids_any": [ACTION_SELL],
                "subject_uris_any": [reviewed_seller.subject_uri],
            },
            completeness="PARTIAL_SOURCE",
            freshness="FRESH",
            max_records=8,
        )
        if discovery.record_ids != (seller_published.record_id,):
            raise LocalBuySellDemoError(
                "SELLER_DISCOVERY_INVALID",
                "demo discovery did not resolve the exact local seller listing",
            )

        match = runtime.matching.evaluate(
            buyer_published.record_id,
            seller_published.record_id,
            method=DEFAULT_MATCH_METHOD,
            base_status="SATISFIED",
            observations=(),
            evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
        )
        conclusion, protocol_truth, creates_agreement = _review_match_result(
            match,
            buyer_record_id=buyer_published.record_id,
            seller_record_id=seller_published.record_id,
        )
        return LocalBuySellDemoResult(
            seller_record_id=seller_published.record_id,
            buyer_record_id=buyer_published.record_id,
            discovered_seller_record_ids=discovery.record_ids,
            match_method=DEFAULT_MATCH_METHOD,
            match_conclusion=conclusion,
            protocol_truth=protocol_truth,
            creates_agreement=creates_agreement,
            discovery_global_completeness=discovery.global_completeness,
            discovery_absence_is_negative_evidence=discovery.absence_is_negative_evidence,
            seller_listing_html=seller_listing_html,
        )


__all__ = [
    "LocalBuySellDemoError",
    "LocalBuySellDemoResult",
    "run_local_buy_sell_demo",
]
