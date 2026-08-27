import unittest

from marketplace import runtime
from marketplace.runtime.inbound_http_response_write_invoke import (
    WRITE_INVOCATION_COMPLETED,
    WRITE_INVOCATION_PROGRESS,
    BoundedInboundHttpResponseWriteInvoker,
    InboundHttpResponseWriteInvocationError,
    InboundHttpResponseWriteInvocationResult,
)


class InboundHttpResponseWriteInvocationExportTests(unittest.TestCase):
    def test_public_runtime_exports_are_exact_m48_symbols(self):
        self.assertIs(runtime.WRITE_INVOCATION_COMPLETED, WRITE_INVOCATION_COMPLETED)
        self.assertIs(runtime.WRITE_INVOCATION_PROGRESS, WRITE_INVOCATION_PROGRESS)
        self.assertIs(runtime.BoundedInboundHttpResponseWriteInvoker, BoundedInboundHttpResponseWriteInvoker)
        self.assertIs(runtime.InboundHttpResponseWriteInvocationError, InboundHttpResponseWriteInvocationError)
        self.assertIs(runtime.InboundHttpResponseWriteInvocationResult, InboundHttpResponseWriteInvocationResult)


if __name__ == "__main__":
    unittest.main()
