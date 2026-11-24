"""The home page as a store, live: the guarantees today's page held, on the store's pages.

Since the owner's «ανέβασε» of 2026-11-24 (10:40 Athens) the store's switch is on
(`data/home_store_switch.json`, docs/PICWISE_HOME_STORE_SPEC.md 3.1 and 9.1). The tests that
pin today's page of 2026-11-12 (the design of 2026-10-31, the app's stages 16 to 21, stage
35, performance 1A, Google's basics) hold the switch off, since that page is the way back;
these pin what they guarded on the pages a visitor now sees: the footer's links and notice,
the search box, History and Favourites only where they work, no search run for a page
without one, the home page's own title, and nothing of Amazon, logins or fakes.
"""

from __future__ import annotations

import io
import re
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from picwise_app import PicwiseLocalApp  # noqa: E402
from picwise_search import search_warmup  # noqa: E402
from picwise_surface import home_store  # noqa: E402
from picwise_surface.browser_lists import HEAD_SCRIPT  # noqa: E402
from picwise_surface.legal import SHORT_AFFILIATE_NOTICE  # noqa: E402

HOME_TITLE = "PicWise — Find the product you want in UK shops"
# Every page a visitor reaches with the switch on, and the store's footer on each.
PAGES = (
    ("/", {}),
    ("/search", {"q": "   "}),
    ("/search", {"q": "power bank"}),
    ("/results", {"q": "power bank"}),
    ("/picwise-reference", {}),
    ("/about", {}),
    ("/contact", {}),
    ("/terms", {}),
    ("/privacy", {}),
    ("/cookies", {}),
    ("/affiliate-disclosure", {}),
)
FOOTER_LINKS = (
    ("/about", "About PicWise"),
    ("/how-picwise-works", "How PicWise works"),
    ("/how-we-choose", "How we choose the Recommended"),
    ("/our-checks", "Our checks"),
    ("/our-shops", "Our shops"),
    ("/contact", "Contact"),
    ("/terms", "Terms"),
    ("/privacy", "Privacy"),
    ("/affiliate-disclosure", "Affiliate disclosure"),
)


def _call(path: str, params: dict[str, str] | None = None) -> tuple[str, str]:
    answer: dict[str, str] = {}

    def start_response(status: str, _headers: list[tuple[str, str]]) -> None:
        answer["status"] = status

    body = b"".join(
        wsgi_app(
            {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": path,
                "QUERY_STRING": urlencode(params or {}),
                "wsgi.input": io.BytesIO(b""),
                "wsgi.url_scheme": "https",
            },
            start_response,
        )
    ).decode("utf-8")
    return answer["status"], body


class _On:
    def setUp(self) -> None:  # noqa: D401
        search_warmup._reset_search_warmup_for_tests()
        self.addCleanup(search_warmup._reset_search_warmup_for_tests)  # type: ignore[attr-defined]
        home_store.set_home_store_on_for_tests(True)
        self.addCleanup(home_store.set_home_store_on_for_tests, None)  # type: ignore[attr-defined]


class TheSwitchIsOnInTheRepoTests(unittest.TestCase):
    def test_the_repo_serves_the_store(self) -> None:
        self.assertTrue(home_store.home_store_on())
        status, page = _call("/")
        self.assertEqual(status, "200 OK")
        self.assertIn('<body class="pw-hs-body">', page)


