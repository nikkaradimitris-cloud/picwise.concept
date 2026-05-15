from __future__ import annotations

import socket
import re
import sys
import threading
import unittest
from pathlib import Path
from urllib.request import HTTPErrorProcessor
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
    class _NoRedirect(HTTPErrorProcessor):
        def http_response(self, request, response):  # type: ignore[override]
            return response

        https_response = http_response

    @staticmethod
    def _extract_amazon_hrefs(body: str) -> list[str]:
        return re.findall(r'href="([^"]+)"[^>]*>View on Amazon<', body)

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

    def _reset_amazon_click_log(self) -> None:
        self.server.RequestHandlerClass.app.clear_amazon_outbound_click_events()

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
        self.assertIn('class="pw-home-search"', body)
        self.assertIn('action="/search"', body)
        self.assertIn('method="get"', body)
        self.assertIn('name="q"', body)
        self.assertIn('placeholder="Search for a product, e.g. power bank"', body)
        self.assertIn(">Search<", body)
        self.assertEqual(body.count('data-main-cta-area="true"'), 1)
        self.assertEqual(body.count('class="pw-btn pw-btn-primary"'), 1)
        self.assertIn("Try the current demo search:", body)
        self.assertIn(
            "Demo results use approved manual Amazon affiliate links where configured.",
            body,
        )
        self.assertNotIn("View demo", body)
        self.assertNotIn("What is PicWise?", body)
        self.assertNotIn("Login", body)
        self.assertNotIn("Register", body)
        self.assertNotIn("search all amazon", body.lower())
        self.assertNotIn("live amazon search", body.lower())
        self.assertNotIn("best prices", body.lower())
        self.assertNotIn("top rated", body.lower())
        self.assertNotIn("live deals", body.lower())
        self.assertNotIn("guaranteed", body.lower())
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
        self.assertIn('action="/search"', body)
        self.assertIn('name="q"', body)

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
        self.assertNotIn("INIU Portable Charger 10500mAh Fast Charging Power Bank", body)
        self.assertNotIn("Portable Charger 5000mAh Compact Power Bank", body)
        self.assertIn("Power bank / portable charger category", body)
        self.assertIn("ASIN: B0GR1257LT", body)
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

    def test_search_route_renders_controlled_manual_result_for_power_bank_query(self) -> None:
        body = self._fetch("/search?q=power%20bank")
        self.assertIn('href="/"', body)
        self.assertTrue(("Back to home" in body) or ("Home" in body))
        self.assertIn('form class="pw-search-form" action="/search" method="get"', body)
        self.assertIn('name="q"', body)
        self.assertIn('value="power bank"', body)
        self.assertIn("Search results for: power bank", body)
        self.assertIn("Approved Amazon options", body)
        self.assertIn("Matched query: power bank", body)
        self.assertIn("Approved manual Amazon affiliate options", body)
        self.assertIn("Only manually reviewed active options are shown.", body)
        self.assertEqual(body.count('class="pw-option"'), 4)
        self.assertIn('class="pw-search-results-grid"', body)
        self.assertIn("grid-template-columns:repeat(4,minmax(0,1fr));", body)
        self.assertIn("@media (max-width:1040px){.pw-search-results-grid{grid-template-columns:repeat(2,minmax(0,1fr));", body)
        self.assertIn("@media (max-width:640px){", body)
        self.assertEqual(body.count('class="pw-safe-product-visual pw-powerbank-visual"'), 4)
        self.assertEqual(body.count('data-visual-slot="'), 4)
        self.assertNotIn("INIU Portable Charger 10500mAh Fast Charging Power Bank", body)
        self.assertNotIn("Portable Charger 5000mAh Compact Power Bank", body)
        self.assertIn("Geavonyg PowerBanks 20000mAh Portable Charger", body)
        self.assertIn("Portable Charger 40000mAh Fast Charging Power Bank", body)
        self.assertIn("Anker Powerbank 25000mAh 165W USB-C Portable Charger", body)
        self.assertIn("BoxWave Rejuva 30000mAh 65W PD High Capacity Power Bank", body)
        for asin in ("B0GR1257LT", "B0GH75LWKN", "B0GV9RDLM4", "B0BJMQBNZP"):
            self.assertIn(f"ASIN: {asin}", body)
        self.assertNotIn("ASIN: B0FQJH2XSY", body)
        self.assertNotIn("ASIN: B08K7GHZ3V", body)
        self.assertEqual(body.count("Power banks / portable chargers"), 4)
        for why_text in (
            "Higher-capacity option for longer days, travel, or multiple phone charges.",
            "Large-capacity option for users who prioritize maximum backup power.",
            "Premium high-capacity option for heavy usage, fast USB-C output, and longer travel coverage.",
            "High-capacity PD backup option for users who need sustained output and broad charging compatibility.",
        ):
            self.assertIn(why_text, body)
        self.assertEqual(body.count(">View on Amazon<"), 4)
        hrefs = self._extract_amazon_hrefs(body)
        self.assertEqual(len(hrefs), 4)
        self.assertTrue(all(href.startswith("/out/amazon?asin=") for href in hrefs))
        self.assertTrue(all("&q=power%20bank" in href for href in hrefs))
        self.assertTrue(all("&src=search" in href for href in hrefs))
        self.assertTrue(all("B08K7GHZ3V" not in href for href in hrefs))
        self.assertTrue(all("B0FQJH2XSY" not in href for href in hrefs))
        self.assertTrue(all("B0F518CRGK" not in href for href in hrefs))
        self.assertFalse(any("amazon.com" in href for href in hrefs))
        self.assertIn("As an Amazon Associate I earn from qualifying purchases.", body)
        self.assertIn(
            "Prices, availability, ratings, reviews, delivery, and seller terms are shown on Amazon and may change. PicWise does not sell products directly.",
            body,
        )
        self._assert_common_footer_links(body)
        self.assertNotIn("B0F518CRGK", body)

    def test_results_route_renders_controlled_manual_results_for_power_bank_query(self) -> None:
        body = self._fetch("/results?q=power%20bank")
        self.assertIn('href="/"', body)
        self.assertIn('form class="pw-search-form" action="/search" method="get"', body)
        self.assertIn('name="q"', body)
        self.assertIn('value="power bank"', body)
        self.assertIn("Search results for: power bank", body)
        self.assertIn("Approved Amazon options", body)
        self.assertIn("Only manually reviewed active options are shown.", body)
        self.assertEqual(body.count('class="pw-option"'), 4)
        self.assertIn('class="pw-search-results-grid"', body)
        self.assertEqual(body.count('class="pw-safe-product-visual pw-powerbank-visual"'), 4)
        self.assertEqual(body.count('data-visual-slot="'), 4)
        for asin in ("B0GR1257LT", "B0GH75LWKN", "B0GV9RDLM4", "B0BJMQBNZP"):
            self.assertIn(f"ASIN: {asin}", body)
        self.assertNotIn("ASIN: B0FQJH2XSY", body)
        self.assertNotIn("ASIN: B08K7GHZ3V", body)
        self.assertEqual(body.count("Power banks / portable chargers"), 4)
        for why_text in (
            "Higher-capacity option for longer days, travel, or multiple phone charges.",
            "Large-capacity option for users who prioritize maximum backup power.",
            "Premium high-capacity option for heavy usage, fast USB-C output, and longer travel coverage.",
            "High-capacity PD backup option for users who need sustained output and broad charging compatibility.",
        ):
            self.assertIn(why_text, body)
        self.assertEqual(body.count(">View on Amazon<"), 4)
        hrefs = self._extract_amazon_hrefs(body)
        self.assertEqual(len(hrefs), 4)
        self.assertTrue(all(href.startswith("/out/amazon?asin=") for href in hrefs))
        self.assertTrue(all("&q=power%20bank" in href for href in hrefs))
        self.assertTrue(all("&src=results" in href for href in hrefs))
        self.assertTrue(all("B08K7GHZ3V" not in href for href in hrefs))
        self.assertTrue(all("B0FQJH2XSY" not in href for href in hrefs))
        self.assertTrue(all("B0F518CRGK" not in href for href in hrefs))
        self.assertFalse(any("amazon.com" in href for href in hrefs))
        self._assert_common_footer_links(body)
        self.assertNotIn("B0F518CRGK", body)

    def test_outbound_amazon_redirect_returns_expected_location(self) -> None:
        from urllib.error import HTTPError
        from urllib.request import build_opener

        opener = build_opener(self._NoRedirect)
        response = opener.open(
            f"http://127.0.0.1:{self.port}/out/amazon?asin=B0GR1257LT&q=power%20bank&src=search",
            timeout=5,
        )
        self.assertEqual(response.status, 302)
        location = response.headers.get("Location", "")
        self.assertIn("amazon.com", location)
        self.assertIn("tag=picwise-20", location)
        self.assertIn("B0GR1257LT", location)

        response = opener.open(
            f"http://127.0.0.1:{self.port}/out/amazon?asin=B0GV9RDLM4&q=power%20bank&src=search",
            timeout=5,
        )
        self.assertEqual(response.status, 302)
        location = response.headers.get("Location", "")
        self.assertIn("amazon.com", location)
        self.assertIn("tag=picwise-20", location)
        self.assertIn("B0GV9RDLM4", location)

        response = opener.open(
            f"http://127.0.0.1:{self.port}/out/amazon?asin=B0BJMQBNZP&q=power%20bank&src=search",
            timeout=5,
        )
        self.assertEqual(response.status, 302)
        location = response.headers.get("Location", "")
        self.assertIn("amazon.com", location)
        self.assertIn("tag=picwise-20", location)
        self.assertIn("B0BJMQBNZP", location)

        response = opener.open(
            f"http://127.0.0.1:{self.port}/out/amazon?asin=B0FQJH2XSY&q=power%20bank&src=search",
            timeout=5,
        )
        self.assertEqual(response.status, 200)
        disabled_compact_body = response.read().decode("utf-8")
        self.assertIn("Amazon option disabled", disabled_compact_body)
        self.assertIn("This Amazon option is not currently available through PicWise.", disabled_compact_body)
        self.assertIn("This option has been disabled after manual review.", disabled_compact_body)
        self.assertIn("Please return to search results.", disabled_compact_body)

        disabled_body = self._fetch("/out/amazon?asin=B08K7GHZ3V&q=power%20bank&src=search")
        self.assertIn("Amazon option disabled", disabled_body)
        self.assertIn("This Amazon option is not currently available through PicWise.", disabled_body)
        self.assertIn("This option has been disabled after manual review.", disabled_body)
        self.assertIn("Please return to search results.", disabled_body)

        unknown_body = self._fetch("/out/amazon?asin=BADASIN&q=power%20bank&src=search")
        self.assertIn("Amazon option disabled", unknown_body)
        self.assertIn("This Amazon option is not currently available through PicWise.", unknown_body)

    def test_outbound_amazon_redirect_rejects_arbitrary_external_url(self) -> None:
        body = self._fetch(
            "/out/amazon?asin=https%3A%2F%2Fevil.example%2Fbad&url=https%3A%2F%2Fevil.example%2Foverride&q=power%20bank"
        )
        self.assertIn("Amazon option disabled", body)
        self.assertIn("This Amazon option is not currently available through PicWise.", body)

    def test_amazon_launch_check_route_is_exposed(self) -> None:
        body = self._fetch("/amazon-launch-check")
        self.assertIn("Tracking ID configured: <code>picwise-20</code>", body)
        self.assertIn("Approved manual links: 6", body)
        self.assertIn("Active public links: 4", body)
        self.assertIn("Disabled/manual review links: 2", body)
        self.assertIn("/search?q=power%20bank", body)
        self.assertIn("/results?q=power%20bank", body)
        self.assertIn("Outbound redirect validation: enabled", body)
        self.assertIn("API access: not available yet", body)
        self.assertIn("Amazon images/live prices: not used", body)
        self.assertIn("Disclosure: present", body)

    def test_amazon_click_proof_route_initial_state_is_safe(self) -> None:
        self._reset_amazon_click_log()
        body = self._fetch("/amazon-click-proof")
        self.assertIn("Amazon click proof", body)
        self.assertIn("Tracking ID configured: <code>picwise-20</code>", body)
        self.assertIn("Recorded outbound clicks: 0", body)
        self.assertIn("Last click ASIN: none", body)
        self.assertIn("Last click query: none", body)
        self.assertIn("Last click source: none", body)
        self.assertIn("Last event type: none", body)
        self.assertIn("Active public links: 4", body)
        self.assertIn("Disabled/manual review links: 2", body)
        self.assertIn("Sales verification: check Amazon Associates", body)
        self.assertIn("Amazon sales are not verified here. Check Amazon Associates for actual sales.", body)
        self.assertNotIn("https://www.amazon.com/", body)

    def test_outbound_click_recording_for_active_and_disabled_asins(self) -> None:
        from urllib.request import build_opener

        self._reset_amazon_click_log()
        opener = build_opener(self._NoRedirect)

        active_search = opener.open(
            f"http://127.0.0.1:{self.port}/out/amazon?asin=B0GV9RDLM4&q=power%20bank&src=search",
            timeout=5,
        )
        self.assertEqual(active_search.status, 302)
        active_search_location = active_search.headers.get("Location", "")
        self.assertIn("tag=picwise-20", active_search_location)
        self.assertIn("B0GV9RDLM4", active_search_location)

        proof_body = self._fetch("/amazon-click-proof")
        self.assertIn("Recorded outbound clicks: 1", proof_body)
        self.assertIn("Last click ASIN: B0GV9RDLM4", proof_body)
        self.assertIn("Last click query: power bank", proof_body)
        self.assertIn("Last click source: search", proof_body)
        self.assertIn("Last event type: amazon_outbound_click", proof_body)

        active_results = opener.open(
            f"http://127.0.0.1:{self.port}/out/amazon?asin=B0BJMQBNZP&q=power%20bank&src=results",
            timeout=5,
        )
        self.assertEqual(active_results.status, 302)
        active_results_location = active_results.headers.get("Location", "")
        self.assertIn("tag=picwise-20", active_results_location)
        self.assertIn("B0BJMQBNZP", active_results_location)

        proof_body = self._fetch("/amazon-click-proof")
        self.assertIn("Recorded outbound clicks: 2", proof_body)
        self.assertIn("Last click ASIN: B0BJMQBNZP", proof_body)
        self.assertIn("Last click query: power bank", proof_body)
        self.assertIn("Last click source: results", proof_body)
        self.assertIn("Last event type: amazon_outbound_click", proof_body)

        disabled_before = self.server.RequestHandlerClass.app.get_amazon_outbound_click_count()
        disabled_response = opener.open(
            f"http://127.0.0.1:{self.port}/out/amazon?asin=B08K7GHZ3V&q=power%20bank&src=search",
            timeout=5,
        )
        self.assertEqual(disabled_response.status, 200)
        disabled_after = self.server.RequestHandlerClass.app.get_amazon_outbound_click_count()
        self.assertEqual(disabled_before, disabled_after)

        disabled_compact_before = self.server.RequestHandlerClass.app.get_amazon_outbound_click_count()
        disabled_compact_response = opener.open(
            f"http://127.0.0.1:{self.port}/out/amazon?asin=B0FQJH2XSY&q=power%20bank&src=search",
            timeout=5,
        )
        self.assertEqual(disabled_compact_response.status, 200)
        disabled_compact_after = self.server.RequestHandlerClass.app.get_amazon_outbound_click_count()
        self.assertEqual(disabled_compact_before, disabled_compact_after)

        unknown_before = self.server.RequestHandlerClass.app.get_amazon_outbound_click_count()
        unknown_response = opener.open(
            f"http://127.0.0.1:{self.port}/out/amazon?asin=BADASIN&q=power%20bank&src=search",
            timeout=5,
        )
        self.assertEqual(unknown_response.status, 200)
        unknown_after = self.server.RequestHandlerClass.app.get_amazon_outbound_click_count()
        self.assertEqual(unknown_before, unknown_after)

    def test_search_route_renders_safe_no_result_for_unapproved_query(self) -> None:
        body = self._fetch("/search?q=laptop")
        self.assertIn('href="/"', body)
        self.assertTrue(("Back to home" in body) or ("Home" in body))
        self.assertIn('form class="pw-search-form" action="/search" method="get"', body)
        self.assertIn('name="q"', body)
        self.assertIn('value="laptop"', body)
        self.assertIn("Search results for: laptop", body)
        self.assertIn("No approved Amazon options are available for this query yet.", body)
        self.assertIn("PicWise only shows approved manual affiliate results at this stage.", body)
        self.assertIn("No fake product data is shown.", body)
        self.assertNotIn("INIU Portable Charger 10500mAh Fast Charging Power Bank", body)
        self.assertNotIn("ASIN: B08K7GHZ3V", body)
        self.assertNotIn(">View on Amazon<", body)
        self.assertNotIn("tag=picwise-20", body)
        self.assertNotIn('class="pw-option"', body)
        self.assertNotIn('class="pw-safe-product-visual', body)
        self._assert_common_footer_links(body)

    def test_search_route_renders_safe_no_result_for_empty_query(self) -> None:
        body = self._fetch("/search?q=")
        self.assertIn("No approved Amazon options are available for this query yet.", body)
        self.assertIn("PicWise only shows approved manual affiliate results at this stage.", body)
        self.assertNotIn(">View on Amazon<", body)
        self.assertNotIn("tag=picwise-20", body)
        self.assertNotIn('class="pw-option"', body)

    def test_search_route_does_not_show_forbidden_commerce_claims(self) -> None:
        body = self._fetch("/search?q=power%20bank")
        lowered = body.lower()
        self.assertNotIn("eur ", lowered)
        self.assertNotIn("in stock", lowered)
        self.assertNotIn("prime", lowered)
        self.assertNotIn("discount", lowered)
        self.assertNotIn("best price", lowered)
        self.assertNotIn("cheapest", lowered)
        self.assertNotIn("top rated", lowered)
        self.assertNotIn("recommended by amazon", lowered)
        self.assertNotIn("guaranteed", lowered)
        self.assertNotIn("<img src=\"https://", lowered)
        self.assertNotIn("<img", lowered)
        self.assertNotIn("amazon.com/images", lowered)
        self.assertNotIn("m.media-amazon.com", lowered)
        self.assertNotIn("images-na.ssl-images-amazon.com", lowered)
        self.assertNotIn("product image hotlinks", lowered)
        self.assertNotIn("class=\"pw-rating-row\"", lowered)
        body_without_safe_note = body.replace(
            "Prices, availability, ratings, reviews, delivery, and seller terms are shown on Amazon and may change. PicWise does not sell products directly.",
            "",
        ).lower()
        self.assertNotIn("rating", body_without_safe_note)
        self.assertNotIn("reviews", body_without_safe_note)

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
