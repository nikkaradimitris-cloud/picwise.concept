"""The design of 2026-10-31, built (owner: «Υλοποίησε τα όλα»).

`docs/design/picwise_design_proposal_2026-10-31.html`. What is pinned here:

- the cards are symmetric: a square photo of a size fixed before it loads and shown
  whole, a role line, a title of at most three lines and a shop line of fixed heights,
  so the prices and the buttons of a row line up; the price reads "£12.74"; the button
  names the shop it goes to; every card states its limitation;
- one product with no other is laid out on its own, never as one small card in the
  middle (owner, 2026-10-31), with its brand and its code only when the shop gives them;
- History and Favourites take the place of Login and Register: kept in the visitor's
  browser, never sent to PicWise, shown only where JavaScript and local storage work,
  and the history kept only once the visitor asks for it;
- the month's trending searches (searches, not sales: owner, 2026-10-31) show only from
  a real source: none is connected, so the home page has no panel; on fictional rows the
  panel says only what its sources give;
- the footer has About and no longer "Demo" or "PicWise Reference"; the privacy and
  cookie pages say what the browser keeps.

Every row is written with fictional brands and `.invalid` URLs, served through
api/index.py, the deployed entry point.
"""
from __future__ import annotations

import csv
import html
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_app.app import single_product_code  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.decision_labels import (  # noqa: E402
    UNVERIFIED_RISK,
    build_fact_based_choice_labels,
)
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402
from picwise_search import resolve_live_search  # noqa: E402
from picwise_surface.browser_lists import (  # noqa: E402
    BROWSER_LISTS_SCRIPT,
    FAVOURITES_STORAGE_KEY,
    HEAD_SCRIPT,
    HISTORY_ON_STORAGE_KEY,
    HISTORY_STORAGE_KEY,
)
from picwise_surface.legal import (  # noqa: E402
    FOOTER_LINKS,
    render_cookies_page,
    render_privacy_page,
    render_public_footer,
)
from picwise_surface.reference import (  # noqa: E402
    _PAGE_STYLES,
    _STOCK_LINES,
    _at_least,
    _card_note,
    _display_price,
    _stock_line,
    render_picwise_reference_surface,
)
from picwise_surface.trends import (  # noqa: E402
    TRENDS_SOURCE_STATUS,
    TrendRow,
    TrendsPanel,
    load_trends_panel,
    render_trends_panel,
)

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock", "merchant_name",
    "description", "data_provenance", "ean", "mpn",
)


