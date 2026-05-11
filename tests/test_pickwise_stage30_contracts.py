import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage30_contracts import STAGE30_ID
from picwise_learning.stage30_shadow_records import build_shadow_record
from picwise_learning.stage30_validation import validate_shadow_record


class TestPickwiseStage30Contracts(unittest.TestCase):
    def test_shadow_record_has_required_fields(self) -> None:
        record = build_shadow_record(
            runtime_query="Samsung Galaxy S24 Ultra 256GB",
            normalized_query="samsung galaxy s24 ultra 256gb",
            source_surface="runtime_app",
            source_route="/demo",
            existing_runtime_decision="general_product_discovery_allowed",
            existing_runtime_target="phones_mobile_accessories",
            existing_runtime_vertical="retail_physical_products",
            shadow_nlu_target="phones_mobile_accessories",
            shadow_vertical="retail_physical_products",
            shadow_confidence=0.91,
            comparison_status="aligned",
            failure_type=None,
            expected_learning_action="none",
            vertical="retail_physical_products",
        )
        self.assertEqual(record.stage, STAGE30_ID)
        self.assertTrue(bool(record.shadow_record_id))
        self.assertTrue(record.offline_only)
        self.assertTrue(record.internal_only)
        self.assertFalse(record.did_affect_runtime)
        report = validate_shadow_record(record)
        self.assertTrue(report["valid"])

    def test_validation_rejects_runtime_impact(self) -> None:
        record = build_shadow_record(
            runtime_query="best erp software",
            normalized_query="best erp software",
            source_surface="runtime_app",
            source_route="/demo",
            existing_runtime_decision="general_product_discovery_allowed",
            existing_runtime_target="erp_core",
            existing_runtime_vertical="software_saas_erp",
            shadow_nlu_target="erp_core",
            shadow_vertical="software_saas_erp",
            shadow_confidence=0.63,
            comparison_status="aligned",
            failure_type=None,
            expected_learning_action="none",
            vertical="software_saas_erp",
        )
        broken = record.__class__(**{**record.__dict__, "did_affect_runtime": True})
        report = validate_shadow_record(broken)
        self.assertFalse(report["valid"])
        self.assertIn("runtime_mutation_not_allowed", report["errors"])


if __name__ == "__main__":
    unittest.main()
