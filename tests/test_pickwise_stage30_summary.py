import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage30_shadow_records import build_shadow_record
from picwise_learning.stage30_summary import build_shadow_summary


class TestPickwiseStage30Summary(unittest.TestCase):
    def test_summary_counts_and_breakdowns(self) -> None:
        records = [
            build_shadow_record(
                runtime_query="query one",
                normalized_query="query one",
                source_surface="runtime_app",
                source_route="/demo",
                existing_runtime_decision="general_product_discovery_allowed",
                existing_runtime_target="phones_mobile_accessories",
                existing_runtime_vertical="retail_physical_products",
                shadow_nlu_target="phones_mobile_accessories",
                shadow_vertical="retail_physical_products",
                shadow_confidence=0.8,
                comparison_status="aligned",
                failure_type=None,
                expected_learning_action="none",
                vertical="retail_physical_products",
            ),
            build_shadow_record(
                runtime_query="query two ??",
                normalized_query="query two ??",
                source_surface="runtime_app",
                source_route="/demo",
                existing_runtime_decision="general_product_discovery_allowed",
                existing_runtime_target="erp_core",
                existing_runtime_vertical="software_saas_erp",
                shadow_nlu_target="finance_tax_accounting",
                shadow_vertical="finance_insurance_business_finance",
                shadow_confidence=0.4,
                comparison_status="disagreement",
                failure_type="wrong_vertical",
                expected_learning_action="collect_failure",
                vertical="software_saas_erp",
            ),
        ]
        summary = build_shadow_summary(records)
        self.assertEqual(summary.total_shadow_records, 2)
        self.assertEqual(summary.aligned_count, 1)
        self.assertEqual(summary.disagreement_count, 1)
        self.assertGreaterEqual(summary.by_vertical.get("retail_physical_products", 0), 1)
        self.assertTrue(summary.top_failure_types)


if __name__ == "__main__":
    unittest.main()
