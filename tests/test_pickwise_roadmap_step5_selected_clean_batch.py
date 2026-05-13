from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages import CandidatePageStatus, build_candidate_page_batch  # noqa: E402


def _load_selected_clean_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step5_selected_clean_candidate_batch.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


class PickWiseRoadmapStep5SelectedCleanBatchTests(unittest.TestCase):
    def test_selected_clean_batch_builds_successfully(self) -> None:
        payload = _load_selected_clean_fixture()
        result = build_candidate_page_batch(
            keyword_clusters=payload["keyword_clusters"],
            products=payload["products"],
            locale_decisions=payload["locale_decisions"],
            recommendation_mapping=payload["recommendation_mapping"],
            max_candidate_pages=int(payload["max_candidate_pages"]),
        )
        self.assertEqual(result["total_requested"], 3000)
        self.assertEqual(result["total_built"], len(payload["keyword_clusters"]))
        self.assertEqual(result["blocked_count"], 0)
        self.assertEqual(result["candidate_ready_count"], result["total_built"])
        self.assertTrue(result["can_move_to_step6"])

    def test_target_count_planning_for_3000_is_deterministic(self) -> None:
        payload = _load_selected_clean_fixture()
        first = build_candidate_page_batch(
            keyword_clusters=payload["keyword_clusters"],
            products=payload["products"],
            locale_decisions=payload["locale_decisions"],
            recommendation_mapping=payload["recommendation_mapping"],
            max_candidate_pages=int(payload["target_count"]),
        )
        second = build_candidate_page_batch(
            keyword_clusters=payload["keyword_clusters"],
            products=payload["products"],
            locale_decisions=payload["locale_decisions"],
            recommendation_mapping=payload["recommendation_mapping"],
            max_candidate_pages=int(payload["target_count"]),
        )
        self.assertEqual(first, second)
        self.assertTrue(first["planning_summary"]["capacity_satisfies_requested_slots"])
        self.assertGreaterEqual(first["planning_summary"]["deterministic_slot_capacity"], 3000)

    def test_no_public_index_or_sitemap_flags_set(self) -> None:
        payload = _load_selected_clean_fixture()
        result = build_candidate_page_batch(
            keyword_clusters=payload["keyword_clusters"],
            products=payload["products"],
            locale_decisions=payload["locale_decisions"],
            recommendation_mapping=payload["recommendation_mapping"],
            max_candidate_pages=int(payload["target_count"]),
        )
        for page in result["candidate_pages"]:
            self.assertEqual(page["status"], CandidatePageStatus.candidate_ready.value)
            self.assertFalse(page["is_public"])
            self.assertFalse(page["is_indexable"])
            self.assertFalse(page["sitemap_included"])
            self.assertEqual(page["product_count"], 4)
            self.assertIn(page["recommended_product_id"], page["selected_product_ids"])

    def test_step5_closure_proof_is_planning_only_not_step6_decision(self) -> None:
        payload = _load_selected_clean_fixture()
        result = build_candidate_page_batch(
            keyword_clusters=payload["keyword_clusters"],
            products=payload["products"],
            locale_decisions=payload["locale_decisions"],
            recommendation_mapping=payload["recommendation_mapping"],
            max_candidate_pages=int(payload["target_count"]),
        )
        self.assertTrue(result["can_move_to_step6"])
        self.assertEqual(result["needs_keywords_count"], 0)
        self.assertEqual(result["needs_products_count"], 0)
        self.assertEqual(result["needs_locale_count"], 0)
        self.assertEqual(result["needs_four_products_count"], 0)
        self.assertEqual(result["duplicate_slug_count"], 0)


if __name__ == "__main__":
    unittest.main()
