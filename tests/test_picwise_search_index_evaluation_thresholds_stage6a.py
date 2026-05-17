from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search_memory.blind_evaluation import build_blind_evaluation_report  # noqa: E402
from picwise_search_memory.evaluation_contracts import (  # noqa: E402
    BlindEvaluationCase,
    BlindEvaluationResult,
    BlindEvaluationThresholds,
)


class PicWiseSearchIndexEvaluationThresholdsStage6ATests(unittest.TestCase):
    def test_report_metrics_and_threshold_logic_fail_honestly(self) -> None:
        cases = (
            BlindEvaluationCase(
                case_id="c1",
                canonical_id="id_a",
                canonical_term="coffee grinder",
                mega_category_id="kitchen_cooking_household",
                query="coffee grinder",
                expected_normalized_term="coffee grinder",
                expected_mega_category_id="kitchen_cooking_household",
                variant_type="exact_canonical",
                source="registry",
                should_match=True,
            ),
            BlindEvaluationCase(
                case_id="c2",
                canonical_id="id_b",
                canonical_term="gaming mouse",
                mega_category_id="phones_mobile_accessories",
                query="gming mouse",
                expected_normalized_term="gaming mouse",
                expected_mega_category_id="phones_mobile_accessories",
                variant_type="missing_letter",
                source="generator",
                should_match=True,
            ),
            BlindEvaluationCase(
                case_id="c3",
                canonical_id="",
                canonical_term="",
                mega_category_id="",
                query="bank",
                expected_normalized_term="",
                expected_mega_category_id="",
                variant_type="broad_term_negative",
                source="broad_terms",
                should_match=False,
            ),
        )

        results = (
            BlindEvaluationResult(
                case_id="c1",
                query="coffee grinder",
                expected_canonical_id="id_a",
                expected_mega_category_id="kitchen_cooking_household",
                matched_canonical_id="id_a",
                matched_mega_category_id="kitchen_cooking_household",
                status="match",
                score=1.0,
                passed=True,
                reason_codes=("exact_normalized_variant_match",),
            ),
            BlindEvaluationResult(
                case_id="c2",
                query="gming mouse",
                expected_canonical_id="id_b",
                expected_mega_category_id="phones_mobile_accessories",
                matched_canonical_id="id_x",
                matched_mega_category_id="kitchen_cooking_household",
                status="match",
                score=0.77,
                passed=False,
                reason_codes=("fuzzy_match",),
            ),
            BlindEvaluationResult(
                case_id="c3",
                query="bank",
                expected_canonical_id="",
                expected_mega_category_id="",
                matched_canonical_id="id_y",
                matched_mega_category_id="fashion_clothing_accessories",
                status="match",
                score=0.76,
                passed=False,
                reason_codes=("false_positive",),
            ),
        )

        report = build_blind_evaluation_report(cases, results, thresholds=BlindEvaluationThresholds())
        self.assertEqual(report.total_cases, 3)
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 2)
        self.assertAlmostEqual(report.accuracy, 0.3333, places=4)
        self.assertAlmostEqual(report.canonical_accuracy, 0.5, places=4)
        self.assertAlmostEqual(report.mega_category_accuracy, 0.5, places=4)
        self.assertAlmostEqual(report.wrong_category_rate, 0.5, places=4)
        self.assertAlmostEqual(report.false_positive_rate, 1.0, places=4)
        self.assertAlmostEqual(report.broad_term_safety_rate, 0.0, places=4)
        self.assertFalse(report.can_proceed_to_stage5)
        self.assertEqual(len(report.failed_cases), 2)

    def test_can_proceed_to_stage5_true_only_when_all_thresholds_pass(self) -> None:
        cases = (
            BlindEvaluationCase(
                case_id="c1",
                canonical_id="id_a",
                canonical_term="coffee grinder",
                mega_category_id="kitchen_cooking_household",
                query="coffee grinder",
                expected_normalized_term="coffee grinder",
                expected_mega_category_id="kitchen_cooking_household",
                variant_type="exact_canonical",
                source="registry",
                should_match=True,
            ),
            BlindEvaluationCase(
                case_id="c2",
                canonical_id="id_b",
                canonical_term="car tyre",
                mega_category_id="car_tyres",
                query="car tire",
                expected_normalized_term="car tyre",
                expected_mega_category_id="car_tyres",
                variant_type="us_uk_spelling",
                source="generator",
                should_match=True,
            ),
            BlindEvaluationCase(
                case_id="c3",
                canonical_id="",
                canonical_term="",
                mega_category_id="",
                query="bank",
                expected_normalized_term="",
                expected_mega_category_id="",
                variant_type="broad_term_negative",
                source="broad_terms",
                should_match=False,
            ),
        )
        results = (
            BlindEvaluationResult(
                case_id="c1",
                query="coffee grinder",
                expected_canonical_id="id_a",
                expected_mega_category_id="kitchen_cooking_household",
                matched_canonical_id="id_a",
                matched_mega_category_id="kitchen_cooking_household",
                status="match",
                score=1.0,
                passed=True,
                reason_codes=("exact",),
            ),
            BlindEvaluationResult(
                case_id="c2",
                query="car tire",
                expected_canonical_id="id_b",
                expected_mega_category_id="car_tyres",
                matched_canonical_id="id_b",
                matched_mega_category_id="car_tyres",
                status="match",
                score=0.96,
                passed=True,
                reason_codes=("us_uk_spelling_match",),
            ),
            BlindEvaluationResult(
                case_id="c3",
                query="bank",
                expected_canonical_id="",
                expected_mega_category_id="",
                matched_canonical_id="",
                matched_mega_category_id="",
                status="no_match",
                score=0.0,
                passed=True,
                reason_codes=("broad_or_ambiguous_query",),
            ),
        )

        report = build_blind_evaluation_report(cases, results, thresholds=BlindEvaluationThresholds())
        self.assertTrue(report.can_proceed_to_stage5)
        self.assertTrue(all(report.threshold_status.values()))


if __name__ == "__main__":
    unittest.main()
