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
from picwise_buying_pages.keyword_source_contract import (  # noqa: E402
    KeywordClusterStatus,
    KeywordVolumeBucket,
    build_keyword_cluster_from_local_input,
    validate_keyword_cluster_batch,
)


def _load_step4_fixture() -> list[dict[str, object]]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step4_keyword_clusters.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    return payload


def _cluster_by_id(cluster_id: str) -> dict[str, object]:
    for item in _load_step4_fixture():
        if str(item.get("cluster_id")) == cluster_id:
            return item
    raise AssertionError(f"Missing fixture cluster: {cluster_id}")


class PickWiseRoadmapStep4KeywordClusterTests(unittest.TestCase):
    def test_valid_cluster_passes_validation(self) -> None:
        cluster, result = build_keyword_cluster_from_local_input(_cluster_by_id("valid-us-power-bank"))
        self.assertEqual(result.status, KeywordClusterStatus.PAGE_READY)
        self.assertTrue(result.is_page_ready)
        self.assertFalse(result.blocked)
        self.assertFalse(result.review_required)
        self.assertEqual(cluster.main_keyword, "best power bank 20000mah")

    def test_exactly_one_main_keyword_is_required(self) -> None:
        payload = dict(_cluster_by_id("valid-us-power-bank"))
        payload["main_keyword"] = ["best power bank 20000mah", "best power bank"]
        _cluster, result = build_keyword_cluster_from_local_input(payload)
        self.assertTrue(result.blocked)
        self.assertIn("invalid_main_keyword_count", result.blocker_reasons)

    def test_support_keywords_preferred_range_is_3_to_5(self) -> None:
        payload = dict(_cluster_by_id("valid-us-power-bank"))
        payload["support_keywords"] = ["only one support keyword"]
        _cluster, result = build_keyword_cluster_from_local_input(payload)
        self.assertIn("support_keywords_outside_preferred_range", result.warning_reasons)
        self.assertFalse(result.blocked)

    def test_long_tail_10_to_30_required_for_page_ready(self) -> None:
        _cluster, result = build_keyword_cluster_from_local_input(_cluster_by_id("too-few-long-tail"))
        self.assertTrue(result.blocked)
        self.assertTrue(result.insufficient_long_tail)
        self.assertIn("insufficient_long_tail_keywords_for_page_ready", result.blocker_reasons)

    def test_volume_buckets_are_explicit_and_not_fabricated(self) -> None:
        cluster, _result = build_keyword_cluster_from_local_input(_cluster_by_id("valid-us-power-bank"))
        self.assertEqual(cluster.volume_bucket_by_keyword["best power bank 20000mah"], KeywordVolumeBucket.HIGH)
        self.assertEqual(cluster.volume_bucket_by_keyword["powerbank"], KeywordVolumeBucket.UNKNOWN)
        self.assertNotIn("nonexistent-keyword", cluster.volume_bucket_by_keyword)

    def test_language_variants_are_preserved_for_english_greek_greeklish_german(self) -> None:
        _, uk = build_keyword_cluster_from_local_input(_cluster_by_id("valid-uk-tyres-spelling"))
        _, de = build_keyword_cluster_from_local_input(_cluster_by_id("valid-de-reifen"))
        gr_cluster, gr = build_keyword_cluster_from_local_input(_cluster_by_id("valid-gr-greek-greeklish"))
        self.assertFalse(uk.blocked)
        self.assertFalse(de.blocked)
        self.assertFalse(gr.blocked)
        variant_keywords = {item.keyword for item in gr_cluster.variants}
        self.assertIn("καλύτερο power bank", variant_keywords)
        self.assertIn("kalytero power bank 20000mah", gr_cluster.main_keyword)

    def test_typo_spec_brand_model_variants_are_preserved(self) -> None:
        cluster, _result = build_keyword_cluster_from_local_input(_cluster_by_id("product-brand-model-spec-cluster"))
        typed = {(item.keyword, item.variant_type.value) for item in cluster.variants}
        self.assertIn(("Anker737", "typo_variant"), typed)
        self.assertIn(("140w usb c", "spec_variant"), typed)
        self.assertIn(("Anker 737", "brand_model_variant"), typed)

    def test_informational_only_cluster_is_blocked_for_buying_page_readiness(self) -> None:
        _cluster, result = build_keyword_cluster_from_local_input(_cluster_by_id("informational-only-cluster"))
        self.assertTrue(result.blocked)
        self.assertTrue(result.informational_only)
        self.assertIn("informational_only_cluster_not_page_ready", result.blocker_reasons)

    def test_ambiguous_cluster_requires_review(self) -> None:
        _cluster, result = build_keyword_cluster_from_local_input(_cluster_by_id("ambiguous-cluster"))
        self.assertEqual(result.status, KeywordClusterStatus.REVIEW_REQUIRED)
        self.assertTrue(result.review_required)
        self.assertFalse(result.blocked)
        self.assertTrue(result.ambiguous_intent)

    def test_duplicate_heavy_cluster_detected_deterministically(self) -> None:
        _cluster, result = build_keyword_cluster_from_local_input(_cluster_by_id("duplicate-heavy-cluster"))
        self.assertTrue(result.blocked)
        self.assertGreaterEqual(len(result.duplicate_keywords), 1)
        self.assertIn("keyword_stuffing_detected", result.blocker_reasons)
        self.assertIn("duplicate_keywords_detected", result.review_reasons)

    def test_locale_market_mismatch_is_blocked(self) -> None:
        _cluster, result = build_keyword_cluster_from_local_input(_cluster_by_id("locale-market-mismatch-cluster"))
        self.assertTrue(result.blocked)
        self.assertTrue(result.locale_market_issue)
        self.assertIn("locale_market_mismatch_or_unsupported", result.blocker_reasons)

    def test_product_category_intent_linkage_is_required(self) -> None:
        payload = dict(_cluster_by_id("valid-us-power-bank"))
        payload["target_category"] = "garden/tools"
        payload["main_keyword"] = "best office chair for back support"
        payload["support_keywords"] = ["office chair ergonomic", "office chair lumbar support", "office chair mesh"]
        payload["long_tail_keywords"] = [
            "best office chair for remote work",
            "office chair with headrest",
            "office chair under 200 usd",
            "office chair for lower back pain",
            "ergonomic office chair for long sitting",
            "mesh office chair breathable back",
            "office chair for home office",
            "office chair comparison buyers guide",
            "office chair seat depth adjustment",
            "best office chair for developers"
        ]
        payload["product_spec_signals"] = []
        payload["brand_model_signals"] = []
        _cluster, result = build_keyword_cluster_from_local_input(payload)
        self.assertTrue(result.blocked)
        self.assertIn("missing_product_category_intent_linkage", result.blocker_reasons)

    def test_batch_validator_returns_deterministic_counts(self) -> None:
        batch = _load_step4_fixture()
        first = validate_keyword_cluster_batch(batch)
        second = validate_keyword_cluster_batch(batch)
        self.assertEqual(first, second)
        self.assertEqual(first["total_clusters"], len(batch))
        self.assertEqual(
            first["page_ready_count"] + first["review_required_count"] + first["blocked_count"],
            first["total_clusters"],
        )
        self.assertGreaterEqual(first["duplicate_keyword_count"], 1)
        self.assertGreaterEqual(first["locale_market_issue_count"], 1)

    def test_can_move_to_step5_only_with_no_blockers_and_acceptable_review_rate(self) -> None:
        ready_batch = [
            _cluster_by_id("valid-us-power-bank"),
            _cluster_by_id("valid-uk-tyres-spelling"),
            _cluster_by_id("valid-de-reifen"),
            _cluster_by_id("valid-gr-greek-greeklish"),
            _cluster_by_id("product-brand-model-spec-cluster"),
        ]
        ready = validate_keyword_cluster_batch(ready_batch, review_rate_threshold=0.2)
        self.assertTrue(ready["can_move_to_step5"])

        mixed_batch = [*ready_batch, _cluster_by_id("ambiguous-cluster")]
        strict = validate_keyword_cluster_batch(mixed_batch, review_rate_threshold=0.1)
        self.assertFalse(strict["can_move_to_step5"])

        blocked_batch = [*ready_batch, _cluster_by_id("missing-main-keyword")]
        blocked = validate_keyword_cluster_batch(blocked_batch, review_rate_threshold=0.5)
        self.assertFalse(blocked["can_move_to_step5"])

    def test_no_public_routes_sitemap_or_naming_changes(self) -> None:
        status, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status, 200)
        self.assertIn("Recommended by PickWise", body)
        candidate_status, _candidate_body = render_best_slug_html("roadmap-step4-keyword-cluster-candidate")
        self.assertEqual(candidate_status, 404)
        repository = get_buying_pages_repository()
        self.assertIsNone(repository.get_by_slug("roadmap-step4-keyword-cluster-candidate"))
        sitemap = render_buying_pages_sitemap_xml(repository.list_pages(), base_url="https://localhost")
        self.assertNotIn("roadmap-step4-keyword-cluster-candidate", sitemap)

    def test_no_gates_relaxed_no_scraping_live_google_api_or_credentials_added(self) -> None:
        from picwise_buying_pages import keyword_source_contract as module

        source = inspect.getsource(module).lower()
        forbidden_tokens = (
            "requests",
            "httpx",
            "urllib.request",
            "beautifulsoup",
            "selenium",
            "playwright",
            "scrapy",
            "aiohttp",
            "googleads",
            "search console api",
            "api_key",
            "secret",
            "token",
            "credential",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
