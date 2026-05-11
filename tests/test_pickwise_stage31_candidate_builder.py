import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage30_shadow_records import build_shadow_record
from picwise_learning.stage31_candidate_builder import build_stage31_activation_candidate


class TestPickwiseStage31CandidateBuilder(unittest.TestCase):
    def test_builds_candidate_from_stage30_shadow_record(self) -> None:
        shadow_record = build_shadow_record(
            runtime_query="best power bank for iphone",
            normalized_query="best power bank for iphone",
            source_surface="runtime_app",
            source_route="/demo",
            existing_runtime_decision="general_product_discovery_allowed",
            existing_runtime_target="phones_mobile_accessories",
            existing_runtime_vertical="retail_physical_products",
            shadow_nlu_target="phones_mobile_accessories",
            shadow_vertical="retail_physical_products",
            shadow_confidence=0.94,
            comparison_status="aligned",
            failure_type=None,
            expected_learning_action="none",
            vertical="retail_physical_products",
        )
        runtime_decision = {
            "status": "general_product_discovery_allowed",
            "existing_runtime_target": "phones_mobile_accessories",
            "existing_runtime_vertical": "retail_physical_products",
            "vertical": "retail_physical_products",
        }
        snapshot = dict(runtime_decision)
        candidate = build_stage31_activation_candidate(
            runtime_query="best power bank for iphone",
            runtime_decision=runtime_decision,
            source_shadow_record=shadow_record,
            activation_enabled=False,
        )
        self.assertEqual(runtime_decision, snapshot)
        self.assertEqual(candidate.stage, "31")
        self.assertEqual(candidate.source_shadow_record_id, shadow_record.shadow_record_id)
        self.assertEqual(candidate.shadow_nlu_target, "phones_mobile_accessories")
        self.assertFalse(candidate.did_affect_runtime)
        self.assertTrue(candidate.offline_or_internal_marker)

    def test_builds_candidate_without_shadow_record(self) -> None:
        candidate = build_stage31_activation_candidate(
            runtime_query="best erp software",
            runtime_decision={
                "status": "general_product_discovery_allowed",
                "existing_runtime_target": "erp_core",
                "existing_runtime_vertical": "software_saas_erp",
                "vertical": "software_saas_erp",
                "comparison_status": "disagreement",
                "shadow_confidence": 0.88,
                "shadow_nlu_target": "erp_core",
            },
            activation_enabled=True,
        )
        self.assertIsNone(candidate.source_shadow_record_id)
        self.assertEqual(candidate.vertical, "software_saas_erp")
        self.assertEqual(candidate.comparison_status, "disagreement")


if __name__ == "__main__":
    unittest.main()
