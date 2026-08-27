from __future__ import annotations

import unittest

import marketplace.runtime as runtime
from marketplace.runtime.inbound_http_response_prepare import (
    BoundedInboundHttpResponsePreparer,
    InboundHttpResponsePreparationError,
    PreparedInboundHttpReadResponse,
)


class InboundHttpResponsePreparationExportTests(unittest.TestCase):
    def test_public_runtime_exports_are_exact_m43_symbols(self):
        self.assertIs(
            runtime.BoundedInboundHttpResponsePreparer,
            BoundedInboundHttpResponsePreparer,
        )
        self.assertIs(
            runtime.InboundHttpResponsePreparationError,
            InboundHttpResponsePreparationError,
        )
        self.assertIs(
            runtime.PreparedInboundHttpReadResponse,
            PreparedInboundHttpReadResponse,
        )


if __name__ == "__main__":
    unittest.main()
