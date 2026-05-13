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
    SourceTrustLevel,
    adapt_affiliate_feed_rows,
    remediate_feed_enrichment_candidates,
    run_affiliate_feed_dry_run,
)
from picwise_offers.affiliate_feed_adapter import AffiliateFeedRowStatus  # noqa: E402
from picwise_offers.eligibility import run_product_eligibility_gate  # noqa: E402


def _load_real_feed_fixture() -> list[dict[str, object]]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step2_real_feed_sample.json"
    rows = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(rows, list)
    return rows


class PickWiseRoadmapStep2RealFeedSampleValidationTests(unittest.TestCase):
    def test_local_real_feed_sample_fixture_can_be_loaded(self) -> None:
        rows = _load_real_feed_fixture()
        self.assertGreaterEqual(len(rows), 9)
        required_keys = {"product_id", "title", "merchant", "product_url"}
        for row in rows:
            self.assertIsInstance(row, dict)
            for key in required_keys:
                self.assertIn(key, row)

    def test_stage38_adapter_accepts_sample_and_keeps_mixed_quality_statuses(self) -> None:
        rows = _load_real_feed_fixture()
        batch = adapt_affiliate_feed_rows(
            rows,
            source_id="affiliate_real_provider_local_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        self.assertEqual(len(batch.row_results), len(rows))
        self.assertGreater(batch.status_counts.get("mapped", 0), 0)
        self.assertGreater(batch.status_counts.get("review_required", 0), 0)
        self.assertGreater(batch.status_counts.get("rejected", 0), 0)

        rejected = {
            result.candidate.candidate_id if result.candidate else rows[result.row_index].get("product_id"): result
            for result in batch.row_results
            if result.status == AffiliateFeedRowStatus.REJECTED
        }
        self.assertIn("rw-rejected-invalid-url-1", rejected)
        self.assertIn("invalid_outbound_url", rejected["rw-rejected-invalid-url-1"].reason_codes)

    def test_stage39_dry_run_report_is_deterministic_for_realistic_sample(self) -> None:
        rows = _load_real_feed_fixture()
        report = run_affiliate_feed_dry_run(
            rows,
            source_id="affiliate_real_provider_local_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
            recommendation_query="power bank iphone fast charge",
        )
        self.assertEqual(report.total_rows, 9)
        self.assertEqual(report.mapped_count, 7)
        self.assertEqual(report.review_required_count, 1)
        self.assertEqual(report.rejected_count, 1)
        self.assertEqual(report.eligibility_pass_count, 7)
        self.assertEqual(report.eligibility_fail_count, 1)
        self.assertEqual(report.recommendation_ready_count, 4)

        self.assertEqual(report.missing_field_counts.get("missing_image"), 1)
        self.assertEqual(report.missing_field_counts.get("missing_seller_reliability"), 1)
        self.assertEqual(report.missing_field_counts.get("missing_shipping_info"), 1)
        self.assertEqual(report.missing_field_counts.get("missing_return_policy"), 1)
        self.assertEqual(report.missing_field_counts.get("missing_specifications"), 1)
        self.assertEqual(report.missing_field_counts.get("missing_affiliate_url"), 1)
        self.assertEqual(report.review_reason_counts.get("seller_reliability_unknown"), 1)
        self.assertEqual(report.rejection_reason_counts.get("invalid_outbound_url"), 1)
        self.assertEqual(report.readiness_status, "needs_enrichment")
        self.assertIn("rejected_rows_present", report.blockers_before_3000_candidate_pages)
        self.assertIn("review_required_rows_present", report.blockers_before_3000_candidate_pages)

    def test_stage40_remediation_workflow_yields_deterministic_ready_needs_blocked(self) -> None:
        rows = _load_real_feed_fixture()
        batch = adapt_affiliate_feed_rows(
            rows,
            source_id="affiliate_real_provider_local_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        gate = run_product_eligibility_gate(
            batch.mapped_candidates,
            expected_vertical="retail_physical_products",
            source_trust_level=SourceTrustLevel.PARTNER_VERIFIED,
            source_connected=True,
        )
        remediation = remediate_feed_enrichment_candidates(
            gate.eligible_candidates,
            contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )

        by_candidate_id = {item.candidate_id: item for item in remediation}
        self.assertEqual(by_candidate_id["rw-ready-1"].status, "ready")
        self.assertEqual(by_candidate_id["rw-ready-2"].status, "ready")
        self.assertEqual(by_candidate_id["rw-missing-trust-1"].status, "blocked")
        self.assertIn("needs_seller_trust", by_candidate_id["rw-missing-trust-1"].actions)
        self.assertEqual(by_candidate_id["rw-missing-shipping-returns-1"].status, "blocked")
        self.assertIn("needs_shipping_info", by_candidate_id["rw-missing-shipping-returns-1"].actions)
        self.assertIn("needs_return_policy", by_candidate_id["rw-missing-shipping-returns-1"].actions)
        self.assertEqual(by_candidate_id["rw-missing-specs-description-1"].status, "blocked")
        self.assertIn("needs_specs_or_description", by_candidate_id["rw-missing-specs-description-1"].actions)
        self.assertEqual(by_candidate_id["rw-missing-affiliate-1"].status, "blocked")
        self.assertIn("needs_affiliate_url", by_candidate_id["rw-missing-affiliate-1"].actions)
        self.assertEqual(by_candidate_id["rw-locale-market-currency-mismatch-1"].status, "needs_remediation")
        self.assertIn("needs_locale_review", by_candidate_id["rw-locale-market-currency-mismatch-1"].actions)

        first = remediate_feed_enrichment_candidates(
            gate.eligible_candidates,
            contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        second = remediate_feed_enrichment_candidates(
            gate.eligible_candidates,
            contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        self.assertEqual(first, second)

    def test_no_fake_enrichment_is_applied_without_explicit_contracts(self) -> None:
        rows = _load_real_feed_fixture()
        batch = adapt_affiliate_feed_rows(
            rows,
            source_id="affiliate_real_provider_local_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        gate = run_product_eligibility_gate(
            batch.mapped_candidates,
            expected_vertical="retail_physical_products",
            source_trust_level=SourceTrustLevel.PARTNER_VERIFIED,
            source_connected=True,
        )
        remediation = remediate_feed_enrichment_candidates(gate.eligible_candidates)
        for item in remediation:
            self.assertEqual(item.applied_enrichments, ())

    def test_no_live_api_scraping_or_credentials_used_for_validation_flow(self) -> None:
        source = (
            inspect.getsource(adapt_affiliate_feed_rows).lower()
            + inspect.getsource(run_affiliate_feed_dry_run).lower()
            + inspect.getsource(remediate_feed_enrichment_candidates).lower()
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

    def test_public_routes_sitemap_naming_and_gates_remain_unchanged(self) -> None:
        status, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status, 200)
        self.assertIn("Recommended by PickWise", body)
        candidate_status, _candidate_body = render_best_slug_html("power-bank-20000mah-for-iphone-roadmap-step2-sample")
        self.assertEqual(candidate_status, 404)
        repository = get_buying_pages_repository()
        self.assertIsNone(repository.get_by_slug("power-bank-20000mah-for-iphone-roadmap-step2-sample"))
        sitemap = render_buying_pages_sitemap_xml(repository.list_pages(), base_url="https://localhost")
        self.assertNotIn("roadmap-step2-sample", sitemap)


if __name__ == "__main__":
    unittest.main()
