from __future__ import annotations

import socket
import sys
import threading
import unittest
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp, run_local_server, run_production_v1_audit  # noqa: E402
from picwise_feeds import (  # noqa: E402
    FeedAdapterProtocol,
    LocalFixtureFeedAdapter,
    validate_feed_candidates,
)
from picwise_integrations import prepare_subby_dashboard_payload  # noqa: E402
from picwise_redirects import build_redirect_tracking_payload, resolve_redirect  # noqa: E402
from picwise_surface import render_landing_surface  # noqa: E402


def _pick_open_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


class AppHttpEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _pick_open_port()
        cls.server = run_local_server(host="127.0.0.1", port=cls.port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2.0)

    def _fetch(self, path: str) -> str:
        with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as response:
            self.assertEqual(response.status, 200)
            return response.read().decode("utf-8")

    def test_health_responds_successfully(self) -> None:
        body = self._fetch("/health")
        self.assertIn('"status": "ok"', body)

    def test_demo_responds_successfully(self) -> None:
        body = self._fetch("/demo")
        self.assertIn("<html", body.lower())
        self.assertIn("Recommended by Picwise", body)

    def test_demo_includes_query_confirmation(self) -> None:
        query = "power bank 20000mah for iphone"
        body = self._fetch(f"/demo?q={quote(query)}")
        self.assertIn(query, body)
        self.assertIn("Showing 4 decision-ready options for:", body)

    def test_demo_includes_header_search_theme_and_footer_controls(self) -> None:
        body = self._fetch("/demo?q=power+bank")
        for class_name in (
            "pw-topbar",
            "pw-brand",
            "pw-nav",
            "pw-theme-toggle",
            "pw-search-shell",
            "pw-search-button",
            "pw-bg-network-left",
            "pw-bg-circuit-right",
            "pw-grid",
            "pw-card-recommended",
            "pw-rec-badge",
            "pw-rec-bubble-top",
            "pw-rec-bubble-bottom",
            "pw-rec-pulse-1",
            "pw-rec-pulse-2",
            "pw-rec-pulse-3",
            "pw-footer",
            "pw-footer-left",
            "pw-footer-right",
            "pw-demo-note",
        ):
            self.assertIn(class_name, body)
        self.assertIn("Πώς λειτουργεί", body)
        self.assertIn("FAQ", body)
        self.assertIn("Σχετικά με", body)
        self.assertIn('class="pw-search-shell"', body)
        self.assertIn('class="pw-search-icon"', body)
        self.assertIn('class="pw-search-button"', body)
        self.assertIn('id="theme-toggle"', body)
        self.assertIn("☀ Day", body)
        self.assertIn("☾ Night", body)
        self.assertNotIn(">Night mode<", body)
        self.assertIn("Design by subby.cloud", body)
        self.assertNotIn("Designed by Subby.cloud", body)
        self.assertNotIn("Best fit", body)
        self.assertNotIn("Fast decision", body)

    def test_demo_includes_hero_subtitle_and_demo_note(self) -> None:
        body = self._fetch("/demo")
        self.assertIn(
            "Smart recommendations, side-by-side. Compare and choose with confidence.",
            body,
        )
        self.assertIn(
            "Demo data source: local_test_fixture (not_production_data).",
            body,
        )
        demo_note_index = body.index('<p class="pw-demo-note">')
        footer_index = body.index('<footer class="pw-footer">')
        self.assertLess(demo_note_index, footer_index)

    def test_demo_has_exactly_four_primary_cards_and_one_recommended(self) -> None:
        body = self._fetch("/demo")
        self.assertEqual(body.count('<article class="pw-card'), 4)
        self.assertEqual(body.count('<article class="pw-card pw-card-recommended"'), 1)
        self.assertEqual(body.count("Recommended by Picwise"), 1)
        self.assertIn("pw-rec-bubble-top", body)
        self.assertIn("pw-rec-bubble-bottom", body)
        self.assertIn("pw-rec-pulse-1", body)
        self.assertIn("pw-rec-pulse-2", body)
        self.assertIn("pw-rec-pulse-3", body)

    def test_demo_avoids_cart_checkout_and_fake_markers(self) -> None:
        body = self._fetch("/demo").lower()
        for forbidden in ("cart", "checkout", "e-shop"):
            self.assertNotIn(forbidden, body)
        for forbidden_fake in (
            "fake revenue",
            "fake conversion",
            "fake review",
            "fake rating",
            "fake savings",
            "fake urgency",
            "fake confidence",
        ):
            self.assertNotIn(forbidden_fake, body)

    def test_demo_includes_fixture_not_production_markers(self) -> None:
        body = self._fetch("/demo")
        self.assertIn("local_test_fixture", body)
        self.assertIn("not_production_data", body)


class SpyFeedAdapter(FeedAdapterProtocol):
    def __init__(self) -> None:
        self.called = False
        self._fixture = LocalFixtureFeedAdapter()

    def fetch_candidates(self, query: str):
        self.called = True
        return self._fixture.fetch_candidates(query)


