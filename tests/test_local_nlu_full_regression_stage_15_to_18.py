from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp  # noqa: E402
from picwise_nlu import adapt_local_nlu_intent_for_router, build_local_nlu_intent  # noqa: E402
from picwise_search import route_search_query  # noqa: E402


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


class LocalNLUFullRegressionStage15To18Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = PicwiseLocalApp()

    def test_full_path_build_intent_adapter_and_app_handoff(self) -> None:
        query = "Goodyear EfficientGrip Performance 2 195/65 R15"
        intent = build_local_nlu_intent(query)
        adapted = adapt_local_nlu_intent_for_router(intent)
        output = self.app.build_demo_output(query)
        self.assertTrue(adapted["should_use_local_nlu_intent"])
        self.assertIn(output.tracking_context["search_decision"]["route_type"], {"specific_product", "no_safe_result"})
        self.assertIn("local_nlu_debug", output.tracking_context)

    def test_unknown_query_remains_safe(self) -> None:
        output = self.app.build_demo_output("zzzz asdf ???")
        self.assertEqual(output.choices, [])
        self.assertEqual(output.more_choices, [])
        self.assertEqual(output.recommended_product_id, "")
        self.assertIn(
            output.tracking_context["search_decision"]["route_type"],
            {"no_safe_result", "ambiguous_query"},
        )

    def test_no_claude_api_or_live_llm_dependency(self) -> None:
        query = "best power bank for iphone"
        intent = build_local_nlu_intent(query)
        adapted = adapt_local_nlu_intent_for_router(intent)
        output = self.app.build_demo_output(query)
        blob = json.dumps(
            {
                "intent": intent,
                "adapted": adapted,
                "debug": output.tracking_context.get("local_nlu_debug", {}),
            },
            sort_keys=True,
        ).lower()
        self.assertNotIn("claude", blob)
        self.assertNotIn("openai", blob)
        self.assertNotIn("api_key", blob)
        self.assertNotIn("live_llm", blob)

    def test_nlu_layer_does_not_add_product_offer_result_logic(self) -> None:
        intent = build_local_nlu_intent("best power bank for iphone")
        adapted = adapt_local_nlu_intent_for_router(intent)
        all_keys = _collect_keys({"intent": intent, "adapted": adapted})
        forbidden = {"products", "offers", "price", "prices", "affiliate", "affiliate_url"}
        self.assertTrue(forbidden.isdisjoint(all_keys))

    def test_closed_router_contract_is_still_compatible(self) -> None:
        specific = route_search_query("Casio fx-991CW calculator")
        general = route_search_query("best power bank for iphone")
        self.assertEqual(specific.route_type, "specific_product")
        self.assertEqual(general.route_type, "general_intent")


if __name__ == "__main__":
    unittest.main()
