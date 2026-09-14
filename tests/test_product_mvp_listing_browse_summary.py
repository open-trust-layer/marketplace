from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"


class MarketplaceMvpListingBrowseSummaryTests(unittest.TestCase):
    def listing_summary_block(self) -> str:
        text = APP.read_text(encoding="utf-8")
        return text.split("function productListingSummary(record) {", 1)[1].split("\nfunction proposalResponseSummary", 1)[0]

    def render_list_block(self) -> str:
        text = APP.read_text(encoding="utf-8")
        return text.split("function renderList() {", 1)[1].split("\nfunction selectedProductListingSubjectUri", 1)[0]

    def filtered_records_block(self) -> str:
        text = APP.read_text(encoding="utf-8")
        return text.split("function filteredRecords() {", 1)[1].split("\nfunction localizedIntentCount", 1)[0]

    def test_listing_summary_is_fail_closed_and_uses_reviewed_fields(self):
        block = self.listing_summary_block()
        self.assertIn('/profile/product-listing-v1', block)
        self.assertIn('selectedProductListingSubjectUri(record)', block)
        self.assertIn('/term/consideration', block)
        self.assertIn('/term/quantity', block)
        self.assertIn('consideration.kind !== "monetary"', block)
        self.assertIn('exactDecimalPresentation(consideration.amount)', block)
        self.assertIn('exactDecimalPresentation(quantity.value)', block)
        self.assertIn('actionUri.endsWith("/action/sell")', block)
        self.assertIn('reviewedProposalUri(issuer.principal)', block)
        self.assertIn('reviewedProposalUri(quantity.unit)', block)

    def test_listing_metadata_is_bilingual_and_readable(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn('"Seller {seller} · Price {price} · Quantity {quantity}"', text)
        self.assertIn('"Продавец {seller} · Цена {price} · Количество {quantity}"', text)

    def test_browse_card_shows_listing_metadata_without_changing_identity(self):
        block = self.render_list_block()
        self.assertIn('const listingSummary = summary === null ? productListingSummary(record) : null;', block)
        self.assertIn('i18n.t("browse.listingMetadata"', block)
        self.assertIn('seller: listingSummary.sellerPrincipal', block)
        self.assertIn('price: listingSummary.price', block)
        self.assertIn('quantity: listingSummary.quantity', block)
        self.assertIn('identity.textContent = recordId', block)
        self.assertNotIn('innerHTML', block)

    def test_filter_matches_visible_listing_metadata_without_io(self):
        block = self.filtered_records_block()
        self.assertIn('productListingSummary(record)', block)
        self.assertIn('i18n.t("browse.listingMetadata"', block)
        self.assertIn('[recordId, title, metadata].some', block)
        self.assertNotIn('apiFetch(', block)
        self.assertNotIn('fetch(', block)
        self.assertNotIn('translateRecord', block)
        self.assertNotIn('translateUri', block)


if __name__ == "__main__":
    unittest.main()