def _call(path: str, params: dict[str, str] | None = None) -> str:
    def start_response(_status: str, _headers: list[tuple[str, str]]) -> None:
        return None

    return b"".join(
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


def _cards(page: str) -> list[str]:
    return re.findall(r'<article class="pw-card[^"]*" data-choice-id="[^"]+">.*?</article>', page, re.S)


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


class _FeedMixin:
    def _serve(self, rows: list[dict[str, str]]) -> None:
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for row in rows:
                pid = row["pid"]
                writer.writerow(
                    [pid, row["title"], row.get("brand", row["title"].split()[0]), row.get("type", "Kettles"),
                     "Kitchen Appliances", f"https://fixture.example.invalid/out/{pid}",
                     f"https://fixture.example.invalid/img/{pid}.jpg", row["price"], "GBP", "1",
                     row.get("shop", "Fixture Store One"), fixture_description(), "local_test_fixture",
                     row.get("ean", ""), row.get("mpn", "")]
                )
        previous = os.environ.get("AWIN_FEED_FILE")
        os.environ["AWIN_FEED_FILE"] = str(path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            if previous is None:
                os.environ.pop("AWIN_FEED_FILE", None)
            else:
                os.environ["AWIN_FEED_FILE"] = previous
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)  # type: ignore[attr-defined]


def _ean13(base12: str) -> str:
    total = sum(int(digit) * (3 if position % 2 else 1) for position, digit in enumerate(base12))
    return base12 + str((10 - total % 10) % 10)


def _kettles() -> list[dict[str, str]]:
    shops = ("Fixture Store One", "Fixture Store Two", "Fixture Store Three")
    return [
        {"pid": f"k{index}", "title": f"Fixturon Kettle Model {index} 1.7L", "price": f"{10 + 3 * index}.00",
         "ean": _ean13(f"50{index:010d}"), "shop": shops[index % 3]}
        for index in range(1, 10)
    ]


class SymmetricCardsTests(_FeedMixin, unittest.TestCase):
    def setUp(self) -> None:
        self._serve(_kettles())
        self.page = _call("/search", {"q": "kettle"})
        self.cards = _cards(self.page)

    def test_four_cards_each_with_a_square_photo_shown_whole_and_sized_before_it_loads(self) -> None:
        self.assertEqual(len(self.cards), 4)
        for card in self.cards:
            image = re.search(r'<img class="pw-product-image" [^>]+>', card)
            self.assertIsNotNone(image)
            self.assertIn('width="400" height="400"', image.group(0))
            # The photo comes first, before the card's words.
            self.assertLess(card.index("pw-product-image-wrap"), card.index("pw-card-title"))
        self.assertIn(".pw-product-image-wrap{position:relative;aspect-ratio:1/1;", _PAGE_STYLES)
        self.assertIn("object-fit:contain;", _PAGE_STYLES)
        self.assertNotIn("object-fit:cover", _PAGE_STYLES)

    def test_the_lines_above_the_price_have_fixed_heights_and_the_button_sits_at_the_foot(self) -> None:
        self.assertIn("-webkit-line-clamp:3;", _PAGE_STYLES)
        self.assertIn("height:4.05em;", _PAGE_STYLES)
        self.assertIn(".pw-role{display:flex;flex-direction:column;align-items:flex-start;gap:4px;height:46px;", _PAGE_STYLES)
        self.assertIn(".pw-card-shop{margin:6px 0 0;font-size:13px;color:var(--muted);white-space:nowrap;", _PAGE_STYLES)
        self.assertIn(".pw-card-cta{margin-top:auto;", _PAGE_STYLES)
        self.assertIn("align-items:stretch;", _PAGE_STYLES)

    def test_the_card_names_the_shop_the_price_the_stock_and_the_place(self) -> None:
        for card in self.cards:
            text = _text(card)
            shop = re.search(r'<p class="pw-card-shop">(.*?)</p>', card)
            self.assertIsNotNone(shop)
            self.assertRegex(_text(shop.group(1)), r"^Fixture Store (One|Two|Three) via Awin$")
            price = re.search(r'<p class="pw-price">(.*?)</p>', card).group(1)
            self.assertRegex(html.unescape(price), r"^£\d+\.\d\d$")
            self.assertRegex(text, r"(Cheapest|\d+(st|nd|rd|th) cheapest) of 9")
            # The button says where it goes: the shop.
            self.assertIn("View at " + _text(shop.group(1)).split(" via ")[0], text)
            self.assertIn('rel="nofollow sponsored noopener"', card)
            self.assertIn('class="pw-card-note"', card)

    def test_the_stock_line_claims_only_what_the_feed_says(self) -> None:
        # A stock flag that is "1" on every row says nothing a shop could be held to:
        # listed as available, never "in stock".
        for card in self.cards:
            stock = re.search(r'<p class="pw-card-stock pw-stock-(\w+)">(.*?)</p>', card)
            self.assertIsNotNone(stock)
            self.assertEqual(stock.group(1), "listed")
            self.assertEqual(stock.group(2), "Listed as available by the shop")
        grid = re.search(r'<section class="pw-grid".*?</section>', self.page, re.S).group(0)
        self.assertNotIn("in stock", grid.lower())

    def test_the_owner_s_labels_stay(self) -> None:
        recommended = [card for card in self.cards if "pw-card-recommended" in card[:60]]
        self.assertEqual(len(recommended), 1)
        self.assertIn('<div class="pw-rec-badge">&#9733; Recommended</div>', recommended[0])
        self.assertIn('<p class="pw-role-label">Mid-priced for this category</p>', recommended[0])
        for card in self.cards:
            if card is not recommended[0]:
                self.assertIn('<p class="pw-role-label">Lowest price</p>', card)

    def test_the_count_is_shown_above_the_cards_and_with_more(self) -> None:
        self.assertIn('<p class="pw-results-count">4 of 9</p>', self.page)
        self.assertLess(self.page.index("pw-results-count\">"), self.page.index("<article"))
        self.assertIn('<p class="pw-counter">4 of 9</p>', self.page)
        self.assertIn('class="pw-more-button"', self.page)

    def test_each_card_has_a_heart_that_carries_what_favourites_shows(self) -> None:
        for card in self.cards:
            heart = re.search(r'<button class="pw-fav pw-needs-store"[^>]*>', card)
            self.assertIsNotNone(heart)
            for attribute in ("data-fav-id", "data-fav-title", "data-fav-price", "data-fav-shop", "data-fav-image"):
                self.assertIn(attribute + '="', heart.group(0))
            self.assertIn('aria-pressed="false"', heart.group(0))

    def test_the_search_page_has_no_hero_and_no_trends(self) -> None:
        self.assertNotIn('class="pw-hero-home"', self.page)
        self.assertNotIn('id="pw-trends"', self.page)
        self.assertIn('<meta name="robots" content="noindex">', self.page)


class CardWordingTests(unittest.TestCase):
    def test_the_price_reads_as_a_uk_shopper_writes_it(self) -> None:
        self.assertEqual(_display_price({"price_text": "12.74", "currency": "GBP"}), "£12.74")
        self.assertEqual(_display_price({"price_text": "1299.5", "currency": "GBP"}), "£1,299.50")
        self.assertEqual(_display_price({"price_text": "20", "currency": "GBP"}), "£20")
        self.assertEqual(_display_price({"price_text": "19.99", "currency": "EUR"}), "€19.99")
        self.assertEqual(_display_price({"price_text": "19.99", "currency": "USD"}), "$19.99")
        # Anything else keeps its code: the currency is never lost or guessed.
        self.assertEqual(_display_price({"price_text": "19.99", "currency": "SEK"}), "19.99 SEK")
        self.assertEqual(_display_price({"price_text": "GBP 749.00", "currency": "GBP"}), "GBP 749.00")
        self.assertEqual(_display_price({"price_text": "1.299,50", "currency": "EUR"}), "1.299,50 EUR")
        self.assertEqual(_display_price({"price_text": "", "currency": "GBP"}), "")

    def test_the_stock_line_follows_the_labels_own_fact(self) -> None:
        listed = build_fact_based_choice_labels(
            [{"provider_product_id": "a", "price_text": "10", "currency": "GBP", "availability_state": "trusted"}]
        )[0]
        self.assertEqual(_stock_line(listed), ("Listed as available by the shop", "listed"))
        unknown = build_fact_based_choice_labels(
            [{"provider_product_id": "b", "price_text": "10", "currency": "GBP", "availability_state": "unknown"}]
        )[0]
        self.assertEqual(_stock_line(unknown), ("Stock not confirmed by the shop's feed", "unconfirmed"))
        self.assertEqual(_stock_line(None), ("Stock not confirmed by the shop's feed", "unconfirmed"))
        # Each fact the line rewords is one `decision_labels` really states.
        verified = build_fact_based_choice_labels(
            [{"provider_product_id": "c", "price_text": "10", "currency": "GBP", "verified_purchasable": True,
              "purchasability_state": "purchasable", "availability_state": "trusted"}]
        )[0]
        stated = set(listed.key_reasons) | set(verified.key_reasons)
        for reason, _line, _state in _STOCK_LINES:
            self.assertIn(reason, stated)

    def test_the_limitation_keeps_what_is_particular_to_the_product(self) -> None:
        refurbished = build_fact_based_choice_labels(
            [{"provider_product_id": "r", "price_text": "24.00", "currency": "GBP", "condition": "Refurbished"}]
        )[0]
        self.assertTrue(refurbished.risk_or_limitation.endswith(UNVERIFIED_RISK))
        self.assertEqual(
            _card_note(refurbished),
            "Listed by the feed as Refurbished, not new. Price and stock as the shop lists them, "
            "not verified by PicWise.",
        )
        plain = build_fact_based_choice_labels(
            [{"provider_product_id": "p", "price_text": "24.00", "currency": "GBP"}]
        )[0]
        self.assertEqual(_card_note(plain), "Price and stock as the shop lists them, not verified by PicWise.")

        class _Other:
            risk_or_limitation = "A limitation PicWise has no shorter words for."

        self.assertEqual(_card_note(_Other()), "A limitation PicWise has no shorter words for.")


class SingleProductTests(_FeedMixin, unittest.TestCase):
    def test_one_product_is_laid_out_on_its_own_with_its_facts(self) -> None:
        self._serve([{"pid": "t1", "title": "Fixturon Toaster 2 Slice", "type": "Toasters", "price": "27.49",
                      "ean": "5000000000104", "shop": "Fixture Store Two"}])
        page = _call("/search", {"q": "toaster"})
        self.assertIn('<section class="pw-grid" data-card-count="1" data-layout="single">', page)
        cards = _cards(page)
        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertIn("This is the only product PicWise found for this search in its shops.", card)
        # One product is not "the lowest price" of anything.
        self.assertNotIn('<p class="pw-role-label">', card)
        facts = dict(re.findall(r'<span class="pw-fact-name">(.*?)</span><span class="pw-fact-value">(.*?)</span>', card))
        self.assertEqual(facts.get("Shop"), "Fixture Store Two via Awin")
        self.assertEqual(facts.get("Brand"), "Fixturon")
        self.assertEqual(facts.get("Product code"), "EAN 5000000000104")
        self.assertEqual(html.unescape(facts.get("Delivery", "")), "See the shop's site")
        # No "More" for an answer of one.
        self.assertNotIn('class="pw-more"', page)

    def test_a_code_the_shop_does_not_give_is_not_listed(self) -> None:
        self._serve([{"pid": "t2", "title": "Testline Toaster 4 Slice", "type": "Toasters", "price": "31.00"}])
        page = _call("/search", {"q": "toaster"})
        card = _cards(page)[0]
        self.assertNotIn("Product code", card)
        self.assertIn("Fixture Store One", card)

    def test_the_maker_s_part_number_when_there_is_no_barcode(self) -> None:
        self._serve([{"pid": "t3", "title": "Sampleware Toaster Slim", "type": "Toasters", "price": "22.00",
                      "mpn": "SW-T200"}])
        resolution = resolve_live_search("toaster")
        self.assertEqual(single_product_code(resolution), "Part no. SW-T200")

    def test_several_products_are_never_given_a_single_code(self) -> None:
        self._serve(_kettles())
        self.assertEqual(single_product_code(resolve_live_search("kettle")), "")


class HistoryAndFavouritesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.page = _call("/")

    def test_they_replace_login_and_register(self) -> None:
        self.assertNotIn("pw-login-btn", self.page)
        self.assertNotIn(">Login<", self.page)
        self.assertNotIn(">Register<", self.page)
        self.assertIn('id="pw-history-button"', self.page)
        self.assertIn('id="pw-favourites-button"', self.page)
        self.assertIn('id="pw-history-panel"', self.page)
        self.assertIn('id="pw-favourites-panel"', self.page)
        self.assertIn("Kept only in this browser; PicWise never receives it.", self.page)

    def test_they_show_only_where_javascript_and_local_storage_work(self) -> None:
        # The head script runs before anything is drawn, and only reads.
        self.assertLess(self.page.index(f"<script>{HEAD_SCRIPT}</script>"), self.page.index("<body>"))
        self.assertNotIn("setItem", HEAD_SCRIPT)
        self.assertIn("pw-store", HEAD_SCRIPT)
        self.assertIn('class="pw-head-btn pw-needs-store" id="pw-history-button"', self.page)
        self.assertIn(".pw-needs-store,.pw-needs-js{display:none!important;}", self.page)
        self.assertIn(".pw-store .pw-head-btn.pw-needs-store{display:inline-flex!important;}", self.page)

    def test_nothing_they_keep_is_ever_sent(self) -> None:
        for request in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource", "document.cookie",
                        "navigator.", ".submit("):
            self.assertNotIn(request, BROWSER_LISTS_SCRIPT)
        # Every kept line is drawn as text, never as markup.
        self.assertNotIn("innerHTML", BROWSER_LISTS_SCRIPT)
        self.assertNotIn("insertAdjacentHTML", BROWSER_LISTS_SCRIPT)
        self.assertIn(".textContent", BROWSER_LISTS_SCRIPT)
        for key in (HISTORY_STORAGE_KEY, HISTORY_ON_STORAGE_KEY, FAVOURITES_STORAGE_KEY):
            self.assertIn(f'"{key}"', BROWSER_LISTS_SCRIPT)

    def test_history_is_kept_only_once_the_visitor_asks(self) -> None:
        self.assertIn("function historyOn(){return read(HON)===1;}", BROWSER_LISTS_SCRIPT)
        self.assertIn("if(!q||!historyOn()){return;}", BROWSER_LISTS_SCRIPT)
        self.assertIn("Keep my searches", BROWSER_LISTS_SCRIPT)
        self.assertIn("Stop keeping history", BROWSER_LISTS_SCRIPT)
        # Stopping forgets the list as well as the choice.
        self.assertIn("forget(HKEY);forget(HON);", BROWSER_LISTS_SCRIPT)

    def test_a_favourite_opens_through_the_tracked_redirect(self) -> None:
        self.assertIn('"/out/feed?pid="+encodeURIComponent(item.id)', BROWSER_LISTS_SCRIPT)
        self.assertIn("&src=favourites&rec=0", BROWSER_LISTS_SCRIPT)
        self.assertIn('link.rel="nofollow sponsored noopener";', BROWSER_LISTS_SCRIPT)
        # The price shown is the one seen when saved, and says so.
        self.assertIn('" when saved"', BROWSER_LISTS_SCRIPT)

    def test_the_privacy_and_cookie_pages_say_what_the_browser_keeps(self) -> None:
        privacy = render_privacy_page()
        cookies = render_cookies_page()
        for page in (privacy, cookies):
            self.assertIn("local storage", page)
            self.assertIn("never sent to PicWise", page)
            self.assertNotIn("stores nothing in your browser", page)
        self.assertIn("<h2>Favourites and search history</h2>", privacy)
        self.assertIn("<h2>Your favourites and history, in your browser</h2>", cookies)
        self.assertIn("so it shows no consent banner", cookies)


class HomePageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.page = _call("/")

    def test_the_home_page_keeps_its_heading_and_three_short_facts(self) -> None:
        # Made shorter on 2026-11-12 (owner: the site «μοιάζει πιο πολύ με εφημερίδα ...
        # πρέπει να γράψουμε λιγότερα»; «Έχεις δίκιο για αυτά»; the heading kept, «3»):
        # no paragraph and no boxes of how it chooses, three facts under the box.
        self.assertIn('<h1 class="pw-hero-title">Find the product you want in UK shops</h1>', self.page)
        self.assertNotIn('class="pw-hero-sub"', self.page)
        self.assertNotIn('class="pw-how', self.page)
        self.assertIn('<ul class="pw-facts">', self.page)
        for fact in ("In stock only, updated every night", "Never ranked by commission"):
            self.assertIn(f"<span>{fact}</span></li>", self.page)
        # What PicWise does stays a tap away and in the page's description.
        self.assertIn('<div class="pw-tooltip" id="pw-tooltip">PicWise finds the product you want', self.page)
        self.assertIn('<meta name="description" content="PicWise finds the product you want', self.page)
        # The home page may be indexed; it shows no empty search state.
        self.assertNotIn('<meta name="robots" content="noindex">', self.page)
        self.assertNotIn("pw-empty-state\">", self.page)
        self.assertNotIn('<section class="pw-grid"', self.page)

    def test_the_first_fact_names_what_a_search_holds_and_never_more(self) -> None:
        page = render_picwise_reference_surface("", catalogue=(251235, 80))
        self.assertIn("<span><b>250,000+</b> products from <b>80</b> UK shops</span>", page)
        one = render_picwise_reference_surface("", catalogue=(1, 1))
        self.assertIn("<span><b>1</b> product from <b>1</b> UK shop</span>", one)
        # Before this process has loaded the catalogue it names no number at all.
        unknown = render_picwise_reference_surface("", catalogue=None)
        self.assertIn('<ul class="pw-facts">', unknown)
        self.assertNotIn(" products from ", unknown)
        # A search page has no facts: it goes straight to its products.
        self.assertNotIn('class="pw-facts"', render_picwise_reference_surface("kettle", catalogue=(251235, 80)))

    def test_a_count_reads_its_first_two_figures_and_never_more_than_it_is(self) -> None:
        for count, text in (
            (0, "0"), (3, "3"), (99, "99"), (100, "100"), (735, "730+"), (3412, "3,400+"),
            (39815, "39,000+"), (251235, "250,000+"), (250000, "250,000"), (735204, "730,000+"),
        ):
            self.assertEqual(_at_least(count), text, count)
            self.assertLessEqual(int(text.rstrip("+").replace(",", "")), count)

    def test_the_header_has_no_tagline_and_one_blue_button(self) -> None:
        self.assertNotIn("pw-brand-tagline", self.page)
        self.assertIn(".pw-info-link{background:#fff;color:var(--ink-2);border-color:var(--line);}", self.page)
        self.assertIn(".pw-search-shell:focus-within{border-color:var(--blue-2);", self.page)

    def test_no_trends_panel_without_a_real_source(self) -> None:
        self.assertIsNone(load_trends_panel())
        self.assertEqual(TRENDS_SOURCE_STATUS, "not_connected")
        self.assertNotIn('id="pw-trends"', self.page)
        self.assertNotIn("Trending searches in the UK this month", self.page)