class EveryPageTests(_On, unittest.TestCase):
    def test_each_page_has_the_footers_links_and_notice(self) -> None:
        for path, params in PAGES:
            with self.subTest(path=path, params=params):
                status, page = _call(path, params)
                self.assertEqual(status, "200 OK")
                self.assertIn('<nav class="pw-hs-foot-cols" aria-label="PicWise public footer links">', page)
                for href, label in FOOTER_LINKS:
                    self.assertIn(f'class="pw-hs-foot-link" href="{href}">{label}<', page)
                self.assertIn(SHORT_AFFILIATE_NOTICE, page)
                # The owner's line in the place of "Cookies" (5.9); the page stays, from Privacy.
                self.assertIn("No Cookie Policy — because we don&#x27;t use any.", page)
                self.assertNotIn('class="pw-hs-foot-link" href="/demo"', page)
                self.assertNotIn('class="pw-hs-foot-link" href="/picwise-reference"', page)

    def test_each_page_has_the_search_box_and_what_picwise_is(self) -> None:
        for path, params in PAGES:
            with self.subTest(path=path, params=params):
                _status, page = _call(path, params)
                self.assertIn('action="/search"', page)
                self.assertIn('method="get"', page)
                self.assertIn('name="q"', page)
                self.assertIn('placeholder="What are you looking for?"', page)
                self.assertIn("What is PicWise?", page)
                self.assertIn('<html lang="en-GB">', page)

    def test_no_page_has_amazon_a_login_or_the_owners_address(self) -> None:
        for path, params in PAGES:
            with self.subTest(path=path, params=params):
                _status, page = _call(path, params)
                lower = page.lower()
                for word in ("search all amazon", "live amazon search", "view on amazon", "manual_amazon_affiliate"):
                    self.assertNotIn(word, lower)
                self.assertNotIn(">Login<", page)
                self.assertNotIn(">Register<", page)
                self.assertNotIn("mysubby.cloud@gmail.com", page)
                # A page of searches never speaks of a checkout (the Terms rightly do).
                if path in ("/", "/search", "/results", "/picwise-reference"):
                    self.assertNotIn("checkout", lower)
                    self.assertNotIn("fake product", lower)

    def test_the_privacy_page_still_leads_to_the_cookies_page(self) -> None:
        _status, page = _call("/privacy")
        self.assertIn('href="/cookies"', page)

    def test_the_info_pages_keep_their_address_description_and_index(self) -> None:
        for path in ("/about", "/contact", "/terms", "/privacy", "/cookies", "/affiliate-disclosure"):
            with self.subTest(path=path):
                _status, page = _call(path)
                self.assertIn("contact.picwise@subby.cloud", page)
                self.assertNotIn("contact@picwise.subby.cloud", page)
                self.assertIn('<meta name="description"', page)
                self.assertNotIn('<meta name="robots" content="noindex">', page)


class HistoryAndFavouritesTests(_On, unittest.TestCase):
    def test_they_show_only_where_javascript_and_local_storage_work(self) -> None:
        for path, params in PAGES:
            with self.subTest(path=path, params=params):
                _status, page = _call(path, params)
                self.assertLess(page.index(f"<script>{HEAD_SCRIPT}</script>"), page.index("<body"))
                self.assertIn('class="pw-head-btn pw-needs-store" id="pw-history-button"', page)
                self.assertIn('id="pw-favourites-button"', page)
                self.assertIn('id="pw-history-panel"', page)
                self.assertIn('id="pw-favourites-panel"', page)
                self.assertIn(".pw-needs-store,.pw-needs-js{display:none!important;}", page)
                self.assertIn(".pw-store .pw-head-btn.pw-needs-store{display:inline-flex!important;}", page)
                self.assertIn("Kept only in this browser; PicWise never receives it.", page)


class TheHomePageTests(_On, unittest.TestCase):
    def test_it_keeps_its_title_and_takes_the_owners_heading(self) -> None:
        _status, page = _call("/")
        self.assertIn(f"<title>{HOME_TITLE}</title>", page)
        self.assertEqual(
            re.findall(r"<h1[^>]*>(.*?)</h1>", page, flags=re.S), ["Arrive confused.<br>Leave decided."]
        )
        self.assertIn('<meta name="description" content="PicWise finds the product you want', page)
        self.assertNotIn('<meta name="robots" content="noindex">', page)
        self.assertNotIn("<article", page)

    def test_a_search_of_blanks_is_the_home_page_with_no_cards(self) -> None:
        _status, home = _call("/")
        status, page = _call("/search", {"q": "   "})
        self.assertEqual(status, "200 OK")
        self.assertEqual(re.findall(r"<h1[^>]*>(.*?)</h1>", page, flags=re.S), ["Arrive confused.<br>Leave decided."])
        self.assertNotIn("<article", page)
        for word in ("provider_not_connected", "not_understood", "fake revenue"):
            self.assertNotIn(word, page)
        self.assertGreater(len(home), 0)

    def test_the_months_ten_link_to_their_searches(self) -> None:
        _status, page = _call("/")
        self.assertIn("Most popular in the UK", page)
        self.assertIn('href="/search?q=air%20fryer"', page)

    def test_a_page_without_a_search_runs_none(self) -> None:
        app = PicwiseLocalApp()
        with mock.patch("picwise_app.app.resolve_live_search") as resolve:
            home = app.root_landing_html()
            blank = app.picwise_reference_html("  \t  ")
            _call("/")
            _call("/search", {"q": "   "})
            _call("/picwise-reference")
        resolve.assert_not_called()
        for page in (home, blank):
            self.assertIn('<body class="pw-hs-body">', page)
            self.assertIn('action="/search"', page)


if __name__ == "__main__":
    unittest.main()
