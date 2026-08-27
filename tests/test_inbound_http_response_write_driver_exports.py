import unittest

from marketplace import runtime
from marketplace.runtime.inbound_http_response_write_driver import (
    BoundedInboundHttpResponseWriteDriver,
    CompletedInboundHttpResponseWriteDriverResult,
    InboundHttpResponseWriteDriverError,
    InboundHttpResponseWriteDriverLimits,
)


class InboundHttpResponseWriteDriverExportTests(unittest.TestCase):
    def test_public_runtime_exports_are_exact_m49_symbols(self):
        self.assertIs(runtime.BoundedInboundHttpResponseWriteDriver, BoundedInboundHttpResponseWriteDriver)
        self.assertIs(runtime.CompletedInboundHttpResponseWriteDriverResult, CompletedInboundHttpResponseWriteDriverResult)
        self.assertIs(runtime.InboundHttpResponseWriteDriverError, InboundHttpResponseWriteDriverError)
        self.assertIs(runtime.InboundHttpResponseWriteDriverLimits, InboundHttpResponseWriteDriverLimits)


if __name__ == "__main__":
    unittest.main()
