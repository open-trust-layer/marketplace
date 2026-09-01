"""Bounded local-user console adapter over the merged-green M74 demo path."""
from __future__ import annotations

from collections.abc import Callable
import re

from ..application import ExactDecimal, ProductListingDraft
from .local_demo_v1 import (
    LocalBuySellDemoError,
    LocalBuySellDemoResult,
    run_local_buy_sell_demo,
)


_DECIMAL_RE = re.compile(r"^[0-9]+(?:\.[0-9]{1,18})?$")
_COORDINATE_RE = re.compile(r"^(?P<sign>-?)(?P<whole>[0-9]{1,3})(?:\.(?P<fraction>[0-9]{1,6}))?$")

_MAX_URI_BYTES = 2048
_MAX_TITLE_BYTES = 120
_MAX_DESCRIPTION_BYTES = 4096
_MAX_DECIMAL_BYTES = 64
_MAX_CURRENCY_BYTES = 3
_MAX_COORDINATE_BYTES = 32


class LocalConsoleInteractionError(RuntimeError):
    """Stable local-console failure that never reflects hostile input values."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _require_callable(value: object, *, name: str) -> Callable:
    if not callable(value):
        raise LocalConsoleInteractionError(
            "ADAPTER_INVALID",
            f"{name} must be a callable local line adapter",
        )
    return value


def _write_line(writer: Callable[[str], None], line: str) -> None:
    try:
        writer(line)
    except Exception as exc:
        raise LocalConsoleInteractionError(
            "OUTPUT_FAILED",
            "local console output could not be written",
        ) from exc


def _read_bounded_text(
    reader: Callable[[str], object],
    *,
    prompt: str,
    max_bytes: int,
) -> str:
    try:
        value = reader(prompt)
    except Exception as exc:
        raise LocalConsoleInteractionError(
            "INPUT_READ_FAILED",
            "local console input could not be read",
        ) from exc
    if type(value) is not str:
        raise LocalConsoleInteractionError(
            "INPUT_INVALID",
            "local console input must be bounded UTF-8 text",
        )
    value = value.strip()
    if not value:
        raise LocalConsoleInteractionError(
            "INPUT_INVALID",
            "local console input must be non-empty bounded UTF-8 text",
        )
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise LocalConsoleInteractionError(
            "INPUT_INVALID",
            "local console input must be valid bounded UTF-8 text",
        ) from exc
    if len(encoded) > max_bytes:
        raise LocalConsoleInteractionError(
            "INPUT_INVALID",
            "local console input exceeds its bounded field size",
        )
    return value


def _parse_exact_decimal(value: str) -> ExactDecimal:
    if _DECIMAL_RE.fullmatch(value) is None:
        raise LocalConsoleInteractionError(
            "INPUT_INVALID",
            "local console decimal input is invalid",
        )
    whole, separator, fraction = value.partition(".")
    coefficient_text = whole + (fraction if separator else "")
    try:
        return ExactDecimal(
            coefficient=int(coefficient_text),
            scale=len(fraction) if separator else 0,
        )
    except (TypeError, ValueError) as exc:
        raise LocalConsoleInteractionError(
            "INPUT_INVALID",
            "local console decimal input is outside the supported exact range",
        ) from exc


def _parse_wgs84_e6(value: str) -> int:
    match = _COORDINATE_RE.fullmatch(value)
    if match is None:
        raise LocalConsoleInteractionError(
            "INPUT_INVALID",
            "local console coordinate input is invalid",
        )
    whole = int(match.group("whole"))
    fraction = match.group("fraction") or ""
    coordinate = whole * 1_000_000 + int(fraction.ljust(6, "0") or "0")
    if match.group("sign") == "-":
        coordinate = -coordinate
    return coordinate


def _collect_listing_and_buyer(
    reader: Callable[[str], object],
) -> tuple[ProductListingDraft, str, str]:
    seller_principal = _read_bounded_text(
        reader,
        prompt="Seller principal URI: ",
        max_bytes=_MAX_URI_BYTES,
    )
    subject_uri = _read_bounded_text(
        reader,
        prompt="Subject URI: ",
        max_bytes=_MAX_URI_BYTES,
    )
    title = _read_bounded_text(
        reader,
        prompt="Listing title: ",
        max_bytes=_MAX_TITLE_BYTES,
    )
    description = _read_bounded_text(
        reader,
        prompt="Listing description: ",
        max_bytes=_MAX_DESCRIPTION_BYTES,
    )
    consideration_text = _read_bounded_text(
        reader,
        prompt="Consideration amount (exact decimal): ",
        max_bytes=_MAX_DECIMAL_BYTES,
    )
    currency_code = _read_bounded_text(
        reader,
        prompt="Currency code (3 uppercase letters): ",
        max_bytes=_MAX_CURRENCY_BYTES,
    )
    quantity_text = _read_bounded_text(
        reader,
        prompt="Quantity (exact decimal): ",
        max_bytes=_MAX_DECIMAL_BYTES,
    )
    unit_uri = _read_bounded_text(
        reader,
        prompt="Quantity unit URI: ",
        max_bytes=_MAX_URI_BYTES,
    )
    latitude_text = _read_bounded_text(
        reader,
        prompt="Latitude (decimal degrees, max 6 fractional digits): ",
        max_bytes=_MAX_COORDINATE_BYTES,
    )
    longitude_text = _read_bounded_text(
        reader,
        prompt="Longitude (decimal degrees, max 6 fractional digits): ",
        max_bytes=_MAX_COORDINATE_BYTES,
    )
    buyer_principal = _read_bounded_text(
        reader,
        prompt="Buyer principal URI: ",
        max_bytes=_MAX_URI_BYTES,
    )
    buyer_action_uri = _read_bounded_text(
        reader,
        prompt="Buyer action URI: ",
        max_bytes=_MAX_URI_BYTES,
    )

    try:
        listing = ProductListingDraft(
            seller_principal=seller_principal,
            subject_uri=subject_uri,
            title=title,
            description=description,
            consideration=_parse_exact_decimal(consideration_text),
            currency_code=currency_code,
            quantity=_parse_exact_decimal(quantity_text),
            unit_uri=unit_uri,
            latitude_e6=_parse_wgs84_e6(latitude_text),
            longitude_e6=_parse_wgs84_e6(longitude_text),
        )
    except LocalConsoleInteractionError:
        raise
    except (TypeError, ValueError) as exc:
        raise LocalConsoleInteractionError(
            "INPUT_INVALID",
            "local console values could not form a valid product listing",
        ) from exc
    return listing, buyer_principal, buyer_action_uri


def run_local_buy_sell_console(
    *,
    read_line: Callable[[str], object],
    write_line: Callable[[str], None],
) -> LocalBuySellDemoResult:
    """Prompt once for a bounded local buy/sell interaction and return the M74 result."""
    reader = _require_callable(read_line, name="read_line")
    writer = _require_callable(write_line, name="write_line")

    _write_line(writer, "Marketplace local buy/sell interaction")
    _write_line(
        writer,
        "Local ephemeral demo only: no agreement, payment, settlement, ownership transfer, or protocol truth is created.",
    )

    listing, buyer_principal, buyer_action_uri = _collect_listing_and_buyer(reader)
    try:
        result = run_local_buy_sell_demo(
            seller_listing=listing,
            buyer_principal=buyer_principal,
            buyer_action_uri=buyer_action_uri,
        )
    except LocalBuySellDemoError as exc:
        code = "INPUT_INVALID" if exc.code == "BUYER_RECORD_INVALID" else "DEMO_FAILED"
        raise LocalConsoleInteractionError(
            code,
            "local buy/sell interaction could not complete through the reviewed demo path",
        ) from exc

    _write_line(writer, f"seller_record_id={result.seller_record_id}")
    _write_line(writer, f"buyer_record_id={result.buyer_record_id}")
    _write_line(writer, f"match_conclusion={result.match_conclusion}")
    _write_line(writer, "protocol_truth=false")
    _write_line(writer, "creates_agreement=false")
    return result


__all__ = [
    "LocalConsoleInteractionError",
    "run_local_buy_sell_console",
]
