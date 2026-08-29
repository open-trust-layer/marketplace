from __future__ import annotations

import ast
import inspect
import unittest
from unittest.mock import patch

import marketplace.runtime.inbound_http_response_preparer_factory as m56
from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from marketplace.runtime.inbound_http_read_outcome import InboundHttpReadOutcome
from marketplace.runtime.inbound_http_response_prepare import (
    BoundedInboundHttpResponsePreparer,
)
from marketplace.runtime.inbound_http_wire import BoundedInboundHttpWireAdapter
from marketplace.runtime.inbound_http_response_preparer_factory import (
    BoundedInboundHttpResponsePreparerCompositionFactory,
    InboundHttpResponsePreparerCompositionError,
)

AUTHORITY = "market.example"


def _wire_adapter() -> BoundedInboundHttpWireAdapter:
    application = object.__new__(BoundedInboundHttpApplicationAdapter)
    object.__setattr__(application, "_limits", InboundHttpApplicationLimits())
    object.__setattr__(application, "handle", lambda request: None)
    return BoundedInboundHttpWireAdapter(
        application_adapter=application,
        authority=AUTHORITY,
    )


class _Reader:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def __call__(self, max_bytes: int):
        self.calls.append(max_bytes)
        return InboundHttpReadOutcome.eof()


class _Clock:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> float:
        self.calls += 1
        return 0.0


class InboundHttpResponsePreparerCompositionFactoryTests(unittest.TestCase):
    def test_public_surface_is_exact_and_minimal(self):
        constructor = inspect.signature(
            BoundedInboundHttpResponsePreparerCompositionFactory.__init__
        )
        self.assertEqual(
            tuple(constructor.parameters),
            ("self", "wire_adapter", "clock"),
        )
        call = inspect.signature(
            BoundedInboundHttpResponsePreparerCompositionFactory.__call__
        )
        self.assertEqual(tuple(call.parameters), ("self", "reader"))

    def test_one_call_builds_exact_m43_without_invoking_reader_or_clock(self):
        wire = _wire_adapter()
        reader = _Reader()
        clock = _Clock()
        factory = BoundedInboundHttpResponsePreparerCompositionFactory(
            wire_adapter=wire,
            clock=clock,
        )

        preparer = factory(reader)
        self.assertIs(type(preparer), BoundedInboundHttpResponsePreparer)
        self.assertIs(getattr(preparer, "_wire"), wire)
        driver = getattr(preparer, "_driver")
        invoker = getattr(driver, "_invoker")
        self.assertIs(getattr(invoker, "_reader"), reader)
        self.assertIs(getattr(driver, "_clock"), clock)
        self.assertEqual(reader.calls, [])
        self.assertEqual(clock.calls, 0)

    def test_factory_is_one_shot(self):
        reader = _Reader()
        factory = BoundedInboundHttpResponsePreparerCompositionFactory(
            wire_adapter=_wire_adapter(),
            clock=_Clock(),
        )
        factory(reader)

        with self.assertRaises(InboundHttpResponsePreparerCompositionError) as caught:
            factory(reader)

        self.assertEqual(caught.exception.code, "PREPARER_FACTORY_EXHAUSTED")
        self.assertEqual(reader.calls, [])

    def test_rejects_invalid_wire_clock_and_reader(self):
        with self.assertRaises(TypeError):
            BoundedInboundHttpResponsePreparerCompositionFactory(
                wire_adapter=object(),  # type: ignore[arg-type]
                clock=_Clock(),
            )
        with self.assertRaises(InboundHttpResponsePreparerCompositionError) as caught:
            BoundedInboundHttpResponsePreparerCompositionFactory(
                wire_adapter=_wire_adapter(),
                clock=None,  # type: ignore[arg-type]
            )
        self.assertEqual(caught.exception.code, "PREPARER_FACTORY_CLOCK_INVALID")

        factory = BoundedInboundHttpResponsePreparerCompositionFactory(
            wire_adapter=_wire_adapter(),
            clock=_Clock(),
        )
        with self.assertRaises(InboundHttpResponsePreparerCompositionError) as caught:
            factory(None)  # type: ignore[arg-type]
        self.assertEqual(caught.exception.code, "PREPARER_FACTORY_READER_INVALID")

    def test_constructor_graph_substitution_is_blocked_before_execution(self):
        hostile_calls = []
        factory = BoundedInboundHttpResponsePreparerCompositionFactory(
            wire_adapter=_wire_adapter(),
            clock=_Clock(),
        )

        def hostile_init(*args, **kwargs):
            hostile_calls.append((args, kwargs))
            raise AssertionError("hostile constructor MUST NOT execute")

        with patch.object(
            m56.BoundedInboundHttpReadPlanner,
            "__init__",
            hostile_init,
        ):
            with self.assertRaises(
                InboundHttpResponsePreparerCompositionError
            ) as caught:
                factory(_Reader())

        self.assertEqual(caught.exception.code, "PREPARER_FACTORY_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])

    def test_private_binding_witness_poisoning_fails_closed(self):
        reader = _Reader()
        factory = BoundedInboundHttpResponsePreparerCompositionFactory(
            wire_adapter=_wire_adapter(),
            clock=_Clock(),
        )
        object.__setattr__(factory, "_binding_witness", ("poison",))

        with self.assertRaises(InboundHttpResponsePreparerCompositionError) as caught:
            factory(reader)

        self.assertEqual(caught.exception.code, "PREPARER_FACTORY_BINDING_DRIFT")
        self.assertEqual(reader.calls, [])


class InboundHttpResponsePreparerCompositionFactorySourceTests(unittest.TestCase):
    def test_source_has_no_external_io_background_retry_or_loop_surface(self):
        source = inspect.getsource(m56)
        tree = ast.parse(source)
        forbidden_roots = {
            "socket",
            "ssl",
            "asyncio",
            "threading",
            "multiprocessing",
            "subprocess",
            "selectors",
            "select",
            "logging",
            "os",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(
                    all(alias.name.split(".", 1)[0] not in forbidden_roots for alias in node.names)
                )
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".", 1)[0], forbidden_roots)
            self.assertNotIsInstance(node, (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))

        for forbidden in (".recv(", ".send(", ".bind(", ".listen(", ".accept(", ".connect("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
