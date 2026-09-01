"""Reference OLP adapter for the M72 human product-listing profile."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from olp import RecordV1

from ..application.listing import (
    ACTION_SELL,
    CORE_PROFILE,
    LOCATION_WGS84_E6,
    PRODUCT_LISTING_PROFILE,
    TERM_CONSIDERATION,
    TERM_DESCRIPTION,
    TERM_LOCATION,
    TERM_QUANTITY,
    TERM_TITLE,
    TYPE_INTENT,
    ExactDecimal,
    ProductListingDraft,
    build_product_listing_mapping,
)
from .record_v1 import (
    validate_location,
    validate_market_record,
    validate_quantity,
    validate_value_expression,
)


class ProductListingProfileError(ValueError):
    """Stable product-listing profile validation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise ProductListingProfileError(code, message)


def _mapping(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail("PRODUCT_LISTING_SHAPE_INVALID", f"{name} MUST be a mapping")
    if any(type(key) is not str for key in value):
        _fail("PRODUCT_LISTING_SHAPE_INVALID", f"{name} keys MUST be exact text")
    return value


def _exact_keys(value: Mapping[str, object], expected: set[str], *, name: str) -> None:
    if set(value) != expected:
        _fail("PRODUCT_LISTING_SHAPE_INVALID", f"{name} has an invalid field set")


def _decimal(value: object, *, name: str) -> ExactDecimal:
    mapping = _mapping(value, name=name)
    _exact_keys(mapping, {"coefficient", "scale"}, name=name)
    try:
        return ExactDecimal(mapping["coefficient"], mapping["scale"])
    except (TypeError, ValueError) as exc:
        raise ProductListingProfileError(
            "PRODUCT_LISTING_SHAPE_INVALID",
            f"{name} is not a canonical bounded decimal",
        ) from exc


def _validated_draft(record: object) -> ProductListingDraft:
    if type(record) is not RecordV1:
        _fail("PRODUCT_LISTING_RECORD_INVALID", "record MUST be exact OLP RecordV1")
    if type(record.type) is not str or record.type != TYPE_INTENT:
        _fail("PRODUCT_LISTING_RECORD_INVALID", "product listing MUST be a MarketIntentV1")
    if type(record.content) is not MappingProxyType:
        _fail("PRODUCT_LISTING_RECORD_INVALID", "record content container changed")
    if type(record.semantic_bindings) is not MappingProxyType or record.semantic_bindings:
        _fail("PRODUCT_LISTING_RECORD_INVALID", "record semantic bindings changed")
    if type(record.relationships) is not tuple or record.relationships:
        _fail("PRODUCT_LISTING_RECORD_INVALID", "record relationships changed")
    if type(record.extensions) is not MappingProxyType or record.extensions:
        _fail("PRODUCT_LISTING_RECORD_INVALID", "record extensions changed")
    if type(record.profiles) is not tuple or len(record.profiles) != 2:
        _fail("PRODUCT_LISTING_PROFILE_SET_INVALID", "product listing profile set changed")
    if any(type(profile) is not str for profile in record.profiles):
        _fail("PRODUCT_LISTING_PROFILE_SET_INVALID", "product listing profile set changed")
    if set(record.profiles) != {CORE_PROFILE, PRODUCT_LISTING_PROFILE}:
        _fail("PRODUCT_LISTING_PROFILE_SET_INVALID", "product listing profile set changed")
    try:
        validate_market_record(record)
    except Exception as exc:
        raise ProductListingProfileError(
            "PRODUCT_LISTING_RECORD_INVALID",
            "record is not a valid Marketplace record",
        ) from exc

    content = _mapping(record.content, name="content")
    _exact_keys(content, {"version", "issuer", "subjects", "action", "terms"}, name="content")
    if type(content["version"]) is not int or content["version"] != 1:
        _fail("PRODUCT_LISTING_SHAPE_INVALID", "content.version MUST equal integer 1")

    issuer = _mapping(content["issuer"], name="content.issuer")
    _exact_keys(issuer, {"principal"}, name="content.issuer")
    seller_principal = issuer["principal"]

    subjects = content["subjects"]
    if type(subjects) is not tuple or len(subjects) != 1:
        _fail("PRODUCT_LISTING_SHAPE_INVALID", "content.subjects MUST contain one subject")
    subject = _mapping(subjects[0], name="content.subjects[0]")
    _exact_keys(subject, {"uri"}, name="content.subjects[0]")
    subject_uri = subject["uri"]

    action = _mapping(content["action"], name="content.action")
    _exact_keys(action, {"id"}, name="content.action")
    if action["id"] != ACTION_SELL:
        _fail("PRODUCT_LISTING_SHAPE_INVALID", "product listing action changed")

    terms = _mapping(content["terms"], name="content.terms")
    _exact_keys(
        terms,
        {TERM_TITLE, TERM_DESCRIPTION, TERM_CONSIDERATION, TERM_QUANTITY, TERM_LOCATION},
        name="content.terms",
    )

    title = terms[TERM_TITLE]
    description = terms[TERM_DESCRIPTION]

    consideration = _mapping(terms[TERM_CONSIDERATION], name="consideration")
    _exact_keys(consideration, {"kind", "amount", "currency_code"}, name="consideration")
    if consideration["kind"] != "monetary":
        _fail("PRODUCT_LISTING_SHAPE_INVALID", "consideration MUST be monetary")
    try:
        validate_value_expression(consideration, "consideration")
    except Exception as exc:
        raise ProductListingProfileError(
            "PRODUCT_LISTING_SHAPE_INVALID", "consideration is invalid"
        ) from exc
    consideration_decimal = _decimal(consideration["amount"], name="consideration.amount")
    currency_code = consideration["currency_code"]

    quantity = _mapping(terms[TERM_QUANTITY], name="quantity")
    _exact_keys(quantity, {"value", "unit"}, name="quantity")
    try:
        validate_quantity(quantity, "quantity")
    except Exception as exc:
        raise ProductListingProfileError("PRODUCT_LISTING_SHAPE_INVALID", "quantity is invalid") from exc
    quantity_decimal = _decimal(quantity["value"], name="quantity.value")
    unit_uri = quantity["unit"]

    location = _mapping(terms[TERM_LOCATION], name="location")
    _exact_keys(location, {"scheme", "value"}, name="location")
    try:
        validate_location(location, "location")
    except Exception as exc:
        raise ProductListingProfileError("PRODUCT_LISTING_SHAPE_INVALID", "location is invalid") from exc
    if location["scheme"] != LOCATION_WGS84_E6:
        _fail("PRODUCT_LISTING_SHAPE_INVALID", "location scheme changed")
    location_value = _mapping(location["value"], name="location.value")
    _exact_keys(location_value, {"latitude_e6", "longitude_e6"}, name="location.value")

    try:
        return ProductListingDraft(
            seller_principal=seller_principal,
            subject_uri=subject_uri,
            title=title,
            description=description,
            consideration=consideration_decimal,
            currency_code=currency_code,
            quantity=quantity_decimal,
            unit_uri=unit_uri,
            latitude_e6=location_value["latitude_e6"],
            longitude_e6=location_value["longitude_e6"],
        )
    except (TypeError, ValueError) as exc:
        raise ProductListingProfileError(
            "PRODUCT_LISTING_SHAPE_INVALID", "product listing terms are outside profile bounds"
        ) from exc


def validate_product_listing_record(record: object) -> None:
    _validated_draft(record)


def extract_product_listing(record: object) -> ProductListingDraft:
    return _validated_draft(record)


def build_product_listing_record(draft: ProductListingDraft) -> RecordV1:
    if type(draft) is not ProductListingDraft:
        raise TypeError("draft MUST be exact ProductListingDraft")
    try:
        record = RecordV1.from_mapping(build_product_listing_mapping(draft))
        validate_market_record(record)
        validate_product_listing_record(record)
    except ProductListingProfileError:
        raise
    except Exception as exc:
        raise ProductListingProfileError(
            "PRODUCT_LISTING_BUILD_INVALID",
            "product listing could not be materialized as a valid Marketplace record",
        ) from exc
    return record
