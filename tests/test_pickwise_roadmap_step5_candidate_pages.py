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
from picwise_buying_pages import (  # noqa: E402
    CandidatePageStatus,
    build_candidate_page_batch,
    render_buying_pages_sitemap_xml,
)


def _load_step5_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step5_candidate_page_inputs.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


class PickWiseRoadmapStep5CandidatePagesTests(unittest.TestCase):
    def test_fixture_loads(self) -> None:
        payload = _load_step5_fixture()
        self.assertIn("keyword_clusters", payload)
        self.assertIn("products", payload)
        self.assertIn("locale_decisions", payload)
        self.assertIn("recommendation_mapping", payload)

    def test_candidate_builder_accepts_local_inputs_only(self) -> None:
        source = inspect.getsource(build_candidate_page_batch).lower()
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
            "api_key",
            "secret",
            "token",
            "credential",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)

    def test_step5_candidate_batch_contract_behaviors(self) -> None:
        payload = _load_step5_fixture()
        result = build_candidate_page_batch(
            keyword_clusters=payload["keyword_clusters"],
            products=payload["products"],
            locale_decisions=payload["locale_decisions"],
            recommendation_mapping=payload["recommendation_mapping"],
            max_candidate_pages=3000,
        )

        self.assertEqual(result["total_requested"], 3000)
        self.assertEqual(result["total_built"], len(payload["keyword_clusters"]))
        self.assertEqual(result, build_candidate_page_batch(**{
            "keyword_clusters": payload["keyword_clusters"],
            "products": payload["products"],
            "locale_decisions": payload["locale_decisions"],
            "recommendation_mapping": payload["recommendation_mapping"],
            "max_candidate_pages": 3000,
        }))

        by_cluster = {item["source_cluster_id"]: item for item in result["candidate_pages"]}

        ready = by_cluster["step5-us-power-bank-a"]
        self.assertEqual(ready["status"], CandidatePageStatus.candidate_ready.value)
        self.assertEqual(ready["product_count"], 4)
        self.assertEqual(set(ready["selected_product_ids"]), {"pb-us-1", "pb-us-2", "pb-us-3", "pb-us-4"})
        self.assertEqual(ready["recommended_product_id"], "pb-us-1")
        self.assertNotIn("pb-wrong-locale-gr-1", ready["selected_product_ids"])
        self.assertNotIn("pb-not-provider-ready-1", ready["selected_product_ids"])

        duplicate = by_cluster["step5-us-power-bank-b"]
        self.assertEqual(duplicate["status"], CandidatePageStatus.duplicate_slug_blocked.value)
        self.assertIn("duplicate_slug_detected", duplicate["blocker_reasons"])

        not_page_ready = by_cluster["step5-gr-non-page-ready-cluster"]
        self.assertEqual(not_page_ready["status"], CandidatePageStatus.needs_keywords.value)
        self.assertIn("keyword_cluster_not_page_ready", not_page_ready["blocker_reasons"])

        needs_four = by_cluster["step5-de-kaffee-four-products-missing"]
        self.assertEqual(needs_four["status"], CandidatePageStatus.needs_four_products.value)
        self.assertEqual(needs_four["product_count"], 3)
        self.assertIn("fewer_than_four_products", needs_four["blocker_reasons"])

        for page in result["candidate_pages"]:
            self.assertFalse(page["is_public"])
            self.assertFalse(page["is_indexable"])
            self.assertFalse(page["sitemap_included"])

        self.assertFalse(result["can_move_to_step6"])
        self.assertEqual(
            result["candidate_ready_count"]
            + result["blocked_count"],
            result["total_built"],
        )

    def test_no_best_route_exposure_no_sitemap_expansion_no_naming_changes(self) -> None:
        status, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status, 200)
        self.assertIn("Recommended by PickWise", body)

        candidate_status, _candidate_body = render_best_slug_html("best-power-bank-for-travel")
        self.assertEqual(candidate_status, 404)
        repository = get_buying_pages_repository()
        self.assertIsNone(repository.get_by_slug("best-power-bank-for-travel"))

        sitemap = render_buying_pages_sitemap_xml(repository.list_pages(), base_url="https://localhost")
        self.assertNotIn("best-power-bank-for-travel", sitemap)

    def test_no_gates_relaxed_no_fake_inputs_or_live_dependencies(self) -> None:
        source = inspect.getsource(build_candidate_page_batch).lower()
        forbidden_tokens = (
            "fabricate",
            "search volume api",
            "google api",
            "scrape",
            "credential",
            "api_key",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
