from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app.buying_routes import render_best_slug_html  # noqa: E402
from picwise_buying_pages import CandidateIndexDecisionStatus, evaluate_candidate_index_batch  # noqa: E402


def _load_selected_clean_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step6_selected_clean_index_batch.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


class PickWiseRoadmapStep6SelectedCleanIndexBatchTests(unittest.TestCase):
    def test_selected_clean_fixture_loads(self) -> None:
        payload = _load_selected_clean_fixture()
        self.assertIn("candidate_pages", payload)
        self.assertIn("candidate_evidence", payload)

    def test_all_selected_candidates_return_index_candidate(self) -> None:
        payload = _load_selected_clean_fixture()
        result = evaluate_candidate_index_batch(
            candidate_pages=payload["candidate_pages"],
            supporting_evidence={"candidate_evidence": payload["candidate_evidence"]},
        )
        self.assertEqual(result["total_candidates"], len(payload["candidate_pages"]))
        self.assertEqual(result["index_candidate_count"], len(payload["candidate_pages"]))
        self.assertEqual(result["rejected_count"], 0)
        self.assertEqual(result["hold_manual_review_count"], 0)
        self.assertEqual(result["duplicate_canonical_required_count"], 0)
        self.assertEqual(result["noindex_candidate_count"], 0)
        self.assertTrue(result["can_move_to_step7"])
        for decision in result["decisions"]:
            self.assertEqual(decision["status"], CandidateIndexDecisionStatus.index_candidate.value)
            self.assertFalse(decision["is_public"])
            self.assertTrue(decision["is_indexable"])
            self.assertTrue(decision["sitemap_allowed"])

    def test_all_decisions_remain_non_public_and_no_best_route_wiring(self) -> None:
        payload = _load_selected_clean_fixture()
        result = evaluate_candidate_index_batch(
            candidate_pages=payload["candidate_pages"],
            supporting_evidence={"candidate_evidence": payload["candidate_evidence"]},
        )
        for decision in result["decisions"]:
            self.assertFalse(decision["is_public"])
            status_code, _body = render_best_slug_html(decision["slug"])
            self.assertEqual(status_code, 404)

    def test_no_live_sitemap_expansion_side_effects(self) -> None:
        payload = _load_selected_clean_fixture()
        result = evaluate_candidate_index_batch(
            candidate_pages=payload["candidate_pages"],
            supporting_evidence={"candidate_evidence": payload["candidate_evidence"]},
        )
        self.assertEqual(result["sitemap_allowed_candidate_count"], len(payload["candidate_pages"]))
        # Candidate-level sitemap_allowed does not mutate any live sitemap file/route.
        self.assertTrue(payload["assertions"]["no_live_sitemap_file_changes"])
        self.assertTrue(payload["assertions"]["candidate_only_sitemap_allowed"])

    def test_step6_can_be_marked_closed_for_index_eligibility_decisioning(self) -> None:
        payload = _load_selected_clean_fixture()
        result = evaluate_candidate_index_batch(
            candidate_pages=payload["candidate_pages"],
            supporting_evidence={"candidate_evidence": payload["candidate_evidence"]},
        )
        self.assertTrue(result["can_move_to_step7"])
        self.assertTrue(payload["assertions"]["step6_closure_expected"])


if __name__ == "__main__":
    unittest.main()
