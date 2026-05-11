from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.seo_contracts import PageQualityStatus, SEOIndexStatus  # noqa: E402
from picwise_buying_pages.seo_page_builder import SEOPageBuildRequest, build_seo_buying_page  # noqa: E402
from picwise_mvp import run_pickwise_mvp_search_flow  # noqa: E402
from picwise_offers import ProductSourceStatus, RecommendationStatus  # noqa: E402


def _request_for_query(query: str) -> SEOPageBuildRequest:
    flow = run_pickwise_mvp_search_flow(query)
    return SEOPageBuildRequest(
        target_query=query,
        query_aliases=(query, f"best {query}"),
        search_decision=flow.search_decision,
        intake_result=flow.intake_result,
        eligibility_result=flow.eligibility_result,
        recommendation_set=flow.recommendation_set,
    )


class PickWiseStage37PageBuilderTests(unittest.TestCase):
    def test_builder_emits_indexable_page_for_valid_retail_flow(self) -> None:
        request = _request_for_query("power bank for iphone")
        page = build_seo_buying_page(request)
        self.assertEqual(page.index_status, SEOIndexStatus.INDEXABLE)
        self.assertEqual(page.page_quality_status, PageQualityStatus.QUALITY_PASSED)
        self.assertTrue(page.sitemap_eligible)
        self.assertEqual(page.canonical_path, f"/best/{page.slug}")

    def test_builder_sets_noindex_needs_data_when_source_not_connected(self) -> None:
        request = _request_for_query("power bank for iphone")
        request = replace(
            request,
            intake_result=replace(request.intake_result, status=ProductSourceStatus.NOT_CONNECTED),
        )
        page = build_seo_buying_page(request)
        self.assertEqual(page.page_quality_status, PageQualityStatus.NEEDS_DATA)
        self.assertEqual(page.index_status, SEOIndexStatus.NOINDEX)
        self.assertFalse(page.sitemap_eligible)

    def test_builder_sets_noindex_when_not_enough_valid_products(self) -> None:
        request = _request_for_query("power bank for iphone")
        request = replace(
            request,
            recommendation_set=replace(
                request.recommendation_set,
                status=RecommendationStatus.NOT_ENOUGH_VALID_CANDIDATES,
                display_slots=request.recommendation_set.display_slots[:2],
                wise_recommended_product=None,
            ),
            eligibility_result=replace(
                request.eligibility_result,
                eligible_candidates=request.eligibility_result.eligible_candidates[:2],
            ),
        )
        page = build_seo_buying_page(request)
        self.assertEqual(page.page_quality_status, PageQualityStatus.NEEDS_DATA)
        self.assertEqual(page.index_status, SEOIndexStatus.NOINDEX)
        self.assertEqual(page.valid_product_count, 2)
        self.assertIsNone(page.wise_recommended_product)

    def test_builder_sets_manual_review_for_finance_flow(self) -> None:
        request = _request_for_query("loan insurance comparison")
        page = build_seo_buying_page(request)
        self.assertEqual(page.page_quality_status, PageQualityStatus.MANUAL_REVIEW)
        self.assertEqual(page.index_status, SEOIndexStatus.MANUAL_REVIEW)
        self.assertFalse(page.sitemap_eligible)

    def test_builder_blocks_invalid_slug(self) -> None:
        request = _request_for_query("!!")
        page = build_seo_buying_page(request)
        self.assertEqual(page.page_quality_status, PageQualityStatus.BLOCKED)
        self.assertEqual(page.index_status, SEOIndexStatus.BLOCKED)
        self.assertEqual(page.slug, "invalid")

    def test_builder_filters_slots_outside_eligible_set(self) -> None:
        request = _request_for_query("power bank for iphone")
        request = replace(
            request,
            eligibility_result=replace(
                request.eligibility_result,
                eligible_candidates=request.eligibility_result.eligible_candidates[:3],
            ),
        )
        page = build_seo_buying_page(request)
        self.assertEqual(page.valid_product_count, 3)
        self.assertEqual(page.product_slot_count, 3)
        self.assertEqual(page.page_quality_status, PageQualityStatus.NEEDS_DATA)


if __name__ == "__main__":
    unittest.main()