def _panel(rows: tuple[TrendRow, ...], **overrides: str) -> TrendsPanel:
    fields = {
        "period": "October 2026",
        "country": "United Kingdom",
        "rows": rows,
        "ranking_source": "Google Ads Keyword Planner (monthly searches, UK)",
        "searches_source": "Google Ads Keyword Planner, approximate",
        "offers_source": "PicWise's shops, last night",
    }
    fields.update(overrides)
    return TrendsPanel(**fields)  # type: ignore[arg-type]


class TrendsPanelTests(unittest.TestCase):
    """Fictional rows: the panel's renderer, ready for the day a source gives real ones."""

    def _rows(self) -> tuple[TrendRow, ...]:
        return (
            TrendRow(rank=2, name="Fixturon Air Fryer 5L", category="Kitchen", demand_level=4, change="new",
                     monthly_searches="~74K", offers=9, from_price="£49"),
            TrendRow(rank=1, name="Testline Phone 12", category="Phones", demand_level=5, change="up", change_by=1,
                     monthly_searches="~550K", offers=27, from_price="£699"),
            TrendRow(rank=3, name="Sampleware Vacuum <Pro>", category="Home", demand_level=3, change="down",
                     change_by=2, offers=0),
        )

    def test_nothing_without_rows_or_without_a_named_source(self) -> None:
        self.assertEqual(render_trends_panel(None), "")
        self.assertEqual(render_trends_panel(_panel(())), "")
        self.assertEqual(render_trends_panel(_panel(self._rows(), ranking_source="")), "")

    def test_rows_in_rank_order_with_what_their_sources_give(self) -> None:
        panel = render_trends_panel(_panel(self._rows()))
        names = re.findall(r'<span class="pw-tp-name">(.*?)</span>', panel)
        self.assertEqual(names, ["Testline Phone 12", "Fixturon Air Fryer 5L", "Sampleware Vacuum &lt;Pro&gt;"])
        self.assertIn("Trending searches in the UK this month", panel)
        self.assertIn("The products people search for most on Google this month", panel)
        # Searches, not sales (owner, 2026-10-31).
        for word in ("bought", "sold", "best sellers", "sales"):
            self.assertNotIn(word, panel.lower())
        self.assertIn("October 2026 · United Kingdom", panel)
        self.assertIn("~550K searches a month", panel)
        self.assertIn('aria-label="Search interest: Very high"', panel)
        self.assertIn("Up 1 place on last month", panel)
        self.assertIn("New in the top 10 this month", panel)
        self.assertIn("Down 2 places on last month", panel)
        self.assertIn('href="/search?q=Testline%20Phone%2012"', panel)
        self.assertIn("27 offers · from £699", panel)
        self.assertIn("Ranking and interest: Google Ads Keyword Planner (monthly searches, UK).", panel)
        self.assertIn("Searches: Google Ads Keyword Planner, approximate.", panel)

    def test_a_product_not_in_the_shops_never_links_to_an_empty_search(self) -> None:
        panel = render_trends_panel(_panel(self._rows()))
        row = re.search(r'<li class="pw-tp-row" data-category="Home">.*?</li>', panel, re.S).group(0)
        self.assertIn("Not in our shops yet", row)
        self.assertNotIn("href=", row)
        # A column the source did not give is left out, never filled.
        self.assertNotIn("searches a month", row)

    def test_a_source_not_used_is_not_named(self) -> None:
        rows = (TrendRow(rank=1, name="Testline Phone 12", category="Phones", offers=3, from_price="£699"),)
        panel = render_trends_panel(_panel(rows))
        self.assertNotIn("Searches:", panel)
        self.assertNotIn("pw-tp-scale", panel)
        self.assertNotIn("pw-tp-chg", panel)

    def test_ten_rows_at_most(self) -> None:
        rows = tuple(TrendRow(rank=index, name=f"Fixturon Item {index}", category="Home") for index in range(1, 14))
        panel = render_trends_panel(_panel(rows))
        self.assertEqual(panel.count('<li class="pw-tp-row"'), 10)
        self.assertNotIn("Fixturon Item 11", panel)


class FooterTests(unittest.TestCase):
    def test_about_in_and_the_building_pages_out(self) -> None:
        labels = [label for label, _href in FOOTER_LINKS]
        self.assertEqual(
            labels, ["Home", "About", "Terms", "Privacy", "Cookies", "Affiliate Disclosure", "Contact"]
        )
        footer = render_public_footer()
        self.assertNotIn('href="/demo"', footer)
        self.assertNotIn('href="/picwise-reference"', footer)
        self.assertNotIn(">Demo<", footer)
        self.assertNotIn("PicWise Reference", footer)

    def test_the_building_pages_still_answer(self) -> None:
        self.assertIn("<!doctype html>", _call("/demo"))
        self.assertIn("<!doctype html>", _call("/picwise-reference"))


if __name__ == "__main__":
    unittest.main()
