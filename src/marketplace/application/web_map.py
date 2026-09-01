"""Deterministic offline HTML/SVG projection for validated product listings."""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

from .listing import ExactDecimal, ProductListingDraft


MAX_RENDERED_LISTINGS = 64
_MIN_WIDTH = 240
_MAX_WIDTH = 2048
_MIN_HEIGHT = 120
_MAX_HEIGHT = 1024
_LATITUDE_SPAN_E6 = 180_000_000
_LONGITUDE_SPAN_E6 = 360_000_000


def _exact_int(value: object, *, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} MUST be an exact integer")
    return value


@dataclass(frozen=True, slots=True)
class OfflineMapFixture:
    """Bounded equirectangular canvas with no external map-provider authority."""

    width: int = 720
    height: int = 360

    def __post_init__(self) -> None:
        width = _exact_int(self.width, name="width")
        height = _exact_int(self.height, name="height")
        if width < _MIN_WIDTH or width > _MAX_WIDTH:
            raise ValueError("width is outside the offline fixture bound")
        if height < _MIN_HEIGHT or height > _MAX_HEIGHT:
            raise ValueError("height is outside the offline fixture bound")


DEFAULT_OFFLINE_MAP_FIXTURE = OfflineMapFixture()


def _review_fixture(value: object) -> OfflineMapFixture:
    if type(value) is not OfflineMapFixture:
        raise TypeError("fixture MUST be exact OfflineMapFixture")
    return OfflineMapFixture(width=value.width, height=value.height)


def project_wgs84_e6(
    latitude_e6: int,
    longitude_e6: int,
    fixture: OfflineMapFixture = DEFAULT_OFFLINE_MAP_FIXTURE,
) -> tuple[int, int]:
    """Project exact WGS84 microdegrees onto the bounded offline fixture."""
    latitude = _exact_int(latitude_e6, name="latitude_e6")
    longitude = _exact_int(longitude_e6, name="longitude_e6")
    if latitude < -90_000_000 or latitude > 90_000_000:
        raise ValueError("latitude_e6 MUST be in WGS84 range")
    if longitude < -180_000_000 or longitude > 180_000_000:
        raise ValueError("longitude_e6 MUST be in WGS84 range")
    reviewed_fixture = _review_fixture(fixture)
    x = ((longitude + 180_000_000) * (reviewed_fixture.width - 1)) // _LONGITUDE_SPAN_E6
    y = ((90_000_000 - latitude) * (reviewed_fixture.height - 1)) // _LATITUDE_SPAN_E6
    return x, y


