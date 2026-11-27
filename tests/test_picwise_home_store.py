"""The home page as a store (`docs/PICWISE_HOME_STORE_SPEC.md`; task H3).

The owner, 2026-11-23, of the fifth picture of a home page that reads as a store:
«Κράτα αυτό και ανέβασε το»; then «Όλα μαζί», «Με χρυσοκίτρινο banner», «Στα προϊόντα της
στο PicWise», and «Ναι σε όλα» ("See" on step 2, not "Compare"). Pinned here:

- behind its switch: off (as built), `/` is the home page of 2026-11-12, byte for byte;
  only `true` turns it on;
- on, the page of the specification's section 5: its words, its head as today's home page's,
  nothing declared to Google, every link inside the site, none to a shop, none to a part of
  section 7 not built yet; each section left out when its data is not known;
- the phone's rules: no word under 12 px, whatever is tapped 48 px, 8 px apart; one family
  of colours, no red, orange or green;
- what it knows of the catalogue (`home_store_facts`): each kind's Recommended exactly as its
  search's first card shows it, the tiles whose search has products, the shops; shown only
  beside the catalogue it was worked out for.

Every row of a feed here is fictional, served with `.invalid` addresses.
"""
from __future__ import annotations

import colorsys
import html
import io
import json
import os
import re
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import test_picwise_price_first as price_first  # noqa: E402
from api.index import app as wsgi_app  # noqa: E402
from picwise_providers.state import peek_search_catalogue_counts  # noqa: E402
from picwise_search.live_search_resolver import empty_landing_search_resolution  # noqa: E402
from picwise_surface import home_store, home_store_facts  # noqa: E402
from picwise_surface.home_store import (  # noqa: E402
    HOME_STORE_STYLES,
    HomeFacts,
    HomeLists,
    Kind,
    OfferCard,
    Pick,
    Section,
    Tile,
    load_home_lists,
    render_home_store_page,
)
from picwise_surface.reference import render_picwise_reference_surface  # noqa: E402
from picwise_surface.trends import TrendRow, TrendsPanel, load_trends_panel  # noqa: E402

ALL_PARTS = frozenset({"departments", "offers", "pages"})
_PART_PATHS = {
    "departments": ("/departments", "/department/"),
    "offers": ("/offers",),
    "pages": ("/how-picwise-works", "/how-we-choose", "/our-checks", "/our-shops"),
}
# The addresses of the parts not built yet: never a link (the specification, section 6).
_NOT_BUILT = tuple(path for part, paths in _PART_PATHS.items() if part not in home_store.PARTS_BUILT for path in paths)


def _get(path: str, query: str = "") -> str:
    def start_response(_status: str, _headers: list[tuple[str, str]]) -> None:
        return None

    return b"".join(
        wsgi_app(
            {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": path,
                "QUERY_STRING": query,
                "wsgi.input": io.BytesIO(b""),
                "wsgi.url_scheme": "https",
            },
            start_response,
        )
    ).decode("utf-8")


def _markup(page: str) -> str:
    """The page without its scripts and styles: what a visitor's eye and taps meet."""
    page = re.sub(r"<script\b.*?</script>", "", page, flags=re.S)
    return re.sub(r"<style\b.*?</style>", "", page, flags=re.S)


def _visible_text(page: str) -> str:
    body = _markup(page).split("<body", 1)[1]
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


def _links(page: str) -> list[str]:
    return [html.unescape(href) for href in re.findall(r'<a\b[^>]*\bhref="([^"]*)"', _markup(page))]


def _offers(count: int) -> tuple[OfferCard, ...]:
    return tuple(
        OfferCard(
            shop=f"Fixture Store {index}",
            offer_id=f"fx-{index}",
            title=("10% off kettles", "Free second kettle lid")[index - 1],
            end=datetime(datetime.now(timezone.utc).year, 11, 30, tzinfo=timezone.utc),
            products=10 - index,
        )
        for index in range(1, count + 1)
    )


def _picks(count: int) -> tuple[Pick, ...]:
    return tuple(
        Pick(
            query=query,
            kind=kind,
            link=f"See {query}s",
            title=f"Fixturon {kind} {index}",
            price=f"£{100 + index}.95",
            shop="Fixture Store One",
            image=f"https://fixture.example.invalid/img/{index}.jpg",
        )
        for index, (query, kind) in enumerate(
            [("drill", "Drill"), ("air fryer", "Air fryer"), ("printer", "Printer")][:count], start=1
        )
    )


