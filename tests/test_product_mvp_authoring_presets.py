from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"


class MarketplaceMvpAuthoringPresetTests(unittest.TestCase):
    def test_listing_form_exposes_non_submitting_presets(self):
        text = INDEX.read_text(encoding="utf-8")
        for preset_id in ("preset-price-scale-2", "preset-quantity-one"):
            fragment = text.split(f'id="{preset_id}"', 1)[1].split(">", 1)[0]
            self.assertIn('type="button"', fragment)
            self.assertIn('class="secondary"', fragment)
        self.assertIn("Use 2-decimal price", text)
        self.assertIn("Set quantity to 1", text)

    def test_presets_touch_only_explicit_transport_fields(self):
        text = APP.read_text(encoding="utf-8")
        price = text.split("function applyPriceScale2Preset() {", 1)[1].split("}", 1)[0]
        quantity = text.split("function applyQuantityOnePreset() {", 1)[1].split("}", 1)[0]
        self.assertIn('consideration_scale: "2"', price)
        self.assertIn('quantity_coefficient: "1"', quantity)
        self.assertIn('quantity_scale: "0"', quantity)
        for forbidden in ("currency_code", "unit_uri", "latitude_e6", "longitude_e6", "seller_principal", "subject_uri"):
            self.assertNotIn(forbidden, price)
            self.assertNotIn(forbidden, quantity)

    def test_presets_refresh_preview_and_never_submit_or_fetch(self):
        text = APP.read_text(encoding="utf-8")
        start = text.index("function applyListingPreset")
        end = text.index("function fillSyntheticProposalExample", start)
        block = text[start:end]
        self.assertIn('fillSyntheticExample("create", values)', block)
        self.assertIn("renderListingDraftPreview()", block)
        self.assertIn('setFormStatus("create-status", "author.presetApplied")', block)
        for forbidden in ("apiFetch", "fetch(", "submit()", "requestSubmit", "localStorage", "sessionStorage"):
            self.assertNotIn(forbidden, block)

    def test_presets_are_bilingual_and_wired_explicitly(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn('"author.priceScale2Preset": ["Use 2-decimal price", "Цена с 2 знаками после запятой"]', text)
        self.assertIn('"author.quantityOnePreset": ["Set quantity to 1", "Установить количество 1"]', text)
        self.assertIn('"author.presetApplied": ["Preset applied. Review remaining fields before submitting."', text)
        self.assertIn('byId("preset-price-scale-2").addEventListener("click", applyPriceScale2Preset)', text)
        self.assertIn('byId("preset-quantity-one").addEventListener("click", applyQuantityOnePreset)', text)


if __name__ == "__main__":
    unittest.main()
