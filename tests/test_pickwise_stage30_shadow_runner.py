import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage30_shadow_runner import Stage30ShadowRunner


class TestPickwiseStage30ShadowRunner(unittest.TestCase):
    def test_runner_returns_structured_shadow_record(self) -> None:
        runner = Stage30ShadowRunner()
        record = runner.run_shadow(
            runtime_query="Samsung Galaxy S24 Ultra 256GB",
            runtime_decision={
                "route_type": "specific_product",
                "status": "exact_product_resolution_required",
                "normalized_query": "samsung galaxy s24 ultra 256gb",
                "existing_runtime_target": "phones_mobile_accessories",
                "existing_runtime_vertical": "retail_physical_products",
            },
        )
        self.assertEqual(record.stage, "30")
        self.assertTrue(bool(record.shadow_record_id))
        self.assertFalse(record.did_affect_runtime)
        self.assertIn(record.comparison_status, {"aligned", "disagreement", "runtime_unknown", "shadow_unknown", "both_unknown", "manual_review", "unsafe_shadow", "unsupported"})

    def test_runner_does_not_mutate_runtime_decision_payload(self) -> None:
        runner = Stage30ShadowRunner()
        runtime_decision = {
            "route_type": "general_intent",
            "status": "general_product_discovery_allowed",
            "normalized_query": "power bank for iphone",
            "existing_runtime_target": "phones_mobile_accessories",
            "existing_runtime_vertical": "retail_physical_products",
        }
        snapshot = dict(runtime_decision)
        _ = runner.run_shadow(runtime_query="power bank for iphone", runtime_decision=runtime_decision)
        self.assertEqual(runtime_decision, snapshot)


if __name__ == "__main__":
    unittest.main()
