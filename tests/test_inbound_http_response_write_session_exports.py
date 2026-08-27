from __future__ import annotations

import unittest

import marketplace.runtime as runtime
from marketplace.runtime.inbound_http_response_write_session import (
    BoundedInboundHttpResponseWriteSession,
    CompletedInboundHttpResponseWriteSession,
    InboundHttpResponseWriteSessionError,
    InboundHttpResponseWriteSessionProgress,
)


class InboundHttpResponseWriteSessionExportTests(unittest.TestCase):
    def test_public_runtime_exports_are_exact_m46_symbols(self):
        self.assertIs(
            runtime.BoundedInboundHttpResponseWriteSession,
            BoundedInboundHttpResponseWriteSession,
        )
        self.assertIs(
            runtime.CompletedInboundHttpResponseWriteSession,
            CompletedInboundHttpResponseWriteSession,
        )
        self.assertIs(
            runtime.InboundHttpResponseWriteSessionError,
            InboundHttpResponseWriteSessionError,
        )
        self.assertIs(
            runtime.InboundHttpResponseWriteSessionProgress,
            InboundHttpResponseWriteSessionProgress,
        )


if __name__ == "__main__":
    unittest.main()
