import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage31_audit import Stage31AuditLog, build_stage31_audit_record
from picwise_learning.stage31_candidate_builder import build_stage31_activation_candidate


class TestPickwiseStage31Audit(unittest.TestCase):
    def test_build_audit_record_from_candidate(self) -> None:
        candidate = build_stage31_activation_candidate(
            runtime_query="best power bank for iphone",
            runtime_decision={
                "status": "general_product_discovery_allowed",
                "existing_runtime_target": "phones_mobile_accessories",
                "existing_runtime_vertical": "retail_physical_products",
                "vertical": "retail_physical_products",
                "comparison_status": "aligned",
                "shadow_confidence": 0.92,
            },
            activation_enabled=False,
        )
        record = build_stage31_audit_record(candidate)
        self.assertEqual(record.candidate_id, candidate.candidate_id)
        self.assertEqual(record.activation_status, candidate.activation_status)
        self.assertFalse(record.did_affect_runtime)

    def test_audit_log_keeps_records(self) -> None:
        candidate = build_stage31_activation_candidate(
            runtime_query="best power bank for iphone",
            runtime_decision={
                "status": "general_product_discovery_allowed",
                "existing_runtime_target": "phones_mobile_accessories",
                "existing_runtime_vertical": "retail_physical_products",
                "vertical": "retail_physical_products",
                "comparison_status": "aligned",
                "shadow_confidence": 0.92,
            },
            activation_enabled=False,
        )
        audit_log = Stage31AuditLog()
        audit_log.append_candidate(candidate)
        self.assertEqual(len(audit_log.get_records()), 1)


if __name__ == "__main__":
    unittest.main()
