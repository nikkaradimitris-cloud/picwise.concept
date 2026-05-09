from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.economic_scoring import (  # noqa: E402
    CandidateApprovalStatus,
    score_candidate,
)
from picwise_buying_pages.keyword_clusters import KeywordClusterCandidate  # noqa: E402


def _candidate() -> KeywordClusterCandidate:
    return KeywordClusterCandidate(
        slug="best-wireless-headphones",
        main_keyword="best wireless headphones",
        keyword_aliases=("best wireless headphones", "wireless headphones comparison"),
        category="electronics/gadgets",
        price_band_applicable=True,
        generation_trace=("seed=test",),
    )


def _non_standard_candidate() -> KeywordClusterCandidate:
    return KeywordClusterCandidate(
        slug="best-insurance-plans",
        main_keyword="best insurance plans",
        keyword_aliases=("insurance comparison", "insurance plans for families"),
        category="insurance/lead-gen",
        price_band_applicable=False,
        generation_trace=("seed=test",),
    )


class BuyingPagesEconomicScoringTests(unittest.TestCase):
    def test_scoring_includes_all_required_inputs(self) -> None:
        scored = score_candidate(
            _candidate(),
            buying_intent_strength=0.82,
            product_availability=0.88,
            price_target_fit=0.91,
            commission_potential=0.75,
            estimated_traffic=0.63,
            competition_inverse=0.54,
            expected_revenue=0.66,
        )
        self.assertGreater(scored.weighted_score, 0.0)
        self.assertLessEqual(scored.weighted_score, 1.0)
        self.assertGreater(scored.signals.buying_intent_strength, 0.0)
        self.assertGreater(scored.signals.product_availability, 0.0)
        self.assertGreater(scored.signals.price_target_fit, 0.0)
        self.assertGreater(scored.signals.commission_potential, 0.0)
        self.assertGreater(scored.signals.estimated_traffic, 0.0)
        self.assertGreater(scored.signals.competition_inverse, 0.0)
        self.assertGreater(scored.signals.expected_revenue, 0.0)

    def test_keyword_existence_alone_is_not_enough_for_approval(self) -> None:
        scored = score_candidate(
            _candidate(),
            buying_intent_strength=0.95,
            product_availability=0.10,
            price_target_fit=0.20,
            commission_potential=0.15,
            estimated_traffic=0.25,
            competition_inverse=0.20,
            expected_revenue=0.12,
        )
        self.assertEqual(scored.approval_status, CandidateApprovalStatus.REJECTED_CANDIDATE)
        self.assertIn("hard_gates_failed", scored.approval_reason)

    def test_statuses_separate_approved_review_and_rejected(self) -> None:
        approved = score_candidate(
            _candidate(),
            buying_intent_strength=0.90,
            product_availability=0.85,
            price_target_fit=0.92,
            commission_potential=0.80,
            estimated_traffic=0.78,
            competition_inverse=0.65,
            expected_revenue=0.70,
        )
        review = score_candidate(
            _candidate(),
            buying_intent_strength=0.61,
            product_availability=0.58,
            price_target_fit=0.66,
            commission_potential=0.52,
            estimated_traffic=0.50,
            competition_inverse=0.47,
            expected_revenue=0.41,
        )
        rejected = score_candidate(
            _candidate(),
            buying_intent_strength=0.30,
            product_availability=0.20,
            price_target_fit=0.50,
            commission_potential=0.25,
            estimated_traffic=0.40,
            competition_inverse=0.35,
            expected_revenue=0.22,
        )
        self.assertEqual(approved.approval_status, CandidateApprovalStatus.APPROVED_CANDIDATE)
        self.assertEqual(review.approval_status, CandidateApprovalStatus.REVIEW_REQUIRED)
        self.assertEqual(rejected.approval_status, CandidateApprovalStatus.REJECTED_CANDIDATE)

    def test_price_target_fit_treats_80_250_band_as_economic_target_when_applicable(self) -> None:
        candidate = _candidate()
        weak_fit = score_candidate(
            candidate,
            buying_intent_strength=0.85,
            product_availability=0.80,
            price_target_fit=0.15,
            commission_potential=0.75,
            estimated_traffic=0.70,
            competition_inverse=0.62,
            expected_revenue=0.72,
        )
        strong_fit = score_candidate(
            candidate,
            buying_intent_strength=0.85,
            product_availability=0.80,
            price_target_fit=0.95,
            commission_potential=0.75,
            estimated_traffic=0.70,
            competition_inverse=0.62,
            expected_revenue=0.72,
        )
        self.assertGreater(strong_fit.weighted_score, weak_fit.weighted_score)
        self.assertIn(strong_fit.approval_status, (CandidateApprovalStatus.APPROVED_CANDIDATE,))

    def test_non_standard_candidates_are_not_forced_into_80_250_fit(self) -> None:
        scored = score_candidate(
            _non_standard_candidate(),
            buying_intent_strength=0.86,
            product_availability=0.76,
            price_target_fit=0.30,
            commission_potential=0.82,
            estimated_traffic=0.72,
            competition_inverse=0.68,
            expected_revenue=0.75,
        )
        self.assertIn(
            scored.approval_status,
            (CandidateApprovalStatus.APPROVED_CANDIDATE, CandidateApprovalStatus.REVIEW_REQUIRED),
        )


if __name__ == "__main__":
    unittest.main()
