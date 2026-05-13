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
    CandidateIndexDecisionStatus,
    evaluate_candidate_index_batch,
    evaluate_candidate_index_eligibility,
    render_buying_pages_sitemap_xml,
)


def _load_step6_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step6_candidate_index_gate_inputs.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


class PickWiseRoadmapStep6CandidateIndexGateTests(unittest.TestCase):
    def test_clean_candidate_becomes_index_candidate(self) -> None:
        payload = _load_step6_fixture()
        clean = next(item for item in payload["candidate_pages"] if item["candidate_page_id"] == "step6-clean-index-candidate")
        evidence = payload["candidate_evidence"]["step6-clean-index-candidate"]
        decision = evaluate_candidate_index_eligibility(clean, supporting_evidence=evidence)
        self.assertEqual(decision["status"], CandidateIndexDecisionStatus.index_candidate.value)
        self.assertTrue(decision["is_indexable"])
        self.assertTrue(decision["sitemap_allowed"])
        self.assertFalse(decision["is_public"])

    def test_missing_four_products_blocks_as_policy_requires(self) -> None:
        payload = _load_step6_fixture()
        candidate = next(item for item in payload["candidate_pages"] if item["candidate_page_id"] == "step6-missing-four-products")
        evidence = payload["candidate_evidence"]["step6-missing-four-products"]
        decision = evaluate_candidate_index_eligibility(candidate, supporting_evidence=evidence)
        self.assertIn(decision["status"], {
            CandidateIndexDecisionStatus.rejected.value,
            CandidateIndexDecisionStatus.noindex_candidate.value,
            CandidateIndexDecisionStatus.hold_manual_review.value,
        })
        self.assertIn("requires_exactly_four_products", decision["blocker_reasons"])

    def test_recommended_product_outside_selection_blocks_index_candidate(self) -> None:
        payload = _load_step6_fixture()
        candidate = next(item for item in payload["candidate_pages"] if item["candidate_page_id"] == "step6-recommended-outside-selection")
        evidence = payload["candidate_evidence"]["step6-recommended-outside-selection"]
        decision = evaluate_candidate_index_eligibility(candidate, supporting_evidence=evidence)
        self.assertNotEqual(decision["status"], CandidateIndexDecisionStatus.index_candidate.value)
        self.assertIn("recommended_product_not_in_selected_products", decision["blocker_reasons"])

    def test_duplicate_slug_returns_duplicate_canonical_required_or_rejected(self) -> None:
        payload = _load_step6_fixture()
        result = evaluate_candidate_index_batch(
            candidate_pages=payload["candidate_pages"],
            supporting_evidence={"candidate_evidence": payload["candidate_evidence"]},
        )
        decisions = {item["candidate_page_id"]: item for item in result["decisions"]}
        for candidate_id in ("step6-duplicate-slug-a", "step6-duplicate-slug-b"):
            self.assertIn(decisions[candidate_id]["status"], {
                CandidateIndexDecisionStatus.duplicate_canonical_required.value,
                CandidateIndexDecisionStatus.rejected.value,
            })

    def test_similar_candidate_requires_canonical(self) -> None:
        payload = _load_step6_fixture()
        result = evaluate_candidate_index_batch(
            candidate_pages=payload["candidate_pages"],
            supporting_evidence={"candidate_evidence": payload["candidate_evidence"]},
        )
        decisions = {item["candidate_page_id"]: item for item in result["decisions"]}
        duplicate = decisions["step6-similar-candidate-duplicate"]
        self.assertEqual(duplicate["status"], CandidateIndexDecisionStatus.duplicate_canonical_required.value)
        self.assertTrue(duplicate["canonical_required"])
        self.assertIsNotNone(duplicate["canonical_target_slug"])

    def test_missing_affiliate_link_blocks_monetized_index_candidate(self) -> None:
        payload = _load_step6_fixture()
        candidate = next(item for item in payload["candidate_pages"] if item["candidate_page_id"] == "step6-missing-affiliate")
        evidence = payload["candidate_evidence"]["step6-missing-affiliate"]
        decision = evaluate_candidate_index_eligibility(candidate, supporting_evidence=evidence)
        self.assertNotEqual(decision["status"], CandidateIndexDecisionStatus.index_candidate.value)
        self.assertIn("missing_affiliate_links_for_monetized_page", decision["blocker_reasons"])

    def test_unsupported_locale_currency_blocks(self) -> None:
        payload = _load_step6_fixture()
        candidate = next(item for item in payload["candidate_pages"] if item["candidate_page_id"] == "step6-unsupported-locale-currency")
        evidence = payload["candidate_evidence"]["step6-unsupported-locale-currency"]
        decision = evaluate_candidate_index_eligibility(candidate, supporting_evidence=evidence)
        self.assertNotEqual(decision["status"], CandidateIndexDecisionStatus.index_candidate.value)
        self.assertIn("unsupported_locale_market_currency", decision["blocker_reasons"])

    def test_keyword_stuffing_blocks(self) -> None:
        payload = _load_step6_fixture()
        candidate = next(item for item in payload["candidate_pages"] if item["candidate_page_id"] == "step6-keyword-stuffing")
        evidence = payload["candidate_evidence"]["step6-keyword-stuffing"]
        decision = evaluate_candidate_index_eligibility(candidate, supporting_evidence=evidence)
        self.assertNotEqual(decision["status"], CandidateIndexDecisionStatus.index_candidate.value)
        self.assertIn("keyword_stuffing_detected", decision["blocker_reasons"])

    def test_thin_content_blocks_or_holds_review(self) -> None:
        payload = _load_step6_fixture()
        candidate = next(item for item in payload["candidate_pages"] if item["candidate_page_id"] == "step6-thin-content")
        evidence = payload["candidate_evidence"]["step6-thin-content"]
        decision = evaluate_candidate_index_eligibility(candidate, supporting_evidence=evidence)
        self.assertIn(decision["status"], {
            CandidateIndexDecisionStatus.noindex_candidate.value,
            CandidateIndexDecisionStatus.hold_manual_review.value,
            CandidateIndexDecisionStatus.rejected.value,
        })
        reasons = set(decision["blocker_reasons"]) | set(decision["review_reasons"])
        self.assertIn("thin_content_indicators_detected", reasons)

    def test_uncertain_evidence_becomes_hold_manual_review(self) -> None:
        payload = _load_step6_fixture()
        candidate = next(item for item in payload["candidate_pages"] if item["candidate_page_id"] == "step6-uncertain-evidence")
        evidence = payload["candidate_evidence"]["step6-uncertain-evidence"]
        decision = evaluate_candidate_index_eligibility(candidate, supporting_evidence=evidence)
        self.assertEqual(decision["status"], CandidateIndexDecisionStatus.hold_manual_review.value)
        self.assertIn("uncertain_supporting_evidence", decision["review_reasons"])

    def test_sitemap_allowed_is_candidate_only_with_no_live_expansion(self) -> None:
        payload = _load_step6_fixture()
        result = evaluate_candidate_index_batch(
            candidate_pages=payload["candidate_pages"],
            supporting_evidence={"candidate_evidence": payload["candidate_evidence"]},
        )
        repository = get_buying_pages_repository()
        sitemap_xml = render_buying_pages_sitemap_xml(repository.list_pages(), base_url="https://localhost")
        for decision in result["decisions"]:
            if decision["sitemap_allowed"]:
                self.assertNotIn(decision["slug"], sitemap_xml)

    def test_no_public_best_route_exposure(self) -> None:
        payload = _load_step6_fixture()
        for candidate in payload["candidate_pages"]:
            status_code, _body = render_best_slug_html(candidate["slug"])
            self.assertEqual(status_code, 404)

    def test_no_naming_changes(self) -> None:
        status_code, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status_code, 200)
        self.assertIn("Recommended by PickWise", body)

    def test_no_gates_relaxed_and_no_fake_live_dependencies(self) -> None:
        source_eligibility = inspect.getsource(evaluate_candidate_index_eligibility).lower()
        source_batch = inspect.getsource(evaluate_candidate_index_batch).lower()
        source = f"{source_eligibility}\n{source_batch}"
        forbidden_tokens = (
            "requests",
            "httpx",
            "urllib.request",
            "scrape",
            "selenium",
            "playwright",
            "google api",
            "affiliate api",
            "api_key",
            "credential",
            "fabricate",
            "search volume api",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)

    def test_batch_evaluator_returns_deterministic_counts(self) -> None:
        payload = _load_step6_fixture()
        args = {
            "candidate_pages": payload["candidate_pages"],
            "supporting_evidence": {"candidate_evidence": payload["candidate_evidence"]},
        }
        first = evaluate_candidate_index_batch(**args)
        second = evaluate_candidate_index_batch(**args)
        self.assertEqual(first, second)
        self.assertEqual(first["total_candidates"], len(payload["candidate_pages"]))
        self.assertEqual(
            first["total_candidates"],
            first["index_candidate_count"]
            + first["noindex_candidate_count"]
            + first["hold_manual_review_count"]
            + first["rejected_count"]
            + first["duplicate_canonical_required_count"],
        )


if __name__ == "__main__":
    unittest.main()
