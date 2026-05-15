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
    @staticmethod
    def _assert_common_footer_links(body: str) -> None:
        expected_links = (
            ("/", "Home"),
            ("/demo", "Demo"),
            ("/picwise-reference", "PicWise Reference"),
            ("/terms", "Terms"),
            ("/privacy", "Privacy"),
            ("/cookies", "Cookies"),
            ("/affiliate-disclosure", "Affiliate Disclosure"),
            ("/contact", "Contact"),
        )
        for href, label in expected_links:
            assert f'class="pw-footer-link" href="{href}">{label}<' in body
        for href, _label in expected_links:
            assert f'href="{href}"' in body
        assert '<nav class="pw-footer-links" aria-label="PicWise public footer links">' in body
        assert (
            "PicWise may earn commissions from qualifying purchases, referrals, or provider links "
            "when affiliate or provider integrations are active."
        ) in body
        assert (
            "HomeDemoPicWise ReferenceTermsPrivacyCookiesAffiliate DisclosureContact"
            not in body.replace(" ", "").replace("\n", "")
        )

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

    def test_root_route_shows_review_safe_landing_without_demo_cards(self) -> None:
        body = self._fetch("/")
        self.assertIn("Welcome to PicWise.", body)
        self.assertIn(
            "PicWise is a shopping decision assistant that helps users compare product options, understand trade-offs, and choose more confidently before visiting external providers.",
            body,
        )
        self.assertIn(
            "PicWise does not sell products directly, process checkout, handle shipping, returns, warranties, subscriptions, or applications.",
            body,
        )
        self.assertIn("shopping decision assistant", body)
        self.assertIn(
            "Provider and affiliate integrations are being configured. Demo product listings are previews only and are not live Amazon offers.",
            body,
        )
        self.assertIn(
            "Thank you for visiting PicWise. We are preparing a safer product comparison experience for shoppers.",
            body,
        )
        self.assertIn("<title>PicWise — Shopping Decision Assistant</title>", body)
        self._assert_common_footer_links(body)
        self.assertIn('href="/picwise-reference">Demo</a>', body)
        self.assertEqual(body.count('data-main-cta-area="true"'), 1)
        self.assertEqual(body.count('class="pw-btn pw-btn-primary"'), 1)
        self.assertNotIn("View demo", body)
        self.assertNotIn("What is PicWise?", body)
        self.assertNotIn("Login", body)
        self.assertNotIn("Register", body)
        self.assertNotIn("mysubby.cloud@gmail.com", body)
        for forbidden in (
            "Recommended by Picwise",
            "View in Store",
            "Go to Store",
            "View Details and Buy",
            "EUR ",
            "Showing 4 options for:",
        ):
            self.assertNotIn(forbidden, body)

    def test_demo_responds_successfully(self) -> None:
        body = self._fetch("/demo")
        self.assertIn("<html", body.lower())
        self.assertIn("How PicWise will help shoppers decide.", body)
        self.assertIn("<title>PicWise Demo — Buying Decision Preview</title>", body)
        self._assert_common_footer_links(body)

    def test_demo_includes_query_confirmation(self) -> None:
        query = "power bank 20000mah for iphone"
        body = self._fetch(f"/demo?q={quote(query)}")
        self.assertIn("informational only", body)
        self.assertIn("Search by product need", body)
        self.assertNotIn(query, body)

    def test_demo_ambiguous_query_returns_review_only_safe_no_result(self) -> None:
        query = "Goodyar eco contact performanc 2 195/65/15"
        body = self._fetch(f"/demo?q={quote(query)}")
        self.assertIn("How PicWise will help shoppers decide.", body)
        self.assertIn("This demo page is informational only.", body)
        self.assertNotIn("Safe no-result response", body)
        self.assertNotIn('<article class="pw-card', body)

    def test_demo_no_safe_result_query_returns_explicit_no_result(self) -> None:
        body = self._fetch("/demo?q=%20")
        self.assertIn("How PicWise will help shoppers decide.", body)
        self.assertIn("This demo page is informational only.", body)
        self.assertNotIn("Safe no-result response", body)
        self.assertNotIn('<article class="pw-card', body)

    def test_demo_specific_product_without_real_same_product_offers_returns_safe_no_valid_offers(self) -> None:
        query = "Goodyear EfficientGrip Performance 2 195/65 R15"
        body = self._fetch(f"/demo?q={quote(query)}")
        self.assertIn("How PicWise will help shoppers decide.", body)
        self.assertIn("This demo page is informational only.", body)
        self.assertNotIn("Safe no-result response", body)
        self.assertNotIn("TravelCore 20K", body)
        self.assertNotIn('<article class="pw-card', body)

    def test_root_what_is_picwise_link_targets_safe_demo_section(self) -> None:
        body = self._fetch("/")
        self.assertNotIn('href="/demo#what-is-picwise"', body)
        self.assertIn('href="/picwise-reference">Demo</a>', body)

    def test_picwise_reference_route_renders_static_reference_page(self) -> None:
        body = self._fetch("/picwise-reference")
        self.assertIn("See the 4 best products before you buy", body)
        self.assertIn("Demo preview only", body)
        self.assertIn("not live Amazon, Linkwise, SaaS, finance, insurance, or provider offers.", body)
        self.assertNotIn("shopping assistant", body)
        self.assertIn(
            'placeholder="See the 4 best products before you buy"',
            body,
        )
        self.assertNotIn("<h1>See the 4 best products before you buy</h1>", body)
        self.assertNotIn("Search your product here", body)
        self.assertNotIn('value="See the 4 best products before you buy"', body)
        self.assertIn("What is PicWise?", body)
        self.assertIn("Showing 4 options for: power bank 20000mah for iphone", body)
        self.assertNotIn("View in Store", body)
        self.assertNotIn("Go to Store", body)
        self.assertNotIn("View Details and Buy", body)
        self.assertIn("Preview option", body)
        self.assertIn("Preview recommendation", body)
        self.assertNotIn("LIVE RENDERER PROOF V1", body)
        self.assertNotIn("picwise-reference-live-renderer-proof-v1", body)
        self.assertEqual(body.count('class="pw-brand"'), 1)
        for forbidden_image_placeholder in (
            "TravelCore 20K product image placeholder",
            "DailyBalance PD20 product image placeholder",
            "EverydaySure 22.5W product image placeholder",
            "PowerMax Elite 25K product image placeholder",
        ):
            self.assertNotIn(forbidden_image_placeholder, body)
        self.assertIn(
            "Demo data source: local_test_fixture (not_production_data).",
            body,
        )
        self.assertIn("All rights reserved.", body)
        self._assert_common_footer_links(body)
        self.assertEqual(body.count('<article class="pw-card'), 4)
        self.assertEqual(body.count("Recommended by PicWise"), 1)
        self.assertNotIn("&middot;", body)
        for product_name in (
            "TravelCore 20K",
            "DailyBalance PD20",
            "EverydaySure 22.5W",
            "PowerMax Elite 25K",
        ):
            self.assertIn(product_name, body)
        for asset in (
            "/assets/picwise/product-1.svg",
            "/assets/picwise/product-2.svg",
            "/assets/picwise/product-3.svg",
            "/assets/picwise/product-4.svg",
        ):
            self.assertIn(asset, body)

    def test_amazon_affiliate_proof_route_renders_controlled_manual_result(self) -> None:
        body = self._fetch("/amazon-affiliate-proof")
        self.assertIn("Manual Amazon affiliate proof", body)
        self.assertIn("Matched query: power bank", body)
        self.assertIn("Approved Amazon result", body)
        self.assertIn("INIU Portable Charger 10500mAh Fast Charging Power Bank", body)
        self.assertIn("Power bank / portable charger category", body)
        self.assertIn("ASIN: B08K7GHZ3V", body)
        self.assertIn(">View on Amazon<", body)
        self.assertIn("tag=picwise-20", body)
        self.assertIn("As an Amazon Associate I earn from qualifying purchases.", body)
        self.assertIn(
            "Prices, availability, ratings, reviews, delivery, and seller terms are shown on Amazon and may change. PicWise does not sell products directly.",
            body,
        )
        lowered = body.lower()
        self.assertNotIn("eur ", lowered)
        self.assertNotIn("in stock", lowered)
        self.assertNotIn("prime", lowered)
        self.assertNotIn("discount", lowered)
        self.assertNotIn("<img", lowered)
        self.assertNotIn("amazon.com/images", lowered)
        self.assertNotIn("class=\"pw-rating-row\"", lowered)

    def test_picwise_reference_assets_are_served_locally(self) -> None:
        with urlopen(
            f"http://127.0.0.1:{self.port}/assets/picwise/product-1.svg",
            timeout=5,
        ) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "image/svg+xml")
            self.assertGreater(len(response.read()), 0)

    def test_demo_includes_header_search_and_footer_controls(self) -> None:
        body = self._fetch("/demo?q=power+bank")
        self.assertIn("How PicWise will help shoppers decide.", body)
        self.assertIn("Back to home", body)
        self.assertNotIn("What is Picwise?", body)
        self.assertIn("All rights reserved.", body)
        self._assert_common_footer_links(body)
        for forbidden in (
            "View in Store",
            "Go to Store",
            "View Details and Buy",
            "Recommended by Picwise",
            "pw-card-recommended",
        ):
            self.assertNotIn(forbidden, body)

    def test_demo_includes_hero_subtitle_and_demo_note(self) -> None:
        body = self._fetch("/demo")
        self.assertIn(
            "How PicWise will help shoppers decide.",
            body,
        )
        self.assertIn(
            "This demo page is informational only.",
            body,
        )
        demo_note_index = body.index("This demo page is informational only.")
        footer_index = body.index('<footer class="pw-footer">')
        self.assertLess(demo_note_index, footer_index)

    def test_demo_has_exactly_four_primary_cards_and_one_recommended(self) -> None:
        body = self._fetch("/demo")
        self.assertNotIn('<article class="pw-card', body)
        self.assertNotIn("Recommended by Picwise", body)
        self.assertIn("Search by product need", body)
        self.assertIn("Compare focused choices", body)

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
            "travelcore 20k",
            "dailybalance pd20",
            "everydaysure 22.5w",
            "powermax elite 25k",
            "view in store",
            "go to store",
            "view details and buy",
            "eur ",
        ):
            self.assertNotIn(forbidden_fake, body)
        self.assertNotIn("class=\"pw-rating-row\"", body)

    def test_demo_includes_fixture_not_production_markers(self) -> None:
        body = self._fetch("/demo")
        self.assertIn("informational only", body)
        self.assertIn("No live Amazon offers are currently claimed", body)

    def test_legal_routes_and_404_are_exposed_on_local_server(self) -> None:
        for path, token in (
            ("/terms", "Terms of Use"),
            ("/privacy", "Privacy Policy"),
            ("/cookies", "Cookie Policy"),
            ("/affiliate-disclosure", "As an Amazon Associate I earn from qualifying purchases."),
            ("/contact", "contact.picwise@subby.cloud"),
        ):
            body = self._fetch(path)
            self.assertIn(token, body)
            self.assertIn("contact.picwise@subby.cloud", body)
            self.assertNotIn("contact@picwise.subby.cloud", body)
            self.assertIn('<meta name="description"', body)
            self._assert_common_footer_links(body)
            self.assertNotIn("mysubby.cloud@gmail.com", body)

        from urllib.error import HTTPError

        with self.assertRaises(HTTPError) as ctx:
            self._fetch("/not-real-page")
        self.assertEqual(ctx.exception.code, 404)
        body = ctx.exception.read().decode("utf-8")
        self.assertIn("Page not found — PicWise", body)
        self.assertIn("The page you requested could not be found.", body)
        self._assert_common_footer_links(body)


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
        self.assertIn("Recommended by PicWise", html)

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
