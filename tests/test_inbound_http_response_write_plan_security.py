from __future__ import annotations

import unittest

import marketplace.runtime as runtime
from marketplace.runtime.inbound_http_response_write_plan import (
    BoundedInboundHttpResponseWritePlanner,
    InboundHttpResponseWritePlanError,
)
from test_inbound_http_response_write_plan import _prepared


class InboundHttpResponseWritePlanSecurityTests(unittest.TestCase):
    def test_top_level_m43_authority_promotion_is_rejected_before_replay(self):
        prepared = _prepared()
        object.__setattr__(prepared, "request_authenticated", True)
        with self.assertRaises(InboundHttpResponseWritePlanError) as ctx:
            BoundedInboundHttpResponseWritePlanner().plan(
                prepared, write_calls_completed=0, bytes_written=0
            )
        self.assertEqual(ctx.exception.code, "WRITE_AUTHORITY_ESCALATION")

    def test_public_exports_are_exact_m44_symbols(self):
        import marketplace.runtime.inbound_http_response_write_plan as m44

        self.assertIs(runtime.BoundedInboundHttpResponseWritePlanner, m44.BoundedInboundHttpResponseWritePlanner)
        self.assertIs(runtime.InboundHttpResponseWriteLimits, m44.InboundHttpResponseWriteLimits)
        self.assertIs(runtime.InboundHttpResponseWritePlan, m44.InboundHttpResponseWritePlan)
        self.assertIs(runtime.InboundHttpResponseWritePlanError, m44.InboundHttpResponseWritePlanError)
        self.assertEqual(runtime.WRITE_ACTION_WRITE, m44.WRITE_ACTION_WRITE)
        self.assertEqual(runtime.WRITE_ACTION_COMPLETE, m44.WRITE_ACTION_COMPLETE)


if __name__ == "__main__":
    unittest.main()
