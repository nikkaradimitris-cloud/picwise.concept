from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp  # noqa: E402
from picwise_nlu.validation import build_safe_manual_review_intent  # noqa: E402


class LocalNLUAppHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = PicwiseLocalApp()

    def test_messy_tyre_query_includes_local_nlu_debug_intent(self) -> None:
        output = self.app.build_demo_output("goodyar eficiency grim 195 65 15 aneto")
        debug = output.tracking_context["local_nlu_debug"]
        self.assertIn("json_output", debug)
        self.assertIn("visual_intent", debug)
        self.assertIn("system_flow", debug)
        self.assertEqual(debug["json_output"]["raw_query"], "goodyar eficiency grim 195 65 15 aneto")
        self.assertIn("status", debug["visual_intent"])

    def test_app_still_returns_valid_output(self) -> None:
        output = self.app.build_demo_output("power bank for iphone")
        self.assertIn("search_decision", output.tracking_context)
        self.assertEqual(output.tracking_context["search_decision"]["route_type"], "general_intent")
        self.assertEqual(len(output.choices), 4)

    def test_router_fallback_still_works_when_local_nlu_fails(self) -> None:
        with patch("picwise_app.app.build_local_nlu_intent", side_effect=RuntimeError("nlu down")):
            output = self.app.build_demo_output("power bank for iphone")
        self.assertEqual(output.tracking_context["search_decision"]["route_type"], "general_intent")
        self.assertEqual(len(output.choices), 4)
        self.assertTrue(output.tracking_context["local_nlu_debug"]["system_flow"]["router_fallback_used"])

    def test_unknown_query_does_not_fake_fill(self) -> None:
        output = self.app.build_demo_output("zzzz asdf ???")
        self.assertEqual(output.choices, [])
        self.assertEqual(output.recommended_product_id, "")
        self.assertIn(
            output.tracking_context["search_decision"]["route_type"],
            {"no_safe_result", "ambiguous_query"},
        )

    def test_unsafe_local_nlu_status_does_not_create_products(self) -> None:
        unsafe_intent = build_safe_manual_review_intent("power bank for iphone", ["manual_review_required"])
        with patch("picwise_app.app.build_local_nlu_intent", return_value=unsafe_intent):
            output = self.app.build_demo_output("power bank for iphone")
        self.assertEqual(output.choices, [])
        self.assertEqual(output.recommended_product_id, "")
        self.assertEqual(output.tracking_context["local_nlu_adapter"]["adapter_decision"], "safe_review_only")

    def test_closed_router_and_offer_resolver_files_remain_unchanged_by_handoff(self) -> None:
        router_source = (SRC / "picwise_search" / "decision_router.py").read_text(encoding="utf-8")
        offer_source = (SRC / "picwise_search" / "offer_resolver.py").read_text(encoding="utf-8")
        self.assertIn("def route_search_query", router_source)
        self.assertIn("def resolve_specific_product_offers_from_candidates", offer_source)


if __name__ == "__main__":
    unittest.main()
