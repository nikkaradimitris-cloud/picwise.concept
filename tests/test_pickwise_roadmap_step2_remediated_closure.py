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
from picwise_offers import FeedEnrichmentContracts, adapt_affiliate_feed_rows, run_roadmap_step2_closure_proof  # noqa: E402


def _load_corrected_rows() -> list[dict[str, object]]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step2_selected_provider_batch_corrected.json"
    rows = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(rows, list)
    return rows


def _trusted_map() -> dict[str, str]:
    return {
        "Trusted Merchant": "trusted",
        "Partner Merchant": "acceptable",
    }


def _run_corrected_closure():
    return run_roadmap_step2_closure_proof(
        _load_corrected_rows(),
        source_id="selected_provider_local_corrected_v1",
        trusted_seller_status_by_name=_trusted_map(),
        enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
    )


class PickWiseRoadmapStep2RemediatedClosureTests(unittest.TestCase):
    def test_corrected_fixture_loads_and_contains_only_selected_usable_rows(self) -> None:
        rows = _load_corrected_rows()
        self.assertGreaterEqual(len(rows), 4)
        for row in rows:
            self.assertIsInstance(row, dict)
            self.assertTrue(str(row.get("title", "")).strip())
            self.assertTrue(str(row.get("image_url", "")).startswith("https://"))
            self.assertTrue(str(row.get("affiliate_url", "")).startswith("https://"))
            self.assertNotEqual(str(row.get("product_url", "")).strip().lower()[:11], "javascript:")

        batch = adapt_affiliate_feed_rows(
            rows,
            source_id="selected_provider_local_corrected_v1",
            trusted_seller_status_by_name=_trusted_map(),
        )
        self.assertEqual(batch.status_counts.get("rejected", 0), 0)
        self.assertEqual(batch.status_counts.get("review_required", 0), 0)

    def test_all_1_to_9_required_field_coverage_is_full(self) -> None:
        result = _run_corrected_closure()
        expected_required = {
            "title",
            "image",
            "price",
            "description",
            "specs",
            "availability",
            "merchant_seller",
            "affiliate_link",
            "category_data",
        }
        self.assertEqual(set(result.field_coverage.keys()), expected_required)
        for field_name in expected_required:
            self.assertEqual(result.field_coverage[field_name], 1.0)
            self.assertEqual(result.rows_missing_each_field[field_name], ())

    def test_no_rejected_no_review_required_and_no_locale_currency_mismatch(self) -> None:
        result = _run_corrected_closure()
        self.assertEqual(result.adapter_summary["status_counts"].get("rejected", 0), 0)
        self.assertEqual(result.adapter_summary["status_counts"].get("review_required", 0), 0)
        self.assertEqual(result.dry_run_summary["rejected_count"], 0)
        self.assertEqual(result.dry_run_summary["review_required_count"], 0)
        self.assertEqual(result.evidence_summary["locale_currency_mismatch_count"], 0)
        self.assertEqual(result.evidence_summary["review_required_rate"], 0.0)
        self.assertEqual(result.blockers, ())

    def test_provider_readiness_and_closure_report_step2_closed(self) -> None:
        result = _run_corrected_closure()
        self.assertEqual(result.provider_readiness_summary["status"], "step2_ready")
        self.assertTrue(result.provider_readiness_summary["can_move_to_step3"])
        self.assertTrue(result.step2_closure_status["step2_closed"])
        self.assertFalse(result.step2_closure_status["step2_not_ready"])
        self.assertTrue(result.can_move_to_step3)

    def test_no_fake_enrichment_and_only_allowed_closure_evidence_flags(self) -> None:
        result = _run_corrected_closure()
        self.assertTrue(result.evidence_summary["no_fabricated_enrichment_detected"])
        self.assertTrue(result.evidence_summary["no_public_routes_or_sitemap_changes"])
        self.assertTrue(result.evidence_summary["no_live_api_scraping_credentials"])
        for item in result.remediation_summary["results"]:
            self.assertEqual(item["applied_enrichments"], ())

    def test_no_public_route_sitemap_or_naming_changes(self) -> None:
        status, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status, 200)
        self.assertIn("Recommended by PickWise", body)

        candidate_status, _candidate_body = render_best_slug_html("power-bank-roadmap-step2-remediated-closure")
        self.assertEqual(candidate_status, 404)
        repository = get_buying_pages_repository()
        self.assertIsNone(repository.get_by_slug("power-bank-roadmap-step2-remediated-closure"))
        sitemap = render_buying_pages_sitemap_xml(repository.list_pages(), base_url="https://localhost")
        self.assertNotIn("roadmap-step2-remediated-closure", sitemap)

    def test_no_gates_relaxed_no_scraping_live_api_or_credentials_added(self) -> None:
        source = (
            inspect.getsource(run_roadmap_step2_closure_proof).lower()
            + inspect.getsource(adapt_affiliate_feed_rows).lower()
        )
        sanitized_source = (
            source.replace("require_no_live_api_scraping_or_credentials", "")
            .replace("no_live_api_scraping_credentials", "")
            .replace("no_credentials_added", "")
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
            self.assertNotIn(token, sanitized_source)


if __name__ == "__main__":
    unittest.main()
