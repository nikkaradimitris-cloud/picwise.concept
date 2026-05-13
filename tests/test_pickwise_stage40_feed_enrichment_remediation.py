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
    FeedEnrichmentContracts,
    adapt_affiliate_feed_rows,
    remediate_feed_enrichment_candidates,
    run_affiliate_feed_dry_run,
)


def _fixture_rows() -> list[dict[str, object]]:
    fixture_path = ROOT / "tests" / "fixtures" / "stage39_affiliate_feed_sample.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _mapped_candidates_default():
    batch = adapt_affiliate_feed_rows(
        _fixture_rows(),
        source_id="affiliate_local_feed_v1",
        trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
    )
    return batch.mapped_candidates


class PickWiseStage40FeedEnrichmentRemediationTests(unittest.TestCase):
    def test_explicit_trusted_seller_map_can_mark_seller_trust_only_when_provided(self) -> None:
        unknown_batch = adapt_affiliate_feed_rows(
            [
                {
                    "product_id": "trust-1",
                    "title": "Trust Candidate",
                    "merchant": "Seller Need Mapping",
                    "product_url": "https://example.com/products/trust-1",
                    "price": "11.0",
                    "currency": "EUR",
                }
            ],
            source_id="affiliate_local_feed_v1",
        )
        result_without_map = remediate_feed_enrichment_candidates(unknown_batch.mapped_candidates)[0]
        self.assertIn("needs_seller_trust", result_without_map.actions)

        result_with_map = remediate_feed_enrichment_candidates(
            unknown_batch.mapped_candidates,
            contracts=FeedEnrichmentContracts(
                trusted_seller_reliability_by_name={"Seller Need Mapping": "trusted"},
                shipping_info_available_by_candidate_id={"trust-1": True},
                return_policy_available_by_candidate_id={"trust-1": True},
                taxonomy_linkage_by_candidate_id={"trust-1": "Electronics > Power Banks"},
                specs_or_description_by_candidate_id={"trust-1": {"short_description": "Explicit description"}},
                affiliate_url_by_candidate_id={"trust-1": "https://example.invalid/aff/trust-1"},
            ),
        )[0]
        self.assertNotIn("needs_seller_trust", result_with_map.actions)
        self.assertIn("trusted_seller_reliability_mapping", result_with_map.applied_enrichments)

    def test_missing_seller_trust_remains_needs_seller_trust(self) -> None:
        candidates = _mapped_candidates_default()
        target = next(item for item in candidates if item.candidate_id == "missing-trust-1")
        result = remediate_feed_enrichment_candidates((target,))[0]
        self.assertIn("needs_seller_trust", result.actions)
        self.assertIn("seller_reliability_status", result.missing_fields)

    def test_shipping_and_return_policy_are_applied_only_from_explicit_input(self) -> None:
        candidates = _mapped_candidates_default()
        target = next(item for item in candidates if item.candidate_id == "missing-shipping-returns-1")

        without_contracts = remediate_feed_enrichment_candidates((target,))[0]
        self.assertIn("needs_shipping_info", without_contracts.actions)
        self.assertIn("needs_return_policy", without_contracts.actions)

        with_contracts = remediate_feed_enrichment_candidates(
            (target,),
            contracts=FeedEnrichmentContracts(
                shipping_info_available_by_candidate_id={"missing-shipping-returns-1": True},
                return_policy_available_by_candidate_id={"missing-shipping-returns-1": True},
                trusted_seller_reliability_by_name={"Trusted Merchant": "trusted"},
                affiliate_url_by_candidate_id={"missing-shipping-returns-1": "https://example.invalid/aff/nopolicy-10k"},
            ),
        )[0]
        self.assertNotIn("needs_shipping_info", with_contracts.actions)
        self.assertNotIn("needs_return_policy", with_contracts.actions)
        self.assertIn("shipping_info_coverage", with_contracts.applied_enrichments)
        self.assertIn("return_policy_coverage", with_contracts.applied_enrichments)

    def test_taxonomy_linkage_is_applied_only_from_explicit_input(self) -> None:
        batch = adapt_affiliate_feed_rows(
            [
                {
                    "product_id": "taxonomy-gap-1",
                    "title": "Taxonomy Gap Product",
                    "merchant": "Trusted Merchant",
                    "product_url": "https://example.com/products/taxonomy-gap-1",
                    "price": 30,
                    "currency": "EUR",
                    "shipping_info_available": True,
                    "return_policy_available": True,
                }
            ],
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        without_contracts = remediate_feed_enrichment_candidates(batch.mapped_candidates)[0]
        self.assertIn("needs_taxonomy_linkage", without_contracts.actions)

        with_contracts = remediate_feed_enrichment_candidates(
            batch.mapped_candidates,
            contracts=FeedEnrichmentContracts(
                taxonomy_linkage_by_candidate_id={"taxonomy-gap-1": "Electronics > Electronics Accessories > Power Banks"},
                affiliate_url_by_candidate_id={"taxonomy-gap-1": "https://example.invalid/aff/taxonomy-gap-1"},
                specs_or_description_by_candidate_id={"taxonomy-gap-1": {"short_description": "Added from trusted map"}},
            ),
        )[0]
        self.assertNotIn("needs_taxonomy_linkage", with_contracts.actions)
        self.assertIn("taxonomy_linkage_coverage", with_contracts.applied_enrichments)

    def test_specs_description_completeness_detected_honestly(self) -> None:
        batch = adapt_affiliate_feed_rows(
            [
                {
                    "product_id": "spec-gap-1",
                    "title": "Spec Gap Product",
                    "merchant": "Trusted Merchant",
                    "product_url": "https://example.com/products/spec-gap-1",
                    "price": 22,
                    "currency": "EUR",
                    "shipping_info_available": True,
                    "return_policy_available": True,
                    "category_bucket": "power_banks",
                }
            ],
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        result = remediate_feed_enrichment_candidates(batch.mapped_candidates)[0]
        self.assertIn("needs_specs_or_description", result.actions)
        self.assertIn("specifications_or_description", result.missing_fields)

    def test_affiliate_url_absence_is_reported_not_fabricated(self) -> None:
        candidates = _mapped_candidates_default()
        target = next(item for item in candidates if item.candidate_id == "missing-affiliate-1")
        result = remediate_feed_enrichment_candidates((target,))[0]
        self.assertIn("needs_affiliate_url", result.actions)
        self.assertIn("affiliate_url", result.missing_fields)

    def test_locale_currency_mismatch_triggers_review(self) -> None:
        candidates = _mapped_candidates_default()
        target = next(item for item in candidates if item.candidate_id == "locale-market-1")
        result = remediate_feed_enrichment_candidates(
            (target,),
            contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "USD"}),
        )[0]
        self.assertIn("needs_locale_review", result.actions)
        self.assertIn("market_currency_mismatch", result.review_reasons)

    def test_invalid_core_fields_stay_blocked(self) -> None:
        batch = adapt_affiliate_feed_rows(
            [
                {
                    "product_id": "broken-core-1",
                    "merchant": "Trusted Merchant",
                    "product_url": "javascript:alert(1)",
                }
            ],
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        mapped_candidates = batch.mapped_candidates
        self.assertEqual(mapped_candidates, ())

        # Candidate with missing core fields still blocks even with partial explicit enrichment.
        batch2 = adapt_affiliate_feed_rows(
            [
                {
                    "product_id": "broken-core-2",
                    "title": "",
                    "merchant": "",
                    "product_url": "https://example.com/products/broken-core-2",
                }
            ],
            source_id="affiliate_local_feed_v1",
        )
        result = remediate_feed_enrichment_candidates(batch2.mapped_candidates)[0]
        self.assertIn("blocked_invalid_core_fields", result.actions)
        self.assertFalse(result.can_continue_to_candidate_page_dry_run)

    def test_remediation_result_is_deterministic(self) -> None:
        candidates = _mapped_candidates_default()
        contracts = FeedEnrichmentContracts(
            trusted_seller_reliability_by_name={"Trusted Merchant": "trusted", "Unknown Merchant": "unknown"},
            shipping_info_available_by_candidate_id={"missing-shipping-returns-1": True},
            return_policy_available_by_candidate_id={"missing-shipping-returns-1": True},
        )
        first = remediate_feed_enrichment_candidates(candidates, contracts=contracts)
        second = remediate_feed_enrichment_candidates(candidates, contracts=contracts)
        self.assertEqual(first, second)

    def test_stage39_dry_run_still_works_unchanged_and_optional_enrichment_is_additive(self) -> None:
        base = run_affiliate_feed_dry_run(
            _fixture_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
            recommendation_query="power bank iphone fast charge",
        )
        self.assertIsNone(base.enrichment_remediation_summary)
        self.assertEqual(base.total_rows, 8)
        self.assertEqual(base.readiness_status, "needs_enrichment")

        enriched = run_affiliate_feed_dry_run(
            _fixture_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
            recommendation_query="power bank iphone fast charge",
            include_enrichment_remediation_summary=True,
            enrichment_contracts=FeedEnrichmentContracts(
                trusted_seller_reliability_by_name={"Unknown Merchant": "trusted"},
                shipping_info_available_by_candidate_id={"missing-shipping-returns-1": True},
                return_policy_available_by_candidate_id={"missing-shipping-returns-1": True},
                affiliate_url_by_candidate_id={"missing-affiliate-1": "https://example.invalid/aff/outboundonly-20k"},
            ),
        )
        self.assertIsNotNone(enriched.enrichment_remediation_summary)
        assert enriched.enrichment_remediation_summary is not None
        self.assertEqual(enriched.total_rows, base.total_rows)
        self.assertEqual(enriched.mapped_count, base.mapped_count)
        self.assertEqual(enriched.readiness_status, base.readiness_status)

    def test_existing_gates_naming_routes_sitemap_and_no_live_api_constraints(self) -> None:
        status, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status, 200)
        self.assertIn("Recommended by PickWise", body)
        candidate_status, _candidate_body = render_best_slug_html("power-bank-20000mah-for-iphone-stage40-candidate")
        self.assertEqual(candidate_status, 404)
        repository = get_buying_pages_repository()
        self.assertIsNone(repository.get_by_slug("power-bank-20000mah-for-iphone-stage40-candidate"))
        xml = render_buying_pages_sitemap_xml(repository.list_pages(), base_url="https://localhost")
        self.assertNotIn("stage40-candidate", xml)

        source = (
            inspect.getsource(remediate_feed_enrichment_candidates).lower()
            + inspect.getsource(run_affiliate_feed_dry_run).lower()
        )
        forbidden_tokens = (
            "requests",
            "httpx",
            "urllib.request",
            "beautifulsoup",
            "selenium",
            "playwright",
            "scrapy",
            "aiohttp",
            "api_key",
            "secret",
            "token",
            "credential",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
