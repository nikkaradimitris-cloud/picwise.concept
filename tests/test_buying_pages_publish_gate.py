from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app.buying_routes import get_buying_pages_repository, render_best_slug_html  # noqa: E402
from picwise_buying_pages import (  # noqa: E402
    APPROVAL_DECISION_APPROVED,
    APPROVAL_DECISION_MANUAL_REQUIRED,
    APPROVAL_DECISION_PENDING,
    APPROVAL_DECISION_REJECTED,
    APPROVAL_DECISION_REVIEW_REQUIRED,
    ApprovalStatus,
    BuyingPagesRepository,
    IndexStatus,
    PUBLISH_OUTCOME_BLOCKED,
    PUBLISH_OUTCOME_NEEDS_REVIEW,
    PUBLISH_OUTCOME_PUBLISHED,
    evaluate_publish_gate,
    generate_first_scale_batch,
    is_publicly_eligible,
    load_seed_buying_pages,
    render_buying_pages_sitemap_xml,
)
from picwise_buying_pages.models import SellerReliabilityStatus  # noqa: E402


def _unsafe_mutate_page(page, **changes):
    for key, value in changes.items():
        object.__setattr__(page, key, value)
    return page


class BuyingPagesPublishGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.published_pages = load_seed_buying_pages()
        self.published_repository = BuyingPagesRepository(self.published_pages)
        self.candidate = generate_first_scale_batch().candidate_pages[0]

    def test_candidate_passing_all_gates_and_approved_becomes_published(self) -> None:
        result = evaluate_publish_gate(
            self.candidate,
            approval_decision=APPROVAL_DECISION_APPROVED,
            published_repository=self.published_repository,
            economic_score_passed=True,
        )
        self.assertEqual(result.outcome, PUBLISH_OUTCOME_PUBLISHED)
        self.assertEqual(result.page.approval_status, ApprovalStatus.APPROVED)
        self.assertEqual(result.page.index_status, IndexStatus.INDEXABLE)
        self.assertEqual(result.page.slug, self.candidate.slug)

    def test_approved_candidate_failing_economic_scoring_is_blocked(self) -> None:
        result = evaluate_publish_gate(
            self.candidate,
            approval_decision=APPROVAL_DECISION_APPROVED,
            published_repository=self.published_repository,
            economic_score_passed=False,
        )
        self.assertEqual(result.outcome, PUBLISH_OUTCOME_BLOCKED)
        self.assertIn("economic_scoring_not_passed", result.reason_codes)

    def test_approved_candidate_failing_google_quality_gate_is_blocked(self) -> None:
        broken = _unsafe_mutate_page(
            replace(self.candidate),
            products=tuple(
                replace(product, reason_summary="keyword", buying_reason="keyword")
                for product in self.candidate.products
            ),
            faq_items=tuple(),
            related_searches=tuple(),
        )
        result = evaluate_publish_gate(
            broken,
            approval_decision=APPROVAL_DECISION_APPROVED,
            published_repository=self.published_repository,
            economic_score_passed=True,
        )
        self.assertEqual(result.outcome, PUBLISH_OUTCOME_BLOCKED)
        self.assertIn("google_quality_gate_not_passed", result.reason_codes)

    def test_approved_candidate_failing_product_and_seller_gates_is_blocked(self) -> None:
        broken = _unsafe_mutate_page(
            replace(self.candidate),
            products=(
                replace(
                    self.candidate.products[0],
                    availability="out_of_stock",
                    seller_reliability_status=SellerReliabilityStatus.BLOCKED,
                ),
                *self.candidate.products[1:],
            ),
        )
        result = evaluate_publish_gate(
            broken,
            approval_decision=APPROVAL_DECISION_APPROVED,
            published_repository=self.published_repository,
            economic_score_passed=True,
        )
        self.assertEqual(result.outcome, PUBLISH_OUTCOME_BLOCKED)
        self.assertIn("product_ok_gate_not_passed", result.reason_codes)
        self.assertIn("seller_reliability_gate_not_passed", result.reason_codes)

    def test_rejected_candidate_remains_noindex_and_non_public(self) -> None:
        result = evaluate_publish_gate(
            self.candidate,
            approval_decision=APPROVAL_DECISION_REJECTED,
            published_repository=self.published_repository,
            economic_score_passed=True,
        )
        self.assertEqual(result.outcome, PUBLISH_OUTCOME_BLOCKED)
        self.assertEqual(result.page.approval_status, ApprovalStatus.REJECTED)
        self.assertEqual(result.page.index_status, IndexStatus.NOINDEX)
        self.assertFalse(is_publicly_eligible(result.page, economic_score_passed=True))

    def test_manual_or_review_required_candidate_remains_noindex_and_non_public(self) -> None:
        for decision in (APPROVAL_DECISION_MANUAL_REQUIRED, APPROVAL_DECISION_REVIEW_REQUIRED):
            result = evaluate_publish_gate(
                self.candidate,
                approval_decision=decision,
                published_repository=self.published_repository,
                economic_score_passed=True,
            )
            self.assertEqual(result.outcome, PUBLISH_OUTCOME_NEEDS_REVIEW)
            self.assertEqual(result.page.approval_status, ApprovalStatus.PENDING_REVIEW)
            self.assertEqual(result.page.index_status, IndexStatus.NOINDEX)
            self.assertFalse(is_publicly_eligible(result.page, economic_score_passed=True))

    def test_pending_candidate_is_not_public(self) -> None:
        result = evaluate_publish_gate(
            self.candidate,
            approval_decision=APPROVAL_DECISION_PENDING,
            published_repository=self.published_repository,
            economic_score_passed=True,
        )
        self.assertEqual(result.outcome, PUBLISH_OUTCOME_NEEDS_REVIEW)
        self.assertEqual(result.page.approval_status, ApprovalStatus.PENDING_REVIEW)
        self.assertEqual(result.page.index_status, IndexStatus.NOINDEX)

    def test_duplicate_slug_publish_is_blocked(self) -> None:
        existing = self.published_pages[0]
        result = evaluate_publish_gate(
            existing,
            approval_decision=APPROVAL_DECISION_APPROVED,
            published_repository=self.published_repository,
            economic_score_passed=True,
        )
        self.assertEqual(result.outcome, PUBLISH_OUTCOME_BLOCKED)
        self.assertIn("duplicate_slug_conflict", result.reason_codes)

    def test_alias_conflict_publish_is_blocked(self) -> None:
        existing = self.published_pages[0]
        conflicting = _unsafe_mutate_page(
            replace(self.candidate),
            keyword_aliases=(existing.main_keyword, *self.candidate.keyword_aliases[1:]),
        )
        result = evaluate_publish_gate(
            conflicting,
            approval_decision=APPROVAL_DECISION_APPROVED,
            published_repository=self.published_repository,
            economic_score_passed=True,
        )
        self.assertEqual(result.outcome, PUBLISH_OUTCOME_BLOCKED)
        self.assertIn("alias_conflict", result.reason_codes)

    def test_published_result_sets_approved_and_indexable_statuses(self) -> None:
        result = evaluate_publish_gate(
            self.candidate,
            approval_decision=APPROVAL_DECISION_APPROVED,
            published_repository=self.published_repository,
            economic_score_passed=True,
        )
        self.assertEqual(result.page.approval_status, ApprovalStatus.APPROVED)
        self.assertEqual(result.page.index_status, IndexStatus.INDEXABLE)

    def test_rejected_manual_and_pending_results_keep_noindex(self) -> None:
        for decision in (
            APPROVAL_DECISION_REJECTED,
            APPROVAL_DECISION_MANUAL_REQUIRED,
            APPROVAL_DECISION_PENDING,
        ):
            result = evaluate_publish_gate(
                self.candidate,
                approval_decision=decision,
                published_repository=self.published_repository,
                economic_score_passed=True,
            )
            self.assertEqual(result.page.index_status, IndexStatus.NOINDEX)

    def test_reason_codes_are_preserved_and_understandable(self) -> None:
        broken = _unsafe_mutate_page(
            replace(self.candidate),
            products=(
                replace(
                    self.candidate.products[0],
                    availability="out_of_stock",
                    reason_summary="placeholder",
                    buying_reason="placeholder",
                ),
                *self.candidate.products[1:],
            ),
            recommended_product_id="missing-id",
            faq_items=tuple(),
            related_searches=tuple(),
        )
        result = evaluate_publish_gate(
            broken,
            approval_decision=APPROVAL_DECISION_APPROVED,
            published_repository=self.published_repository,
            economic_score_passed=False,
        )
        self.assertIn("economic_scoring_not_passed", result.reason_codes)
        self.assertIn("google_quality_gate_not_passed", result.reason_codes)
        self.assertIn("index_gate_not_passed", result.reason_codes)
        self.assertIn("invalid_recommended_product", result.reason_codes)
        self.assertTrue(any(code.startswith("google:") for code in result.reason_codes))
        self.assertTrue(any(code.startswith("index:") for code in result.reason_codes))

    def test_sitemap_includes_published_approved_page(self) -> None:
        result = evaluate_publish_gate(
            self.candidate,
            approval_decision=APPROVAL_DECISION_APPROVED,
            published_repository=self.published_repository,
            economic_score_passed=True,
        )
        self.assertEqual(result.outcome, PUBLISH_OUTCOME_PUBLISHED)
        xml = render_buying_pages_sitemap_xml((result.page,), base_url="https://localhost")
        self.assertIn(f"/best/{self.candidate.slug}", xml)

    def test_sitemap_excludes_pending_rejected_and_manual_candidates(self) -> None:
        manual = evaluate_publish_gate(
            self.candidate,
            approval_decision=APPROVAL_DECISION_MANUAL_REQUIRED,
            published_repository=self.published_repository,
            economic_score_passed=True,
        )
        rejected = evaluate_publish_gate(
            self.candidate,
            approval_decision=APPROVAL_DECISION_REJECTED,
            published_repository=self.published_repository,
            economic_score_passed=True,
        )
        pending = evaluate_publish_gate(
            self.candidate,
            approval_decision=APPROVAL_DECISION_PENDING,
            published_repository=self.published_repository,
            economic_score_passed=True,
        )
        xml = render_buying_pages_sitemap_xml(
            (manual.page, rejected.page, pending.page),
            base_url="https://localhost",
        )
        self.assertNotIn(f"/best/{self.candidate.slug}", xml)

    def test_best_route_behavior_for_existing_fixtures_remains_unchanged(self) -> None:
        status, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status, 200)
        self.assertIn("Recommended by PickWise", body)
        missing_status, _missing_body = render_best_slug_html("does-not-exist")
        self.assertEqual(missing_status, 404)

    def test_existing_candidate_only_slugs_still_do_not_leak(self) -> None:
        status, _body = render_best_slug_html(self.candidate.slug)
        self.assertEqual(status, 404)
        repository = get_buying_pages_repository()
        self.assertIsNone(repository.get_by_slug(self.candidate.slug))


if __name__ == "__main__":
    unittest.main()
