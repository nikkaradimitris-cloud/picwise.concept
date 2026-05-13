from __future__ import annotations

import inspect
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app.buying_routes import get_buying_pages_repository, render_best_slug_html  # noqa: E402
from picwise_buying_pages import render_buying_pages_sitemap_xml  # noqa: E402
from picwise_offers import (  # noqa: E402
    ALLOWED_REMEDIATION_INPUTS,
    PROVIDER_FEED_CONTRACT,
    FeedEnrichmentContracts,
    describe_provider_contract,
    evaluate_provider_batch_readiness,
    run_affiliate_feed_dry_run,
)
from picwise_offers.provider_contract import ProviderBatchThresholds  # noqa: E402


def _load_rows() -> list[dict[str, object]]:
    fixture_path = ROOT / "tests" / "fixtures" / "stage39_affiliate_feed_sample.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


class PickWiseRoadmapStep2ProviderContractHardeningTests(unittest.TestCase):
    def test_provider_contract_lists_required_core_fields(self) -> None:
        fields = set(PROVIDER_FEED_CONTRACT.required_core)
        self.assertIn("product_id_or_deterministic_external_id", fields)
        self.assertIn("title", fields)
        self.assertIn("product_url_or_outbound_url", fields)
        self.assertIn("image_url", fields)
        self.assertIn("price", fields)
        self.assertIn("currency", fields)
        self.assertIn("availability", fields)
        self.assertIn("merchant_or_seller", fields)
        self.assertIn("category_or_taxonomy_signal", fields)
        self.assertIn("locale_or_market_signal_when_available", fields)

    def test_provider_contract_lists_public_candidate_fields(self) -> None:
        fields = set(PROVIDER_FEED_CONTRACT.required_for_public_candidate)
        self.assertIn("affiliate_url_when_monetized", fields)
        self.assertIn("seller_reliability_status_from_trusted_mapping", fields)
        self.assertIn("shipping_information", fields)
        self.assertIn("return_policy_information", fields)
        self.assertIn("specifications_or_useful_description", fields)
        self.assertIn("category_or_taxonomy_linkage", fields)
        self.assertIn("locale_market_currency_consistency", fields)

    def test_forbidden_to_fabricate_fields_are_explicit(self) -> None:
        forbidden = set(PROVIDER_FEED_CONTRACT.forbidden_to_fabricate)
        self.assertIn("seller_reliability_status", forbidden)
        self.assertIn("shipping_information", forbidden)
        self.assertIn("return_policy_information", forbidden)
        self.assertIn("taxonomy_linkage", forbidden)
        self.assertIn("specifications_or_description", forbidden)
        self.assertIn("affiliate_url", forbidden)
        self.assertIn("price", forbidden)
        self.assertIn("currency", forbidden)
        self.assertIn("availability", forbidden)

    def test_missing_seller_trust_fails_readiness_unless_trusted_map_covers_it(self) -> None:
        base_report = run_affiliate_feed_dry_run(_load_rows(), source_id="affiliate_local_feed_v1")
        base_eval = evaluate_provider_batch_readiness(base_report)
        self.assertIn("seller_trust_coverage", base_eval.failed_thresholds)

        fixed_report = run_affiliate_feed_dry_run(
            _load_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted", "Unknown Merchant": "trusted"},
            include_enrichment_remediation_summary=True,
            enrichment_contracts=FeedEnrichmentContracts(
                trusted_seller_reliability_by_name={"Unknown Merchant": "trusted"},
                shipping_info_available_by_candidate_id={"missing-shipping-returns-1": True},
                return_policy_available_by_candidate_id={"missing-shipping-returns-1": True},
                affiliate_url_by_candidate_id={"missing-affiliate-1": "https://example.invalid/aff/outboundonly-20k"},
            ),
        )
        fixed_eval = evaluate_provider_batch_readiness(
            fixed_report,
            threshold_config=ProviderBatchThresholds(max_review_required_rate=0.2),
        )
        self.assertNotIn("seller_trust_coverage", fixed_eval.failed_thresholds)

    def test_rejected_rows_block_step2_readiness(self) -> None:
        report = run_affiliate_feed_dry_run(
            _load_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        result = evaluate_provider_batch_readiness(report)
        self.assertIn("rejected_rate", result.failed_thresholds)
        self.assertIn("rejected_rows_present", result.blockers)
        self.assertEqual(result.status, "step2_not_ready")
        self.assertFalse(result.can_move_to_step3)

    def test_locale_currency_mismatch_blocks_readiness(self) -> None:
        report = run_affiliate_feed_dry_run(
            _load_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        payload = {
            "total_rows": report.total_rows,
            "mapped_count": report.mapped_count,
            "review_required_count": report.review_required_count,
            "rejected_count": 0,
            "missing_field_counts": {
                "missing_image": 0,
                "missing_price": 0,
                "missing_seller_reliability": 0,
                "missing_shipping_info": 0,
                "missing_return_policy": 0,
                "missing_specifications": 0,
                "missing_affiliate_url": 0,
            },
            "review_reason_counts": {"market_currency_mismatch": 1},
        }
        result = evaluate_provider_batch_readiness(payload)
        self.assertIn("locale_currency_mismatch_rate", result.failed_thresholds)
        self.assertIn("locale_currency_mismatch_detected", result.blockers)
        self.assertEqual(result.status, "step2_not_ready")

    def test_incomplete_affiliate_url_coverage_blocks_monetized_readiness(self) -> None:
        payload = {
            "total_rows": 5,
            "mapped_count": 5,
            "review_required_count": 0,
            "rejected_count": 0,
            "missing_field_counts": {
                "missing_image": 0,
                "missing_price": 0,
                "missing_seller_reliability": 0,
                "missing_shipping_info": 0,
                "missing_return_policy": 0,
                "missing_specifications": 0,
                "missing_affiliate_url": 2,
            },
            "review_reason_counts": {},
        }
        result = evaluate_provider_batch_readiness(payload)
        self.assertIn("affiliate_url_coverage", result.failed_thresholds)
        self.assertIn("affiliate_url_coverage_below_threshold", result.blockers)
        self.assertFalse(result.can_move_to_step3)

    def test_good_batch_can_become_step2_ready_when_thresholds_pass(self) -> None:
        payload = {
            "total_rows": 10,
            "mapped_count": 10,
            "review_required_count": 0,
            "rejected_count": 0,
            "missing_field_counts": {
                "missing_image": 0,
                "missing_price": 0,
                "missing_seller_reliability": 0,
                "missing_shipping_info": 0,
                "missing_return_policy": 0,
                "missing_specifications": 0,
                "missing_affiliate_url": 0,
            },
            "review_reason_counts": {},
            "public_routes_unchanged": True,
            "sitemap_unchanged": True,
            "no_live_api_calls": True,
            "no_scraping": True,
            "no_credentials_added": True,
            "fabricated_enrichment_detected": False,
        }
        result = evaluate_provider_batch_readiness(payload)
        self.assertEqual(result.status, "step2_ready")
        self.assertEqual(result.failed_thresholds, ())
        self.assertTrue(result.can_move_to_step3)

    def test_conditional_batch_can_become_step2_conditionally_ready_only_with_explicit_blockers(self) -> None:
        payload = {
            "total_rows": 20,
            "mapped_count": 20,
            "review_required_count": 2,
            "rejected_count": 0,
            "missing_field_counts": {
                "missing_image": 0,
                "missing_price": 0,
                "missing_seller_reliability": 0,
                "missing_shipping_info": 1,
                "missing_return_policy": 0,
                "missing_specifications": 0,
                "missing_affiliate_url": 0,
            },
            "review_reason_counts": {},
        }
        result = evaluate_provider_batch_readiness(
            payload,
            threshold_config=ProviderBatchThresholds(
                max_review_required_rate=0.2,
                min_shipping_info_coverage=1.0,
            ),
        )
        self.assertEqual(result.status, "step2_conditionally_ready")
        self.assertIn("shipping_info_coverage", result.failed_thresholds)
        self.assertIn("shipping_info_coverage_below_threshold", result.blockers)
        self.assertFalse(result.can_move_to_step3)

    def test_evaluator_never_relaxes_existing_gates(self) -> None:
        payload = {
            "total_rows": 10,
            "mapped_count": 10,
            "review_required_count": 0,
            "rejected_count": 0,
            "missing_field_counts": {
                "missing_image": 0,
                "missing_price": 0,
                "missing_seller_reliability": 0,
                "missing_shipping_info": 0,
                "missing_return_policy": 0,
                "missing_specifications": 0,
                "missing_affiliate_url": 0,
            },
            "review_reason_counts": {},
            "public_routes_unchanged": False,
            "sitemap_unchanged": False,
            "no_live_api_calls": True,
            "no_scraping": True,
            "no_credentials_added": True,
            "fabricated_enrichment_detected": False,
        }
        result = evaluate_provider_batch_readiness(payload)
        self.assertIn("no_public_route_or_sitemap_changes", result.failed_thresholds)
        self.assertIn("public_route_or_sitemap_changes_detected", result.blockers)
        self.assertFalse(result.can_move_to_step3)

    def test_no_public_routes_sitemap_naming_changes(self) -> None:
        status, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status, 200)
        self.assertIn("Recommended by PickWise", body)
        staged_status, _staged_body = render_best_slug_html("power-bank-stage2-provider-contract-candidate")
        self.assertEqual(staged_status, 404)
        repository = get_buying_pages_repository()
        self.assertIsNone(repository.get_by_slug("power-bank-stage2-provider-contract-candidate"))
        sitemap = render_buying_pages_sitemap_xml(repository.list_pages(), base_url="https://localhost")
        self.assertNotIn("stage2-provider-contract-candidate", sitemap)

    def test_no_fake_data_scraping_live_api_or_credentials(self) -> None:
        contract_dict = describe_provider_contract()
        self.assertIn("forbidden_to_fabricate", contract_dict)
        forbidden = set(contract_dict["forbidden_to_fabricate"])
        self.assertIn("seller_reliability_status", forbidden)
        self.assertIn("shipping_information", forbidden)
        self.assertIn("return_policy_information", forbidden)
        self.assertIn("affiliate_url", forbidden)

        source = inspect.getsource(evaluate_provider_batch_readiness).lower()
        forbidden_tokens = (
            "requests",
            "httpx",
            "urllib.request",
            "beautifulsoup",
            "selenium",
            "playwright",
            "scrapy",
            "aiohttp",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)

    def test_allowed_remediation_inputs_are_explicit(self) -> None:
        self.assertEqual(
            ALLOWED_REMEDIATION_INPUTS,
            PROVIDER_FEED_CONTRACT.enrichment_allowed_from_trusted_map,
        )
        self.assertIn("trusted_seller_reliability_by_name", ALLOWED_REMEDIATION_INPUTS)
        self.assertIn("shipping_info_available_by_candidate_id", ALLOWED_REMEDIATION_INPUTS)
        self.assertIn("return_policy_available_by_candidate_id", ALLOWED_REMEDIATION_INPUTS)
        self.assertIn("affiliate_url_by_candidate_id", ALLOWED_REMEDIATION_INPUTS)


if __name__ == "__main__":
    unittest.main()
