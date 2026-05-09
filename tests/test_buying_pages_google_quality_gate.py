from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages import (  # noqa: E402
    ApprovalStatus,
    BuyingPagesRepository,
    evaluate_google_quality_gate,
    generate_first_scale_batch,
    is_publicly_eligible,
    render_buying_pages_sitemap_xml,
)
from picwise_buying_pages.fixtures import load_seed_buying_pages  # noqa: E402
from picwise_buying_pages.models import IndexStatus  # noqa: E402
from picwise_buying_pages.models import SellerReliabilityStatus  # noqa: E402


def _unsafe_mutate_page(page, **changes):
    for key, value in changes.items():
        object.__setattr__(page, key, value)
    return page


class BuyingPagesGoogleQualityGateTests(unittest.TestCase):
    def test_keyword_only_pages_are_rejected(self) -> None:
        page = load_seed_buying_pages()[0]
        mutated = _unsafe_mutate_page(
            page,
            products=tuple(
                replace(product, reason_summary="keyword", buying_reason="keyword")
                for product in page.products
            ),
            faq_items=tuple(),
            related_searches=tuple(),
        )
        result = evaluate_google_quality_gate(mutated)
        self.assertFalse(result.quality_passed)
        self.assertIn("weak_unique_user_value", result.reasons)
        self.assertIn("missing_required_faq", result.reasons)
        self.assertIn("missing_required_related_searches", result.reasons)

    def test_duplicate_and_near_duplicate_keywords_are_rejected(self) -> None:
        pages = load_seed_buying_pages()
        base_page = pages[0]
        duplicate = _unsafe_mutate_page(
            replace(pages[1]),
            main_keyword=base_page.main_keyword,
            keyword_aliases=pages[1].keyword_aliases,
        )
        result = evaluate_google_quality_gate(duplicate, existing_pages=(base_page,))
        self.assertFalse(result.quality_passed)
        self.assertTrue(
            "duplicate_keyword" in result.reasons or "near_duplicate_keyword" in result.reasons
        )

    def test_thin_affiliate_pages_are_rejected(self) -> None:
        page = load_seed_buying_pages()[1]
        mutated = _unsafe_mutate_page(
            page,
            products=tuple(
                replace(product, reason_summary="ok", buying_reason="ok")
                for product in page.products
            ),
        )
        result = evaluate_google_quality_gate(mutated)
        self.assertFalse(result.quality_passed)
        self.assertIn("thin_affiliate_page", result.reasons)

    def test_doorway_style_pages_are_rejected(self) -> None:
        page = load_seed_buying_pages()[2]
        mutated = _unsafe_mutate_page(page, slug=f"{page.slug}--city-doorway")
        result = evaluate_google_quality_gate(mutated)
        self.assertFalse(result.quality_passed)
        self.assertIn("doorway_style_slug", result.reasons)

    def test_fake_price_review_rating_availability_markers_are_rejected(self) -> None:
        page = load_seed_buying_pages()[3]
        products = (
            replace(
                page.products[0],
                availability="fake_in_stock",
                reason_summary="fake reviews and ratings here",
                suspicious_markers=("fake_price",),
            ),
            *page.products[1:],
        )
        mutated = _unsafe_mutate_page(
            page,
            products=products,
        )
        result = evaluate_google_quality_gate(mutated)
        self.assertFalse(result.quality_passed)
        self.assertIn("fake_product_data", result.reasons)
        self.assertIn("product_display_incomplete", result.reasons)

    def test_unknown_seller_requires_manual_review_and_is_not_public(self) -> None:
        page = load_seed_buying_pages()[0]
        unknown = _unsafe_mutate_page(
            replace(page),
            products=(
                replace(page.products[0], seller_reliability_status=SellerReliabilityStatus.UNKNOWN),
                *page.products[1:],
            ),
        )
        result = evaluate_google_quality_gate(unknown)
        self.assertFalse(result.publication_ready)
        self.assertFalse(is_publicly_eligible(unknown))
        self.assertIn("seller_manual_review_required", result.reasons)

    def test_structured_data_mismatch_is_rejected(self) -> None:
        page = load_seed_buying_pages()[4]
        structured_data = {
            "products": [
                {
                    "product_id": page.products[0].product_id,
                    "price": page.products[0].price + 5.0,
                    "availability": page.products[0].availability,
                }
            ]
        }
        result = evaluate_google_quality_gate(page, structured_data=structured_data)
        self.assertFalse(result.quality_passed)
        self.assertIn("structured_data_mismatch", result.reasons)

    def test_candidate_pages_stay_non_public_until_explicitly_approved(self) -> None:
        candidate = generate_first_scale_batch().candidate_pages[0]
        result = evaluate_google_quality_gate(candidate, economic_score_passed=False)
        self.assertEqual(candidate.index_status, IndexStatus.NOINDEX)
        self.assertEqual(candidate.approval_status, ApprovalStatus.PENDING_REVIEW)
        self.assertFalse(result.publication_ready)
        self.assertFalse(is_publicly_eligible(candidate, economic_score_passed=False))
        self.assertIn("approval_status_not_approved", result.reasons)
        self.assertIn("index_gate_not_passed", result.reasons)

    def test_sitemap_only_includes_quality_index_and_approval_passing_pages(self) -> None:
        pages = load_seed_buying_pages()
        page = pages[0]
        pending = _unsafe_mutate_page(replace(pages[1]), approval_status=ApprovalStatus.PENDING_REVIEW)
        noindex = _unsafe_mutate_page(replace(pages[2]), index_status=IndexStatus.NOINDEX)
        broken = _unsafe_mutate_page(
            replace(pages[3]),
            products=tuple(
                replace(product, reason_summary="placeholder", buying_reason="placeholder")
                for product in pages[3].products
            ),
        )
        xml = render_buying_pages_sitemap_xml((page, pending, noindex, broken), base_url="https://localhost")
        self.assertIn(f"/best/{page.slug}", xml)
        self.assertNotIn(f"/best/{pending.slug}", xml)
        self.assertNotIn(f"/best/{noindex.slug}", xml)
        self.assertNotIn(f"/best/{broken.slug}", xml)

    def test_route_lookup_repository_excludes_quality_failed_candidates(self) -> None:
        pages = load_seed_buying_pages()
        page = pages[0]
        broken = _unsafe_mutate_page(
            replace(pages[1]),
            products=tuple(
                replace(product, reason_summary="placeholder", buying_reason="placeholder")
                for product in pages[1].products
            ),
        )
        public_pages = tuple(candidate for candidate in (page, broken) if is_publicly_eligible(candidate))
        repository = BuyingPagesRepository(public_pages)
        self.assertIsNotNone(repository.get_by_slug(page.slug))
        self.assertIsNone(repository.get_by_slug(broken.slug))

    def test_missing_anchor_price_blocks_public_eligibility(self) -> None:
        page = next(item for item in load_seed_buying_pages() if item.price_band_applicable)
        no_anchor = _unsafe_mutate_page(
            replace(page),
            products=(
                replace(page.products[0], price=42.0),
                replace(page.products[1], price=65.0),
                replace(page.products[2], price=301.0),
                replace(page.products[3], price=420.0),
            ),
        )
        self.assertFalse(is_publicly_eligible(no_anchor))
        self.assertIn("missing_price_band_anchor", evaluate_google_quality_gate(no_anchor).reasons)

    def test_non_standard_pages_can_skip_price_band_without_forcing_80_250(self) -> None:
        page = next(item for item in load_seed_buying_pages() if not item.price_band_applicable)
        widened = _unsafe_mutate_page(
            replace(page),
            products=(
                replace(page.products[0], price=35.0),
                replace(page.products[1], price=410.0),
                page.products[2],
                page.products[3],
            ),
        )
        result = evaluate_google_quality_gate(widened)
        self.assertTrue(result.publication_ready)
        self.assertNotIn("index_gate_not_passed", result.reasons)


if __name__ == "__main__":
    unittest.main()
