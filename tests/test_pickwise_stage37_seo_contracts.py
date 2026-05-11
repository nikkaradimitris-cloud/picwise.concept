from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.seo_contracts import (  # noqa: E402
    PageQualityStatus,
    SEOIndexStatus,
    SEOBuyingPage,
    SEOBuyingPageContractError,
)
from picwise_offers import RecommendationStatus  # noqa: E402
from picwise_mvp import run_pickwise_mvp_search_flow  # noqa: E402


def _build_contract_page(index_status: SEOIndexStatus = SEOIndexStatus.INDEXABLE) -> SEOBuyingPage:
    flow = run_pickwise_mvp_search_flow("power bank for iphone")
    recommendation_set = replace(flow.recommendation_set, status=RecommendationStatus.READY)
    return SEOBuyingPage(
        page_id="seo-test-1",
        slug="power-bank-for-iphone",
        canonical_path="/best/power-bank-for-iphone",
        main_keyword="power bank for iphone",
        query_aliases=("best power bank for iphone",),
        detected_intent="general_intent",
        vertical="retail_physical_products",
        retail_engine="electronics_hypermarket",
        category_bucket="power_banks",
        google_taxonomy_path="Electronics > Electronics Accessories > Power Banks",
        saas_erp_contract_ref=None,
        finance_insurance_contract_ref=None,
        recommendation_set=recommendation_set,
        wise_recommended_product=recommendation_set.wise_recommended_product,
        product_slot_count=4,
        valid_product_count=4,
        page_quality_status=PageQualityStatus.QUALITY_PASSED if index_status == SEOIndexStatus.INDEXABLE else PageQualityStatus.NEEDS_DATA,
        index_status=index_status,
        noindex_reason=None if index_status == SEOIndexStatus.INDEXABLE else "needs_data",
        sitemap_eligible=index_status == SEOIndexStatus.INDEXABLE,
        last_updated=datetime.now(tz=timezone.utc),
        metadata={"title": "Best options for power bank for iphone | PickWise"},
    )


class PickWiseStage37SEOContractsTests(unittest.TestCase):
    def test_indexable_contract_requires_quality_passed_and_sitemap_eligible(self) -> None:
        page = _build_contract_page()
        self.assertEqual(page.index_status, SEOIndexStatus.INDEXABLE)
        self.assertEqual(page.page_quality_status, PageQualityStatus.QUALITY_PASSED)
        self.assertTrue(page.sitemap_eligible)
        self.assertEqual(page.robots_meta, "index,follow")

    def test_non_indexable_contract_requires_noindex_reason(self) -> None:
        page = _build_contract_page(index_status=SEOIndexStatus.NOINDEX)
        self.assertEqual(page.robots_meta, "noindex,follow")
        self.assertEqual(page.noindex_reason, "needs_data")

    def test_canonical_path_must_match_slug_under_best(self) -> None:
        with self.assertRaises(SEOBuyingPageContractError):
            replace(_build_contract_page(), canonical_path="/results/power-bank-for-iphone")

    def test_negative_counts_are_rejected(self) -> None:
        with self.assertRaises(SEOBuyingPageContractError):
            replace(_build_contract_page(), valid_product_count=-1)


if __name__ == "__main__":
    unittest.main()
