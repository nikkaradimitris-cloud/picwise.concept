import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage31_activation_gate import evaluate_stage31_activation_gate
from picwise_learning.stage31_candidate_builder import build_stage31_activation_candidate
from picwise_learning.stage31_config import Stage31ActivationConfig


class TestPickwiseStage31ActivationGate(unittest.TestCase):
    def _base_candidate(self, *, activation_enabled: bool = True):
        return build_stage31_activation_candidate(
            runtime_query="best power bank for iphone",
            runtime_decision={
                "status": "general_product_discovery_allowed",
                "existing_runtime_target": "phones_mobile_accessories",
                "existing_runtime_vertical": "retail_physical_products",
                "vertical": "retail_physical_products",
                "comparison_status": "aligned",
                "shadow_confidence": 0.96,
                "route_type": "general_intent",
            },
            activation_enabled=activation_enabled,
        )

    def test_gate_returns_disabled_when_activation_off(self) -> None:
        candidate = self._base_candidate(activation_enabled=False)
        config = Stage31ActivationConfig(activation_enabled=False)
        result = evaluate_stage31_activation_gate(candidate, config=config)
        self.assertEqual(result.activation_status, "disabled")

    def test_gate_returns_eligible_when_all_guardrails_pass(self) -> None:
        candidate = self._base_candidate(activation_enabled=True)
        config = Stage31ActivationConfig(activation_enabled=True, min_confidence=0.8)
        result = evaluate_stage31_activation_gate(candidate, config=config)
        self.assertEqual(result.activation_status, "eligible")
        self.assertEqual(result.block_reasons, ())

    def test_gate_blocks_low_confidence_candidate(self) -> None:
        candidate = self._base_candidate(activation_enabled=True)
        low_conf = candidate.__class__(**{**candidate.__dict__, "shadow_confidence": 0.3})
        config = Stage31ActivationConfig(activation_enabled=True, min_confidence=0.8)
        result = evaluate_stage31_activation_gate(low_conf, config=config)
        self.assertEqual(result.activation_status, "blocked")
        self.assertIn("shadow_confidence_below_threshold", result.block_reasons)

    def test_gate_manual_review_for_finance_vertical(self) -> None:
        candidate = self._base_candidate(activation_enabled=True)
        finance = candidate.__class__(
            **{
                **candidate.__dict__,
                "vertical": "finance_insurance_business_finance",
                "shadow_vertical": "finance_insurance_business_finance",
            }
        )
        config = Stage31ActivationConfig(activation_enabled=True)
        result = evaluate_stage31_activation_gate(finance, config=config)
        self.assertEqual(result.activation_status, "manual_review")
        self.assertIn("blocked_vertical", result.block_reasons)

    def test_gate_blocks_ambiguous_queries(self) -> None:
        candidate = self._base_candidate(activation_enabled=True)
        marked = candidate.__class__(
            **{
                **candidate.__dict__,
                "metadata": {**candidate.metadata, "query_is_ambiguous": True},
            }
        )
        config = Stage31ActivationConfig(activation_enabled=True)
        result = evaluate_stage31_activation_gate(marked, config=config)
        self.assertEqual(result.activation_status, "blocked")
        self.assertIn("ambiguous_query_blocked", result.block_reasons)


if __name__ == "__main__":
    unittest.main()
