from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http_response_write_outcome import (
    InboundHttpResponseWriteOutcomeError,
)
from test_inbound_http_response_write_outcome import _parts


class InboundHttpResponseWriteOutcomeCleanupTests(unittest.TestCase):
    def test_explicit_close_recovers_drifted_m46_owned_state(self):
        _, _, _, session, handler = _parts()
        session._bytes_written = 1
        with self.assertRaises(InboundHttpResponseWriteOutcomeError):
            handler.progress()
        handler.close()
        self.assertTrue(session.closed)
        self.assertIsNone(session._prepared_response)

    def test_explicit_close_remains_idempotent_after_terminal_path(self):
        _, _, _, session, handler = _parts()
        handler.close()
        handler.close()
        self.assertTrue(session.closed)
        self.assertIsNone(session._prepared_response)


if __name__ == "__main__":
    unittest.main()
