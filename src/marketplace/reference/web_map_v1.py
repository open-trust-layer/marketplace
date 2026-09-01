"""Reference bridge from genuine M72 records to the inert M73 web/map projection."""
from __future__ import annotations

from olp import RecordV1

from ..application.web_map import MAX_RENDERED_LISTINGS, render_product_listing_page
from .product_listing_v1 import extract_product_listing


def render_product_listing_record_page(records: tuple[RecordV1, ...]) -> str:
    """Validate/extract a bounded exact record tuple, then render it without external I/O."""
    if type(records) is not tuple:
        raise TypeError("records MUST be an exact tuple")
    if len(records) > MAX_RENDERED_LISTINGS:
        raise ValueError("records exceed the bounded local render limit")
    listings = tuple(extract_product_listing(record) for record in records)
    return render_product_listing_page(listings)


__all__ = ["render_product_listing_record_page"]
