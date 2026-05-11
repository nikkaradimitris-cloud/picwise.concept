import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage30_config import build_default_stage30_config
from picwise_learning.stage30_decision_comparison import compare_runtime_vs_shadow


class TestPickwiseStage30DecisionComparison(unittest.TestCase):
    def test_aligned_when_targets_match(self) -> None:
        result = compare_runtime_vs_shadow(
            runtime_target="phones_mobile_accessories",
            runtime_vertical="retail_physical_products",
            runtime_decision="general_product_discovery_allowed",
            shadow_target="phones_mobile_accessories",
            shadow_vertical="retail_physical_products",
            shadow_status="general_intent_resolved",
            shadow_needs_review=False,
            config=build_default_stage30_config(),
        )
        self.assertEqual(result.comparison_status, "aligned")
        self.assertEqual(result.expected_learning_action, "none")

    def test_runtime_unknown_classification(self) -> None:
        result = compare_runtime_vs_shadow(
            runtime_target="unknown",
            runtime_vertical="retail_physical_products",
            runtime_decision="no_valid_offers",
            shadow_target="phones_mobile_accessories",
            shadow_vertical="retail_physical_products",
            shadow_status="specific_product_resolved",
            shadow_needs_review=False,
            config=build_default_stage30_config(),
        )
        self.assertEqual(result.comparison_status, "runtime_unknown")
        self.assertEqual(result.expected_learning_action, "collect_failure")

    def test_finance_disagreement_becomes_manual_review(self) -> None:
        result = compare_runtime_vs_shadow(
            runtime_target="finance_tax_accounting",
            runtime_vertical="finance_insurance_business_finance",
            runtime_decision="general_product_discovery_allowed",
            shadow_target="insurance_business",
            shadow_vertical="finance_insurance_business_finance",
            shadow_status="general_intent_resolved",
            shadow_needs_review=False,
            config=build_default_stage30_config(),
        )
        self.assertEqual(result.comparison_status, "manual_review")
        self.assertEqual(result.expected_learning_action, "manual_review")

    def test_saas_and_retail_vertical_mismatch_is_disagreement(self) -> None:
        result = compare_runtime_vs_shadow(
            runtime_target="erp_core",
            runtime_vertical="software_saas_erp",
            runtime_decision="general_product_discovery_allowed",
            shadow_target="phones_mobile_accessories",
            shadow_vertical="retail_physical_products",
            shadow_status="general_intent_resolved",
            shadow_needs_review=False,
            config=build_default_stage30_config(),
        )
        self.assertEqual(result.comparison_status, "disagreement")
        self.assertEqual(result.failure_type, "wrong_vertical")


if __name__ == "__main__":
    unittest.main()
