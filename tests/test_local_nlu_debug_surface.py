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


class LocalNLUDebugSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = PicwiseLocalApp()

    def test_debug_surface_contains_json_visual_and_system_flow_sections(self) -> None:
        output = self.app.build_demo_output("power bank for iphone")
        debug = output.tracking_context["local_nlu_debug"]
        self.assertIn("json_output", debug)
        self.assertIn("visual_intent", debug)
        self.assertIn("system_flow", debug)

    def test_debug_visual_intent_includes_confidence_status_needs_review(self) -> None:
        output = self.app.build_demo_output("goodyar eficiency grim 195 65 15 aneto")
        visual = output.tracking_context["local_nlu_debug"]["visual_intent"]
        self.assertIn("confidence", visual)
        self.assertIn("status", visual)
        self.assertIn("needs_review", visual)

    def test_debug_surface_includes_system_flow_core_fields(self) -> None:
        output = self.app.build_demo_output("zzzz asdf ???")
        flow = output.tracking_context["local_nlu_debug"]["system_flow"]
        for key in (
            "raw_query",
            "normalized_query",
            "typo_normalized_query",
            "adapter_decision",
            "router_fallback_used",
        ):
            self.assertIn(key, flow)

    def test_debug_surface_has_no_secrets_or_api_keys(self) -> None:
        output = self.app.build_demo_output("power bank for iphone")
        blob = json.dumps(output.tracking_context["local_nlu_debug"], sort_keys=True).lower()
        for forbidden in ("api_key", "secret", "x-bridge-api-key", "claude", "openai"):
            self.assertNotIn(forbidden, blob)

    def test_debug_surface_has_no_fake_product_offer_fields(self) -> None:
        output = self.app.build_demo_output("power bank for iphone")
        all_keys = _collect_keys(output.tracking_context["local_nlu_debug"])
        forbidden = {"products", "offers", "price", "prices", "affiliate", "affiliate_url"}
        self.assertTrue(forbidden.isdisjoint(all_keys))


if __name__ == "__main__":
    unittest.main()
