import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage31_candidate_builder import build_stage31_activation_candidate
from picwise_learning.stage31_validation import validate_stage31_activation_candidate


class TestPickwiseStage31Contracts(unittest.TestCase):
    def test_candidate_has_required_stage31_fields(self) -> None:
        candidate = build_stage31_activation_candidate(
            runtime_query="best power bank for iphone",
            runtime_decision={
                "status": "general_product_discovery_allowed",
                "existing_runtime_target": "phones_mobile_accessories",
                "existing_runtime_vertical": "retail_physical_products",
                "vertical": "retail_physical_products",
                "comparison_status": "aligned",
                "shadow_confidence": 0.9,
            },
            activation_enabled=False,
        )
        self.assertEqual(candidate.stage, "31")
        self.assertFalse(candidate.did_affect_runtime)
        report = validate_stage31_activation_candidate(candidate)
        self.assertTrue(report["valid"])

    def test_validation_rejects_runtime_impact_when_disabled(self) -> None:
        candidate = build_stage31_activation_candidate(
            runtime_query="best power bank for iphone",
            runtime_decision={
                "status": "general_product_discovery_allowed",
                "existing_runtime_target": "phones_mobile_accessories",
                "existing_runtime_vertical": "retail_physical_products",
                "vertical": "retail_physical_products",
                "comparison_status": "aligned",
                "shadow_confidence": 0.91,
            },
            activation_enabled=False,
        )
        broken = candidate.__class__(**{**candidate.__dict__, "did_affect_runtime": True})
        report = validate_stage31_activation_candidate(broken)
        self.assertFalse(report["valid"])
        self.assertIn("runtime_impact_requires_activation_enabled", report["errors"])

    def test_validation_rejects_finance_auto_activation(self) -> None:
        candidate = build_stage31_activation_candidate(
            runtime_query="best business finance software",
            runtime_decision={
                "status": "general_product_discovery_allowed",
                "existing_runtime_target": "finance_tax_accounting",
                "existing_runtime_vertical": "finance_insurance_business_finance",
                "vertical": "finance_insurance_business_finance",
                "comparison_status": "aligned",
                "shadow_confidence": 0.95,
            },
            activation_enabled=True,
        )
        broken = candidate.__class__(
            **{
                **candidate.__dict__,
                "activation_status": "activated",
                "activation_reason": "forced_activation",
                "did_affect_runtime": True,
            }
        )
        report = validate_stage31_activation_candidate(broken)
        self.assertFalse(report["valid"])
        self.assertIn("finance_activation_requires_manual_review", report["errors"])

    def test_validation_requires_rollback_path(self) -> None:
        candidate = build_stage31_activation_candidate(
            runtime_query="best power bank for iphone",
            runtime_decision={
                "status": "general_product_discovery_allowed",
                "existing_runtime_target": "phones_mobile_accessories",
                "existing_runtime_vertical": "retail_physical_products",
                "vertical": "retail_physical_products",
                "comparison_status": "aligned",
                "shadow_confidence": 0.95,
            },
            activation_enabled=True,
        )
        broken = candidate.__class__(**{**candidate.__dict__, "has_rollback_path": False})
        report = validate_stage31_activation_candidate(broken)
        self.assertFalse(report["valid"])
        self.assertIn("missing_rollback_default_path", report["errors"])


if __name__ == "__main__":
    unittest.main()
