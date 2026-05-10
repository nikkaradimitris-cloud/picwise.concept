from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu import validate_local_nlu_intent  # noqa: E402


def _payload_for_status(status: str, needs_review: bool = False) -> dict:
    return {
        "raw_query": "best gaming laptop",
        "normalized_query": "best gaming laptop",
        "query_type": "general_intent",
        "category": "laptops",
        "brand_candidates": ["Lenovo"],
        "model_candidates": ["Legion"],
        "specs": {"screen_size": "16_inch"},
        "buying_priority": ["performance"],
        "confidence": 0.7,
        "needs_review": needs_review,
        "status": status,
        "reason_codes": [],
        "source": "local_nlu",
        "schema_version": "1.0.0",
    }


class LocalNLUSafeStatusesTests(unittest.TestCase):
    def test_ambiguous_needs_review_forces_true(self) -> None:
        validated = validate_local_nlu_intent(
            _payload_for_status("ambiguous_needs_review", needs_review=False)
        )
        self.assertTrue(validated["needs_review"])

    def test_manual_review_required_forces_true(self) -> None:
        validated = validate_local_nlu_intent(
            _payload_for_status("manual_review_required", needs_review=False)
        )
        self.assertTrue(validated["needs_review"])

    def test_insufficient_data_forces_true(self) -> None:
        validated = validate_local_nlu_intent(
            _payload_for_status("insufficient_data", needs_review=False)
        )
        self.assertTrue(validated["needs_review"])

    def test_no_safe_result_forces_true(self) -> None:
        validated = validate_local_nlu_intent(
            _payload_for_status("no_safe_result", needs_review=False)
        )
        self.assertTrue(validated["needs_review"])

    def test_invalid_intent_forces_true(self) -> None:
        validated = validate_local_nlu_intent(
            _payload_for_status("invalid_intent", needs_review=False)
        )
        self.assertTrue(validated["needs_review"])

    def test_intent_resolved_can_be_false(self) -> None:
        payload = _payload_for_status("intent_resolved", needs_review=False)
        payload["query_type"] = "general_intent"
        validated = validate_local_nlu_intent(payload)
        self.assertFalse(validated["needs_review"])

    def test_specific_product_resolved_can_be_false(self) -> None:
        payload = _payload_for_status("specific_product_resolved", needs_review=False)
        payload["query_type"] = "specific_product"
        validated = validate_local_nlu_intent(payload)
        self.assertFalse(validated["needs_review"])

    def test_general_intent_resolved_can_be_false(self) -> None:
        payload = _payload_for_status("general_intent_resolved", needs_review=False)
        payload["query_type"] = "general_intent"
        validated = validate_local_nlu_intent(payload)
        self.assertFalse(validated["needs_review"])


if __name__ == "__main__":
    unittest.main()
