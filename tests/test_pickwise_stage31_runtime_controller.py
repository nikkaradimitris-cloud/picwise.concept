import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage30_shadow_records import build_shadow_record
from picwise_learning.stage31_config import Stage31ActivationConfig
from picwise_learning.stage31_runtime_controller import Stage31RuntimeController


class TestPickwiseStage31RuntimeController(unittest.TestCase):
    def _shadow_record(self):
        return build_shadow_record(
            runtime_query="best power bank for iphone",
            normalized_query="best power bank for iphone",
            source_surface="runtime_app",
            source_route="/demo",
            existing_runtime_decision="general_product_discovery_allowed",
            existing_runtime_target="phones_mobile_accessories",
            existing_runtime_vertical="retail_physical_products",
            shadow_nlu_target="phones_mobile_accessories",
            shadow_vertical="retail_physical_products",
            shadow_confidence=0.95,
            comparison_status="aligned",
            failure_type=None,
            expected_learning_action="none",
            vertical="retail_physical_products",
        )

    def test_disabled_controller_returns_original_runtime_decision(self) -> None:
        controller = Stage31RuntimeController(config=Stage31ActivationConfig(activation_enabled=False))
        runtime_decision = {
            "status": "general_product_discovery_allowed",
            "existing_runtime_target": "phones_mobile_accessories",
            "existing_runtime_vertical": "retail_physical_products",
            "vertical": "retail_physical_products",
            "route_type": "general_intent",
        }
        resolved, candidate = controller.process_runtime_decision(
            runtime_query="best power bank for iphone",
            runtime_decision=runtime_decision,
            source_shadow_record=self._shadow_record(),
        )
        self.assertEqual(resolved, runtime_decision)
        self.assertEqual(candidate.activation_status, "disabled")
        self.assertFalse(candidate.did_affect_runtime)

    def test_enabled_controller_attaches_internal_metadata_only(self) -> None:
        controller = Stage31RuntimeController(
            config=Stage31ActivationConfig(
                activation_enabled=True,
                min_confidence=0.8,
                allow_nlu_target_influence=False,
            )
        )
        runtime_decision = {
            "status": "general_product_discovery_allowed",
            "existing_runtime_target": "phones_mobile_accessories",
            "existing_runtime_vertical": "retail_physical_products",
            "vertical": "retail_physical_products",
            "route_type": "general_intent",
        }
        resolved, candidate = controller.process_runtime_decision(
            runtime_query="best power bank for iphone",
            runtime_decision=runtime_decision,
            source_shadow_record=self._shadow_record(),
        )
        self.assertEqual(candidate.activation_status, "activated")
        self.assertFalse(candidate.did_affect_runtime)
        self.assertIn("stage31_internal", resolved)
        self.assertEqual(runtime_decision["existing_runtime_target"], "phones_mobile_accessories")

    def test_blocked_candidate_returns_original_runtime_decision(self) -> None:
        controller = Stage31RuntimeController(
            config=Stage31ActivationConfig(
                activation_enabled=True,
                min_confidence=0.99,
            )
        )
        runtime_decision = {
            "status": "general_product_discovery_allowed",
            "existing_runtime_target": "phones_mobile_accessories",
            "existing_runtime_vertical": "retail_physical_products",
            "vertical": "retail_physical_products",
            "route_type": "general_intent",
        }
        resolved, candidate = controller.process_runtime_decision(
            runtime_query="best power bank for iphone",
            runtime_decision=runtime_decision,
            source_shadow_record=self._shadow_record(),
        )
        self.assertEqual(candidate.activation_status, "blocked")
        self.assertEqual(resolved, runtime_decision)
        self.assertFalse(candidate.did_affect_runtime)

    def test_finance_vertical_never_auto_activates(self) -> None:
        controller = Stage31RuntimeController(config=Stage31ActivationConfig(activation_enabled=True))
        runtime_decision = {
            "status": "general_product_discovery_allowed",
            "existing_runtime_target": "finance_tax_accounting",
            "existing_runtime_vertical": "finance_insurance_business_finance",
            "vertical": "finance_insurance_business_finance",
            "route_type": "general_intent",
            "comparison_status": "aligned",
            "shadow_confidence": 0.99,
            "shadow_nlu_target": "finance_tax_accounting",
        }
        resolved, candidate = controller.process_runtime_decision(
            runtime_query="best business finance software",
            runtime_decision=runtime_decision,
            source_shadow_record=None,
        )
        self.assertEqual(candidate.activation_status, "manual_review")
        self.assertEqual(resolved, runtime_decision)
        self.assertFalse(candidate.did_affect_runtime)


if __name__ == "__main__":
    unittest.main()