def _review_listing(value: object) -> ProductListingDraft:
    if type(value) is not ProductListingDraft:
        raise TypeError("each listing MUST be exact ProductListingDraft")
    try:
        return ProductListingDraft(
            seller_principal=value.seller_principal,
            subject_uri=value.subject_uri,
            title=value.title,
            description=value.description,
            consideration=value.consideration,
            currency_code=value.currency_code,
            quantity=value.quantity,
            unit_uri=value.unit_uri,
            latitude_e6=value.latitude_e6,
            longitude_e6=value.longitude_e6,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("listing changed after validation") from exc


def _format_decimal(value: ExactDecimal) -> str:
    coefficient = value.coefficient
    scale = value.scale
    sign = "-" if coefficient < 0 else ""
    digits = str(abs(coefficient))
    if scale == 0:
        return f"{sign}{digits}"
    digits = digits.rjust(scale + 1, "0")
    return f"{sign}{digits[:-scale]}.{digits[-scale:]}"


def _format_e6(value: int) -> str:
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    return f"{sign}{absolute // 1_000_000}.{absolute % 1_000_000:06d}"


def _marker_svg(index: int, listing: ProductListingDraft, fixture: OfflineMapFixture) -> str:
    x, y = project_wgs84_e6(listing.latitude_e6, listing.longitude_e6, fixture)
    return (
        f'<g class="marker" transform="translate({x} {y})">'
        '<circle r="7"></circle>'
        f'<text x="0" y="3">{index}</text>'
        "</g>"
    )


def _listing_html(index: int, listing: ProductListingDraft) -> str:
    title = escape(listing.title, quote=True)
    description = escape(listing.description, quote=True)
    seller = escape(listing.seller_principal, quote=True)
    subject = escape(listing.subject_uri, quote=True)
    unit = escape(listing.unit_uri, quote=True)
    price = f"{_format_decimal(listing.consideration)} {listing.currency_code}"
    quantity = _format_decimal(listing.quantity)
    coordinates = f"{_format_e6(listing.latitude_e6)}, {_format_e6(listing.longitude_e6)}"
    return (
        '<article class="listing">'
        f"<h2>{index}. {title}</h2>"
        f'<p class="description">{description}</p>'
        '<dl>'
        f"<dt>Price</dt><dd>{price}</dd>"
        f"<dt>Quantity</dt><dd>{quantity}</dd>"
        f"<dt>Unit</dt><dd>{unit}</dd>"
        f"<dt>Coordinates</dt><dd>{coordinates}</dd>"
        f"<dt>Seller</dt><dd>{seller}</dd>"
        f"<dt>Subject</dt><dd>{subject}</dd>"
        "</dl>"
        "</article>"
    )


def _style() -> str:
    return """<style>
body { font-family: system-ui, sans-serif; margin: 0; background: #f6f7f9; color: #17202a; }
main { max-width: 1100px; margin: 0 auto; padding: 24px; }
header { margin-bottom: 20px; }
.notice { background: #fff; border: 1px solid #d9dee5; border-radius: 10px; padding: 12px 16px; }
.map { width: 100%; height: auto; background: #eef3f7; border: 1px solid #b7c1cb; border-radius: 12px; }
.grid { stroke: #c7d0d8; stroke-width: 1; }
.axis { stroke: #98a7b5; stroke-width: 1.5; }
.marker circle { fill: #17202a; }
.marker text { fill: #fff; font: bold 9px system-ui, sans-serif; text-anchor: middle; }
.listings { display: grid; gap: 14px; margin-top: 20px; }
.listing { background: #fff; border: 1px solid #d9dee5; border-radius: 10px; padding: 16px; }
.listing h2 { margin: 0 0 8px; font-size: 1.1rem; }
.description { white-space: pre-wrap; }
dl { display: grid; grid-template-columns: minmax(100px, 140px) 1fr; gap: 6px 12px; }
dt { font-weight: 650; }
dd { margin: 0; overflow-wrap: anywhere; }
small { color: #566573; }
</style>"""


def _map_svg(listings: tuple[ProductListingDraft, ...], fixture: OfflineMapFixture) -> str:
    width = fixture.width
    height = fixture.height
    vertical = tuple((width - 1) * step // 6 for step in range(1, 6))
    horizontal = tuple((height - 1) * step // 6 for step in range(1, 6))
    lines = [
        f'<svg class="map" viewBox="0 0 {width} {height}" role="img" aria-label="Offline listing coordinate map">'
    ]
    for x in vertical:
        lines.append(f'<line class="grid" x1="{x}" y1="0" x2="{x}" y2="{height - 1}"></line>')
    for y in horizontal:
        lines.append(f'<line class="grid" x1="0" y1="{y}" x2="{width - 1}" y2="{y}"></line>')
    equator_y = (height - 1) // 2
    meridian_x = (width - 1) // 2
    lines.append(
        f'<line class="axis" x1="0" y1="{equator_y}" x2="{width - 1}" y2="{equator_y}"></line>'
    )
    lines.append(
        f'<line class="axis" x1="{meridian_x}" y1="0" x2="{meridian_x}" y2="{height - 1}"></line>'
    )
    for index, listing in enumerate(listings, start=1):
        lines.append(_marker_svg(index, listing, fixture))
    lines.append("</svg>")
    return "".join(lines)


def render_product_listing_page(
    listings: tuple[ProductListingDraft, ...],
    *,
    fixture: OfflineMapFixture = DEFAULT_OFFLINE_MAP_FIXTURE,
) -> str:
    """Render a bounded, inert local view. Rendering performs no external I/O."""
    if type(listings) is not tuple:
        raise TypeError("listings MUST be an exact tuple")
    if len(listings) > MAX_RENDERED_LISTINGS:
        raise ValueError("listings exceed the bounded local render limit")
    reviewed_fixture = _review_fixture(fixture)
    reviewed = tuple(_review_listing(listing) for listing in listings)
    map_html = _map_svg(reviewed, reviewed_fixture)
    if reviewed:
        listing_html = "".join(_listing_html(index, item) for index, item in enumerate(reviewed, start=1))
    else:
        listing_html = (
            '<p class="notice">No local listings in this bounded view. '
            "This is not global nonexistence or deletion evidence.</p>"
        )
    return (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Open Layer Marketplace — Local Offline Listings</title>"
        f"{_style()}</head><body><main>"
        "<header><h1>Local Marketplace Listings</h1>"
        '<p class="notice"><strong>Offline deterministic coordinate view.</strong> '
        "No map-provider request is made. Location is issuer-attributed, not verified.</p></header>"
        f"{map_html}"
        '<small>Markers use WGS84 microdegrees projected deterministically onto an offline equirectangular fixture.</small>'
        f'<section class="listings" aria-label="Local listings">{listing_html}</section>'
        "</main></body></html>"
    )
