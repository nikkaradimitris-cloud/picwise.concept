from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp, run_production_v1_audit  # noqa: E402
from picwise_feeds import (  # noqa: E402
    ConfiguredFeedAdapter,
    FeedSourceConfig,
    evaluate_feed_connection_readiness,
    validate_feed_candidates,
)
from picwise_integrations import (  # noqa: E402
    NoopSubbyTransport,
    SubbyConfig,
    SubbyHttpResponse,
    SubbyHttpSender,
    prepare_subby_dashboard_payload,
)
from picwise_redirects import (  # noqa: E402
    AffiliateRedirectConfig,
    evaluate_affiliate_redirect_readiness,
    resolve_affiliate_provider_redirect,
)


class Stage22ProofStatusTests(unittest.TestCase):
    def test_stage_22_live_proof_is_logged_and_marked_passed(self) -> None:
        text = (ROOT / "PROGRESS.md").read_text(encoding="utf-8")
        self.assertIn("| 22 | Live deployment to picwise.subby.cloud | PASSED |", text)
        self.assertIn("https://picwise.subby.cloud/health", text)
        self.assertIn("https://picwise.subby.cloud/demo", text)


class Stage23FeedAndRedirectTests(unittest.TestCase):
    def test_feed_template_contains_required_names_only(self) -> None:
        env_template = (ROOT / "deployment" / "app.env.template").read_text(encoding="utf-8")
        for expected in (
            "PICWISE_FEED_SOURCE_TYPE=",
            "PICWISE_FEED_SOURCE_URL=",
            "PICWISE_FEED_API_KEY=",
            "PICWISE_AFFILIATE_PROVIDER=",
            "PICWISE_AFFILIATE_TRACKING_ID=",
            "PICWISE_AFFILIATE_REDIRECT_TEMPLATE=",
        ):
            self.assertIn(expected, env_template)
        for forbidden in ("AKIA", "PRIVATE KEY", "SECRET=", "token "):
            self.assertNotIn(forbidden, env_template)

    def test_feed_adapter_rejects_fake_markers_and_commission_ranking(self) -> None:
        with self.assertRaises(Exception):
            validate_feed_candidates(
                [
                    {
                        "product_id": "f1",
                        "title": "Candidate",
                        "merchant_or_provider": "Provider",
                        "price_or_cost_display": "fake price marker",
                        "role": "budget",
                        "decision_label": "Label",
                        "subtitle": "Subtitle",
                        "key_reasons": ["Reason"],
                        "risks_or_limitations": "Risk",
                        "cta_label": "View in Store",
                        "redirect_target": "https://example.com/item",
                    }
                ],
                source_id="test",
            )
        with self.assertRaises(Exception):
            validate_feed_candidates(
                [
                    {
                        "product_id": "f2",
                        "title": "Candidate",
                        "merchant_or_provider": "Provider",
                        "price_or_cost_display": "EUR 10",
                        "role": "budget",
                        "decision_label": "Label",
                        "subtitle": "Subtitle",
                        "key_reasons": ["Reason"],
                        "risks_or_limitations": "Risk",
                        "cta_label": "View in Store",
                        "redirect_target": "https://example.com/item",
                        "commission_rank": 1,
                    }
                ],
                source_id="test",
            )

    def test_feed_adapter_reports_missing_real_config(self) -> None:
        config = FeedSourceConfig(source_type="", source_url="", api_key="")
        readiness = evaluate_feed_connection_readiness(config)
        adapter = ConfiguredFeedAdapter(config=config)
        result = adapter.fetch_candidates("power bank")
        self.assertEqual(readiness.status, "NEEDS_REAL_FEED_CONFIG")
        self.assertEqual(result.source_metadata["status"], "NEEDS_REAL_FEED_CONFIG")
        self.assertEqual(result.candidates, [])

    def test_affiliate_redirect_reports_missing_config_without_fabrication(self) -> None:
        config = AffiliateRedirectConfig(provider="", tracking_id="", redirect_template="")
        readiness = evaluate_affiliate_redirect_readiness(config)
        resolution = resolve_affiliate_provider_redirect(
            "https://merchant.example/item",
            config=config,
        )
        self.assertEqual(readiness.status, "NEEDS_AFFILIATE_CONFIG")
        self.assertEqual(resolution.status, "NEEDS_AFFILIATE_CONFIG")
        self.assertFalse(resolution.used_affiliate_redirect)
        self.assertEqual(resolution.resolved_target, "https://merchant.example/item")


class Stage24SubbyIntegrationTests(unittest.TestCase):
    def test_subby_payload_uses_canonical_missing_data_enum(self) -> None:
        output = PicwiseLocalApp().build_demo_output("power bank for iphone")
        payload, _result = prepare_subby_dashboard_payload(output)
        self.assertTrue(payload["missing_data_states"])
        allowed = {"not_connected", "data_not_yet", "not_applicable", "unknown"}
        for state in payload["missing_data_states"]:
            self.assertIn(state, allowed)

    def test_subby_payload_rejects_fake_revenue_or_conversion_markers(self) -> None:
        with self.assertRaises(Exception):
            NoopSubbyTransport().send(
                {
                    "missing_data_states": ["unknown"],
                    "conversion_tracking": {"status": "not_connected", "value": None},
                    "revenue_tracking": {"status": "not_connected", "value": None},
                    "fake_revenue": "fake revenue marker",
                }
            )

    def test_subby_transport_defaults_to_noop_when_live_config_missing(self) -> None:
        output = PicwiseLocalApp().build_demo_output("power bank for iphone")
        config = SubbyConfig(endpoint="", project_id="", api_key="")
        _payload, result = prepare_subby_dashboard_payload(output, config=config)
        self.assertEqual(result.mode, "noop_local_test")
        self.assertFalse(result.sent)

    def test_subby_live_sender_is_not_called_without_live_config(self) -> None:
        class SpySender(SubbyHttpSender):
            def __init__(self) -> None:
                self.called = False

            def send(self, *, endpoint: str, project_id: str, api_key: str, payload: dict):
                self.called = True
                return SubbyHttpResponse(accepted=True, reason="sent")

        sender = SpySender()
        output = PicwiseLocalApp().build_demo_output("power bank for iphone")
        with patch.dict(os.environ, {}, clear=True):
            _payload, result = prepare_subby_dashboard_payload(output, live_sender=sender)
        self.assertFalse(sender.called)
        self.assertEqual(result.mode, "noop_local_test")


class Stage25ProductionAuditTests(unittest.TestCase):
    def test_production_audit_marks_stage_22_passed_with_live_proof_notes(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = run_production_v1_audit(
                ROOT,
                tests_passed=True,
                live_deployment_proven=True,
                live_subby_proven=False,
            )
        self.assertTrue(result.checks["stage_22_marked_passed"])
        self.assertTrue(result.checks["stage_22_live_proof_logged"])

    def test_production_audit_keeps_stage_23_and_24_non_passed_without_live_proof(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = run_production_v1_audit(
                ROOT,
                tests_passed=True,
                live_deployment_proven=True,
                live_subby_proven=False,
            )
        self.assertTrue(result.checks["stage_23_progress_honest"])
        self.assertTrue(result.checks["stage_24_progress_honest"])

    def test_production_audit_keeps_stage_25_needs_live_proof_without_feed_subby_proof(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = run_production_v1_audit(
                ROOT,
                tests_passed=True,
                live_deployment_proven=True,
                live_subby_proven=False,
            )
        self.assertEqual(result.status, "NEEDS_LIVE_PROOF")


if __name__ == "__main__":
    unittest.main()
