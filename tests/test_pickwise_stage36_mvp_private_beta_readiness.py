from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_mvp import (  # noqa: E402
    ReadinessStatus,
    build_mvp_private_beta_readiness_report,
    run_pickwise_mvp_search_flow,
    validate_private_beta_report,
)


class PickWiseStage36MVPPrivateBetaReadinessTests(unittest.TestCase):
    def test_readiness_report_contains_required_check_keys(self) -> None:
        report = build_mvp_private_beta_readiness_report()
        validate_private_beta_report(report)
        keys = {check.key for check in report.checks}
        expected_keys = {
            "app_health_ok",
            "search_result_route_ok",
            "no_result_state_ok",
            "product_source_connected_or_honest_not_connected",
            "eligibility_gate_active",
            "recommendation_engine_active",
            "no_fake_commercial_data",
            "no_owned_inventory_checkout_cart_payment",
            "finance_regulated_not_auto_decided",
            "sitemap_noindex_safe",
        }
        self.assertTrue(expected_keys.issubset(keys))
        self.assertIn(report.status, set(ReadinessStatus))

    def test_finance_flow_is_manual_review_only(self) -> None:
        flow = run_pickwise_mvp_search_flow("best finance software for business")
        self.assertEqual(flow.expected_vertical, "finance_insurance_business_finance")
        self.assertEqual(flow.state, "manual_review")
        self.assertIn("finance_vertical_manual_review_only", flow.reason_codes)


if __name__ == "__main__":
    unittest.main()