class _Switch:
    def _switch(self, value: bool | None) -> None:
        home_store.set_home_store_on_for_tests(value)
        self.addCleanup(home_store.set_home_store_on_for_tests, None)


class TheSwitchTests(_Switch, unittest.TestCase):
    def test_the_switch_is_on_on_the_owners_word_and_the_strip_stays_off(self) -> None:
        # Owner, 2026-11-24 (10:40 Athens), told that every part is built and what the look
        # on the server's data found (the specification's 9.1): «Ανέβασε το όλο έχουμε άλλα
        # πράγματα να κάνουμε». The phone strip is not part of it: off by its own line until
        # the proof of 7.5.
        payload = json.loads((ROOT / "data" / "home_store_switch.json").read_text(encoding="utf-8"))
        self.assertIs(payload["on"], True)
        self.assertEqual(payload["set"], "2026-11-24")
        self.assertIn("«Ανέβασε το όλο", payload["by"])
        self.assertIs(payload["strip"], False)
        self.assertTrue(home_store.home_store_on())
        self.assertFalse(home_store.strip_shown())

    def test_only_true_turns_it_on(self) -> None:
        folder = Path(tempfile.mkdtemp())
        saved = os.environ.get(home_store.SWITCH_ENV)
        self.addCleanup(
            lambda: os.environ.pop(home_store.SWITCH_ENV, None)
            if saved is None
            else os.environ.__setitem__(home_store.SWITCH_ENV, saved)
        )
        for index, (text, expected) in enumerate(
            (('{"on": true}', True), ('{"on": "true"}', False), ('{"on": 1}', False), ("not json", False))
        ):
            path = folder / f"switch-{index}.json"
            path.write_text(text, encoding="utf-8")
            os.environ[home_store.SWITCH_ENV] = str(path)
            self.assertIs(home_store.home_store_on(), expected, text)
        os.environ[home_store.SWITCH_ENV] = str(folder / "missing.json")
        self.assertFalse(home_store.home_store_on())

    def test_off_the_home_page_is_the_one_of_12_november_byte_for_byte(self) -> None:
        self._switch(False)
        expected = render_picwise_reference_surface(
            query="",
            resolution=empty_landing_search_resolution(""),
            source_page="search",
            catalogue=peek_search_catalogue_counts(),
            indexable=True,
            single_product_code="",
            assist=None,
        )
        self.assertEqual(_get("/"), expected)
        self.assertIn("Find the product you want in UK shops", expected)
        self.assertNotIn("pw-hs", expected)
        self.assertNotIn("Arrive confused", expected)

    def test_on_the_home_page_is_the_store(self) -> None:
        self._switch(True)
        page = _get("/")
        # The owner's own heading (2026-11-24).
        self.assertIn('<h1 class="pw-hs-h1" id="pw-hs-h1">Arrive confused.<br>Leave decided.</h1>', page)
        self.assertNotIn('class="pw-hero-title"', _markup(page))
        # A search is not the home page: its own page, under the store's header (7.4).
        search = _markup(_get("/search", "q=kettle"))
        self.assertNotIn('class="pw-hs-h1"', search)
        self.assertNotIn("Arrive confused", search)


