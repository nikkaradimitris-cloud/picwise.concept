"""Offers per product (owner, 2026-11-01), and the order at the price after them (2026-11-15).

From 2026-11-01 to 2026-11-15 the products an offer covered came first («Ένα προϊόν με
προσφορά θα μπαίνει πρώτα από το φθηνότερο»). The owner, 2026-11-15: «Οι προσφορές δεν
πρέπει να βγαίνουν πάνω από το φθηνότερο προϊόν» and «η έκπτωση πρέπει να υπολογίζει την
τελική τιμή και να γίνεται κατάταξη με βάση την πραγματική αξία». Pinned here:

- which offer covers which product (`picwise_providers.product_offers`), on offer titles
  written as Awin's real ones were (31/10): a stated discount, for shoppers, live now,
  on the whole shop or on a kind every word of which is in the title; "up to" and
  "selected" cover nothing; a voucher only with its code, which Awin gives for the
  programmes PicWise is joined to (most real vouchers of 01/11 came without one);
- the price after an offer, worked out only where its words leave no doubt that the
  buyer of this one product gets it (`price_after_offer`);
- the order: the Recommended, then every product cheapest first, each at its price
  after its offer where that is certain; "More" goes on in that order; the price bar
  reads the same prices;
- the Recommended: a product on offer whenever there is one («Εάν υπάρχει προσφορά να
  προτείνει την προσφορά»; «το recommended όταν υπάρχει προσφορά πρέπει να δείχνει την
  προσφορά»), the one nearest the middle of their prices, one with a code first, reading
  "On offer"; else as before;
- the card: "Offer" instead of "Lowest price", the price after the offer with the shop's
  own price beside the offer, the offer in the shop's words, its end, its code only where
  given, its terms; the page saying the order;
- the pages that say how PicWise orders and earns, saying it truly.

Every shop, product and offer is fictional; URLs are `.invalid`.
"""
from __future__ import annotations

import csv
import html
import io
import json
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime, timezone
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
from picwise_providers import product_offers  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.product_offers import (  # noqa: E402
    ProductOffer,
    offer_for_product,
    price_after_offer,
    offer_scope,
    offers_covering,
    set_offers_document,
)
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402
from picwise_surface.legal import render_about_page, render_affiliate_disclosure_page  # noqa: E402

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def _shop(name: str, offers: list[dict], *, joined: bool = False) -> dict:
    return {"name": name, "joined": joined, "offers": offers}


def _offer(number: int, title: str, *, code: str = "", start: str | None = "2026-10-01T00:00:00+00:00",
           end: str = "2026-12-31T23:59:59+00:00", terms: str = "") -> dict:
    row = {"id": number, "type": "voucher" if code else "promotion", "title": title, "description": "",
           "terms": terms, "start": start, "end": end, "regions_all": True}
    if code:
        row["code"] = code
        row["exclusive"] = False
    return row


def _product(pid: str, title: str, shop_id: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=title, brand="Fixturon", category_text="Kitchen",
        product_url=f"https://fixture.example.invalid/out/{pid}", image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text="20.00", availability_text="in stock", currency="GBP", raw={"merchant_id": shop_id},
    )


