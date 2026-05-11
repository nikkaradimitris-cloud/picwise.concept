import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage30_failure_bridge import build_failure_candidate
from picwise_learning.stage30_shadow_records import build_shadow_record


class TestPickwiseStage30FailureBridge(unittest.TestCase):
    def test_bridge_builds_runtime_shadow_failure_candidate(self) -> None:
        record = build_shadow_record(
            runtime_query="best accounting software",
            normalized_query="best accounting software",
            source_surface="runtime_app",
            source_route="/demo",
            existing_runtime_decision="general_product_discovery_allowed",
            existing_runtime_target="erp_core",
            existing_runtime_vertical="software_saas_erp",
            shadow_nlu_target="finance_tax_accounting",
            shadow_vertical="finance_insurance_business_finance",
            shadow_confidence=0.74,
            comparison_status="disagreement",
            failure_type="wrong_vertical",
            expected_learning_action="collect_failure",
            vertical="software_saas_erp",
        )
        candidate = build_failure_candidate(record)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.source, "runtime_shadow")
        self.assertEqual(candidate.failure_type, "wrong_vertical")
        self.assertIn(candidate.risk_level, {"medium", "high"})

    def test_bridge_skips_none_expected_action(self) -> None:
        record = build_shadow_record(
            runtime_query="samsung galaxy s24",
            normalized_query="samsung galaxy s24",
            source_surface="runtime_app",
            source_route="/demo",
            existing_runtime_decision="exact_product_resolution_required",
            existing_runtime_target="phones_mobile_accessories",
            existing_runtime_vertical="retail_physical_products",
            shadow_nlu_target="phones_mobile_accessories",
            shadow_vertical="retail_physical_products",
            shadow_confidence=0.92,
            comparison_status="aligned",
            failure_type=None,
            expected_learning_action="none",
            vertical="retail_physical_products",
        )
        self.assertIsNone(build_failure_candidate(record))


if __name__ == "__main__":
    unittest.main()
