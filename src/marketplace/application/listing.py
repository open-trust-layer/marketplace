"""Human product-listing profile projected onto Marketplace MarketIntentV1."""
from __future__ import annotations

from dataclasses import dataclass
import re


BASE = "https://open-trust-layer.github.io/marketplace/semantics/v1"
CORE_PROFILE = f"{BASE}/profile/core-v1"
TYPE_INTENT = f"{BASE}/record/market-intent"
PRODUCT_LISTING_PROFILE = f"{BASE}/profile/product-listing-v1"
ACTION_SELL = f"{PRODUCT_LISTING_PROFILE}/action/sell"
TERM_TITLE = f"{PRODUCT_LISTING_PROFILE}/term/title"
TERM_DESCRIPTION = f"{PRODUCT_LISTING_PROFILE}/term/description"
TERM_CONSIDERATION = f"{PRODUCT_LISTING_PROFILE}/term/consideration"
TERM_QUANTITY = f"{PRODUCT_LISTING_PROFILE}/term/quantity"
TERM_LOCATION = f"{PRODUCT_LISTING_PROFILE}/term/location"
UNIT_ITEM = f"{PRODUCT_LISTING_PROFILE}/unit/item"
LOCATION_WGS84_E6 = f"{PRODUCT_LISTING_PROFILE}/location/wgs84-e6"

_MAX_TITLE_BYTES = 120
_MAX_DESCRIPTION_BYTES = 4096
_MAX_URI_BYTES = 2048
_MIN_COEFFICIENT = -(1 << 63)
_MAX_COEFFICIENT = (1 << 63) - 1
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def _bounded_text(value: object, *, name: str, max_bytes: int) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{name} MUST be non-empty text")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{name} MUST be valid UTF-8 text") from exc
    if len(encoded) > max_bytes:
        raise ValueError(f"{name} exceeds its UTF-8 byte bound")
    return value


def _absolute_uri(value: object, *, name: str) -> str:
    text = _bounded_text(value, name=name, max_bytes=_MAX_URI_BYTES)
    if _URI_RE.fullmatch(text) is None:
        raise ValueError(f"{name} MUST be an absolute URI")
    return text


def _exact_int(value: object, *, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} MUST be an exact integer")
    return value


@dataclass(frozen=True, slots=True)
class ExactDecimal:
    """Canonical exact decimal compatible with Marketplace DecimalV1."""

    coefficient: int
    scale: int

    def __post_init__(self) -> None:
        coefficient = _exact_int(self.coefficient, name="coefficient")
        scale = _exact_int(self.scale, name="scale")
        if coefficient < _MIN_COEFFICIENT or coefficient > _MAX_COEFFICIENT:
            raise ValueError("coefficient exceeds the bounded application integer domain")
        if scale < 0 or scale > 18:
            raise ValueError("scale MUST be in range 0..18")
        if coefficient == 0:
            scale = 0
        else:
            while scale > 0 and coefficient % 10 == 0:
                coefficient //= 10
                scale -= 1
        object.__setattr__(self, "coefficient", coefficient)
        object.__setattr__(self, "scale", scale)

    @classmethod
    def from_minor_units(cls, value: int, *, scale: int) -> "ExactDecimal":
        return cls(value, scale)

    def as_mapping(self) -> dict[str, int]:
        return {"coefficient": self.coefficient, "scale": self.scale}


@dataclass(frozen=True, slots=True)
class ProductListingDraft:
    seller_principal: str
    subject_uri: str
    title: str
    description: str
    consideration: ExactDecimal
    currency_code: str
    quantity: ExactDecimal
    unit_uri: str
    latitude_e6: int
    longitude_e6: int

    def __post_init__(self) -> None:
        _absolute_uri(self.seller_principal, name="seller_principal")
        _absolute_uri(self.subject_uri, name="subject_uri")
        _bounded_text(self.title, name="title", max_bytes=_MAX_TITLE_BYTES)
        _bounded_text(self.description, name="description", max_bytes=_MAX_DESCRIPTION_BYTES)
        if type(self.consideration) is not ExactDecimal:
            raise ValueError("consideration MUST be ExactDecimal")
        if self.consideration.coefficient < 0:
            raise ValueError("consideration MUST NOT be negative")
        if type(self.currency_code) is not str or _CURRENCY_RE.fullmatch(self.currency_code) is None:
            raise ValueError("currency_code MUST be three uppercase ASCII letters")
        if type(self.quantity) is not ExactDecimal or self.quantity.coefficient <= 0:
            raise ValueError("quantity MUST be a positive ExactDecimal")
        _absolute_uri(self.unit_uri, name="unit_uri")
        latitude = _exact_int(self.latitude_e6, name="latitude_e6")
        longitude = _exact_int(self.longitude_e6, name="longitude_e6")
        if latitude < -90_000_000 or latitude > 90_000_000:
            raise ValueError("latitude_e6 MUST be in WGS84 range")
        if longitude < -180_000_000 or longitude > 180_000_000:
            raise ValueError("longitude_e6 MUST be in WGS84 range")


def build_product_listing_mapping(draft: ProductListingDraft) -> dict[str, object]:
    """Build one detached MarketIntentV1 mapping for the product-listing profile."""
    if type(draft) is not ProductListingDraft:
        raise TypeError("draft MUST be exact ProductListingDraft")
    terms: dict[str, object] = {
        TERM_TITLE: draft.title,
        TERM_DESCRIPTION: draft.description,
        TERM_CONSIDERATION: {
            "kind": "monetary",
            "amount": draft.consideration.as_mapping(),
            "currency_code": draft.currency_code,
        },
        TERM_QUANTITY: {
            "value": draft.quantity.as_mapping(),
            "unit": draft.unit_uri,
        },
        TERM_LOCATION: {
            "scheme": LOCATION_WGS84_E6,
            "value": {
                "latitude_e6": draft.latitude_e6,
                "longitude_e6": draft.longitude_e6,
            },
        },
    }
    return {
        "envelope_version": 1,
        "type": TYPE_INTENT,
        "content": {
            "version": 1,
            "issuer": {"principal": draft.seller_principal},
            "subjects": [{"uri": draft.subject_uri}],
            "action": {"id": ACTION_SELL},
            "terms": terms,
        },
        "profiles": [CORE_PROFILE, PRODUCT_LISTING_PROFILE],
    }
