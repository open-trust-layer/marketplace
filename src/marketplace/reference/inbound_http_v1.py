"""Strict OLP JSON codec bridge for the transport-free M34 application adapter.

This module intentionally performs no HTTP parsing, socket I/O, listener setup,
TLS termination, authentication, or transmission.  It only reuses the already
reviewed deterministic OLP JSON single-envelope codec from M26.
"""
from __future__ import annotations

from typing import Any

from .transport_json_v1 import (
    decode_transport_envelope_json,
    encode_transport_envelope_json,
)


def decode_inbound_control_envelope_json(body: bytes) -> tuple[Any, ...]:
    """Decode one strict inbound OLP JSON envelope for M34/M32 composition."""
    return decode_transport_envelope_json(body)


def encode_prepared_inbound_response_json(envelope: Any) -> bytes:
    """Encode one prepared M32/M33 OLP envelope for an unsent M34 response."""
    return encode_transport_envelope_json(envelope)