class ThePageTests(_Switch, unittest.TestCase):
    def setUp(self) -> None:
        self._switch(True)
        self.page = _get("/")

    def test_its_head_is_todays_home_pages(self) -> None:
        old = render_picwise_reference_surface(
            query="", resolution=empty_landing_search_resolution(""), catalogue=None, indexable=True
        )
        head, old_head = self.page.split("<style>")[0], old.split("<style>")[0]
        self.assertEqual(head, old_head)
        self.assertIn('<link rel="canonical" href="https://picwise.subby.cloud/">', head)
        self.assertNotIn('name="robots"', head)
        self.assertNotIn("application/ld+json", self.page)
        # The site's own search without words is the same page, kept out of Google.
        self.assertIn('<meta name="robots" content="noindex">', _get("/search", "q="))
        self.assertIn("pw-hs-h1", _get("/search", "q="))

    def test_its_words(self) -> None:
        text = " ".join(_visible_text(self.page).split())
        for words in (
            "HOW PICWISE WORKS",
            "1 Search Type what you need 2 See 4 choices, cheapest first 3 Decide One is Recommended",
            "THE PICWISE PROMISE",
            "What you can count on",
            # The owner's texts, word for word (2026-11-24).
            "30-Day Price History Zero Cookies & Tracking",
            "4 honest choices, zero paid rankings: Commissions never change the order of results or our \u201cRecommended\u201d pick.",
            "Real price history: Check the last 30 nights at a glance. No fake discounts, no \u201churry up\u201d tricks.",
            "100% Private (No Cookies): No pop-ups, no accounts. Your favourites and search history stay on your own "
            "device\u2014we never see them.",
            "No Cookie Policy \u2014 because we don't use any.",
            "BACK TO TOP",
            "United Kingdom · Prices in £",
            "PicWise earns a commission from some shops, through Awin",
            "© 2026 PicWise. All rights reserved.",
        ):
            self.assertIn(words, text)
        # Never presented as price comparison (owner, 12/11 and 23/11).
        self.assertNotRegex(text.lower(), r"compar")

    def test_every_link_stays_inside_the_site_and_none_leads_where_nothing_is_built(self) -> None:
        links = _links(self.page)
        self.assertTrue(links)
        for href in links:
            self.assertTrue(href.startswith(("/", "#")), href)
            self.assertFalse(href.startswith("/out/"), href)
            self.assertFalse(href.startswith(_NOT_BUILT), href)
        for tag in re.findall(r"<(?:img|script|iframe)\b[^>]*>", _markup(self.page)):
            self.assertNotRegex(tag, r'src="(?:https?:)?//', tag)
        # The site's own footer pages answer.
        for href in ("/about", "/contact", "/terms", "/privacy", "/affiliate-disclosure"):
            self.assertIn(href, links)
        # No "Cookies" link: the owner's line in its place (2026-11-24); the page itself
        # stays, and opens from the Privacy page.
        self.assertNotIn("/cookies", links)
        self.assertIn("/cookies", _links(_get("/privacy")))
        self.assertIn("PicWise sets no cookies", _get("/cookies"))

    def test_the_shops_tick_is_never_false(self) -> None:
        self.assertEqual(home_store.trust_shops_line((118048, 109)), "100+ UK Shops")
        self.assertEqual(home_store.trust_shops_line((90000, 101)), "100+ UK Shops")
        self.assertEqual(home_store.trust_shops_line((90000, 100)), "100 UK Shops")
        self.assertEqual(home_store.trust_shops_line((90000, 98)), "98 UK Shops")
        self.assertEqual(home_store.trust_shops_line(None), "")
        page = _markup(render_home_store_page(catalogue=None, indexable=True, trends=None))
        self.assertNotIn("UK Shops", page)
        self.assertIn("Zero Cookies &amp; Tracking", page)

    def test_the_search_box_is_every_page_s(self) -> None:
        old = render_picwise_reference_surface(query="", resolution=empty_landing_search_resolution(""))
        box = re.search(r'<section class="pw-search-wrap".*?</section>', old, flags=re.S).group(0)
        self.assertIn(box, self.page)
        self.assertEqual(box, home_store.search_box_html())
        for name in ('id="pw-history-button"', 'id="pw-favourites-button"', 'id="pw-info-button"', 'id="pw-scan"'):
            self.assertIn(name, self.page)

    def test_the_phone_strip_waits_for_its_own_line(self) -> None:
        # Not drawn until the proof of 7.5 exists and the owner turns its line on.
        self.assertFalse(home_store.strip_shown())
        self.assertNotIn("pw-hs-strip", _markup(self.page))
        home_store.set_strip_shown_for_tests(True)
        self.addCleanup(home_store.set_strip_shown_for_tests, None)
        page = _get("/")
        # Drawn hidden: its script shows it on a phone only, never in the installed app,
        # never once its "×" was pressed on this device.
        self.assertIn('<div class="pw-hs-strip" id="pw-hs-strip" hidden>', page)
        self.assertIn('<div class="pw-hs-sheet" id="pw-hs-sheet" role="dialog"', page)
        text = re.sub(r" ([.,])", r"\1", " ".join(_visible_text(page).split()))
        self.assertIn("Add PicWise to your home screen 1 Tap the Share button in your browser's bar. "
                      "2 Choose Add to Home Screen. 3 Tap Add. Got it", text)
        self.assertIn("(display-mode: standalone)", page)
        self.assertIn('"picwise.strip.closed"', page)
        self.assertIn("beforeinstallprompt", page)
        # Its line on the Cookies and Privacy pages, and only while it is shown.
        line = "PicWise remembers on this device that you closed"
        for path in ("/cookies", "/privacy"):
            self.assertIn(line, _get(path), path)
        self.assertNotIn(line, _get("/terms"))
        home_store.set_strip_shown_for_tests(None)
        self.assertNotIn(line, _get("/cookies"))
        # Never while the store is off.
        self._switch(False)
        home_store.set_strip_shown_for_tests(True)
        self.assertFalse(home_store.strip_shown())

    def test_every_drawing_is_a_file_of_the_site_with_its_size(self) -> None:
        images = re.findall(r"<img\b[^>]*>", _markup(self.page))
        self.assertTrue(images)
        for tag in images:
            self.assertRegex(tag, r'width="\d+"', tag)
            self.assertRegex(tag, r'height="\d+"', tag)
            source = re.search(r'src="([^"]+)"', tag).group(1)
            self.assertTrue(source.startswith(("/assets/home/art/", "/assets/home/ov/")), source)
            self.assertTrue((ROOT / source.lstrip("/")).is_file(), source)

    def test_the_lists_name_only_drawings_that_exist(self) -> None:
        lists = load_home_lists()
        names = {kind.drawing for kind in lists.recommended}
        names |= {tile.drawing for section in lists.sections for tile in section.tiles}
        names |= {item.drawing for item in lists.departments}
        names |= set(lists.popular_drawings.values())
        names |= {name for banner in lists.banners for name, _ground in banner.drawings}
        names |= {kind.drawing for banner in lists.banners for kind in banner.kinds}
        for name in names:
            self.assertTrue((ROOT / "assets" / "home" / "art" / f"{name}.svg").is_file(), name)
        # Fourteen sections from 2026-11-27 (six until then; `test_picwise_home_more_kinds`);
        # a grid keeps four tiles, a row that slides holds four or more.
        self.assertEqual(len(lists.sections), 14)
        self.assertTrue(all(len(section.tiles) == 4 for section in lists.sections if section.layout == "grid"))
        self.assertTrue(all(len(section.tiles) >= 4 for section in lists.sections if section.layout == "row"))
        self.assertEqual(len(lists.departments), 13)
        # A tile searches the kind itself: "watch", not "watches" (read on the site, 23/11).
        queries = {tile.query for section in lists.sections for tile in section.tiles}
        self.assertTrue({"watch", "boots", "air purifier"} <= queries)
        self.assertFalse({"watches", "boot", "air purifiers"} & queries)


