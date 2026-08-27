from __future__ import annotations

import unittest

import marketplace.runtime as runtime
from marketplace.runtime.inbound_http_response_write_outcome import (
    WRITE_OUTCOME_FAILURE,
    WRITE_OUTCOME_PROGRESS,
    WRITE_OUTCOME_ZERO,
    BoundedInboundHttpResponseWriteOutcomeHandler,
    InboundHttpResponseWriteOutcome,
    InboundHttpResponseWriteOutcomeError,
)


class InboundHttpResponseWriteOutcomeExportTests(unittest.TestCase):
    def test_public_runtime_exports_are_exact_m47_symbols(self):
        self.assertIs(
            runtime.BoundedInboundHttpResponseWriteOutcomeHandler,
            BoundedInboundHttpResponseWriteOutcomeHandler,
        )
        self.assertIs(runtime.InboundHttpResponseWriteOutcome, InboundHttpResponseWriteOutcome)
        self.assertIs(
            runtime.InboundHttpResponseWriteOutcomeError,
            InboundHttpResponseWriteOutcomeError,
        )
        self.assertEqual(runtime.WRITE_OUTCOME_PROGRESS, WRITE_OUTCOME_PROGRESS)
        self.assertEqual(runtime.WRITE_OUTCOME_ZERO, WRITE_OUTCOME_ZERO)
        self.assertEqual(runtime.WRITE_OUTCOME_FAILURE, WRITE_OUTCOME_FAILURE)


if __name__ == "__main__":
    unittest.main()
