from __future__ import annotations

import io
import json
import os
import re
import sys
import unittest
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.index import app as deployment_app  # noqa: E402
from picwise_integrations.subby_dashboard import UrllibSubbyBridgeEventSender  # noqa: E402
from wsgi import app as wsgi_app  # noqa: E402


def _call_wsgi(path: str, query_string: str = "") -> tuple[str, dict[str, str], str]:
    status_holder: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_holder["status"] = status
        status_holder["headers"] = {key: value for key, value in headers}

    environ: dict[str, object] = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "wsgi.input": io.BytesIO(b""),
        "CONTENT_LENGTH": "0",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "wsgi.url_scheme": "https",
    }
    body_chunks = deployment_app(environ, start_response)
    body = b"".join(body_chunks).decode("utf-8")
    return status_holder["status"], status_holder["headers"], body


class DeploymentEntrypointTests(unittest.TestCase):
    @staticmethod
    def _extract_amazon_hrefs(body: str) -> list[str]:
        return re.findall(r'href="([^"]+)"[^>]*>View on Amazon<', body)

    @staticmethod
    def _extract_location(headers: dict[str, str]) -> str:
        for key, value in headers.items():
            if key.lower() == "location":
                return value
        return ""

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

    def test_deployment_entrypoint_imports(self) -> None:
        self.assertTrue(callable(deployment_app))
        self.assertTrue(callable(wsgi_app))

    def test_health_route_works_through_deployment_entrypoint(self) -> None:
        status, headers, body = _call_wsgi("/health")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertIn('"status": "ok"', body)
        self.assertIn('"domain_plan_primary": "picwise.subby.cloud"', body)

    def test_demo_route_works_through_deployment_entrypoint(self) -> None:
        query = "power bank 20000mah for iphone"
        status, headers, body = _call_wsgi("/demo", f"q={quote(query)}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("How PicWise will help shoppers decide.", body)
        self.assertIn("This demo page is informational only.", body)
        self.assertNotIn(query, body)
        self.assertIn("<title>PicWise Demo — Buying Decision Preview</title>", body)
        self.assertIn('<meta name="description"', body)
        self._assert_common_footer_links(body)

    def test_root_route_returns_main_picwise_reference_ui(self) -> None:
        status, headers, body = _call_wsgi("/")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("<main", body.lower())
        self.assertIn("See the 4 best products before you buy", body)
        self.assertIn("Live safe mode", body)
        self.assertIn("shopping decision assistant", body)
        self.assertIn("<title>PicWise Reference — Buying Decision Preview</title>", body)
        self.assertIn('<meta name="description"', body)
        self._assert_common_footer_links(body)
        self.assertIn('class="pw-search-shell"', body)
        self.assertIn('action="/search"', body)
        self.assertIn('method="get"', body)
        self.assertIn('name="q"', body)
        self.assertIn('placeholder="See the 4 best products before you buy"', body)
        self.assertIn('class="pw-search-button"', body)
        self.assertIn("What is PicWise?", body)
        self.assertIn("Login", body)
        self.assertIn("Register", body)
        self.assertNotIn("search all amazon", body.lower())
        self.assertNotIn("live amazon search", body.lower())
        self.assertNotIn(">View on Amazon<", body)
        self.assertNotIn("not_found", body)
        self.assertNotIn("mysubby.cloud@gmail.com", body)

    def test_picwise_reference_route_returns_main_reference_shell(self) -> None:
        status, headers, body = _call_wsgi("/picwise-reference")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("See the 4 best products before you buy", body)
        self.assertIn("Live safe mode", body)
        self.assertIn(
            'placeholder="See the 4 best products before you buy"',
            body,
        )
        self.assertNotIn("<h1>See the 4 best products before you buy</h1>", body)
        self.assertNotIn("Search your product here", body)
        self.assertNotIn('value="See the 4 best products before you buy"', body)
        for forbidden_image_placeholder in (
            "TravelCore 20K product image placeholder",
            "DailyBalance PD20 product image placeholder",
            "EverydaySure 22.5W product image placeholder",
            "PowerMax Elite 25K product image placeholder",
        ):
            self.assertNotIn(forbidden_image_placeholder, body)
        self.assertNotIn("Showing 4 options for: power bank 20000mah for iphone", body)
        self.assertNotIn("LIVE RENDERER PROOF V1", body)
        self.assertNotIn("picwise-reference-live-renderer-proof-v1", body)
        self.assertNotIn("View in Store", body)
        self.assertNotIn("Go to Store", body)
        self.assertNotIn("View Details and Buy", body)
        self.assertIn("What is PicWise?", body)
        self.assertEqual(body.count('class="pw-brand"'), 1)
        self.assertNotIn("Demo data source: local_test_fixture (not_production_data).", body)
        self.assertIn("All rights reserved.", body)
        self._assert_common_footer_links(body)
        self.assertEqual(body.count('<article class="pw-card'), 0)
        self.assertNotIn("&middot;", body)
        self.assertIn("PicWise safely shows no product cards", body)

    def test_amazon_affiliate_proof_route_renders_controlled_manual_result(self) -> None:
        status, headers, body = _call_wsgi("/amazon-affiliate-proof")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
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
        self.assertNotIn('<img src="https://', lowered)
        self.assertNotIn("amazon.com/images", lowered)
        self.assertNotIn("class=\"pw-rating-row\"", lowered)

    def test_search_route_renders_main_shell_with_live_manual_result_for_power_bank_query(self) -> None:
        status, headers, body = _call_wsgi("/search", "q=power%20bank")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn('href="/"', body)
        self.assertIn('form class="pw-search-shell" action="/search" method="get"', body)
        self.assertIn('name="q"', body)
        self.assertIn('value="power bank"', body)
        self.assertIn("Showing 4 options for: power bank", body)
        self.assertIn("Safe connected provider mode", body)
        self.assertEqual(body.count('<article class="pw-card'), 4)
        self.assertIn('class="pw-grid"', body)
        self.assertIn("grid-template-columns:repeat(4,minmax(0,1fr));", body)
        self.assertIn("@media (max-width:1099px){.pw-grid{grid-template-columns:repeat(2,minmax(0,1fr));", body)
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
        self.assertEqual(body.count(">View on Amazon<"), 4)
        hrefs = self._extract_amazon_hrefs(body)
        self.assertEqual(len(hrefs), 4)
        self.assertTrue(all(href.startswith("/out/amazon?asin=") for href in hrefs))
        self.assertTrue(all(("&q=power%20bank" in href) or ("&amp;q=power%20bank" in href) for href in hrefs))
        self.assertTrue(all(("&src=search" in href) or ("&amp;src=search" in href) for href in hrefs))
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

    def test_search_route_noisy_queries_show_provider_not_connected_and_no_cards(self) -> None:
        noisy_queries = (
            "coffe grindr",
            "vaccum cleaner",
            "bluethoth speker",
            "gming mouse",
            "car batery",
            "bike helmt",
            "winter jakcet",
            "baby car seet",
            "usb caible",
        )
        for query in noisy_queries:
            with self.subTest(query=query):
                status, headers, body = _call_wsgi("/search", f"q={quote(query)}")
                self.assertEqual(status, "200 OK")
                self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
                self.assertIn("PicWise understood this search, but no safe provider is connected yet.", body)
                self.assertNotIn("Showing 4 options for:", body)
                self.assertNotIn("Safe connected provider mode", body)
                self.assertNotIn("ASIN: B0GR1257LT", body)
                self.assertNotIn("ASIN: B0GH75LWKN", body)
                self.assertNotIn("ASIN: B0GV9RDLM4", body)
                self.assertNotIn("ASIN: B0BJMQBNZP", body)
                self.assertNotIn(">View on Amazon<", body)
                self.assertNotIn('class="pw-card"', body)

    def test_results_route_noisy_queries_show_provider_not_connected_and_no_cards(self) -> None:
        noisy_queries = (
            "coffe grindr",
            "bluethoth speker",
            "car batery",
            "baby car seet",
            "usb caible",
        )
        for query in noisy_queries:
            with self.subTest(query=query):
                status, headers, body = _call_wsgi("/results", f"q={quote(query)}")
                self.assertEqual(status, "200 OK")
                self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
                self.assertIn("PicWise understood this search, but no safe provider is connected yet.", body)
                self.assertNotIn("Showing 4 options for:", body)
                self.assertNotIn("ASIN: B0GR1257LT", body)
                self.assertNotIn(">View on Amazon<", body)
                self.assertNotIn('class="pw-card"', body)

    def test_results_route_renders_main_shell_with_live_manual_result_for_power_bank_query(self) -> None:
        status, headers, body = _call_wsgi("/results", "q=power%20bank")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn('href="/"', body)
        self.assertIn('form class="pw-search-shell" action="/search" method="get"', body)
        self.assertIn('name="q"', body)
        self.assertIn('value="power bank"', body)
        self.assertIn("Showing 4 options for: power bank", body)
        self.assertEqual(body.count('<article class="pw-card'), 4)
        self.assertIn('class="pw-grid"', body)
        for asin in ("B0GR1257LT", "B0GH75LWKN", "B0GV9RDLM4", "B0BJMQBNZP"):
            self.assertIn(f"ASIN: {asin}", body)
        self.assertNotIn("ASIN: B0FQJH2XSY", body)
        self.assertNotIn("ASIN: B08K7GHZ3V", body)
        self.assertEqual(body.count(">View on Amazon<"), 4)
        hrefs = self._extract_amazon_hrefs(body)
        self.assertEqual(len(hrefs), 4)
        self.assertTrue(all(href.startswith("/out/amazon?asin=") for href in hrefs))
        self.assertTrue(all(("&q=power%20bank" in href) or ("&amp;q=power%20bank" in href) for href in hrefs))
        self.assertTrue(all(("&src=results" in href) or ("&amp;src=results" in href) for href in hrefs))
        self.assertTrue(all("B08K7GHZ3V" not in href for href in hrefs))
        self.assertTrue(all("B0FQJH2XSY" not in href for href in hrefs))
        self.assertTrue(all("B0F518CRGK" not in href for href in hrefs))
        self.assertFalse(any("amazon.com" in href for href in hrefs))
        self._assert_common_footer_links(body)
        self.assertNotIn("B0F518CRGK", body)

    def test_outbound_amazon_redirect_returns_302_with_safe_affiliate_location(self) -> None:
        status, headers, _body = _call_wsgi("/out/amazon", "asin=B0GR1257LT&q=power%20bank")
        self.assertEqual(status, "302 Found")
        location = self._extract_location(headers)
        self.assertIn("amazon.com", location)
        self.assertIn("tag=picwise-20", location)
        self.assertIn("B0GR1257LT", location)

        status, headers, _body = _call_wsgi("/out/amazon", "asin=B0GV9RDLM4&q=power%20bank&src=search")
        self.assertEqual(status, "302 Found")
        location = self._extract_location(headers)
        self.assertIn("amazon.com", location)
        self.assertIn("tag=picwise-20", location)
        self.assertIn("B0GV9RDLM4", location)

        status, headers, _body = _call_wsgi("/out/amazon", "asin=B0BJMQBNZP&q=power%20bank&src=search")
        self.assertEqual(status, "302 Found")
        location = self._extract_location(headers)
        self.assertIn("amazon.com", location)
        self.assertIn("tag=picwise-20", location)
        self.assertIn("B0BJMQBNZP", location)

    def test_outbound_amazon_redirect_disabled_compact_asin_returns_safe_manual_review_page(self) -> None:
        status, headers, body = _call_wsgi("/out/amazon", "asin=B0FQJH2XSY&q=power%20bank&src=search")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Amazon option disabled", body)
        self.assertIn("This Amazon option is not currently available through PicWise.", body)
        self.assertIn("This option has been disabled after manual review.", body)
        self.assertIn("Please return to search results.", body)

    def test_outbound_amazon_redirect_unknown_asin_returns_not_found(self) -> None:
        status, headers, body = _call_wsgi("/out/amazon", "asin=B000000000&q=power%20bank")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Amazon option disabled", body)
        self.assertIn("This Amazon option is not currently available through PicWise.", body)

    def test_outbound_amazon_redirect_does_not_accept_arbitrary_url(self) -> None:
        query = (
            "asin=https%3A%2F%2Fevil.example%2Fbad"
            "&url=https%3A%2F%2Fevil.example%2Foverride"
            "&q=power%20bank"
        )
        status, headers, body = _call_wsgi("/out/amazon", query)
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Amazon option disabled", body)

    def test_outbound_amazon_redirect_disabled_asin_returns_safe_manual_review_page(self) -> None:
        status, headers, body = _call_wsgi("/out/amazon", "asin=B08K7GHZ3V&q=power%20bank&src=search")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Amazon option disabled", body)
        self.assertIn("This Amazon option is not currently available through PicWise.", body)
        self.assertIn("This option has been disabled after manual review.", body)
        self.assertIn("Please return to search results.", body)

    def test_amazon_launch_check_route_reports_launch_safety_state(self) -> None:
        status, headers, body = _call_wsgi("/amazon-launch-check")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
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
        status, headers, body = _call_wsgi("/amazon-click-proof")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Amazon click proof", body)
        self.assertIn("Tracking ID configured: <code>picwise-20</code>", body)
        self.assertIn("Recorded outbound clicks:", body)
        self.assertIn("Active public links: 4", body)
        self.assertIn("Disabled/manual review links: 2", body)
        self.assertIn("Sales verification: check Amazon Associates", body)
        self.assertIn("Amazon sales are not verified here. Check Amazon Associates for actual sales.", body)
        self.assertNotIn("https://www.amazon.com/", body)

    def test_amazon_click_proof_updates_after_outbound_click(self) -> None:
        status, headers, _body = _call_wsgi(
            "/out/amazon",
            "asin=B0GV9RDLM4&q=power%20bank&src=search",
        )
        self.assertEqual(status, "302 Found")
        location = self._extract_location(headers)
        self.assertIn("tag=picwise-20", location)
        self.assertIn("B0GV9RDLM4", location)

        status, headers, body = _call_wsgi("/amazon-click-proof")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Last click ASIN: B0GV9RDLM4", body)
        self.assertIn("Last click query: power bank", body)
        self.assertIn("Last click source: search", body)
        self.assertIn("Last event type: amazon_outbound_click", body)

    def test_amazon_traffic_protocol_route_documents_manual_first_live_traffic_checks(self) -> None:
        status, headers, body = _call_wsgi("/amazon-traffic-protocol")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("First live traffic protocol", body)
        self.assertIn("Tracking ID: picwise-20", body)
        self.assertIn("https://picwise.subby.cloud/search?q=power%20bank", body)
        self.assertIn("/amazon-click-proof", body)
        self.assertIn("/amazon-launch-check", body)

    def test_amazon_traffic_protocol_readiness_checklist_is_explicit(self) -> None:
        _status, _headers, body = _call_wsgi("/amazon-traffic-protocol")
        self.assertIn("Search page active: ready", body)
        self.assertIn("Active Amazon links: 4", body)
        self.assertIn("Disabled links blocked: ready", body)
        self.assertIn("Click proof: ready", body)
        self.assertIn("Amazon sales proof: manual Amazon Associates only", body)
        self.assertIn("Ads: not ready", body)
        self.assertIn("API reporting: not available yet", body)

    def test_amazon_traffic_protocol_has_no_fake_sales_earnings_or_conversion_claims(self) -> None:
        _status, _headers, body = _call_wsgi("/amazon-traffic-protocol")
        lowered = body.lower()
        self.assertNotIn("orders verified", lowered)
        self.assertNotIn("sales verified", lowered)
        self.assertNotIn("earnings verified", lowered)
        self.assertNotIn("conversion rate verified", lowered)
        self.assertNotIn("ads are ready", lowered)

    def test_search_route_renders_safe_no_result_for_unapproved_query(self) -> None:
        status, _headers, body = _call_wsgi("/search", "q=laptop")
        self.assertEqual(status, "200 OK")
        self.assertIn('href="/"', body)
        self.assertIn('form class="pw-search-shell" action="/search" method="get"', body)
        self.assertIn('name="q"', body)
        self.assertIn('value="laptop"', body)
        self.assertIn("PicWise understood this search, but no safe provider is connected yet.", body)
        self.assertIn("Detected category: Computers / Office / Peripherals", body)
        self.assertNotIn("INIU Portable Charger 10500mAh Fast Charging Power Bank", body)
        self.assertNotIn("ASIN: B08K7GHZ3V", body)
        self.assertNotIn(">View on Amazon<", body)
        self.assertNotIn("tag=picwise-20", body)
        self.assertNotIn('class="pw-card"', body)
        self._assert_common_footer_links(body)

    def test_search_route_random_garbage_query_shows_not_understood_message(self) -> None:
        status, _headers, body = _call_wsgi("/search", "q=asdf@@@")
        self.assertEqual(status, "200 OK")
        self.assertIn("PicWise could not understand this search safely.", body)
        self.assertNotIn(">View on Amazon<", body)
        self.assertNotIn("ASIN: B0GR1257LT", body)
        self.assertNotIn('class="pw-card"', body)

    def test_search_route_provider_not_connected_shows_explicit_message(self) -> None:
        status, _headers, body = _call_wsgi("/search", "q=wall%20charger")
        self.assertEqual(status, "200 OK")
        self.assertIn("PicWise understood this search, but no safe provider is connected yet.", body)
        self.assertIn("Detected category: Phones / Mobile / Accessories", body)
        self.assertNotIn(">View on Amazon<", body)
        self.assertNotIn("ASIN: B0GR1257LT", body)
        self.assertNotIn('class="pw-card"', body)

    def test_results_route_provider_not_connected_shows_detected_category(self) -> None:
        status, _headers, body = _call_wsgi("/results", "q=laptop")
        self.assertEqual(status, "200 OK")
        self.assertIn("PicWise understood this search, but no safe provider is connected yet.", body)
        self.assertIn("Detected category: Computers / Office / Peripherals", body)
        self.assertNotIn(">View on Amazon<", body)
        self.assertNotIn("ASIN: B0GR1257LT", body)
        self.assertNotIn('class="pw-card"', body)

    def test_search_route_unrelated_safety_queries_do_not_show_power_bank_cards(self) -> None:
        safety_queries = (
            "bank account",
            "river bank",
            "blood bank",
            "bang speaker",
            "laptop",
            "wall charger",
            "charging cable",
            "travel adapter",
            "phone case",
            "car insurance",
            "παπούτσια",
        )
        for query in safety_queries:
            with self.subTest(query=query):
                status, _headers, body = _call_wsgi("/search", f"q={quote(query)}")
                self.assertEqual(status, "200 OK")
                self.assertNotIn("Showing 4 options for:", body)
                self.assertNotIn("ASIN: B0GR1257LT", body)
                self.assertNotIn("ASIN: B0GH75LWKN", body)
                self.assertNotIn("ASIN: B0GV9RDLM4", body)
                self.assertNotIn("ASIN: B0BJMQBNZP", body)
                self.assertNotIn(">View on Amazon<", body)
                self.assertNotIn('class="pw-card"', body)

    def test_broad_negatives_show_safe_no_result_without_cards(self) -> None:
        blocked = (
            "bank",
            "charger",
            "apple",
            "nike",
            "bosch",
            "insurance",
            "loan",
            "erp",
            "crm",
            "accounting software",
            "river bank",
            "bank account",
            "car insurance",
        )
        for query in blocked:
            with self.subTest(query=query):
                status, _headers, body = _call_wsgi("/search", f"q={quote(query)}")
                self.assertEqual(status, "200 OK")
                self.assertIn("PicWise could not understand this search safely.", body)
                self.assertNotIn("ASIN: B0GR1257LT", body)
                self.assertNotIn("ASIN: B0GH75LWKN", body)
                self.assertNotIn("ASIN: B0GV9RDLM4", body)
                self.assertNotIn("ASIN: B0BJMQBNZP", body)
                self.assertNotIn(">View on Amazon<", body)
                self.assertNotIn('class="pw-card"', body)

    def test_no_overmatch_negative_queries(self) -> None:
        blocked = (
            "bank",
            "apple",
            "charger",
            "galaxy",
            "bosch",
            "nike",
            "insurance",
            "loan",
            "erp",
            "crm",
            "accounting software",
        )
        for query in blocked:
            with self.subTest(query=query):
                status, _headers, body = _call_wsgi("/search", f"q={quote(query)}")
                self.assertEqual(status, "200 OK")
                self.assertIn("PicWise could not understand this search safely.", body)
                self.assertNotIn(">View on Amazon<", body)
                self.assertNotIn("ASIN: B0GR1257LT", body)

    def test_search_route_renders_safe_no_result_for_empty_query(self) -> None:
        status, _headers, body = _call_wsgi("/search", "q=")
        self.assertEqual(status, "200 OK")
        self.assertIn("PicWise safely shows no product cards", body)
        self.assertNotIn(">View on Amazon<", body)
        self.assertNotIn("tag=picwise-20", body)
        self.assertNotIn('class="pw-card"', body)

    def test_search_route_does_not_show_forbidden_commerce_claims(self) -> None:
        _status, _headers, body = _call_wsgi("/search", "q=power%20bank")
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
        self.assertNotIn('<img src="https://', lowered)
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

    def test_reference_route_and_required_core_routes_are_registered(self) -> None:
        health_status, _health_headers, _health_body = _call_wsgi("/health")
        root_status, _root_headers, _root_body = _call_wsgi("/")
        demo_status, _demo_headers, _demo_body = _call_wsgi("/demo")
        reference_status, _reference_headers, reference_body = _call_wsgi("/picwise-reference")

        self.assertEqual(health_status, "200 OK")
        self.assertEqual(root_status, "200 OK")
        self.assertEqual(demo_status, "200 OK")
        self.assertEqual(reference_status, "200 OK")

        self.assertIn("See the 4 best products before you buy", reference_body)
        self.assertNotIn("shopping assistant", reference_body)
        self.assertIn(
            'placeholder="See the 4 best products before you buy"',
            reference_body,
        )
        self.assertNotIn("<h1>See the 4 best products before you buy</h1>", reference_body)
        self.assertNotIn("Search your product here", reference_body)
        self.assertNotIn('value="See the 4 best products before you buy"', reference_body)
        self.assertNotIn(
            "Showing 4 options for: power bank 20000mah for iphone",
            reference_body,
        )
        self.assertNotIn("View in Store", reference_body)
        self.assertNotIn("Go to Store", reference_body)
        self.assertNotIn("View Details and Buy", reference_body)
        self.assertNotIn("LIVE RENDERER PROOF V1", reference_body)
        self.assertNotIn("picwise-reference-live-renderer-proof-v1", reference_body)
        self.assertIn("What is PicWise?", reference_body)
        self.assertEqual(reference_body.count('class="pw-brand"'), 1)
        self.assertIn("PicWise safely shows no product cards", reference_body)
        self._assert_common_footer_links(reference_body)

    def test_terms_privacy_cookies_affiliate_contact_routes(self) -> None:
        expected = {
            "/terms": ("Terms of Use", "<title>Terms of Use — PicWise</title>", True),
            "/privacy": ("Privacy Policy", "<title>Privacy Policy — PicWise</title>", True),
            "/cookies": ("Cookie Policy", "<title>Cookie Policy — PicWise</title>", True),
            "/affiliate-disclosure": ("Affiliate Disclosure", "<title>Affiliate Disclosure — PicWise</title>", True),
            "/contact": ("contact.picwise@subby.cloud", "<title>Contact — PicWise</title>", True),
        }
        for path, (must_have, title_tag, must_have_email) in expected.items():
            status, headers, body = _call_wsgi(path)
            self.assertEqual(status, "200 OK")
            self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
            self.assertIn(must_have, body)
            self.assertIn(title_tag, body)
            if must_have_email:
                self.assertIn("contact.picwise@subby.cloud", body)
            self.assertNotIn("contact@picwise.subby.cloud", body)
            self.assertNotIn("mysubby.cloud@gmail.com", body)
            self.assertIn('<meta name="description"', body)
            self._assert_common_footer_links(body)

    def test_affiliate_disclosure_contains_required_terms(self) -> None:
        _status, _headers, body = _call_wsgi("/affiliate-disclosure")
        self.assertIn("As an Amazon Associate I earn from qualifying purchases.", body)
        self.assertIn("Linkwise", body)
        self.assertIn("SaaS", body)
        self.assertIn("finance", body.lower())

    def test_privacy_contains_required_terms(self) -> None:
        _status, _headers, body = _call_wsgi("/privacy")
        lowered = body.lower()
        self.assertIn("cookies", lowered)
        self.assertIn("pixels", lowered)
        self.assertIn("european economic area", lowered)
        self.assertIn("united kingdom", lowered)
        self.assertIn("legal basis", lowered)
        self.assertIn("affiliate", lowered)
        self.assertIn("saas", lowered)
        self.assertIn("finance", lowered)

    def test_cookies_contains_required_terms(self) -> None:
        _status, _headers, body = _call_wsgi("/cookies")
        lowered = body.lower()
        self.assertIn("essential cookies", lowered)
        self.assertIn("non-essential cookies", lowered)
        self.assertIn("pixels", lowered)
        self.assertIn("consent", lowered)
        self.assertIn("affiliate", lowered)

    def test_terms_contains_required_disclaimer_and_liability_terms(self) -> None:
        _status, _headers, body = _call_wsgi("/terms")
        lowered = body.lower()
        self.assertIn("picwise does not sell products directly", lowered)
        self.assertIn("no checkout", lowered)
        self.assertIn("external seller/provider", lowered)
        self.assertIn("saas", lowered)
        self.assertIn("finance", lowered)
        self.assertIn("no financial advice", lowered)
        self.assertIn("disclaimer", lowered)
        self.assertIn("Limitation of liability", body)
        self.assertIn("Use of PicWise is at the user's own risk.", body)
        self.assertIn("No professional advice", body)
        self.assertIn("does not guarantee", lowered)
        self.assertIn("best, cheapest, most suitable", lowered)
        self.assertIn("Users remain responsible for their final decision", body)

    def test_branded_404_page_is_returned(self) -> None:
        status, headers, body = _call_wsgi("/missing-legal-route")
        self.assertEqual(status, "404 Not Found")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Page not found — PicWise", body)
        self.assertIn("The page you requested could not be found.", body)
        self.assertIn('href="/"', body)
        self._assert_common_footer_links(body)

    def test_demo_has_search_form_with_query_value(self) -> None:
        query = "best office chair under 200"
        _status, _headers, body = _call_wsgi("/demo", f"q={quote(query)}")
        self.assertIn("How PicWise will help shoppers decide.", body)
        self.assertIn("Back to home", body)
        self.assertNotIn("What is Picwise?", body)
        self.assertNotIn('name="q"', body)
        self.assertNotIn(f'value="{query}"', body)

    def test_root_route_contains_four_primary_cards_and_one_recommended_marker(self) -> None:
        _status, _headers, body = _call_wsgi("/")
        self.assertIn("See the 4 best products before you buy", body)
        self.assertIn('action="/search"', body)
        self.assertIn('name="q"', body)
        self.assertIn('placeholder="See the 4 best products before you buy"', body)
        self.assertIn('class="pw-search-button"', body)
        self.assertNotIn("View demo", body)
        self.assertIn("What is PicWise?", body)
        self.assertIn("Login", body)
        self.assertIn("Register", body)
        self.assertNotIn('<article class="pw-card pw-card-recommended"', body)
        self.assertNotIn("Recommended by Picwise", body)

    def test_recommended_card_has_required_highlight_elements(self) -> None:
        _status, _headers, body = _call_wsgi("/demo")
        self.assertIn("How PicWise will help shoppers decide.", body)
        self.assertIn("External provider integrations in progress", body)
        for forbidden in (
            "pw-card-recommended",
            "Recommended by Picwise",
            "View in Store",
            "Go to Store",
            "View Details and Buy",
        ):
            self.assertNotIn(forbidden, body)

    def test_landing_contains_header_with_login_register(self) -> None:
        _status, _headers, body = _call_wsgi("/demo")
        self.assertIn('class="pw-brand"', body)
        self.assertIn(">PicWise<", body)
        self.assertIn("Back to home", body)
        self.assertNotIn("What is Picwise?", body)

    def test_landing_contains_hero_subtitle(self) -> None:
        _status, _headers, body = _call_wsgi("/demo")
        self.assertIn(
            "How PicWise will help shoppers decide.",
            body,
        )

    def test_landing_contains_footer_nav_links(self) -> None:
        _status, _headers, body = _call_wsgi("/demo")
        self.assertIn('class="pw-footer"', body)
        self.assertIn("All rights reserved.", body)
        lowered = body.lower()
        self.assertNotIn("advertising", lowered)
        self.assertNotIn("η τρίτη δεκαετία", lowered)
        self.assertNotIn("διαφήμιση", lowered)
        self.assertNotIn("leaf", lowered)
        self.assertNotIn("climate", lowered)

    def test_landing_contains_discreet_demo_note_above_footer(self) -> None:
        _status, _headers, body = _call_wsgi("/demo")
        self.assertIn(
            "This demo page is informational only.",
            body,
        )
        self.assertEqual(body.count("informational only"), 1)
        demo_note_index = body.index("This demo page is informational only.")
        footer_index = body.index('<footer class="pw-footer">')
        self.assertLess(demo_note_index, footer_index)

    def test_landing_html_avoids_cart_checkout_and_fake_markers(self) -> None:
        _status, _headers, body = _call_wsgi("/")
        lowered = body.lower()
        for forbidden in ("add to cart", "cart", "e-shop"):
            self.assertNotIn(forbidden, lowered)
        for forbidden_fake in (
            "fake revenue",
            "fake conversion",
            "fake review",
            "fake rating",
            "fake urgency",
            "view in store",
            "go to store",
            "view details and buy",
        ):
            self.assertNotIn(forbidden_fake, lowered)

    def test_demo_has_no_fake_cards_prices_ratings_or_store_ctas(self) -> None:
        _status, _headers, body = _call_wsgi("/demo")
        lowered = body.lower()
        for forbidden in (
            "travelcore 20k",
            "dailybalance pd20",
            "everydaysure 22.5w",
            "powermax elite 25k",
            "recommended by picwise",
            "view in store",
            "go to store",
            "view details and buy",
            "eur ",
        ):
            self.assertNotIn(forbidden, lowered)
        self.assertNotIn("class=\"pw-rating-row\"", body)
        self.assertIn("How PicWise will help shoppers decide.", body)
        self.assertIn("Search by product need", body)
        self.assertIn("External provider integrations in progress", body)

    def test_subby_proof_missing_env_returns_safe_missing_config(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            status, headers, body = _call_wsgi("/subby-proof")
        payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(payload["status"], "missing_config")
        self.assertEqual(
            payload["missing"],
            [
                "PICWISE_SUBBY_ENDPOINT",
                "PICWISE_SUBBY_PROJECT_ID",
                "PICWISE_SUBBY_API_KEY",
            ],
        )
        self.assertFalse(payload["secret_values_exposed"])

    def test_subby_proof_does_not_expose_api_key_in_response(self) -> None:
        class SpySender:
            def __init__(self) -> None:
                self.called = False
                self.headers: dict[str, str] = {}
                self.payload: dict[str, Any] = {}

            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                self.called = True
                self.headers = headers
                self.payload = payload
                _ = endpoint
                return 202, {"accepted": True}

        sender = SpySender()
        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://bridge.subby.cloud/events",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "secret-live-key-value",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=sender):
                status, _headers, body = _call_wsgi("/subby-proof")
        payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertTrue(sender.called)
        self.assertNotIn("secret-live-key-value", body)
        self.assertNotIn("api_key", payload)
        self.assertFalse(payload["secret_values_exposed"])
        self.assertEqual(payload["status"], "sent")
        self.assertEqual(payload["bridge_http_status"], 202)
        self.assertTrue(payload["accepted"])

    def test_subby_proof_urlerror_returns_safe_diagnostics_without_secret(self) -> None:
        class FailingSender:
            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                _ = (endpoint, headers, payload)
                raise URLError("upstream timeout for secret-live-key-value")

        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://manager.subby.cloud/events/bridge",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "secret-live-key-value",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=FailingSender()):
                status, _headers, body = _call_wsgi("/subby-proof")
        response_payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(response_payload["status"], "error")
        self.assertIsNone(response_payload["bridge_http_status"])
        self.assertEqual(response_payload["safe_error_type"], "URLError")
        self.assertIn("safe_error_message", response_payload)
        self.assertNotIn("secret-live-key-value", body)
        self.assertFalse(response_payload["secret_values_exposed"])

    def test_subby_proof_timeout_returns_sent_unconfirmed_with_dashboard_check(self) -> None:
        class TimeoutSender:
            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                _ = (endpoint, headers, payload)
                raise TimeoutError("read timed out for secret-live-key-value")

        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://manager.subby.cloud/events/bridge",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "secret-live-key-value",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=TimeoutSender()):
                status, _headers, body = _call_wsgi("/subby-proof")
        response_payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(response_payload["status"], "sent_unconfirmed")
        self.assertIsNone(response_payload["bridge_http_status"])
        self.assertTrue(response_payload["dashboard_check_required"])
        self.assertEqual(response_payload["safe_error_type"], "TimeoutError")
        self.assertIn("safe_error_message", response_payload)
        self.assertIn("response timed out", response_payload["message"])
        self.assertNotIn("secret-live-key-value", body)
        self.assertFalse(response_payload["secret_values_exposed"])

    def test_subby_proof_httperror_returns_http_status_and_safe_type(self) -> None:
        class FailingSender:
            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                _ = (endpoint, headers, payload)
                raise HTTPError(
                    url="https://manager.subby.cloud/events/bridge",
                    code=403,
                    msg="forbidden",
                    hdrs=None,
                    fp=io.BytesIO(
                        b'{"accepted":false,"error":"token secret-live-key-value rejected"}'
                    ),
                )

        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://manager.subby.cloud/events/bridge",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "secret-live-key-value",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=FailingSender()):
                status, _headers, body = _call_wsgi("/subby-proof")
        response_payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(response_payload["status"], "error")
        self.assertEqual(response_payload["bridge_http_status"], 403)
        self.assertEqual(response_payload["safe_error_type"], "HTTPError")
        self.assertFalse(response_payload["accepted"])
        self.assertIn("safe_error_message", response_payload)
        self.assertNotIn("secret-live-key-value", body)
        self.assertFalse(response_payload["secret_values_exposed"])

    def test_subby_proof_rejected_response_includes_safe_diagnostics(self) -> None:
        class RejectedSender:
            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                _ = (endpoint, headers, payload)
                return 405, {"accepted": False, "error": "bridge token secret-live-key-value rejected"}

        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://manager.subby.cloud/events/bridge",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "secret-live-key-value",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=RejectedSender()):
                status, _headers, body = _call_wsgi("/subby-proof")
        response_payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(response_payload["status"], "rejected")
        self.assertEqual(response_payload["bridge_http_status"], 405)
        self.assertEqual(response_payload["safe_error_type"], "HTTPStatusRejected")
        self.assertIn("safe_error_message", response_payload)
        self.assertFalse(response_payload["accepted"])
        self.assertNotIn("secret-live-key-value", body)
        self.assertFalse(response_payload["secret_values_exposed"])

    def test_subby_proof_safe_error_message_redacts_api_key_and_token_like_strings(self) -> None:
        class FailingSender:
            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                _ = (endpoint, headers, payload)
                raise RuntimeError(
                    "PICWISE_SUBBY_API_KEY=secret-live-key-value token ABCDEFGHIJKLMNOPQRSTUVWX123456"
                )

        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://manager.subby.cloud/events/bridge",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "secret-live-key-value",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=FailingSender()):
                status, _headers, body = _call_wsgi("/subby-proof")
        response_payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(response_payload["status"], "error")
        self.assertEqual(response_payload["safe_error_type"], "RuntimeError")
        self.assertIn("safe_error_message", response_payload)
        self.assertIn("[REDACTED]", response_payload["safe_error_message"])
        self.assertIn("[REDACTED_TOKEN]", response_payload["safe_error_message"])
        self.assertNotIn("secret-live-key-value", body)
        self.assertFalse(response_payload["secret_values_exposed"])

    def test_subby_proof_sender_payload_and_headers_are_correct_and_mockable(self) -> None:
        class SpySender:
            def __init__(self) -> None:
                self.calls = 0
                self.endpoint = ""
                self.headers: dict[str, str] = {}
                self.payload: dict[str, Any] = {}

            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                self.calls += 1
                self.endpoint = endpoint
                self.headers = headers
                self.payload = payload
                return 200, {"accepted": True}

        sender = SpySender()
        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://bridge.subby.cloud/events",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "super-secret-key",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=sender):
                _status, _headers, body = _call_wsgi("/subby-proof")
        response_payload = json.loads(body)
        self.assertEqual(sender.calls, 1)
        self.assertEqual(sender.endpoint, "https://bridge.subby.cloud/events")
        self.assertEqual(sender.headers["X-Bridge-Project-ID"], "picwise-prod")
        self.assertEqual(sender.headers["X-Bridge-API-Key"], "super-secret-key")
        self.assertEqual(sender.headers["Content-Type"], "application/json")

        self.assertEqual(sender.payload["schema_version"], "1.0")
        self.assertEqual(sender.payload["source_app"], "picwise")
        self.assertEqual(sender.payload["source"], "picwise_live_proof")
        self.assertEqual(sender.payload["project_id"], "picwise-prod")
        self.assertEqual(sender.payload["signal_type"], "health/live_proof")
        self.assertTrue(sender.payload["test_mode"])
        self.assertTrue(sender.payload["operator_generated"])
        self.assertEqual(sender.payload["payload"]["domain"], "picwise.subby.cloud")
        self.assertEqual(sender.payload["payload"]["route"], "/subby-proof")
        self.assertEqual(sender.payload["payload"]["proof_type"], "live_subby_bridge_event")
        self.assertTrue(sender.payload["payload"]["no_revenue"])
        self.assertTrue(sender.payload["payload"]["no_conversion"])
        self.assertEqual(sender.payload["payload"]["missing_data_state"], "not_applicable")
        self.assertNotIn("revenue", sender.payload)
        self.assertNotIn("conversion", sender.payload)

        self.assertEqual(response_payload["project_id"], "picwise-prod")
        self.assertEqual(response_payload["endpoint_host"], "bridge.subby.cloud")
        self.assertNotIn("X-Bridge-API-Key", response_payload)
        self.assertNotIn("super-secret-key", body)

    def test_urllib_sender_uses_post_json_bytes_and_configured_timeout(self) -> None:
        capture: dict[str, Any] = {}

        class FakeResponse:
            status = 202

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
                _ = (exc_type, exc, tb)
                return False

            def read(self) -> bytes:
                return b'{"accepted":true}'

        def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
            capture["request"] = request
            capture["timeout"] = timeout
            return FakeResponse()

        sender = UrllibSubbyBridgeEventSender(timeout_seconds=4.0)
        with patch("picwise_integrations.subby_dashboard.urlopen", side_effect=fake_urlopen):
            status_code, response_payload = sender.send(
                endpoint="https://manager.subby.cloud/api/bridge/ingest",
                headers={
                    "X-Bridge-Project-ID": "picwise-prod",
                    "X-Bridge-API-Key": "secret-live-key-value",
                    "Content-Type": "application/json",
                },
                payload={"foo": "bar"},
            )

        request = capture["request"]
        self.assertEqual(capture["timeout"], 4.0)
        self.assertEqual(request.get_method(), "POST")
        self.assertIsInstance(request.data, bytes)
        self.assertEqual(request.data, b'{"foo":"bar"}')
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(status_code, 202)
        self.assertEqual(response_payload["accepted"], True)


class DeploymentConfigAndDocsTests(unittest.TestCase):
    def test_deployment_configs_contain_no_secrets(self) -> None:
        vercel_config = (ROOT / "vercel.json").read_text(encoding="utf-8")
        env_template = (ROOT / "deployment" / "app.env.template").read_text(encoding="utf-8")
        wsgi_template = (ROOT / "deployment" / "wsgi_server.template.ini").read_text(encoding="utf-8")

        for forbidden in ("AKIA", "-----BEGIN", "PRIVATE KEY", "SECRET=", "token "):
            self.assertNotIn(forbidden, vercel_config)
            self.assertNotIn(forbidden, env_template)
            self.assertNotIn(forbidden, wsgi_template)

    def test_stage_22_doc_does_not_claim_live_proof(self) -> None:
        stage_doc = (
            ROOT / "docs" / "STAGE_22_LIVE_DEPLOYMENT_TO_PICWISE_SUBBY_CLOUD.md"
        ).read_text(encoding="utf-8")
        self.assertIn("# 22. Live deployment to picwise.subby.cloud", stage_doc)
        self.assertIn("Current stage status in this repository is `PASSED`", stage_doc)
        self.assertIn("- [x] `https://picwise.subby.cloud/health` works", stage_doc)
        self.assertIn("- [x] `https://picwise.subby.cloud/demo` works", stage_doc)


if __name__ == "__main__":
    unittest.main()