class OfferScopeTests(unittest.TestCase):
    """Titles as Awin's real offers wrote them on 31/10, with the shops' names changed."""

    def test_offers_on_the_whole_shop(self) -> None:
        for title, shop in (
            ("Enjoy Flat 23% OFF On Sitewide", "Fixdiam"),
            ("18% off £90", "Testline Pro"),
            ("£15 off £100", "Craftware Shop"),
            ("Welcome Back Offer. Get 5% Off On your Next order", "Game Fixture"),
            ("Get 10% Off Your First Order", "Gardenfix"),
            ("15% off everything", "Cottfix"),
            ("10% Off Everything Including Award-Winning Gin + Free UK Shipping", "King & Fixture"),
            ("Bio Fix 15% off Voucher", "BioFix"),
            ("Get 15% off all orders at Susan Fixture using code SF15OFF", "Susan Fixture"),
            ("10% on first order", "Wilder Fixture"),
            ("10% off for all New customers", "Fixture Brat"),
        ):
            with self.subTest(title=title):
                self.assertEqual(offer_scope(title, shop), ("shop", frozenset()))

    def test_offers_on_a_kind_name_every_word_the_title_must_carry(self) -> None:
        self.assertEqual(offer_scope("10% Off Mixer Grinders", "Geefix Partner Program"),
                         ("kind", frozenset({"mixer", "grinder"})))
        self.assertEqual(offer_scope("AirFryer 10% OFF", "Geefix Partner Program"),
                         ("kind", frozenset({"airfryer"})))
        self.assertEqual(offer_scope("Kettle & Toaster Set 10 OFF", "Geefix Partner Program"),
                         ("kind", frozenset({"kettle", "toaster", "set"})))
        self.assertEqual(offer_scope("15% off all harry potter products", "Craftware Shop"),
                         ("kind", frozenset({"harry", "potter"})))
        self.assertEqual(offer_scope("10% off your Christmas gifts", "Harfix"),
                         ("kind", frozenset({"christmas", "gift"})))

    def test_offers_that_cover_no_product(self) -> None:
        for title, shop in (
            ("Free delivery on orders above £20", "Testline Pro"),       # delivery, not the product
            ("Free Mainland UK Delivery", "Gardenfix"),
            ("Save up to 30%", "Curo Fix"),                              # which products, not said
            ("Save up to 28% on Litter Pickers & Accessories", "The Brush & Fixture"),
            ("10% off selected clothing and footwear", "Viafix Clothing"),
            ("Autumn Edit! The Season of Golden Moments", "Angel Fixture"),  # no discount
            ("30 Creatine Sachets for £24 (80p/day)", "Optimum Fixture UK"),  # a bundle price
            ("Welcome10", "Five Star Fixture"),                          # a code alone
            ("SUNFIXUK10", "SUNFIX UK"),
            ("Mr Fix Christmas & Secret Santa Gifts – 8% Commission", "Mr Fix"),  # for publishers
        ):
            with self.subTest(title=title):
                self.assertIsNone(offer_scope(title, shop))


class OfferForProductTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_offers_document(None)

    def test_a_kind_offer_covers_only_the_products_of_its_kind_in_its_shop(self) -> None:
        set_offers_document({"shops": {"101": _shop("Geefix", [_offer(1, "AirFryer 10% OFF")])}})
        self.assertIsNotNone(offer_for_product(_product("a", "Geefix 5.5L Digital Air Fryer", "101"), now=NOW))
        self.assertIsNone(offer_for_product(_product("b", "Geefix Cordless Kettle 1.7L", "101"), now=NOW))
        # The same kind in another shop: that shop's offer it is not.
        self.assertIsNone(offer_for_product(_product("c", "Testline Air Fryer 4L", "202"), now=NOW))

    def test_only_an_offer_live_now_by_its_own_dates(self) -> None:
        set_offers_document({"shops": {"101": _shop("Geefix", [
            _offer(1, "15% off everything", end="2026-10-31T23:59:59+00:00"),
            _offer(2, "20% off everything", start="2026-11-10T00:00:00+00:00"),
        ])}})
        self.assertIsNone(offer_for_product(_product("a", "Geefix Kettle", "101"), now=NOW))

    def test_a_kind_offer_before_a_shop_one_and_a_code_before_none(self) -> None:
        set_offers_document({"shops": {"101": _shop("Geefix", [
            _offer(1, "15% off everything", end="2026-11-05T00:00:00+00:00"),
            _offer(2, "10% off kettles"),
            _offer(3, "12% off kettles", code="KETTLE12"),
        ], joined=True)}})
        offer = offer_for_product(_product("a", "Geefix Glass Kettle 1.7L", "101"), now=NOW)
        self.assertEqual((offer.offer_id, offer.code, offer.scope), ("3", "KETTLE12", "kind"))
        offer = offer_for_product(_product("b", "Geefix Toaster", "101"), now=NOW)
        self.assertEqual((offer.offer_id, offer.scope), ("1", "shop"))

    def test_a_voucher_without_its_code_covers_nothing(self) -> None:
        # Geepas's real voucher of 01/11, without its code: the account is not joined to
        # the programme, so Awin gave none, and a shopper could not have the discount.
        voucher = {"id": 1, "type": "voucher", "title": "Kettle & Toaster Set 10 OFF", "description": "",
                   "terms": "", "start": None, "end": "2026-12-31T23:59:59+00:00", "regions_all": True}
        product = _product("a", "Geefix 1.7L Electric Kettle & 2 Slice Bread Toaster Set", "101")
        set_offers_document({"shops": {"101": _shop("Geefix", [voucher])}})
        self.assertIsNone(offer_for_product(product, now=NOW))
        self.assertEqual(offers_covering([product], now=NOW), {})
        # With its code, as for a joined programme, it covers the product.
        set_offers_document({"shops": {"101": _shop("Geefix", [dict(voucher, code="SET10")], joined=True)}})
        self.assertEqual(offer_for_product(product, now=NOW).code, "SET10")
        # A promotion needs no code.
        set_offers_document({"shops": {"101": _shop("Geefix", [dict(voucher, type="promotion")])}})
        self.assertIsNotNone(offer_for_product(product, now=NOW))

    def test_the_file_is_read_and_read_again_when_it_changes(self) -> None:
        folder = Path(tempfile.mkdtemp())
        path = folder / "offers.json"
        path.write_text(json.dumps({"shops": {"101": _shop("Geefix", [_offer(1, "15% off everything")])}}))
        saved_env, saved_recheck = os.environ.get(product_offers.OFFERS_FILE_ENV), product_offers._RECHECK_SECONDS
        os.environ[product_offers.OFFERS_FILE_ENV] = str(path)
        product_offers._RECHECK_SECONDS = 0.0
        try:
            set_offers_document(None)
            self.assertIsNotNone(offer_for_product(_product("a", "Geefix Kettle", "101"), now=NOW))
            path.write_text(json.dumps({"shops": {}}))
            os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 5))
            self.assertIsNone(offer_for_product(_product("a", "Geefix Kettle", "101"), now=NOW))
            path.unlink()
            self.assertIsNone(offer_for_product(_product("a", "Geefix Kettle", "101"), now=NOW))
        finally:
            product_offers._RECHECK_SECONDS = saved_recheck
            if saved_env is None:
                os.environ.pop(product_offers.OFFERS_FILE_ENV, None)
            else:
                os.environ[product_offers.OFFERS_FILE_ENV] = saved_env
            set_offers_document(None)

    def test_no_offers_cost_nothing(self) -> None:
        set_offers_document(None)
        saved = os.environ.pop(product_offers.OFFERS_FILE_ENV, None)
        try:
            self.assertEqual(offers_covering([_product("a", "Geefix Kettle", "101")]), {})
        finally:
            if saved is not None:
                os.environ[product_offers.OFFERS_FILE_ENV] = saved


_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category", "aw_deep_link",
    "aw_image_url", "search_price", "currency", "in_stock", "merchant_name", "merchant_id", "description",
    "data_provenance", "ean",
)


def _ean13(base12: str) -> str:
    total = sum(int(digit) * (3 if position % 2 else 1) for position, digit in enumerate(base12))
    return base12 + str((10 - total % 10) % 10)


# Nine kettles from three shops, £13 to £37; the Recommended is the middle one, £25.
KETTLES = [
    ("k1", "Fixturon Kettle One 1.7L", "13.00", "Fixture Store One", "1001"),
    ("k2", "Testline Kettle Two 1.5L", "16.00", "Fixture Store Two", "1002"),
    ("k3", "Sampleware Kettle Three 1.7L", "19.00", "Fixture Store Three", "1003"),
    ("k4", "Fixturon Kettle Four 1.7L", "22.00", "Fixture Store One", "1001"),
    ("k5", "Testline Kettle Five 1.7L", "25.00", "Fixture Store Two", "1002"),
    ("k6", "Sampleware Kettle Six 1.7L", "28.00", "Fixture Store Three", "1003"),
    ("k7", "Fixturon Kettle Seven 1.7L", "31.00", "Fixture Store One", "1001"),
    ("k8", "Testline Kettle Eight 1.7L", "34.00", "Fixture Store Two", "1002"),
    ("k9", "Sampleware Kettle Nine 1.7L", "37.00", "Fixture Store Three", "1003"),
]


class OffersFirstPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.get("AWIN_FEED_FILE")
        self._write_feed()

    def _write_feed(self, *, no_code: frozenset[str] = frozenset(), only: frozenset[str] = frozenset()) -> None:
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for index, (pid, title, price, shop, shop_id) in enumerate(KETTLES, start=1):
                if only and pid not in only:
                    continue
                writer.writerow([pid, title, title.split()[0], "Kettles", "Kitchen Appliances",
                                 f"https://fixture.example.invalid/out/{pid}", f"https://fixture.example.invalid/img/{pid}.jpg",
                                 price, "GBP", "1", shop, shop_id, fixture_description(), "local_test_fixture",
                                 "" if pid in no_code else _ean13(f"50{index:010d}")])
        os.environ["AWIN_FEED_FILE"] = str(path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def tearDown(self) -> None:
        set_offers_document(None)
        if self._previous is None:
            os.environ.pop("AWIN_FEED_FILE", None)
        else:
            os.environ["AWIN_FEED_FILE"] = self._previous
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def _page(self, shown: int = 0) -> str:
        params = {"q": "kettle"}
        if shown:
            params["shown"] = str(shown)
        return b"".join(wsgi_app(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/search", "QUERY_STRING": urlencode(params),
             "wsgi.input": io.BytesIO(b""), "wsgi.url_scheme": "https"},
            lambda _status, _headers: None,
        )).decode("utf-8")

    @staticmethod
    def _cards(page: str) -> list[dict[str, str]]:
        cards = []
        for match in re.finditer(r'<article class="pw-card([^"]*)" data-choice-id="([^"]+)">(.*?)</article>', page, re.S):
            classes, pid, inner = match.groups()
            role = re.search(r'class="pw-role-label">(.*?)</p>', inner)
            offer = re.search(r'<div class="pw-card-offer">(.*?)</div>', inner, re.S)
            cards.append({
                "id": pid, "recommended": "recommended" in classes,
                "role": html.unescape(role.group(1)) if role else "",
                "offer": " ".join(html.unescape(re.sub(r"<[^>]+>", " ", offer.group(1))).split()) if offer else "",
                "marked": 'data-offer="1"' in inner,
            })
        return cards

    def test_a_chosen_price_reads_the_prices_after_offers_and_recommends_none(self) -> None:
        # Owner, 2026-11-12: with a price chosen on the price bar there is no Recommended,
        # on offer or not («Το recommendit πρέπει να ακιρονετε όταν χρησιμοποιεί φίλτρο»).
        set_offers_document({"shops": {"1003": _shop("Fixture Store Three", [
            _offer(7, "10% off kettles", code="KETTLE10", terms="One per order."),
        ], joined=True)}})
        page = b"".join(wsgi_app(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/search",
             "QUERY_STRING": urlencode({"q": "kettle", "min": "20"}),
             "wsgi.input": io.BytesIO(b""), "wsgi.url_scheme": "https"},
            lambda _status, _headers: None,
        )).decode("utf-8")
        cards = self._cards(page)
        # 10% off Store Three's kettles: k3 £17.10, k6 £25.20, k9 £33.30. From £20, at
        # those prices: k4 £22, k5 £25, k6 £25.20, k7 £31; k3 is under £20 after its offer.
        self.assertEqual([card["id"] for card in cards], ["k4", "k5", "k6", "k7"])
        self.assertFalse(any(card["recommended"] for card in cards))
        self.assertEqual(cards[2]["role"], "Offer")
        self.assertIn("Results for: kettle, from £20, cheapest first after offers", page)
        self.assertNotIn("The Recommended is", page)

    def test_without_offers_the_order_is_the_price(self) -> None:
        cards = self._cards(self._page())
        self.assertEqual([card["id"] for card in cards], ["k5", "k1", "k2", "k3"])
        self.assertEqual([card["role"] for card in cards[1:]], ["Lowest price"] * 3)
        self.assertNotIn("after offers", self._page())

    def test_the_offer_is_recommended_and_the_rest_follow_at_their_prices_after_offers(self) -> None:
        set_offers_document({"shops": {"1003": _shop("Fixture Store Three", [
            _offer(7, "10% off kettles", code="KETTLE10", terms="One per order."),
        ], joined=True)}})
        page = self._page()
        cards = self._cards(page)
        # Store Three's kettles are on offer, 10% off: k3 £17.10, k6 £25.20, k9 £33.30. The
        # Recommended is the middle of them, k6; then every kettle cheapest first at its
        # price after its offer: k1 £13, k2 £16, k3 £17.10. No product on offer comes
        # before a cheaper one.
        self.assertEqual([card["id"] for card in cards], ["k6", "k1", "k2", "k3"])
        self.assertTrue(cards[0]["recommended"])
        self.assertEqual(cards[0]["role"], "On offer")
        for card in (cards[0], cards[3]):
            self.assertIn("10% off kettles", card["offer"])
            self.assertIn("until 31 Dec", card["offer"])
            self.assertIn("Code: KETTLE10", card["offer"])
            self.assertIn("Offer terms One per order.", card["offer"])
        self.assertIn("£28.00 at the shop, £25.20 with this offer", cards[0]["offer"])
        self.assertIn("£19.00 at the shop, £17.10 with this offer", cards[3]["offer"])
        self.assertEqual(cards[3]["role"], "Offer")
        self.assertTrue(cards[3]["marked"])
        self.assertEqual([card["role"] for card in cards[1:3]], ["Lowest price"] * 2)
        self.assertEqual([card["offer"] for card in cards[1:3]], ["", ""])
        prices = re.findall(r'<p class="pw-price">(.*?)</p>', page)
        self.assertEqual([html.unescape(price) for price in prices], ["£25.20", "£13.00", "£16.00", "£17.10"])
        self.assertIn("The Recommended is on offer: of the products on offer, the one nearest the middle", page)
        self.assertNotIn("The Recommended is mid-priced for this category", page)
        more = self._cards(self._page(shown=8))
        self.assertEqual([card["id"] for card in more], ["k6", "k1", "k2", "k3", "k4", "k5", "k7", "k9"])
        self.assertEqual([card["role"] for card in more[4:]], ["", "", "", "Offer"])
        self.assertIn("Results for: kettle, cheapest first after offers", page)
        # The order is said by the heading alone (owner, 2026-11-12, «Β»).
        self.assertNotIn("Products a current shop offer covers come first", page)
        self.assertIn("Offers are the shops&#x27; own, as they state them through Awin", page)
        # The place by price is at the prices after offers: k6 is the 6th of nine.
        self.assertIn("6th cheapest of 9", page)

    def test_an_offer_without_a_code_shows_none(self) -> None:
        set_offers_document({"shops": {"1001": _shop("Fixture Store One", [_offer(8, "15% off everything")])}})
        cards = self._cards(self._page())
        # k1 £11.05, k4 £18.70, k7 £26.35 after 15% off: k4 the middle, the Recommended;
        # then k1 £11.05, k2 £16, k3 £19.
        self.assertEqual([card["id"] for card in cards], ["k4", "k1", "k2", "k3"])
        for card in cards[:2]:
            self.assertNotIn("Code:", card["offer"])
            self.assertIn("15% off everything", card["offer"])

    def test_one_product_on_offer_is_the_recommended_whatever_its_price(self) -> None:
        set_offers_document({"shops": {"1003": _shop("Fixture Store Three", [_offer(12, "£5 off Kettle Nine")])}})
        cards = self._cards(self._page())
        # The dearest kettle, k9 £37, alone on offer: recommended, then the cheapest; "Lowest
        # price" is measured against the middle price of the whole answer, k5's £25.
        self.assertEqual([card["id"] for card in cards], ["k9", "k1", "k2", "k3"])
        self.assertEqual(cards[0]["role"], "On offer")
        self.assertEqual([card["role"] for card in cards[1:]], ["Lowest price"] * 3)

    def test_products_on_offer_without_a_code_are_still_recommended(self) -> None:
        # Owner, 2026-11-01, of a live search with an offer and a Recommended not on
        # offer: «το recommended όταν υπάρχει προσφορά πρέπει να δείχνει την προσφορά».
        # With no product on offer carrying an EAN/GTIN, the one nearest the middle of
        # their prices is recommended all the same.
        self._write_feed(no_code=frozenset({"k3", "k6", "k9"}))
        set_offers_document({"shops": {"1003": _shop("Fixture Store Three", [_offer(13, "10% off kettles")])}})
        page = self._page()
        cards = self._cards(page)
        self.assertEqual([card["id"] for card in cards], ["k6", "k1", "k2", "k3"])
        self.assertTrue(cards[0]["recommended"])
        self.assertEqual(cards[0]["role"], "On offer")
        self.assertIn("10% off kettles", cards[0]["offer"])
        self.assertIn("The Recommended is on offer", page)

    def test_a_product_on_offer_with_a_code_comes_before_one_nearer_the_middle_without(self) -> None:
        # k6 (the middle of k3, k6, k9) has no code: k3 and k9 are equally far from it,
        # and the cheaper, k3, is recommended.
        self._write_feed(no_code=frozenset({"k6"}))
        set_offers_document({"shops": {"1003": _shop("Fixture Store Three", [_offer(16, "10% off kettles")])}})
        cards = self._cards(self._page())
        self.assertEqual([card["id"] for card in cards], ["k3", "k1", "k2", "k4"])
        self.assertEqual(cards[0]["role"], "On offer")

    def test_fewer_than_three_products_have_no_recommended_even_on_offer(self) -> None:
        # Fewer than three products have no Recommended (2026-10-16), on offer or not:
        # the product on offer stands at its price after the offer, labelled with it.
        self._write_feed(only=frozenset({"k2", "k6"}))
        set_offers_document({"shops": {"1003": _shop("Fixture Store Three", [_offer(14, "10% off kettles")])}})
        page = self._page()
        cards = self._cards(page)
        self.assertEqual([card["id"] for card in cards], ["k2", "k6"])
        self.assertFalse(any(card["recommended"] for card in cards))
        self.assertEqual(cards[1]["role"], "Offer")
        self.assertIn("10% off kettles", cards[1]["offer"])
        self.assertIn("No Recommended here: these products have no middle price to pick.", page)
        self.assertNotIn("The Recommended is on offer", page)

    def test_an_offer_that_covers_no_product_changes_nothing(self) -> None:
        set_offers_document({"shops": {"1001": _shop("Fixture Store One", [
            _offer(10, "Free delivery on orders over £20"), _offer(11, "Save up to 30% on kettles"),
        ])}})
        self.assertEqual([card["id"] for card in self._cards(self._page())], ["k5", "k1", "k2", "k3"])

    def test_a_voucher_without_its_code_changes_nothing(self) -> None:
        set_offers_document({"shops": {"1003": _shop("Fixture Store Three", [
            {"id": 15, "type": "voucher", "title": "10% off kettles", "description": "", "terms": "",
             "start": None, "end": "2026-12-31T23:59:59+00:00", "regions_all": True},
        ])}})
        page = self._page()
        cards = self._cards(page)
        self.assertEqual([card["id"] for card in cards], ["k5", "k1", "k2", "k3"])
        self.assertEqual([card["offer"] for card in cards], ["", "", "", ""])
        self.assertNotIn("after offers", page)

    def test_an_offer_that_makes_a_product_cheapest_puts_it_first_after_the_recommended(self) -> None:
        set_offers_document({"shops": {"1003": _shop("Fixture Store Three", [_offer(17, "£30 off Kettle Nine")])}})
        cards = self._cards(self._page())
        # k9 £37 is £7 after its offer: the Recommended, being the only one on offer.
        self.assertEqual([card["id"] for card in cards], ["k9", "k1", "k2", "k3"])
        self.assertIn("£37.00 at the shop, £7.00 with this offer", cards[0]["offer"])

    def test_an_offer_whose_price_after_it_is_not_certain_leaves_the_shop_s_price(self) -> None:
        # New customers only: whether the buyer is one, PicWise cannot know.
        self._write_feed(only=frozenset({"k1", "k2", "k6"}))
        set_offers_document({"shops": {"1003": _shop("Fixture Store Three", [
            _offer(18, "50% off kettles for new customers"),
        ])}})
        page = self._page()
        cards = self._cards(page)
        # k6 stays at £28, the dearest: the Recommended is the one on offer, then the rest.
        self.assertEqual([card["id"] for card in cards], ["k6", "k1", "k2"])
        self.assertNotIn("with this offer", cards[0]["offer"])
        self.assertIn("50% off kettles for new customers", cards[0]["offer"])
        self.assertIn("Results for: kettle, cheapest first", page)
        self.assertNotIn("after offers", page)


