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
from picwise_offers import run_affiliate_feed_dry_run  # noqa: E402
from picwise_offers.feed_dry_run import _to_local_rows_or_raise  # noqa: E402


def _load_fixture_rows() -> list[dict[str, object]]:
    fixture_path = ROOT / "tests" / "fixtures" / "stage39_affiliate_feed_sample.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


class PickWiseStage39FeedDryRunReportTests(unittest.TestCase):
    def test_dry_run_accepts_local_rows_only(self) -> None:
        with self.assertRaises(TypeError):
            _to_local_rows_or_raise(("not", "a", "list"))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            _to_local_rows_or_raise([{"ok": "row"}, "not-a-dict"])  # type: ignore[list-item]
        rows = _to_local_rows_or_raise([{"product_id": "x"}])
        self.assertEqual(len(rows), 1)

    def test_dry_run_uses_stage38_adapter_and_summarizes_counts_deterministically(self) -> None:
        report = run_affiliate_feed_dry_run(
            _load_fixture_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
            recommendation_query="power bank iphone fast charge",
        )
        self.assertEqual(report.total_rows, 8)
        self.assertEqual(report.mapped_count, 6)
        self.assertEqual(report.review_required_count, 1)
        self.assertEqual(report.rejected_count, 1)
        self.assertEqual(report.eligibility_pass_count, 6)
        self.assertEqual(report.eligibility_fail_count, 1)
        self.assertEqual(report.recommendation_ready_count, 4)

    def test_missing_field_counts_and_reason_counts_are_deterministic(self) -> None:
        report = run_affiliate_feed_dry_run(
            _load_fixture_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
            recommendation_query="power bank iphone fast charge",
        )
        self.assertEqual(report.missing_field_counts.get("missing_image"), 1)
        self.assertEqual(report.missing_field_counts.get("missing_price"), 1)
        self.assertEqual(report.missing_field_counts.get("missing_seller_reliability"), 1)
        self.assertEqual(report.missing_field_counts.get("missing_shipping_info"), 1)
        self.assertEqual(report.missing_field_counts.get("missing_return_policy"), 1)
        self.assertEqual(report.missing_field_counts.get("missing_affiliate_url"), 1)
        self.assertEqual(report.rejection_reason_counts.get("invalid_outbound_url"), 1)
        self.assertEqual(report.rejection_reason_counts.get("missing_title"), 1)
        self.assertEqual(report.review_reason_counts.get("seller_reliability_unknown"), 1)

    def test_eligibility_gate_is_consumed_without_relaxing(self) -> None:
        report = run_affiliate_feed_dry_run(
            _load_fixture_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        # Missing image is an eligibility failure; missing price remains eligible but not recommendation-safe.
        self.assertEqual(report.eligibility_fail_count, 1)
        self.assertGreater(report.eligibility_pass_count, 0)

    def test_recommendation_readiness_counts_only_safe_eligible_candidates(self) -> None:
        report = run_affiliate_feed_dry_run(
            _load_fixture_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
            recommendation_query="power bank iphone fast charge",
        )
        self.assertEqual(report.recommendation_ready_count, 4)
        self.assertLessEqual(report.recommendation_ready_count, report.eligibility_pass_count)

    def test_locale_market_currency_counts_are_preserved(self) -> None:
        report = run_affiliate_feed_dry_run(
            _load_fixture_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        self.assertEqual(report.locale_counts.get("en-IE"), 1)
        self.assertEqual(report.locale_counts.get("unspecified"), 6)
        self.assertEqual(report.market_counts.get("IE"), 1)
        self.assertEqual(report.market_counts.get("unspecified"), 6)
        self.assertEqual(report.currency_counts.get("EUR"), 6)
        self.assertEqual(report.currency_counts.get("USD"), 1)

    def test_missing_seller_trust_stays_unknown_and_not_promoted(self) -> None:
        report = run_affiliate_feed_dry_run(
            _load_fixture_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        self.assertEqual(report.seller_reliability_counts.get("unknown"), 1)
        self.assertEqual(report.seller_reliability_counts.get("trusted"), 6)
        self.assertNotIn("acceptable", report.seller_reliability_counts)

    def test_missing_shipping_returns_specs_are_reported_not_fabricated(self) -> None:
        report = run_affiliate_feed_dry_run(
            _load_fixture_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
        )
        self.assertEqual(report.missing_field_counts.get("missing_shipping_info"), 1)
        self.assertEqual(report.missing_field_counts.get("missing_return_policy"), 1)
        self.assertEqual(report.missing_field_counts.get("missing_specifications"), 0)

    def test_no_public_route_changes_and_no_sitemap_expansion(self) -> None:
        status, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status, 200)
        self.assertIn("Recommended by PickWise", body)
        candidate_status, _candidate_body = render_best_slug_html("power-bank-20000mah-for-iphone-stage39-candidate")
        self.assertEqual(candidate_status, 404)
        repository = get_buying_pages_repository()
        self.assertIsNone(repository.get_by_slug("power-bank-20000mah-for-iphone-stage39-candidate"))
        xml = render_buying_pages_sitemap_xml(repository.list_pages(), base_url="https://localhost")
        self.assertNotIn("stage39-candidate", xml)

    def test_no_live_api_scraping_or_credentials(self) -> None:
        source = inspect.getsource(run_affiliate_feed_dry_run).lower() + inspect.getsource(_to_local_rows_or_raise).lower()
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

    def test_readiness_status_and_blockers_before_3000_candidate_pages(self) -> None:
        report = run_affiliate_feed_dry_run(
            _load_fixture_rows(),
            source_id="affiliate_local_feed_v1",
            trusted_seller_status_by_name={"Trusted Merchant": "trusted"},
            recommendation_query="power bank iphone fast charge",
        )
        self.assertEqual(report.readiness_status, "needs_enrichment")
        self.assertIn("rejected_rows_present", report.blockers_before_3000_candidate_pages)
        self.assertIn("review_required_rows_present", report.blockers_before_3000_candidate_pages)
        self.assertIn("eligibility_gate_failures_present", report.blockers_before_3000_candidate_pages)
        self.assertIn("missing_seller_reliability", report.blockers_before_3000_candidate_pages)


if __name__ == "__main__":
    unittest.main()
