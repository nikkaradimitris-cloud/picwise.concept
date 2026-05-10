from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.confidence import (  # noqa: E402
    clamp_confidence,
    resolve_safe_status,
    score_detector_analysis,
)
from picwise_nlu.normalizer import normalize_query  # noqa: E402
from picwise_nlu.typo_normalizer import normalize_greeklish_and_typos  # noqa: E402
from picwise_nlu.detector_pipeline import analyze_normalized_query  # noqa: E402


class LocalNLUConfidenceAndStatusTests(unittest.TestCase):
    def test_empty_input_requires_safe_review_status(self) -> None:
        scored = score_detector_analysis({}, raw_query="")
        status = resolve_safe_status(scored, scored["confidence"], raw_query="")
        self.assertIn(status["status"], {"manual_review_required", "invalid_intent"})
        self.assertTrue(status["needs_review"])

    def test_unknown_query_requires_review_or_insufficient_data(self) -> None:
        scored = score_detector_analysis({}, raw_query="asdf qwer zzzz")
        status = resolve_safe_status(scored, scored["confidence"], raw_query="asdf qwer zzzz")
        self.assertIn(status["status"], {"manual_review_required", "insufficient_data", "no_safe_result"})
        self.assertTrue(status["needs_review"])

    def test_strong_tyre_query_resolves_with_good_confidence(self) -> None:
        normalized = normalize_greeklish_and_typos(
            normalize_query("goodyear efficientgrip 195/65 r15 comfort")
        )
        analysis = analyze_normalized_query(normalized)
        scored = score_detector_analysis(analysis, raw_query="goodyear efficientgrip 195/65 r15 comfort")
        status = resolve_safe_status(scored, scored["confidence"], raw_query="goodyear efficientgrip 195/65 r15 comfort")
        self.assertGreaterEqual(scored["confidence"], 0.6)
        self.assertIn(status["status"], {"specific_product_resolved", "intent_resolved", "general_intent_resolved"})

    def test_general_tyre_query_gets_general_intent_resolved(self) -> None:
        normalized = normalize_greeklish_and_typos(normalize_query("lastixa 195/65 r15 isixo"))
        analysis = analyze_normalized_query(normalized)
        scored = score_detector_analysis(analysis, raw_query="lastixa 195/65 r15 isixo")
        status = resolve_safe_status(scored, scored["confidence"], raw_query="lastixa 195/65 r15 isixo")
        self.assertEqual(status["status"], "general_intent_resolved")
        self.assertFalse(status["needs_review"])

    def test_conflicting_signals_get_ambiguous_status(self) -> None:
        analysis = {
            "category": "calculators",
            "brand_candidates": ["Casio"],
            "model_candidates": ["fx-991"],
            "specs": {"width": "195", "profile": "65", "rim": "R15"},
            "buying_priority": ["low_noise"],
            "confidence": 0.8,
            "reason_codes": ["ambiguous_category_signals"],
        }
        scored = score_detector_analysis(analysis, raw_query="casio fx-991 195/65 r15")
        status = resolve_safe_status(scored, scored["confidence"], raw_query="casio fx-991 195/65 r15")
        self.assertEqual(status["status"], "ambiguous_needs_review")
        self.assertTrue(status["needs_review"])

    def test_low_confidence_cannot_pass_as_resolved(self) -> None:
        analysis = {
            "category": "car_tyres",
            "brand_candidates": ["Goodyear"],
            "model_candidates": [],
            "specs": {},
            "buying_priority": [],
            "confidence": 0.1,
            "reason_codes": [],
            "query_type": "general_intent",
        }
        status = resolve_safe_status(analysis, 0.1, raw_query="goodyear tyres")
        self.assertNotIn(status["status"], {"intent_resolved", "specific_product_resolved", "general_intent_resolved"})
        self.assertTrue(status["needs_review"])

    def test_review_statuses_force_needs_review_true(self) -> None:
        for forced_status in [
            "ambiguous_needs_review",
            "manual_review_required",
            "insufficient_data",
            "no_safe_result",
            "invalid_intent",
        ]:
            status = {"status": forced_status, "needs_review": False, "reason_codes": []}
            merged = resolve_safe_status(status, 0.2, raw_query="")
            self.assertTrue(merged["needs_review"])

    def test_confidence_clamped(self) -> None:
        self.assertEqual(clamp_confidence(-9), 0.0)
        self.assertEqual(clamp_confidence(2.4), 1.0)
        self.assertEqual(clamp_confidence("0.456"), 0.46)


if __name__ == "__main__":
    unittest.main()
