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
from picwise_buying_pages.models import SellerReliabilityStatus  # noqa: E402


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
        self.assertTrue(any("missing_affiliate_url" in reason for reason in result.reasons))

    def test_product_without_availability_fails_public_index_eligibility(self) -> None:
        page = load_seed_buying_pages()[1]
        broken_product = replace(page.products[0])
        object.__setattr__(broken_product, "availability", "")
        mutated = _unsafe_mutate_page(page, products=(broken_product, *page.products[1:]))
        result = evaluate_index_gate(mutated)
        self.assertFalse(result.indexable)
        self.assertTrue(any("missing_or_invalid_availability" in reason for reason in result.reasons))

    def test_product_without_image_fails_when_required(self) -> None:
        page = load_seed_buying_pages()[1]
        broken_product = replace(page.products[0])
        object.__setattr__(broken_product, "image_url", "")
        result = evaluate_index_gate(_unsafe_mutate_page(page, products=(broken_product, *page.products[1:])))
        self.assertFalse(result.indexable)
        self.assertTrue(any("missing_image" in reason for reason in result.reasons))

    def test_product_without_price_fails_when_price_is_applicable(self) -> None:
        page = load_seed_buying_pages()[1]
        broken_product = replace(page.products[0], price=0.0)
        result = evaluate_index_gate(_unsafe_mutate_page(page, products=(broken_product, *page.products[1:])))
        self.assertFalse(result.indexable)
        self.assertTrue(any("missing_or_invalid_price" in reason for reason in result.reasons))

    def test_product_without_useful_specs_fails(self) -> None:
        page = load_seed_buying_pages()[1]
        broken_product = replace(page.products[0], specifications=("Spec",))
        result = evaluate_index_gate(_unsafe_mutate_page(page, products=(broken_product, *page.products[1:])))
        self.assertFalse(result.indexable)
        self.assertTrue(any("missing_useful_specs" in reason for reason in result.reasons))

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

    def test_physical_page_without_anchor_product_fails(self) -> None:
        page = next(page for page in load_seed_buying_pages() if page.price_band_applicable)
        out_of_band_products = tuple(
            replace(product, price=39.0 + idx * 10.0)
            for idx, product in enumerate(page.products)
        )
        mutated = _unsafe_mutate_page(page, products=out_of_band_products)
        result = evaluate_index_gate(mutated)
        self.assertFalse(result.indexable)
        self.assertIn("missing_in_band_anchor_product", result.reasons)

    def test_price_band_anchor_with_useful_lower_higher_variants_can_pass(self) -> None:
        page = next(page for page in load_seed_buying_pages() if page.price_band_applicable)
        variant_ok = _unsafe_mutate_page(
            replace(page),
            products=(
                replace(
                    page.products[0],
                    price=74.0,
                    comparison_family=page.products[1].comparison_family,
                ),
                replace(page.products[1], price=120.0),
                replace(page.products[2], price=240.0),
                replace(
                    page.products[3],
                    price=279.0,
                    comparison_family=page.products[1].comparison_family,
                ),
            ),
        )
        self.assertTrue(evaluate_index_gate(variant_ok).indexable)

    def test_unrelated_cheap_or_expensive_filler_fails(self) -> None:
        page = next(page for page in load_seed_buying_pages() if page.price_band_applicable)
        broken = _unsafe_mutate_page(
            replace(page),
            products=(
                replace(page.products[0], price=120.0, comparison_family="anchor-family"),
                replace(page.products[1], price=95.0, comparison_family="anchor-family"),
                replace(
                    page.products[2],
                    title="Totally Unrelated Generic Item",
                    brand="Different Brand",
                    price=29.0,
                    comparison_family="unrelated-family",
                ),
                replace(
                    page.products[3],
                    title="Another Unrelated Premium Item",
                    brand="Different Brand",
                    price=399.0,
                    comparison_family="other-family",
                ),
            ),
        )
        result = evaluate_index_gate(broken)
        self.assertFalse(result.indexable)
        self.assertIn("price_variant_not_same_family_or_useful", result.reasons)

    def test_price_band_cannot_be_disabled_for_physical_categories(self) -> None:
        page = next(page for page in load_seed_buying_pages() if page.price_band_applicable)
        mutated = _unsafe_mutate_page(
            replace(page),
            price_band_applicable=False,
            target_price_min_eur=None,
            target_price_max_eur=None,
        )
        result = evaluate_index_gate(mutated)
        self.assertFalse(result.indexable)
        self.assertIn("price_band_bypass_for_physical_category", result.reasons)

    def test_seller_reliability_statuses_are_enforced(self) -> None:
        page = load_seed_buying_pages()[0]
        trusted = evaluate_index_gate(
            _unsafe_mutate_page(
                replace(page),
                products=(replace(page.products[0], seller_reliability_status=SellerReliabilityStatus.TRUSTED), *page.products[1:]),
            )
        )
        acceptable = evaluate_index_gate(
            _unsafe_mutate_page(
                replace(page),
                products=(replace(page.products[0], seller_reliability_status=SellerReliabilityStatus.ACCEPTABLE), *page.products[1:]),
            )
        )
        unknown = evaluate_index_gate(
            _unsafe_mutate_page(
                replace(page),
                products=(replace(page.products[0], seller_reliability_status=SellerReliabilityStatus.UNKNOWN), *page.products[1:]),
            )
        )
        unreliable = evaluate_index_gate(
            _unsafe_mutate_page(
                replace(page),
                products=(replace(page.products[0], seller_reliability_status=SellerReliabilityStatus.UNRELIABLE), *page.products[1:]),
            )
        )
        blocked = evaluate_index_gate(
            _unsafe_mutate_page(
                replace(page),
                products=(replace(page.products[0], seller_reliability_status=SellerReliabilityStatus.BLOCKED), *page.products[1:]),
            )
        )
        self.assertTrue(trusted.indexable)
        self.assertTrue(acceptable.indexable)
        self.assertFalse(unknown.indexable)
        self.assertFalse(unreliable.indexable)
        self.assertFalse(blocked.indexable)
        self.assertTrue(any("seller_manual_review_required" in reason for reason in unknown.reasons))
        self.assertTrue(any("seller_unreliable_or_blocked" in reason for reason in unreliable.reasons))
        self.assertTrue(any("seller_unreliable_or_blocked" in reason for reason in blocked.reasons))

    def test_duplicate_or_near_duplicate_slots_fail(self) -> None:
        page = load_seed_buying_pages()[0]
        duplicated = _unsafe_mutate_page(
            replace(page),
            products=(
                page.products[0],
                replace(page.products[1], title=page.products[0].title),
                page.products[2],
                page.products[3],
            ),
        )
        result = evaluate_index_gate(duplicated)
        self.assertFalse(result.indexable)
        self.assertIn("duplicate_or_near_duplicate_products", result.reasons)

    def test_recommended_product_must_be_selected_from_valid_products(self) -> None:
        page = load_seed_buying_pages()[0]
        invalid_product = replace(page.products[0], seller_reliability_status=SellerReliabilityStatus.BLOCKED)
        mutated = _unsafe_mutate_page(
            replace(page),
            products=(invalid_product, *page.products[1:]),
            recommended_product_id=invalid_product.product_id,
        )
        result = evaluate_index_gate(mutated)
        self.assertFalse(result.indexable)
        self.assertIn("recommended_product_not_publicly_valid", result.reasons)


if __name__ == "__main__":
    unittest.main()
