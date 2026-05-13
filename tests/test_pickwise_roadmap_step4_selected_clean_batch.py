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


def _selected_clean_fixture_path() -> Path:
    return ROOT / "tests" / "fixtures" / "roadmap_step4_selected_clean_keyword_batch.json"


def _load_selected_clean_batch() -> list[dict[str, object]]:
    payload = json.loads(_selected_clean_fixture_path().read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    return payload


class PickWiseRoadmapStep4SelectedCleanBatchTests(unittest.TestCase):
    def test_selected_clean_fixture_loads(self) -> None:
        batch = _load_selected_clean_batch()
        self.assertEqual(len(batch), 5)

    def test_every_selected_cluster_is_page_ready(self) -> None:
        for item in _load_selected_clean_batch():
            _cluster, result = build_keyword_cluster_from_local_input(item)
            self.assertEqual(result.status, KeywordClusterStatus.PAGE_READY)
            self.assertTrue(result.is_page_ready)
            self.assertFalse(result.blocked)
            self.assertFalse(result.review_required)

    def test_batch_validator_allows_step5_gate_for_selected_clean_batch(self) -> None:
        summary = validate_keyword_cluster_batch(_load_selected_clean_batch(), review_rate_threshold=0.1)
        self.assertEqual(summary["blocked_count"], 0)
        self.assertLessEqual(summary["review_required_count"], 0)
        self.assertTrue(summary["can_move_to_step5"])

    def test_selected_clusters_have_expected_keyword_group_sizes(self) -> None:
        for item in _load_selected_clean_batch():
            main_keyword = item.get("main_keyword")
            support_keywords = item.get("support_keywords", [])
            long_tail_keywords = item.get("long_tail_keywords", [])
            self.assertIsInstance(main_keyword, str)
            self.assertEqual(1, 1 if main_keyword.strip() else 0)
            self.assertGreaterEqual(len(support_keywords), 3)
            self.assertLessEqual(len(support_keywords), 5)
            self.assertGreaterEqual(len(long_tail_keywords), 10)
            self.assertLessEqual(len(long_tail_keywords), 30)

    def test_selected_batch_has_required_locale_market_coverage(self) -> None:
        batch = _load_selected_clean_batch()
        locale_market_pairs = {(str(item["locale"]), str(item["market"])) for item in batch}
        self.assertIn(("en-US", "US"), locale_market_pairs)
        self.assertIn(("en-GB", "UK"), locale_market_pairs)
        self.assertIn(("de-DE", "DE"), locale_market_pairs)
        self.assertIn(("el-GR", "GR"), locale_market_pairs)

    def test_language_variants_preserve_english_german_greek_and_greeklish_inputs(self) -> None:
        by_id = {str(item["cluster_id"]): item for item in _load_selected_clean_batch()}

        uk_cluster, uk_result = build_keyword_cluster_from_local_input(
            by_id["selected-clean-uk-tyres-comparison-intent"]
        )
        de_cluster, de_result = build_keyword_cluster_from_local_input(
            by_id["selected-clean-de-reifen-buyer-intent"]
        )
        gr_cluster, gr_result = build_keyword_cluster_from_local_input(
            by_id["selected-clean-gr-power-bank-greek-greeklish"]
        )

        self.assertFalse(uk_result.blocked)
        self.assertFalse(de_result.blocked)
        self.assertFalse(gr_result.blocked)
        self.assertIn("best all season tires for uk roads", {v.keyword for v in uk_cluster.variants})
        self.assertIn("beste winter reifen fuer suv kaufen", {v.keyword for v in de_cluster.variants})
        self.assertIn("καλύτερο power bank 20000mah για ταξίδι", {v.keyword for v in gr_cluster.variants})
        self.assertIn("kalytero power bank 20000mah gia taxidi", gr_cluster.main_keyword)

    def test_no_fabricated_search_volume_and_unknown_is_used_when_missing(self) -> None:
        def _norm(value: str) -> str:
            return " ".join(value.strip().lower().split())

        for item in _load_selected_clean_batch():
            cluster, _result = build_keyword_cluster_from_local_input(item)
            valid_buckets = {bucket.value for bucket in KeywordVolumeBucket}
            self.assertTrue(cluster.volume_bucket_by_keyword)
            allowed_keywords = {
                _norm(cluster.main_keyword),
                *(_norm(value) for value in cluster.support_keywords),
                *(_norm(value) for value in cluster.long_tail_keywords),
                *(_norm(value.keyword) for value in cluster.variants),
            }
            for keyword, bucket in cluster.volume_bucket_by_keyword.items():
                self.assertIn(bucket.value, valid_buckets)
                self.assertIn(_norm(keyword), allowed_keywords)
            self.assertIn(KeywordVolumeBucket.UNKNOWN, set(cluster.volume_bucket_by_keyword.values()))

    def test_no_public_route_sitemap_or_naming_changes(self) -> None:
        status, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status, 200)
        self.assertIn("Recommended by PickWise", body)
        candidate_status, _candidate_body = render_best_slug_html("roadmap-step4-selected-clean-candidate")
        self.assertEqual(candidate_status, 404)
        repository = get_buying_pages_repository()
        self.assertIsNone(repository.get_by_slug("roadmap-step4-selected-clean-candidate"))
        sitemap = render_buying_pages_sitemap_xml(repository.list_pages(), base_url="https://localhost")
        self.assertNotIn("roadmap-step4-selected-clean-candidate", sitemap)

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
