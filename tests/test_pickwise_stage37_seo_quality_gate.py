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
from picwise_buying_pages.seo_quality_gate import SEOQualityGateInput, evaluate_seo_quality_gate  # noqa: E402
from picwise_mvp import run_pickwise_mvp_search_flow  # noqa: E402
from picwise_offers import ProductSourceStatus, RecommendationStatus  # noqa: E402


def _base_payload() -> SEOQualityGateInput:
    flow = run_pickwise_mvp_search_flow("power bank for iphone")
    recommendation = replace(flow.recommendation_set, status=RecommendationStatus.READY)
    return SEOQualityGateInput(
        main_keyword="power bank for iphone",
        detected_intent="general_intent",
        vertical="retail_physical_products",
        source_status=ProductSourceStatus.CONNECTED,
        recommendation_set=recommendation,
        product_slot_count=4,
        valid_product_count=4,
        canonical_path="/best/power-bank-for-iphone",
        slug_is_valid=True,
        slug_is_unique=True,
        has_content=True,
        finance_insurance_contract_ref=None,
    )


class PickWiseStage37SEOQualityGateTests(unittest.TestCase):
    def test_quality_passes_for_valid_ready_payload(self) -> None:
        result = evaluate_seo_quality_gate(_base_payload())
        self.assertEqual(result.page_quality_status, PageQualityStatus.QUALITY_PASSED)
        self.assertEqual(result.index_status, SEOIndexStatus.INDEXABLE)
        self.assertTrue(result.sitemap_eligible)

    def test_source_not_connected_is_needs_data_noindex(self) -> None:
        payload = replace(_base_payload(), source_status=ProductSourceStatus.NOT_CONNECTED)
        result = evaluate_seo_quality_gate(payload)
        self.assertEqual(result.page_quality_status, PageQualityStatus.NEEDS_DATA)
        self.assertEqual(result.index_status, SEOIndexStatus.NOINDEX)
        self.assertIn("source_not_connected:not_connected", result.reasons)

    def test_insufficient_valid_products_is_noindex(self) -> None:
        payload = replace(_base_payload(), valid_product_count=2, product_slot_count=2)
        result = evaluate_seo_quality_gate(payload)
        self.assertEqual(result.page_quality_status, PageQualityStatus.NEEDS_DATA)
        self.assertEqual(result.index_status, SEOIndexStatus.NOINDEX)
        self.assertIn("not_enough_valid_products", result.reasons)

    def test_finance_vertical_is_manual_review(self) -> None:
        payload = replace(
            _base_payload(),
            vertical="finance_insurance_business_finance",
            finance_insurance_contract_ref="finance_insurance_stage28f_contract",
        )
        result = evaluate_seo_quality_gate(payload)
        self.assertEqual(result.page_quality_status, PageQualityStatus.MANUAL_REVIEW)
        self.assertEqual(result.index_status, SEOIndexStatus.MANUAL_REVIEW)
        self.assertIn("finance_regulated_manual_review_only", result.reasons)

    def test_invalid_slug_or_canonical_is_blocked(self) -> None:
        payload = replace(
            _base_payload(),
            slug_is_valid=False,
            canonical_path="/search/power-bank-for-iphone",
        )
        result = evaluate_seo_quality_gate(payload)
        self.assertEqual(result.page_quality_status, PageQualityStatus.BLOCKED)
        self.assertEqual(result.index_status, SEOIndexStatus.BLOCKED)
        self.assertIn("invalid_slug", result.reasons)


if __name__ == "__main__":
    unittest.main()
