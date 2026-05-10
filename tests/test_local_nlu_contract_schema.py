from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu import (  # noqa: E402
    LOCAL_NLU_SOURCE,
    build_safe_manual_review_intent,
    validate_local_nlu_intent,
)


def _base_payload() -> dict:
    return {
        "raw_query": "best iphone 15 pro case",
        "normalized_query": "best iphone 15 pro case",
        "query_type": "specific_product",
        "category": "phone_accessories",
        "brand_candidates": ["Apple", "Spigen"],
        "model_candidates": ["iPhone 15 Pro"],
        "specs": {"material": "silicone"},
        "buying_priority": ["durability", "price"],
        "confidence": 0.91,
        "needs_review": False,
        "status": "specific_product_resolved",
        "reason_codes": ["exact_model_detected"],
        "source": "local_nlu",
        "schema_version": "1.0.0",
    }


class LocalNLUContractSchemaTests(unittest.TestCase):
    def test_valid_specific_product_intent(self) -> None:
        payload = _base_payload()
        validated = validate_local_nlu_intent(payload)
        self.assertEqual(validated["query_type"], "specific_product")
        self.assertEqual(validated["status"], "specific_product_resolved")
        self.assertEqual(validated["source"], LOCAL_NLU_SOURCE)

    def test_valid_general_intent_intent(self) -> None:
        payload = _base_payload()
        payload["query_type"] = "general_intent"
        payload["status"] = "general_intent_resolved"
        payload["needs_review"] = False
        validated = validate_local_nlu_intent(payload)
        self.assertEqual(validated["query_type"], "general_intent")
        self.assertEqual(validated["status"], "general_intent_resolved")
        self.assertFalse(validated["needs_review"])

    def test_manual_review_required_intent(self) -> None:
        intent = build_safe_manual_review_intent(
            "need help picking a camera", ["ambiguous_query"]
        )
        self.assertEqual(intent["status"], "manual_review_required")
        self.assertTrue(intent["needs_review"])
        self.assertEqual(intent["source"], LOCAL_NLU_SOURCE)

    def test_invalid_confidence_converted_safely(self) -> None:
        payload = _base_payload()
        payload["confidence"] = 1.5
        validated = validate_local_nlu_intent(payload)
        self.assertEqual(validated["status"], "invalid_intent")
        self.assertTrue(validated["needs_review"])

    def test_unknown_query_type_converted_safely(self) -> None:
        payload = _base_payload()
        payload["query_type"] = "product_compare"
        validated = validate_local_nlu_intent(payload)
        self.assertEqual(validated["status"], "invalid_intent")
        self.assertIn("invalid_query_type", validated["reason_codes"])

    def test_unknown_status_converted_safely(self) -> None:
        payload = _base_payload()
        payload["status"] = "ok"
        validated = validate_local_nlu_intent(payload)
        self.assertEqual(validated["status"], "invalid_intent")
        self.assertIn("invalid_status", validated["reason_codes"])

    def test_missing_or_empty_raw_query_safe_handling(self) -> None:
        payload = _base_payload()
        payload["raw_query"] = "   "
        validated = validate_local_nlu_intent(payload)
        self.assertEqual(validated["status"], "invalid_intent")
        self.assertIn("missing_raw_query", validated["reason_codes"])

    def test_json_serializable(self) -> None:
        validated = validate_local_nlu_intent(_base_payload())
        serialized = json.dumps(validated, sort_keys=True)
        self.assertIsInstance(serialized, str)

    def test_source_is_always_local_nlu(self) -> None:
        payload = _base_payload()
        payload["source"] = "external_service"
        validated = validate_local_nlu_intent(payload)
        self.assertEqual(validated["source"], LOCAL_NLU_SOURCE)

    def test_no_claude_or_api_fields_required(self) -> None:
        validated = validate_local_nlu_intent(_base_payload())
        self.assertNotIn("claude", validated)
        self.assertNotIn("api_key", validated)
        self.assertNotIn("model_name", validated)


if __name__ == "__main__":
    unittest.main()