class TheSectionsTests(unittest.TestCase):
    def _page(self, **kwargs) -> str:
        kwargs.setdefault("catalogue", (118048, 109))
        kwargs.setdefault("indexable", True)
        kwargs.setdefault("trends", load_trends_panel())
        # The markup alone: the styles name every class whether drawn or not.
        return _markup(render_home_store_page(**kwargs))

    def test_while_nothing_of_section_7_is_built_its_entries_are_not_drawn(self) -> None:
        page = self._page(parts=frozenset())
        for name in ("pw-hs-banners", "pw-hs-nav", "pw-hs-depts", "pw-hs-arrow"):
            self.assertNotIn(f'class="{name}', page, name)
        self.assertNotIn("How PicWise works ›", page)

    def test_built_every_entry_is_drawn_and_leads_to_its_part(self) -> None:
        page = self._page(parts=ALL_PARTS, facts=HomeFacts(prepared_at=None, offers=_offers(2)))
        links = _links(page)
        self.assertIn("/offers", links)
        self.assertIn("/department/computers", links)
        self.assertIn("/department/tools", links)
        self.assertIn("/departments", links)
        for href in ("/how-picwise-works", "/how-we-choose", "/our-checks", "/our-shops"):
            self.assertIn(href, links)
        # Banner 2 to the first group of all departments (owner, 2026-11-24, 7.1).
        self.assertIn('href="/departments#home-kitchen"', page)
        self.assertIn("Browse home", page)
        # Four for a computer, as on 24/11; seven for a phone (`test_picwise_home_more_kinds`).
        banners = re.findall(r'class="pw-hs-banner pw-hs-banner-\w+( pw-hs-phone| pw-hs-pc)?"', page)
        self.assertEqual(len(banners) - banners.count(" pw-hs-phone"), 4)
        self.assertEqual(len(banners) - banners.count(" pw-hs-pc"), 7)
        # A department of one kind leads to that kind's search (7.1).
        self.assertIn("/search?q=lamp", links)
        self.assertNotIn("/department/lighting", links)
        self.assertNotIn("/department/perfume", links)
        self.assertIn('class="pw-hs-banner pw-hs-banner-gold" href="/offers"', page)
        self.assertEqual(page.count('class="pw-hs-dept"'), 13)

    def test_the_offers_banner_needs_an_offer_to_show(self) -> None:
        page = self._page(parts=ALL_PARTS)
        self.assertNotIn("pw-hs-banner-gold", page)
        self.assertNotIn("pw-hs-offers", page)
        # A computer's blue banner ("Laptops, printers & routers", as on 24/11).
        self.assertIn('class="pw-hs-banner pw-hs-banner-blue pw-hs-pc"', page)

    def test_the_offers_row_in_the_shops_own_words(self) -> None:
        facts = HomeFacts(prepared_at=None, offers=_offers(2))
        # Not drawn while Part C is not built.
        self.assertNotIn("pw-hs-offer", self._page(facts=facts, parts=frozenset({"departments", "pages"})))
        page = self._page(facts=facts, parts=ALL_PARTS)
        self.assertIn("Offers from the shops", page)
        self.assertIn("In the shops&#x27; own words. Never a made-up discount.", page)
        self.assertEqual(page.count('class="pw-hs-offer"'), 2)
        self.assertIn('<a class="pw-hs-offer" href="/offers/fx-1">', page)
        self.assertIn('<span class="pw-hs-offer-title">10% off kettles</span>', page)
        self.assertIn('<span class="pw-hs-offer-end">Ends 30 Nov</span>', page)
        self.assertNotRegex(_visible_text(page), r"£\d")

    def test_a_tile_whose_search_has_nothing_is_not_drawn(self) -> None:
        everything = {tile.query for section in load_home_lists().sections for tile in section.tiles}
        page = self._page()
        tiles = sum(len(section.tiles) for section in load_home_lists().sections)
        drawn = lambda text: len(re.findall(r'class="pw-hs-tile( pw-hs-phone)?"', text))  # noqa: E731
        self.assertEqual(drawn(page), tiles)
        facts = HomeFacts(prepared_at=None, tiles_with_products=frozenset(everything - {"kettle", "ring", "necklace", "earrings"}))
        page = self._page(facts=facts)
        self.assertNotIn('href="/search?q=kettle"', page)
        self.assertIn('href="/search?q=microwave"', page)
        # "Jewellery" keeps only "Bracelets": fewer than two tiles, the section is left out.
        self.assertNotIn(">Jewellery</h2>", page)
        self.assertEqual(drawn(page), tiles - 5)

    def test_the_month_s_ten_as_tiles(self) -> None:
        page = self._page()
        self.assertIn("Most popular in the UK", page)
        self.assertIn('<p class="pw-hs-eyebrow">November 2026 · United Kingdom</p>', page)
        self.assertEqual(page.count('class="pw-hs-pop-item"'), 10)
        self.assertIn('data-more="Show all 10"', page)
        self.assertIn("Ranking: Google Ads Keyword Planner", page)
        # Each of the ten has its drawing (mattress and hoodie since 2026-11-24).
        tile = r'<a class="pw-hs-pop-tile" href="/search\?q=%s">(.*?)</a>'
        for kind in ("mattress", "hoodie"):
            self.assertIn(f'src="/assets/home/art/{kind}.svg"', re.search(tile % kind, page, flags=re.S).group(1))
            self.assertTrue((ROOT / "assets" / "home" / "art" / f"{kind}.svg").is_file())
        # A kind the lists give no drawing keeps its tile, with none.
        lists = load_home_lists()
        without = replace(lists, popular_drawings={k: v for k, v in lists.popular_drawings.items() if k != "mattress"})
        mattress = re.search(tile % "mattress", self._page(lists=without), flags=re.S)
        self.assertNotIn("<img class=\"pw-hs-art\"", mattress.group(1))
        panel = TrendsPanel(
            period="November 2026",
            country="United Kingdom",
            ranking_source="Fixture ranking",
            rows=(
                TrendRow(rank=1, name="Boots", category="", search_query="boots", offers=12, from_price="£9.99"),
                TrendRow(rank=2, name="Snowshoes", category="", search_query="snowshoes", offers=0),
            ),
        )
        page = self._page(trends=panel)
        self.assertIn("12 products from £9.99", page)
        self.assertIn("Not in our shops yet", page)
        self.assertNotIn('href="/search?q=snowshoes"', page)
        self.assertNotIn('id="pw-tp-more"', page)
        self.assertEqual(self._page(trends=None).count("pw-hs-pop"), 0)

    def test_the_recommended_band(self) -> None:
        self.assertNotIn("pw-hs-band", self._page())
        self.assertNotIn("pw-hs-band", self._page(facts=HomeFacts(prepared_at=None, picks=_picks(1))))
        facts = HomeFacts(prepared_at=datetime(2026, 11, 23, 4, 0, tzinfo=timezone.utc), picks=_picks(3))
        page = self._page(facts=facts, parts=ALL_PARTS)
        self.assertIn("RECOMMENDED · UPDATED 23 NOV", page)
        self.assertIn("One honest pick for each kind", page)
        self.assertIn("The middle price of each kind. The commission never decides it.", page)
        self.assertEqual(page.count('class="pw-hs-pick"'), 3)
        self.assertEqual(page.count("Mid-priced for this category"), 3)
        self.assertIn('<a class="pw-hs-pick" href="/search?q=air%20fryer">', page)
        self.assertIn("£102.95", page)
        self.assertIn("at Fixture Store One", page)
        self.assertIn('href="/how-we-choose"', page)
        self.assertIn('src="https://fixture.example.invalid/img/1.jpg"', page)

    def test_the_promise_and_the_shops(self) -> None:
        page = self._page()
        self.assertIn('<span class="pw-hs-fig-big">110,000+</span><span class="pw-hs-fig-small">products</span>', page)
        self.assertIn('<span class="pw-hs-fig-big">109</span><span class="pw-hs-fig-small">UK shops</span>', page)
        unknown = self._page(catalogue=None)
        self.assertNotIn("UK shops</span>", unknown)
        self.assertIn('<span class="pw-hs-fig-big">Nightly</span>', unknown)
        self.assertNotIn("pw-hs-shops", page)
        facts = HomeFacts(prepared_at=None, shops=("Tooled Up", "Geepas"), shop_count=109)
        page = self._page(facts=facts)
        self.assertIn("Some of our 109 UK shops", page)
        self.assertIn('<li class="pw-hs-chip">Tooled Up</li>', page)


