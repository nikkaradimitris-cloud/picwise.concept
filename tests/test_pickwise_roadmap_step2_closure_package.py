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
from picwise_offers import FeedEnrichmentContracts, run_roadmap_step2_closure_proof  # noqa: E402
from picwise_offers.affiliate_feed_adapter import adapt_affiliate_feed_rows  # noqa: E402
from picwise_offers.roadmap_step2_closure import _to_local_rows_or_raise  # noqa: E402


def _load_selected_provider_rows() -> list[dict[str, object]]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step2_selected_provider_batch.json"
    rows = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(rows, list)
    return rows


def _build_rows(*, exclude_ids: set[str] | None = None, override_by_id: dict[str, dict[str, object]] | None = None) -> list[dict[str, object]]:
    rows = _load_selected_provider_rows()
    filtered: list[dict[str, object]] = []
    for row in rows:
        row_id = str(row.get("product_id", ""))
        if exclude_ids and row_id in exclude_ids:
            continue
        payload = dict(row)
        if override_by_id and row_id in override_by_id:
            payload.update(override_by_id[row_id])
        filtered.append(payload)
    return filtered


def _trusted_map(include_unmapped: bool = False) -> dict[str, str]:
    mapping = {"Trusted Merchant": "trusted"}
    if include_unmapped:
        mapping["Unmapped Merchant"] = "trusted"
    return mapping


