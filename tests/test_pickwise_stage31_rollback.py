import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage31_config import Stage31ActivationConfig
from picwise_learning.stage31_rollback import rollback_stage31_runtime_result
from picwise_learning.stage31_runtime_controller import Stage31RuntimeController


class TestPickwiseStage31Rollback(unittest.TestCase):
    def test_rollback_restores_original_runtime_result(self) -> None:
        original = {
            "status": "general_product_discovery_allowed",
            "existing_runtime_target": "phones_mobile_accessories",
            "vertical": "retail_physical_products",
        }
        rollback = rollback_stage31_runtime_result(
            original_runtime_result=original,
            rollback_reason="manual_rollback_test",
        )
        self.assertTrue(rollback.rollback_applied)
        self.assertEqual(rollback.restored_runtime_result, original)
        self.assertEqual(rollback.rollback_reason, "manual_rollback_test")

    def test_controller_error_path_rolls_back_to_original(self) -> None:
        controller = Stage31RuntimeController(
            config=Stage31ActivationConfig(activation_enabled=True, rollback_on_error=True)
        )
        runtime_decision = {
            "status": "general_product_discovery_allowed",
            "existing_runtime_target": "phones_mobile_accessories",
            "existing_runtime_vertical": "retail_physical_products",
            "vertical": "retail_physical_products",
            "route_type": "general_intent",
            "comparison_status": "aligned",
            "shadow_confidence": 0.95,
            "shadow_nlu_target": "phones_mobile_accessories",
        }
        with patch(
            "picwise_learning.stage31_runtime_controller.evaluate_stage31_activation_gate",
            side_effect=RuntimeError("gate_failure"),
        ):
            resolved, candidate = controller.process_runtime_decision(
                runtime_query="best power bank for iphone",
                runtime_decision=runtime_decision,
                source_shadow_record=None,
            )
        self.assertEqual(resolved, runtime_decision)
        self.assertEqual(candidate.activation_status, "rollback")
        self.assertEqual(candidate.activation_reason, "controller_error_rollback")
        self.assertFalse(candidate.did_affect_runtime)


if __name__ == "__main__":
    unittest.main()