class ThePhonesRulesTests(unittest.TestCase):
    def test_no_word_under_12_px(self) -> None:
        sizes = [float(size) for size in re.findall(r"font-size:([\d.]+)px", HOME_STORE_STYLES)]
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 12.0)

    def test_whatever_is_tapped_is_48_px_and_8_px_apart(self) -> None:
        def rule(selector: str) -> str:
            match = re.search(re.escape(selector) + r"\{([^}]*)\}", HOME_STORE_STYLES)
            self.assertIsNotNone(match, selector)
            return match.group(1)

        for selector in (".pw-hs-strip-close", ".pw-hs .pw-mic-button", ".pw-hs .pw-search-button", ".pw-hs-arrow"):
            self.assertIn("width:48px", rule(selector), selector)
            self.assertIn("height:48px", rule(selector), selector)
        self.assertIn("width:48px;height:48px", rule(".pw-hs .pw-head-btn,.pw-hs .pw-info-link"))
        for selector in (".pw-hs-strip-add", ".pw-hs-nav a", ".pw-hs-more"):
            self.assertIn("height:48px", rule(selector), selector)
        for selector in (".pw-hs-link", ".pw-hs-foot-link", ".pw-hs-brand"):
            self.assertIn("min-height:48px", rule(selector), selector)
        self.assertIn("height:52px", rule(".pw-hs-back"))
        for selector in (".pw-hs-nav", ".pw-hs-foot-col", ".pw-hs-actions", ".pw-hs-chips"):
            self.assertIn("gap:8px", rule(selector), selector)

    def test_on_a_computer_the_same_page_inside_the_site_s_width(self) -> None:
        computer = HOME_STORE_STYLES.split("@media (min-width:700px){", 1)[1]
        self.assertIn(".pw-hs-strip{display:none!important;}", computer)
        self.assertIn(".pw-hs-main{width:100%;max-width:1190px;", computer)
        self.assertIn(".pw-hs-head-in{max-width:1190px;", computer)
        self.assertIn(".pw-hs-foot-in{max-width:1190px;", computer)
        wide = HOME_STORE_STYLES.split("@media (min-width:1000px){", 1)[1]
        self.assertIn(".pw-js .pw-hs-dots{display:none!important;}", wide)
        self.assertIn(".pw-hs-secs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));", wide)
        # The phone's rules come first and are the page's own: none of them in a block.
        self.assertLess(HOME_STORE_STYLES.index(".pw-hs-strip{"), HOME_STORE_STYLES.index("@media (min-width:700px)"))

    def test_one_family_of_colours(self) -> None:
        # Owner, 2026-11-23: «γίνεσαι παιδική χαρά». Blues, a gold and its tints, greys.
        for colour in set(re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", HOME_STORE_STYLES)):
            full = colour if len(colour) == 6 else "".join(char * 2 for char in colour)
            red, green, blue = (int(full[index : index + 2], 16) / 255 for index in (0, 2, 4))
            hue, _light, saturation = colorsys.rgb_to_hls(red, green, blue)
            if saturation < 0.25 or max(red, green, blue) - min(red, green, blue) < 0.12:
                continue
            degrees = hue * 360
            self.assertTrue(36 <= degrees <= 50 or 200 <= degrees <= 230, f"#{colour}: {degrees:.0f}°")


class TheFactsTests(price_first._PageMixin, unittest.TestCase):
    """What the page knows of the catalogue: the search's own answers, nothing else."""

    LISTS = HomeLists(
        banners=(),
        recommended=(Kind(query="kettle", kind="Kettle", link="See kettles", drawing="kettle"),),
        sections=(
            Section(
                title="Kitchen favourites",
                arrow="See all kitchen",
                department="kitchen",
                layout="grid",
                tiles=(
                    Tile(name="Kettles", query="kettle", drawing="kettle"),
                    Tile(name="Snowshoes", query="snowshoes", drawing=""),
                ),
            ),
        ),
        departments=(),
        popular_drawings={},
    )

    def setUp(self) -> None:
        self.addCleanup(home_store_facts.set_home_facts_for_tests, None)

    def test_a_kind_s_card_is_its_search_s_recommended(self) -> None:
        self._serve(self._kettles([20, 30, 40, 50, 60, 70, 80, 90, 100]))
        facts = home_store_facts.work_out_home_facts(lists=self.LISTS, products=(), prepared_at=None)
        self.assertEqual(len(facts.picks), 1)
        pick = facts.picks[0]
        page = self._page("kettle")
        card = re.search(r'<article class="pw-card pw-card-recommended"[^>]*>(.*?)</article>', page, flags=re.S).group(1)
        self.assertIn(html.escape(pick.title), card)
        self.assertIn(html.escape(pick.price), card)
        self.assertEqual(pick.title, "Fixturon Electric Kettle 5 1.7L")
        self.assertEqual(pick.price, "£60.00")
        self.assertEqual(pick.shop, "Fixture Store One")
        self.assertEqual(pick.image, "https://fixture.example.invalid/img/k5.jpg")
        self.assertEqual(facts.tiles_with_products, frozenset({"kettle"}))

    def test_a_kind_with_no_recommended_has_no_card(self) -> None:
        # Without a barcode PicWise recommends none (owner, 2026-10-16).
        self._serve(self._kettles([20, 30, 40, 50, 60], codes=False))
        facts = home_store_facts.work_out_home_facts(lists=self.LISTS, products=(), prepared_at=None)
        self.assertEqual(facts.picks, ())
        self.assertEqual(facts.tiles_with_products, frozenset({"kettle"}))

    def test_a_kind_of_one_product_is_on_no_tile(self) -> None:
        # Owner, 2026-11-27: «αν μία κατηγορία έχει λιγότερο από δύο προϊόντα να κρύβεται
        # αυτόματα από τα banners όχι από το site».
        self._serve(self._kettles([20]))
        facts = home_store_facts.work_out_home_facts(lists=self.LISTS, products=(), prepared_at=None)
        self.assertEqual(facts.tiles_with_products, frozenset())
        # Not from the site: its search still shows it.
        self.assertIn("Fixturon Electric Kettle 1 1.7L", self._page("kettle"))
        self._serve(self._kettles([20, 30]))
        facts = home_store_facts.work_out_home_facts(lists=self.LISTS, products=(), prepared_at=None)
        self.assertEqual(facts.tiles_with_products, frozenset({"kettle"}))

    def test_a_search_that_fails_leaves_its_card_and_tile_out(self) -> None:
        def broken(_query: str):
            raise RuntimeError("fixture")

        facts = home_store_facts.work_out_home_facts(lists=self.LISTS, search=broken, products=(), prepared_at=None)
        self.assertEqual(facts.picks, ())
        self.assertEqual(facts.tiles_with_products, frozenset())

    def test_the_shops_by_how_many_products_never_by_anything_else(self) -> None:
        def product(shop: str):
            return SimpleNamespace(raw={"merchant_name": shop})

        products = (
            [product("Geepas Partner Program")] * 3
            + [product("Tooled Up")] * 5
            + [product("Aosom UK")] * 3
            + [product("tooled up")]
            + [product("")]
        )
        shops, count = home_store_facts.top_shops(products, count=2)
        self.assertEqual(shops, ("Tooled Up", "Aosom UK"))
        self.assertEqual(count, 3)

    def test_the_offers_row_one_a_shop_by_how_many_products_it_covers(self) -> None:
        from picwise_providers import product_offers

        product_offers.set_offers_document(
            {
                "shops": {
                    "11": {
                        "name": "Fixture Store One Partner Program",
                        "joined": True,
                        "offers": [
                            {"id": "a1", "type": "promotion", "title": "10% off kettles", "end": "2026-11-30T23:59:00Z"},
                            {"id": "a2", "type": "promotion", "title": "15% off everything", "end": "2026-11-28T23:59:00Z"},
                        ],
                    },
                    "22": {
                        "name": "Fixture Lamps",
                        "joined": False,
                        "offers": [
                            {"id": "b1", "type": "promotion", "title": "20% off sitewide", "end": "2026-12-05T00:00:00Z"}
                        ],
                    },
                    # A voucher without its code covers no product (`product_offers`).
                    "33": {
                        "name": "Fixture Other",
                        "offers": [
                            {"id": "c1", "type": "voucher", "title": "10% off everything", "end": "2026-12-05T00:00:00Z"}
                        ],
                    },
                }
            }
        )
        self.addCleanup(product_offers.set_offers_document, None)

        def product(shop: str, title: str):
            return SimpleNamespace(title=title, raw={"merchant_id": shop})

        products = (
            [product("11", f"Fixturon Electric Kettle {index}") for index in range(3)]
            + [product("11", "Fixturon Desk Lamp")]
            + [product("22", f"Fixturon Floor Lamp {index}") for index in range(2)]
            + [product("33", f"Fixturon Thing {index}") for index in range(5)]
        )
        now = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
        cards = home_store_facts.shop_offers(products, now=now)
        self.assertEqual([(card.shop, card.offer_id, card.products) for card in cards], [
            ("Fixture Store One", "a1", 3),
            ("Fixture Lamps", "b1", 2),
        ])
        self.assertEqual(cards[0].title, "10% off kettles")
        self.assertEqual(home_store_facts.shop_offers(products, now=now, count=1)[0].offer_id, "a1")
        # Ended, an offer is no one's.
        self.assertEqual(home_store_facts.shop_offers(products, now=datetime(2026, 12, 6, tzinfo=timezone.utc)), ())

    def test_facts_are_shown_only_beside_their_own_catalogue(self) -> None:
        facts = HomeFacts(prepared_at=None, picks=_picks(2))
        home_store_facts.set_home_facts_for_tests(facts)
        self.assertIs(home_store_facts.current_home_facts(), facts)
        home_store_facts.set_home_facts_for_tests(
            HomeFacts(prepared_at=datetime(2026, 11, 22, tzinfo=timezone.utc), picks=_picks(2))
        )
        self.assertIsNone(home_store_facts.current_home_facts())

    def test_the_watcher_starts_once_and_does_nothing_while_the_switch_is_off(self) -> None:
        home_store.set_home_store_on_for_tests(False)
        self.addCleanup(home_store.set_home_store_on_for_tests, None)
        saved = dict(home_store_facts._WATCHER)
        home_store_facts._WATCHER.clear()
        self.addCleanup(lambda: (home_store_facts._WATCHER.clear(), home_store_facts._WATCHER.update(saved)))
        stop = home_store_facts.keep_home_facts_current(every_seconds=0.01)
        self.assertIsNotNone(stop)
        self.addCleanup(stop.set)
        self.assertIsNone(home_store_facts.keep_home_facts_current(every_seconds=0.01))
        stop.wait(0.05)
        self.assertIsNone(home_store_facts._STATE["facts"])


if __name__ == "__main__":
    unittest.main()