class PickWiseRoadmapStep2ClosurePackageTests(unittest.TestCase):
    def test_accepts_local_rows_only(self) -> None:
        with self.assertRaises(TypeError):
            _to_local_rows_or_raise(("not", "local"))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            _to_local_rows_or_raise([{"ok": "row"}, "not-a-dict"])  # type: ignore[list-item]
        self.assertEqual(len(_to_local_rows_or_raise([{"product_id": "x"}])), 1)

    def test_closure_proof_checks_all_1_to_9_fields(self) -> None:
        rows = _build_rows(exclude_ids={"selected-rejected-row-1"})
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
            enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        required_keys = {
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
        self.assertEqual(set(result.field_coverage.keys()), required_keys)
        self.assertEqual(set(result.rows_missing_each_field.keys()), required_keys)
        self.assertIn("required_field_names", result.evidence_summary)
        self.assertEqual(
            tuple(result.evidence_summary["required_field_names"]),
            (
                "title",
                "image",
                "price",
                "description",
                "specs",
                "availability",
                "merchant_seller",
                "affiliate_link",
                "category_data",
            ),
        )

    def test_full_valid_row_can_pass_field_proof(self) -> None:
        rows = _build_rows(
            exclude_ids={
                "selected-missing-desc-specs-1",
                "selected-missing-affiliate-1",
                "selected-missing-category-1",
                "selected-missing-image-1",
                "selected-missing-trust-1",
                "selected-locale-currency-mismatch-1",
                "selected-rejected-row-1",
            }
        )
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
            enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        for field_name in result.field_coverage:
            self.assertEqual(result.field_coverage[field_name], 1.0)

    def test_missing_image_blocks_closure(self) -> None:
        rows = _build_rows(exclude_ids={"selected-rejected-row-1"})
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
            enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        self.assertLess(result.field_coverage["image"], 1.0)
        self.assertIn("selected-missing-image-1", result.rows_missing_each_field["image"])
        self.assertIn("image_coverage_below_threshold", result.blockers)
        self.assertTrue(result.step2_closure_status["step2_not_ready"])

    def test_missing_price_blocks_closure(self) -> None:
        rows = _build_rows(exclude_ids={"selected-rejected-row-1"}, override_by_id={"selected-strong-1": {"price": ""}})
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
            enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        self.assertLess(result.field_coverage["price"], 1.0)
        self.assertIn("selected-strong-1", result.rows_missing_each_field["price"])
        self.assertIn("price_coverage_below_threshold", result.blockers)

    def test_missing_description_specs_block_public_readiness(self) -> None:
        rows = _build_rows(exclude_ids={"selected-rejected-row-1"})
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
            enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        self.assertIn("selected-missing-desc-specs-1", result.rows_missing_each_field["description"])
        self.assertIn("selected-missing-desc-specs-1", result.rows_missing_each_field["specs"])
        self.assertIn("description_coverage_below_threshold", result.blockers)
        self.assertIn("specs_coverage_below_threshold", result.blockers)

    def test_missing_affiliate_link_blocks_monetized_readiness(self) -> None:
        rows = _build_rows(exclude_ids={"selected-rejected-row-1"})
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
            enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        self.assertIn("selected-missing-affiliate-1", result.rows_missing_each_field["affiliate_link"])
        self.assertIn("affiliate_link_coverage_below_threshold", result.blockers)

    def test_missing_category_data_blocks_closure(self) -> None:
        rows = _build_rows(exclude_ids={"selected-rejected-row-1"})
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
            enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        self.assertIn("selected-missing-category-1", result.rows_missing_each_field["category_data"])
        self.assertIn("category_data_coverage_below_threshold", result.blockers)

    def test_missing_merchant_seller_blocks_closure(self) -> None:
        rows = _build_rows(
            exclude_ids={"selected-rejected-row-1"},
            override_by_id={"selected-strong-1": {"merchant": "", "seller_name": ""}},
        )
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
            enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        self.assertIn("selected-strong-1", result.rows_missing_each_field["merchant_seller"])
        self.assertIn("merchant_seller_coverage_below_threshold", result.blockers)

    def test_locale_currency_mismatch_blocks_closure(self) -> None:
        rows = _build_rows(exclude_ids={"selected-rejected-row-1"})
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
            enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        self.assertIn("locale_currency_mismatch_detected", result.blockers)
        self.assertTrue(result.step2_closure_status["step2_not_ready"])

    def test_rejected_rows_block_closure(self) -> None:
        rows = _build_rows()
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
        )
        self.assertEqual(result.adapter_summary["status_counts"].get("rejected"), 1)
        self.assertIn("rejected_rows_present", result.blockers)
        self.assertTrue(result.step2_closure_status["step2_not_ready"])

    def test_provider_evaluator_result_is_included(self) -> None:
        rows = _build_rows(exclude_ids={"selected-rejected-row-1"})
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
            enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        provider_summary = result.provider_readiness_summary
        self.assertIn("status", provider_summary)
        self.assertIn("passed_thresholds", provider_summary)
        self.assertIn("failed_thresholds", provider_summary)
        self.assertIn("can_move_to_step3", provider_summary)

    def test_step2_closed_only_when_all_thresholds_pass(self) -> None:
        rows = _build_rows(
            exclude_ids={
                "selected-missing-desc-specs-1",
                "selected-missing-affiliate-1",
                "selected-missing-category-1",
                "selected-missing-image-1",
                "selected-missing-trust-1",
                "selected-rejected-row-1",
            },
            override_by_id={
                "selected-locale-currency-mismatch-1": {"currency": "EUR"},
                "selected-strong-1": {
                    "description": "strong row",
                    "specifications": ["20000mAh", "USB-C PD"],
                    "shipping_info_available": True,
                    "return_policy_available": True,
                },
            },
        )
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(include_unmapped=True),
            enrichment_contracts=FeedEnrichmentContracts(
                expected_currency_by_market={"IE": "EUR"},
                trusted_seller_reliability_by_name={"Unmapped Merchant": "trusted"},
            ),
        )
        self.assertTrue(result.step2_closure_status["step2_closed"])
        self.assertFalse(result.step2_closure_status["step2_not_ready"])
        self.assertTrue(result.can_move_to_step3)
        self.assertEqual(result.blockers, ())
        self.assertEqual(result.provider_readiness_summary["status"], "step2_ready")

    def test_step2_not_ready_when_blockers_exist(self) -> None:
        rows = _build_rows(exclude_ids={"selected-rejected-row-1"})
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
            enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        self.assertTrue(result.step2_closure_status["step2_not_ready"])
        self.assertFalse(result.can_move_to_step3)
        self.assertGreater(len(result.blockers), 0)

    def test_no_fake_enrichment_is_applied(self) -> None:
        rows = _build_rows(exclude_ids={"selected-rejected-row-1"})
        result = run_roadmap_step2_closure_proof(
            rows,
            source_id="selected_provider_local_v1",
            trusted_seller_status_by_name=_trusted_map(),
            enrichment_contracts=FeedEnrichmentContracts(expected_currency_by_market={"IE": "EUR"}),
        )
        self.assertTrue(result.evidence_summary["no_fabricated_enrichment_detected"])
        for item in result.remediation_summary["results"]:
            for enrichment in item["applied_enrichments"]:
                self.assertIn(
                    enrichment,
                    {
                        "affiliate_url_coverage",
                        "return_policy_coverage",
                        "shipping_info_coverage",
                        "specs_description_coverage",
                        "taxonomy_linkage_coverage",
                        "trusted_seller_reliability_mapping",
                    },
                )

    def test_no_route_sitemap_or_naming_changes(self) -> None:
        status, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status, 200)
        self.assertIn("Recommended by PickWise", body)
        candidate_status, _candidate_body = render_best_slug_html("power-bank-roadmap-step2-closure-proof")
        self.assertEqual(candidate_status, 404)
        repository = get_buying_pages_repository()
        self.assertIsNone(repository.get_by_slug("power-bank-roadmap-step2-closure-proof"))
        sitemap = render_buying_pages_sitemap_xml(repository.list_pages(), base_url="https://localhost")
        self.assertNotIn("roadmap-step2-closure-proof", sitemap)

    def test_no_scraping_live_api_or_credentials(self) -> None:
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
