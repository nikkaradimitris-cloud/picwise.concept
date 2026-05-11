import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage30_runtime_probe import Stage30RuntimeProbe


class TestPickwiseStage30RuntimeProbe(unittest.TestCase):
    def test_probe_observes_runtime_without_needing_return_path_changes(self) -> None:
        probe = Stage30RuntimeProbe()
        record = probe.observe_runtime_decision(
            runtime_query="best tools for diy",
            runtime_decision={
                "route_type": "general_intent",
                "status": "general_product_discovery_allowed",
                "normalized_query": "best tools for diy",
                "existing_runtime_target": "tools_diy_garden_repair",
                "existing_runtime_vertical": "retail_physical_products",
            },
            source_surface="runtime_app",
            source_route="/demo",
        )
        self.assertIsNotNone(record)
        self.assertEqual(len(probe.get_shadow_records()), 1)
        self.assertFalse(record.did_affect_runtime)

    def test_probe_produces_internal_summary_and_failure_candidates(self) -> None:
        probe = Stage30RuntimeProbe()
        probe.observe_runtime_decision(
            runtime_query="random ???",
            runtime_decision={
                "route_type": "no_safe_result",
                "status": "no_valid_offers",
                "normalized_query": "random ???",
                "existing_runtime_target": "unknown",
                "existing_runtime_vertical": "retail_physical_products",
            },
            source_surface="runtime_app",
            source_route="/demo",
        )
        summary = probe.build_summary()
        self.assertGreaterEqual(summary.total_shadow_records, 1)
        candidates = probe.build_failure_candidates()
        self.assertIsInstance(candidates, list)


if __name__ == "__main__":
    unittest.main()
