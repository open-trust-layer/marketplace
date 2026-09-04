"""Structured product-listing authoring above the reviewed application API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .api import MarketplaceApplicationApiService
from .listing import ExactDecimal, ProductListingDraft
from .postgres_state import ApplicationStatePutResult


ProductListingRecordBuilder = Callable[[ProductListingDraft], Any]


class ProductListingAuthoringError(RuntimeError):
    """Stable authoring failure without reflecting input/provider details."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ProductListingAuthoringFields:
    """Transport-neutral primitive fields for one root product listing."""

    seller_principal: str
    subject_uri: str
    title: str
    description: str
    consideration_coefficient: int
    consideration_scale: int
    currency_code: str
    quantity_coefficient: int
    quantity_scale: int
    unit_uri: str
    latitude_e6: int
    longitude_e6: int


def _draft_from_fields(fields: ProductListingAuthoringFields) -> ProductListingDraft:
    try:
        return ProductListingDraft(
            seller_principal=fields.seller_principal,
            subject_uri=fields.subject_uri,
            title=fields.title,
            description=fields.description,
            consideration=ExactDecimal(
                fields.consideration_coefficient,
                fields.consideration_scale,
            ),
            currency_code=fields.currency_code,
            quantity=ExactDecimal(
                fields.quantity_coefficient,
                fields.quantity_scale,
            ),
            unit_uri=fields.unit_uri,
            latitude_e6=fields.latitude_e6,
            longitude_e6=fields.longitude_e6,
        )
    except (TypeError, ValueError):
        raise ProductListingAuthoringError(
            "PRODUCT_LISTING_FIELDS_INVALID",
            "structured product-listing fields are invalid",
        ) from None


class MarketplaceProductListingAuthoringService:
    """Build one reviewed root listing, then publish only through the application API."""

    def __init__(
        self,
        *,
        api: MarketplaceApplicationApiService,
        build_record: ProductListingRecordBuilder,
    ) -> None:
        if type(api) is not MarketplaceApplicationApiService:
            raise TypeError("api MUST be exact MarketplaceApplicationApiService")
        if not callable(build_record):
            raise TypeError("build_record MUST be callable")
        self._api = api
        self._build_record = build_record

    def create_product_listing(
        self,
        fields: ProductListingAuthoringFields,
    ) -> ApplicationStatePutResult:
        if type(fields) is not ProductListingAuthoringFields:
            raise TypeError("fields MUST be exact ProductListingAuthoringFields")
        draft = _draft_from_fields(fields)
        try:
            record = self._build_record(draft)
        except Exception:
            raise ProductListingAuthoringError(
                "PRODUCT_LISTING_BUILD_FAILED",
                "product listing record could not be built",
            ) from None
        return self._api.create_intent(record)


__all__ = [
    "MarketplaceProductListingAuthoringService",
    "ProductListingAuthoringError",
    "ProductListingAuthoringFields",
    "ProductListingRecordBuilder",
]
