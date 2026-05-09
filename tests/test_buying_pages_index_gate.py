from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.fixtures import load_seed_buying_pages  # noqa: E402
from picwise_buying_pages.index_gate import evaluate_index_gate  # noqa: E402
from picwise_buying_pages.models import ProductSlot  # noqa: E402


def _unsafe_mutate_page(page, **changes):
    for key, value in changes.items():
        object.__setattr__(page, key, value)
    return page


class BuyingPagesIndexGateTests(unittest.TestCase):
    def test_indexable_valid_page_passes(self) -> None:
        page = load_seed_buying_pages()[0]
        result = evaluate_index_gate(page)
        self.assertTrue(result.indexable)
        self.assertEqual(result.robots_meta_value, "index,follow")

    def test_noindex_page_is_excluded(self) -> None:
        page = next(page for page in load_seed_buying_pages() if str(page.index_status) == "IndexStatus.NOINDEX")
        result = evaluate_index_gate(page)
        self.assertFalse(result.indexable)
        self.assertIn("index_status_not_indexable", result.reasons)

    def test_missing_affiliate_or_product_url_fails(self) -> None:
        page = load_seed_buying_pages()[1]
        broken_product = replace(page.products[0], affiliate_url=None)
        mutated = _unsafe_mutate_page(page, products=(broken_product, *page.products[1:]))
        result = evaluate_index_gate(mutated)
        self.assertFalse(result.indexable)
        self.assertIn("missing_affiliate_url", result.reasons)

    def test_invalid_product_count_fails(self) -> None:
        page = load_seed_buying_pages()[2]
        mutated = _unsafe_mutate_page(page, products=page.products[:3])
        result = evaluate_index_gate(mutated)
        self.assertFalse(result.indexable)
        self.assertIn("invalid_product_count", result.reasons)

    def test_invalid_recommended_product_fails(self) -> None:
        page = load_seed_buying_pages()[3]
        mutated = _unsafe_mutate_page(page, recommended_product_id="missing-product")
        result = evaluate_index_gate(mutated)
        self.assertFalse(result.indexable)
        self.assertIn("invalid_recommended_product", result.reasons)

    def test_physical_price_band_failure_fails(self) -> None:
        page = next(page for page in load_seed_buying_pages() if page.price_band_applicable)
        out_of_band: ProductSlot = replace(page.products[0], price=35.0)
        mutated = _unsafe_mutate_page(page, products=(out_of_band, *page.products[1:]))
        result = evaluate_index_gate(mutated)
        self.assertFalse(result.indexable)
        self.assertIn("price_band_out_of_range", result.reasons)


if __name__ == "__main__":
    unittest.main()