class PriceHistoryBesideAnOfferTests(unittest.TestCase):
    def test_the_history_tells_the_shop_s_own_price_not_the_price_after_the_offer(self) -> None:
        from datetime import date

        from picwise_providers.price_history import SAME, PriceNote, PriceRun
        from picwise_surface import reference

        note = PriceNote(kind=SAME, night=date(2026, 11, 15), currency="GBP", nights=13,
                         runs=(PriceRun(date(2026, 11, 3), date(2026, 11, 15), 13, 0, "GBP"),))
        card = {
            "name": "Fixturon Running Trainers", "choice_id": "s7", "image": "https://fixture.example.invalid/s7.png",
            "price": "£60.00", "shop_price": "£70.00", "shop": "Fixture Store Two", "price_note": note,
            "role_label": "", "description": "", "stock_line": "", "cta": "View", "recommended": False,
            "offer": {"title": "£10 off trainers over £50", "end": "2026-12-31T23:59:59+00:00", "price_after": 60.0},
        }
        html_text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", reference._render_choice_card(card, 1))).split())
        self.assertIn("£70.00 on each of the last 13 nights it was listed.", html_text)
        self.assertNotIn("£60.00 on each", html_text)


class PriceAfterOfferTests(unittest.TestCase):
    """The price after an offer only where its words leave no doubt (owner, 2026-11-15)."""

    @staticmethod
    def _after(title: str, price: float, terms: str = "") -> float | None:
        offer = ProductOffer(shop="1", joined=True, offer_id="1", kind="promotion", title=title, terms=terms,
                             end=NOW, code="", scope="shop")
        return price_after_offer(offer, price)

    def test_one_percentage_one_amount_or_half_price(self) -> None:
        self.assertEqual(self._after("10% off everything", 45.0), 40.5)
        self.assertEqual(self._after("£15 off kettles", 45.0), 30.0)
        self.assertEqual(self._after("Half price kettles", 19.99), 10.0)
        self.assertEqual(self._after("12.5% off sitewide", 80.0), 70.0)

    def test_a_least_spend_the_product_s_price_reaches(self) -> None:
        self.assertEqual(self._after("£15 off orders over £50", 60.0), 45.0)
        self.assertIsNone(self._after("£15 off orders over £50", 45.0))
        self.assertIsNone(self._after("15% off sitewide", 20.0, terms="Minimum spend £30."))
        self.assertEqual(self._after("15% off sitewide", 40.0, terms="Minimum spend £30."), 34.0)

    def test_offers_not_every_buyer_of_one_product_gets(self) -> None:
        for title, terms in (
            ("20% off for new customers", ""), ("10% off your first order", ""), ("BOGOF on kettles", ""),
            ("Buy one get one free", ""), ("Second one free", ""), ("15% off in the app", ""),
            ("10% off everything", "Excludes sale items."), ("Up to 50% off", ""),
            ("10 OFF", ""), ("10% off and £5 off", ""), ("£5 off", ""), ("20% off, 3 for £20", ""),
        ):
            self.assertIsNone(self._after(title, 4.0 if title == "£5 off" else 40.0, terms), title)


class PagesSayTheOrderTests(unittest.TestCase):
    def test_about_and_the_affiliate_disclosure_say_the_order_and_whom_picwise_earns_from(self) -> None:
        about = render_about_page()
        self.assertIn("Cheapest first, in one currency, each product at its price after a current shop offer", about)
        self.assertNotIn("offers first", about)
        disclosure = render_affiliate_disclosure_page()
        self.assertIn("cheapest first, each at its price after a current shop offer where the offer surely applies", disclosure)
        self.assertIn("PicWise is paid nothing to show an offer", disclosure)
        self.assertIn("an offer for new customers, a first order or a second product", disclosure)
        # Awin calls the account joined to some of the shops only (31/10): no page says all.
        self.assertIn("PicWise earns a commission only from the shops that have accepted it", disclosure)
        self.assertNotIn("have accepted PicWise into it", disclosure)


if __name__ == "__main__":
    unittest.main()
