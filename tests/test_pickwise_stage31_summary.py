import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage31_audit import build_stage31_audit_record
from picwise_learning.stage31_candidate_builder import build_stage31_activation_candidate
from picwise_learning.stage31_summary import build_stage31_activation_summary


class TestPickwiseStage31Summary(unittest.TestCase):
    def test_summary_counts_statuses_and_breakdowns(self) -> None:
        disabled_candidate = build_stage31_activation_candidate(
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
        blocked_candidate = build_stage31_activation_candidate(
            runtime_query="best erp software",
            runtime_decision={
                "status": "general_product_discovery_allowed",
                "existing_runtime_target": "erp_core",
                "existing_runtime_vertical": "software_saas_erp",
                "vertical": "software_saas_erp",
                "comparison_status": "disagreement",
                "shadow_confidence": 0.6,
            },
            activation_enabled=True,
        )
        blocked_candidate = blocked_candidate.__class__(
            **{
                **blocked_candidate.__dict__,
                "activation_status": "blocked",
                "activation_reason": "activation_blocked_by_guardrails",
                "block_reasons": ("shadow_confidence_below_threshold",),
                "risk_level": "medium",
            }
        )
        summary = build_stage31_activation_summary(
            [
                build_stage31_audit_record(disabled_candidate),
                build_stage31_audit_record(blocked_candidate),
            ]
        )
        self.assertEqual(summary.total_candidates, 2)
        self.assertEqual(summary.disabled, 1)
        self.assertEqual(summary.blocked, 1)
        self.assertEqual(summary.by_vertical.get("retail_physical_products"), 1)
        self.assertEqual(summary.by_block_reason.get("shadow_confidence_below_threshold"), 1)


if __name__ == "__main__":
    unittest.main()
