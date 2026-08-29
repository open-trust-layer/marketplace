from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http_accept import BoundedInboundHttpSingleAccept
from marketplace.runtime.inbound_tcp_listener import BoundedInboundTcpListenerConstruction


class _Listener:
    def __init__(self) -> None:
        self.bind_calls: list[tuple[str, int]] = []
        self.listen_calls: list[int] = []
        self.close_calls = 0

    def bind(self, address: tuple[str, int]) -> None:
        self.bind_calls.append(address)

    def listen(self, backlog: int) -> None:
        self.listen_calls.append(backlog)

    def accept(self):
        raise AssertionError("source acceptance MUST NOT call accept")

    def close(self) -> None:
        self.close_calls += 1


class InboundTcpListenerConstructionTests(unittest.TestCase):
    def test_construct_once_binds_listens_and_returns_exact_m52_boundary(self):
        listener = _Listener()
        factory_calls: list[object] = []

        def factory():
            factory_calls.append(object())
            return listener

        boundary = BoundedInboundTcpListenerConstruction(
            factory=factory,
            host="127.0.0.1",
            port=18443,
            backlog=1,
        )

        accept_boundary = boundary.construct_once()

        self.assertIs(type(accept_boundary), BoundedInboundHttpSingleAccept)
        self.assertEqual(len(factory_calls), 1)
        self.assertEqual(listener.bind_calls, [("127.0.0.1", 18443)])
        self.assertEqual(listener.listen_calls, [1])
        self.assertEqual(listener.close_calls, 0)


if __name__ == "__main__":
    unittest.main()
