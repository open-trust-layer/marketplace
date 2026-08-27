from __future__ import annotations

import unittest

import marketplace.runtime as runtime
import marketplace.runtime.inbound_http_response_write_transition as m45


class InboundHttpResponseWriteTransitionExportTests(unittest.TestCase):
    def test_public_runtime_exports_are_exact_m45_symbols(self):
        self.assertIs(runtime.BoundedInboundHttpResponseWriteTransitioner, m45.BoundedInboundHttpResponseWriteTransitioner)
        self.assertIs(runtime.InboundHttpResponseWriteTransition, m45.InboundHttpResponseWriteTransition)
        self.assertIs(runtime.InboundHttpResponseWriteTransitionError, m45.InboundHttpResponseWriteTransitionError)


if __name__ == "__main__":
    unittest.main()
