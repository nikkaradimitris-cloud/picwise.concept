from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.output_builder import build_local_nlu_intent  # noqa: E402

_RESOLVED_SPECIFIC = {"specific_product_resolved"}
_RESOLVED_ANY = {"intent_resolved", "specific_product_resolved", "general_intent_resolved"}
_FORBIDDEN_FIELDS = {"product", "products", "offer", "offers", "price", "prices", "affiliate", "affiliate_url"}


def _assert_safe_numeric_confidence(testcase: unittest.TestCase, intent: dict) -> None:
    confidence = intent.get("confidence")
    testcase.assertIsInstance(confidence, (int, float))
    testcase.assertGreaterEqual(float(confidence), 0.0)
    testcase.assertLessEqual(float(confidence), 1.0)


def _assert_no_forbidden_payload_fields(testcase: unittest.TestCase, intent: dict) -> None:
    lowered_keys = {str(key).lower() for key in intent.keys()}
    testcase.assertTrue(_FORBIDDEN_FIELDS.isdisjoint(lowered_keys))


class LocalNLUStage21ThresholdAuditTests(unittest.TestCase):
    def test_weak_query_remains_review_safe(self) -> None:
        intent = build_local_nlu_intent("kati kalo gia to aftokinito")
        self.assertTrue(bool(intent.get("needs_review")))
        self.assertNotIn(intent.get("status"), _RESOLVED_ANY)
        _assert_safe_numeric_confidence(self, intent)

    def test_empty_and_whitespace_queries_stay_review_safe(self) -> None:
        for query in ("", "   ", "\t\t"):
            with self.subTest(query=repr(query)):
                intent = build_local_nlu_intent(query)
                self.assertTrue(bool(intent.get("needs_review")))
                self.assertNotIn(intent.get("status"), _RESOLVED_ANY)
                _assert_safe_numeric_confidence(self, intent)

    def test_brand_only_goodyear_is_not_specific_product(self) -> None:
        intent = build_local_nlu_intent("goodyear")
        self.assertIn("Goodyear", intent.get("brand_candidates", []))
        self.assertNotIn(intent.get("status"), _RESOLVED_SPECIFIC)
        self.assertTrue(bool(intent.get("needs_review")))
        _assert_safe_numeric_confidence(self, intent)

    def test_model_only_efficientgrip_is_not_specific_product(self) -> None:
        intent = build_local_nlu_intent("efficientgrip")
        self.assertIn("EfficientGrip", intent.get("model_candidates", []))
        self.assertNotIn(intent.get("status"), _RESOLVED_SPECIFIC)
        self.assertTrue(bool(intent.get("needs_review")))
        _assert_safe_numeric_confidence(self, intent)

    def test_tyre_size_only_is_not_unsafe_specific_product(self) -> None:
        intent = build_local_nlu_intent("195 65 15")
        self.assertEqual(intent.get("category"), "car_tyres")
        self.assertNotIn(intent.get("status"), _RESOLVED_SPECIFIC)
        _assert_safe_numeric_confidence(self, intent)

    def test_category_only_lastixa_does_not_fake_product_intent(self) -> None:
        intent = build_local_nlu_intent("lastixa")
        self.assertEqual(intent.get("category"), "car_tyres")
        self.assertEqual(intent.get("model_candidates"), [])
        self.assertNotIn(intent.get("status"), _RESOLVED_SPECIFIC)
        self.assertTrue(bool(intent.get("needs_review")))
        _assert_safe_numeric_confidence(self, intent)

    def test_casio_alone_not_unsafe_exact_calculator_intent(self) -> None:
        intent = build_local_nlu_intent("casio")
        self.assertIn("Casio", intent.get("brand_candidates", []))
        self.assertNotIn(intent.get("status"), _RESOLVED_SPECIFIC)
        self.assertTrue(bool(intent.get("needs_review")))
        _assert_safe_numeric_confidence(self, intent)

    def test_iphone_alone_not_unsafe_product_intent(self) -> None:
        intent = build_local_nlu_intent("iphone")
        self.assertNotIn(intent.get("status"), _RESOLVED_ANY)
        self.assertTrue(bool(intent.get("needs_review")))
        _assert_safe_numeric_confidence(self, intent)

    def test_random_text_stays_review_safe(self) -> None:
        intent = build_local_nlu_intent("random text 123")
        self.assertTrue(bool(intent.get("needs_review")))
        self.assertNotIn(intent.get("status"), _RESOLVED_ANY)
        _assert_safe_numeric_confidence(self, intent)

    def test_no_product_offer_price_affiliate_fields_appear(self) -> None:
        queries = [
            "kati kalo gia to aftokinito",
            "goodyear",
            "efficientgrip",
            "195 65 15",
            "casio",
            "iphone",
            "random text 123",
        ]
        for query in queries:
            with self.subTest(query=query):
                intent = build_local_nlu_intent(query)
                _assert_no_forbidden_payload_fields(self, intent)
                _assert_safe_numeric_confidence(self, intent)


if __name__ == "__main__":
    unittest.main()