class PipelineAndFeedTests(unittest.TestCase):
    def test_app_pipeline_uses_feed_adapter_then_engine_then_surface(self) -> None:
        feed = SpyFeedAdapter()
        app = PicwiseLocalApp(feed_adapter=feed)
        output = app.build_demo_output("power bank for iphone")
        html = render_landing_surface(output)
        self.assertTrue(feed.called)
        self.assertIn(output.recommended_product_id, {choice.product_id for choice in output.choices})
        self.assertIn("Recommended by Picwise", html)

    def test_feed_adapter_validates_fixture_candidates(self) -> None:
        result = LocalFixtureFeedAdapter().fetch_candidates("power bank")
        self.assertGreaterEqual(len(result.candidates), 4)
        first = result.candidates[0]
        self.assertEqual(first["tracking_metadata"]["data_origin"], "local_test_fixture")
        self.assertEqual(first["tracking_metadata"]["data_classification"], "not_production_data")

    def test_feed_adapter_rejects_forbidden_fake_or_commission_fields(self) -> None:
        bad_fake = [
            {
                "product_id": "bad-1",
                "title": "Bad Fixture",
                "merchant_or_provider": "X",
                "price_or_cost_display": "EUR 1",
                "role": "budget",
                "decision_label": "bad",
                "subtitle": "bad",
                "key_reasons": ["bad"],
                "risks_or_limitations": "bad",
                "cta_label": "View in Store",
                "redirect_target": "https://example.com/bad",
                "fake_reviews": True,
            }
        ]
        bad_commission = [
            {
                "product_id": "bad-2",
                "title": "Bad Fixture",
                "merchant_or_provider": "X",
                "price_or_cost_display": "EUR 1",
                "role": "budget",
                "decision_label": "bad",
                "subtitle": "bad",
                "key_reasons": ["bad"],
                "risks_or_limitations": "bad",
                "cta_label": "View in Store",
                "redirect_target": "https://example.com/bad",
                "commission_rank": 1,
            }
        ]
        with self.assertRaises(Exception):
            validate_feed_candidates(bad_fake, source_id="test")
        with self.assertRaises(Exception):
            validate_feed_candidates(bad_commission, source_id="test")


class RedirectIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = PicwiseLocalApp()
        self.output = self.app.build_demo_output("power bank 20000mah for iphone")

    def test_redirect_resolver_prepares_safe_redirect_payload(self) -> None:
        resolution = resolve_redirect(
            self.output,
            selected_product_id=self.output.recommended_product_id,
            session_id=str(uuid4()),
            click_to_redirect_budget_ms=210,
            local_safe_mode=True,
        )
        self.assertTrue(resolution.resolved_target.startswith("/local-safe-redirect?target="))
        self.assertEqual(
            resolution.is_recommended,
            any(
                c.product_id == self.output.recommended_product_id and c.is_recommended
                for c in self.output.choices
            ),
        )
        payload = build_redirect_tracking_payload(resolution)
        self.assertIn("cta_click_event_id", payload)
        self.assertFalse(payload["contains_conversion_data"])
        self.assertFalse(payload["contains_revenue_data"])

    def test_redirect_budget_enforces_under_300ms(self) -> None:
        with self.assertRaises(Exception):
            resolve_redirect(
                self.output,
                selected_product_id=self.output.recommended_product_id,
                session_id=str(uuid4()),
                click_to_redirect_budget_ms=300,
                local_safe_mode=True,
            )


class DeploymentAndSubbyReadinessTests(unittest.TestCase):
    def test_deployment_templates_contain_no_secrets(self) -> None:
        env_template = (ROOT / "deployment" / "app.env.template").read_text(encoding="utf-8")
        server_template = (ROOT / "deployment" / "wsgi_server.template.ini").read_text(
            encoding="utf-8"
        )
        for forbidden in ("AKIA", "SECRET=", "PRIVATE KEY", "token "):
            self.assertNotIn(forbidden, env_template)
            self.assertNotIn(forbidden, server_template)

    def test_deployment_docs_do_not_claim_live_deployment(self) -> None:
        text = (ROOT / "docs" / "STAGE_19_LIVE_APP_DEPLOYMENT.md").read_text(encoding="utf-8")
        self.assertIn("DEPLOYMENT_READY", text)
        self.assertIn("Not live deployed yet", text)

    def test_subby_defaults_to_noop_local_transport(self) -> None:
        app = PicwiseLocalApp()
        output = app.build_demo_output("power bank for iphone")
        payload, result = prepare_subby_dashboard_payload(output)
        self.assertEqual(result.mode, "noop_local_test")
        self.assertFalse(result.sent)
        self.assertEqual(payload["conversion_tracking"]["status"], "not_connected")
        self.assertIsNone(payload["conversion_tracking"]["value"])
        self.assertEqual(payload["revenue_tracking"]["status"], "not_connected")
        self.assertIsNone(payload["revenue_tracking"]["value"])

    def test_subby_docs_do_not_claim_live_integration(self) -> None:
        text = (ROOT / "docs" / "STAGE_20_LIVE_SUBBY_DASHBOARD_INTEGRATION.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("INTEGRATION_READY", text)
        self.assertIn("Not live integrated yet", text)


class ProductionAuditTests(unittest.TestCase):
    def test_production_audit_flags_missing_live_proof(self) -> None:
        result = run_production_v1_audit(
            ROOT,
            tests_passed=True,
            live_deployment_proven=False,
            live_subby_proven=False,
        )
        self.assertEqual(result.status, "NEEDS_LIVE_PROOF")

    def test_production_audit_passes_local_readiness_checks(self) -> None:
        result = run_production_v1_audit(
            ROOT,
            tests_passed=True,
            live_deployment_proven=False,
            live_subby_proven=False,
        )
        self.assertTrue(result.checks["stage_16_local_app_ready"])
        self.assertTrue(result.checks["stage_17_feed_adapter_ready"])
        self.assertTrue(result.checks["stage_18_redirect_ready"])


if __name__ == "__main__":
    unittest.main()
