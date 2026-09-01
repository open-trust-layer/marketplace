from __future__ import annotations

import unittest

from marketplace.reference.local_console_v1 import (
    LocalConsoleInteractionError,
    run_local_buy_sell_console,
)


class ScriptedReader:
    def __init__(self, values: list[object]) -> None:
        self._values = iter(values)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> object:
        self.prompts.append(prompt)
        return next(self._values)


def valid_console_values() -> list[str]:
    return [
        "did:example:seller",
        "urn:example:product:bicycle-1",
        "City bicycle",
        "One carefully maintained bicycle.",
        "125.00",
        "EUR",
        "1",
        "https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1/unit/item",
        "52.520000",
        "13.405000",
        "did:example:buyer",
        "https://example.test/actions/buy",
    ]


class M75LocalConsoleInteractionTests(unittest.TestCase):
    def test_human_console_input_completes_existing_local_buy_sell_demo(self):
        reader = ScriptedReader(valid_console_values())
        output: list[str] = []

        result = run_local_buy_sell_console(read_line=reader, write_line=output.append)

        self.assertEqual(len(reader.prompts), 12)
        self.assertTrue(result.seller_record_id.startswith("r1_"))
        self.assertTrue(result.buyer_record_id.startswith("r1_"))
        self.assertEqual(result.discovered_seller_record_ids, (result.seller_record_id,))
        self.assertEqual(result.match_conclusion, "COMPATIBLE_UNDER_METHOD")
        self.assertFalse(result.protocol_truth)
        self.assertFalse(result.creates_agreement)
        rendered = "\n".join(output)
        self.assertIn("local buy/sell interaction", rendered.lower())
        self.assertIn(f"seller_record_id={result.seller_record_id}", rendered)
        self.assertIn(f"buyer_record_id={result.buyer_record_id}", rendered)
        self.assertIn("protocol_truth=false", rendered)
        self.assertIn("creates_agreement=false", rendered)
        self.assertNotIn("One carefully maintained bicycle.", rendered)
        self.assertNotIn("did:example:buyer", rendered)
        self.assertNotIn("<html", rendered.lower())

    def test_invalid_exact_decimal_fails_without_reflecting_hostile_input(self):
        values = valid_console_values()
        values[4] = "12.3.4-HOSTILE"
        reader = ScriptedReader(values)

        with self.assertRaises(LocalConsoleInteractionError) as raised:
            run_local_buy_sell_console(read_line=reader, write_line=lambda _line: None)

        self.assertEqual(raised.exception.code, "INPUT_INVALID")
        self.assertNotIn("12.3.4-HOSTILE", str(raised.exception))

    def test_oversized_input_fails_before_marketplace_materialization(self):
        values = valid_console_values()
        values[2] = "x" * 5000
        reader = ScriptedReader(values)

        with self.assertRaises(LocalConsoleInteractionError) as raised:
            run_local_buy_sell_console(read_line=reader, write_line=lambda _line: None)

        self.assertEqual(raised.exception.code, "INPUT_INVALID")
        self.assertNotIn("x" * 100, str(raised.exception))

    def test_non_text_reader_value_fails_closed(self):
        values: list[object] = valid_console_values()
        values[0] = b"did:example:seller"
        reader = ScriptedReader(values)

        with self.assertRaises(LocalConsoleInteractionError) as raised:
            run_local_buy_sell_console(read_line=reader, write_line=lambda _line: None)

        self.assertEqual(raised.exception.code, "INPUT_INVALID")

    def test_invalid_coordinate_fails_with_stable_non_reflective_error(self):
        values = valid_console_values()
        values[8] = "91.000001-HOSTILE"
        reader = ScriptedReader(values)

        with self.assertRaises(LocalConsoleInteractionError) as raised:
            run_local_buy_sell_console(read_line=reader, write_line=lambda _line: None)

        self.assertEqual(raised.exception.code, "INPUT_INVALID")
        self.assertNotIn("91.000001-HOSTILE", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
