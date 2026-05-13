from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app.buying_routes import get_buying_pages_repository, render_best_slug_html  # noqa: E402
from picwise_offers import (  # noqa: E402
    SourceTrustLevel,
    adapt_affiliate_feed_rows,
    build_pickwise_recommendation_set,
    run_product_eligibility_gate,
)
from picwise_offers.recommendation_engine import RecommendationStatus  # noqa: E402


class PickWiseStage38RealOfferSourceAdapterTests(unittest.TestCase):
    def test_valid_affiliate_row_maps_to_offer_candidate(self) -> None:
        rows = [
            {
                "product_id": "aff-1",
                "title": "TravelCore 20K Power Bank",
                "brand": "TravelCore",
                "model": "20K",
                "image_url": "https://example.com/images/travelcore-20k.jpg",
                "price": "29.90",
                "currency": "EUR",
                "merchant": "Trusted Merchant",
                "merchant_url": "https://example.com/stores/trusted",
                "availability": "available",
                "product_url": "https://example.com/products/travelcore-20k",
                "affiliate_url": "https://example.invalid/aff/travelcore-20k",
                "category": "power_bank",
                "vertical": "retail_physical_products",
                "engine": "electronics_hypermarket",
                "category_bucket": "power_banks",
                "google_taxonomy_path": "Electronics > Electronics Accessories > Power Banks",
                "description": "Compact battery for travel charging.",
                "specifications": ["20000mAh", "USB-C PD"],
                "shipping_info_available": True,
                "return_policy_available": True,
                "locale": "en-IE",
                "market": "IE",
                "source_updated_at": "2026-05-11T10:00:00Z",
            }
        ]
        result = adapt_affiliate_feed_rows(
            rows,
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        self.assertEqual(result.status_counts.get("mapped"), 1)
        self.assertEqual(len(result.mapped_candidates), 1)
        candidate = result.mapped_candidates[0]
        self.assertEqual(candidate.candidate_id, "aff-1")
        self.assertEqual(candidate.source_id, "affiliate_local_feed_v1")
        self.assertEqual(candidate.source_type, "affiliate_feed")
        self.assertEqual(candidate.title, "TravelCore 20K Power Bank")
        self.assertEqual(candidate.outbound_url, "https://example.com/products/travelcore-20k")
        self.assertEqual(candidate.affiliate_url, "https://example.invalid/aff/travelcore-20k")
        self.assertEqual(candidate.metadata["enrichment"]["seller_reliability_status"], "trusted")
        self.assertEqual(candidate.metadata["enrichment"]["shipping_info_available"], True)
        self.assertEqual(candidate.metadata["enrichment"]["return_policy_available"], True)
        self.assertEqual(candidate.metadata["locale_market"]["locale"], "en-IE")
        self.assertEqual(candidate.metadata["locale_market"]["market"], "IE")

    def test_missing_critical_fields_are_rejected_or_review_required(self) -> None:
        rows = [
            {"title": "Missing candidate id", "merchant": "Seller", "product_url": "https://example.com/p/1"},
            {
                "product_id": "invalid-url",
                "title": "Invalid URL row",
                "merchant": "Seller",
                "product_url": "javascript:alert(1)",
            },
            {
                "product_id": "review-row",
                "title": "Review Needed Row",
                "merchant": "Seller",
                "product_url": "https://example.com/p/3",
            },
        ]
        result = adapt_affiliate_feed_rows(rows, source_id="affiliate_local_feed_v1")
        self.assertEqual(result.row_results[0].status.value, "rejected")
        self.assertIn("missing_candidate_id", result.row_results[0].reason_codes)
        self.assertEqual(result.row_results[1].status.value, "rejected")
        self.assertIn("invalid_outbound_url", result.row_results[1].reason_codes)
        self.assertEqual(result.row_results[2].status.value, "review_required")
        self.assertIn("seller_reliability_unknown", result.row_results[2].reason_codes)

    def test_missing_seller_trust_stays_unknown_and_not_auto_trusted(self) -> None:
        result = adapt_affiliate_feed_rows(
            [
                {
                    "product_id": "aff-unknown-seller",
                    "title": "Power Bank Unknown Seller",
                    "merchant": "Seller Without Trust Mapping",
                    "product_url": "https://example.com/products/x",
                }
            ],
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Different Seller": "trusted"},
        )
        candidate = result.mapped_candidates[0]
        self.assertEqual(candidate.metadata["enrichment"]["seller_reliability_status"], "unknown")
        self.assertIn("seller_reliability_unknown", result.row_results[0].reason_codes)

    def test_missing_shipping_return_specs_are_not_fabricated(self) -> None:
        result = adapt_affiliate_feed_rows(
            [
                {
                    "product_id": "aff-minimal-enrichment",
                    "title": "Minimal Data Product",
                    "merchant": "Seller",
                    "product_url": "https://example.com/products/minimal",
                }
            ],
            source_id="affiliate_local_feed_v1",
        )
        candidate = result.mapped_candidates[0]
        self.assertIsNone(candidate.metadata["enrichment"]["shipping_info_available"])
        self.assertIsNone(candidate.metadata["enrichment"]["return_policy_available"])
        self.assertFalse(candidate.metadata["enrichment"]["has_specifications"])
        self.assertNotIn("short_description", candidate.metadata)
        self.assertNotIn("specifications", candidate.metadata)

    def test_affiliate_and_outbound_url_contract_compatibility(self) -> None:
        result = adapt_affiliate_feed_rows(
            [
                {
                    "product_id": "with-both",
                    "title": "With both links",
                    "merchant": "Seller A",
                    "product_url": "https://example.com/products/with-both",
                    "affiliate_url": "https://example.invalid/aff/with-both",
                },
                {
                    "product_id": "with-affiliate-only",
                    "title": "With affiliate only",
                    "merchant": "Seller B",
                    "affiliate_url": "https://example.invalid/aff/only",
                },
            ],
            source_id="affiliate_local_feed_v1",
        )
        with_both = next(item for item in result.mapped_candidates if item.candidate_id == "with-both")
        affiliate_only = next(item for item in result.mapped_candidates if item.candidate_id == "with-affiliate-only")
        self.assertEqual(with_both.outbound_url, "https://example.com/products/with-both")
        self.assertEqual(with_both.affiliate_url, "https://example.invalid/aff/with-both")
        self.assertIsNone(affiliate_only.outbound_url)
        self.assertEqual(affiliate_only.affiliate_url, "https://example.invalid/aff/only")
        self.assertNotIn("missing_outbound_and_affiliate_url", result.row_results[0].reason_codes)

    def test_eligibility_gate_consumes_adapter_output(self) -> None:
        result = adapt_affiliate_feed_rows(
            [
                {
                    "product_id": "eligible-1",
                    "title": "Eligible Product",
                    "brand": "BrandA",
                    "model": "ModelA",
                    "image_url": "https://example.com/images/eligible-1.jpg",
                    "price": 19.0,
                    "currency": "EUR",
                    "merchant": "Trusted Merchant",
                    "merchant_url": "https://example.com/stores/trusted",
                    "availability": "available",
                    "product_url": "https://example.com/products/eligible-1",
                    "category_bucket": "power_banks",
                    "google_taxonomy_path": "Electronics > Electronics Accessories > Power Banks",
                    "vertical": "retail_physical_products",
                }
            ],
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        gate = run_product_eligibility_gate(
            result.mapped_candidates,
            expected_vertical="retail_physical_products",
            source_trust_level=SourceTrustLevel.PARTNER_VERIFIED,
            source_connected=True,
        )
        self.assertEqual(len(gate.decisions), 1)
        self.assertEqual(gate.decisions[0].status.value, "eligible")
        self.assertIn("eligible_for_display", gate.decisions[0].reason_codes)

    def test_recommendation_engine_consumes_eligible_adapter_output(self) -> None:
        rows = []
        for index in range(1, 5):
            rows.append(
                {
                    "product_id": f"eligible-{index}",
                    "title": f"Power Bank iPhone Fast Charge {index}",
                    "brand": "Brand",
                    "model": f"M{index}",
                    "image_url": f"https://example.com/images/eligible-{index}.jpg",
                    "price": 10.0 + index,
                    "currency": "EUR",
                    "merchant": "Trusted Merchant",
                    "merchant_url": "https://example.com/stores/trusted",
                    "availability": "available",
                    "product_url": f"https://example.com/products/eligible-{index}",
                    "category_bucket": "power_banks",
                    "google_taxonomy_path": "Electronics > Electronics Accessories > Power Banks",
                    "vertical": "retail_physical_products",
                }
            )
        mapped = adapt_affiliate_feed_rows(
            rows,
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        gate = run_product_eligibility_gate(
            mapped.mapped_candidates,
            expected_vertical="retail_physical_products",
            source_trust_level=SourceTrustLevel.PARTNER_VERIFIED,
            source_connected=True,
        )
        recommendation = build_pickwise_recommendation_set(
            query="power bank iphone fast charge",
            eligible_candidates=gate.eligible_candidates,
        )
        self.assertEqual(recommendation.status, RecommendationStatus.READY)
        self.assertEqual(len(recommendation.display_slots), 4)

    def test_existing_public_index_gates_and_routes_remain_unchanged(self) -> None:
        status, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status, 200)
        self.assertIn("Recommended by PickWise", body)
        candidate_status, _candidate_body = render_best_slug_html("power-bank-20000mah-for-iphone-stage38-candidate")
        self.assertEqual(candidate_status, 404)
        repository = get_buying_pages_repository()
        self.assertIsNone(repository.get_by_slug("power-bank-20000mah-for-iphone-stage38-candidate"))


if __name__ == "__main__":
    unittest.main()
