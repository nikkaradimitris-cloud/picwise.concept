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
    adapt_local_nlu_intent_for_router,
    build_local_nlu_intent,
    build_router_query_from_intent,
    build_safe_router_metadata,
    should_use_local_nlu_intent,
)


def _collect_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key).lower())
            keys |= _collect_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            keys |= _collect_keys(nested)
    return keys


class LocalNLUIntegrationAdapterTests(unittest.TestCase):
    def test_specific_product_intent_adapts_to_router_query_and_metadata(self) -> None:
        intent = build_local_nlu_intent("Goodyear EfficientGrip Performance 2 195/65 R15")
        adapted = adapt_local_nlu_intent_for_router(intent)
        self.assertTrue(should_use_local_nlu_intent(intent))
        self.assertTrue(adapted["should_use_local_nlu_intent"])
        self.assertEqual(adapted["source"], "local_nlu_adapter")
        self.assertEqual(adapted["raw_query"], intent["raw_query"])
        self.assertEqual(adapted["normalized_query"], intent["normalized_query"])
        self.assertGreater(len(build_router_query_from_intent(intent)), 0)
        self.assertIn("router_query", adapted["router_metadata"])

    def test_general_intent_adapts_safely(self) -> None:
        intent = build_local_nlu_intent("goodyar eficiency grim 195 65 15 aneto")
        adapted = adapt_local_nlu_intent_for_router(intent)
        metadata = build_safe_router_metadata(intent)
        self.assertTrue(adapted["should_use_local_nlu_intent"])
        self.assertEqual(metadata["source"], "local_nlu_adapter")
        self.assertEqual(metadata["adapter_decision"], "use_local_nlu_intent")
        self.assertGreater(len(metadata["router_query"]), 0)

    def test_needs_review_intent_does_not_unsafe_pass(self) -> None:
        intent = build_local_nlu_intent("zzzz asdf ???")
        adapted = adapt_local_nlu_intent_for_router(intent)
        self.assertFalse(adapted["should_use_local_nlu_intent"])
        self.assertEqual(adapted["adapter_decision"], "safe_review_only")
        self.assertEqual(adapted["router_query"], "")

    def test_invalid_intent_returns_safe_metadata(self) -> None:
        adapted = adapt_local_nlu_intent_for_router({"raw_query": "", "query_type": "bad"})
        metadata = adapted["router_metadata"]
        self.assertFalse(adapted["should_use_local_nlu_intent"])
        self.assertEqual(metadata["source"], "local_nlu_adapter")
        self.assertEqual(metadata["adapter_decision"], "safe_review_only")
        self.assertIn(metadata["status"], {"invalid_intent", "manual_review_required"})

    def test_adapter_output_is_json_serializable(self) -> None:
        intent = build_local_nlu_intent("casio fx-991cw calculator")
        adapted = adapt_local_nlu_intent_for_router(intent)
        encoded = json.dumps(adapted, sort_keys=True)
        self.assertIsInstance(encoded, str)

    def test_adapter_has_no_product_offer_price_affiliate_fields(self) -> None:
        intent = build_local_nlu_intent("best power bank for iphone")
        adapted = adapt_local_nlu_intent_for_router(intent)
        all_keys = _collect_keys(adapted)
        forbidden = {"products", "offers", "price", "prices", "affiliate", "affiliate_url"}
        self.assertTrue(forbidden.isdisjoint(all_keys))

    def test_adapter_has_no_api_or_claude_requirement(self) -> None:
        intent = build_local_nlu_intent("best power bank for iphone")
        adapted = adapt_local_nlu_intent_for_router(intent)
        blob = json.dumps(adapted, sort_keys=True).lower()
        self.assertNotIn("claude", blob)
        self.assertNotIn("openai", blob)
        self.assertNotIn("api_key", blob)
        self.assertNotIn("live_llm", blob)


if __name__ == "__main__":
    unittest.main()
