"""Offers per product, and the products they cover first (owner, 2026-11-01).

«Ανά προϊόν... προϊόντα με προσφορές πρώτα»; asked whether that changes "cheapest first":
«Ένα προϊόν με προσφορά θα μπαίνει πρώτα από το φθηνότερο». Pinned here:

- which offer covers which product (`picwise_providers.product_offers`), on offer titles
  written as Awin's real ones were (31/10): a stated discount, for shoppers, live now,
  on the whole shop or on a kind every word of which is in the title; "up to" and
  "selected" cover nothing;
- the order: the Recommended, then the products an offer covers, cheapest first, then
  the rest, cheapest first; "More" goes on in that order; without offers, the price alone;
- the card: "Offer" instead of "Lowest price", the offer in the shop's words, its end,
  its code only where given, its terms; the page saying the order;
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
    offer_for_product,
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
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for index, (pid, title, price, shop, shop_id) in enumerate(KETTLES, start=1):
                writer.writerow([pid, title, title.split()[0], "Kettles", "Kitchen Appliances",
                                 f"https://fixture.example.invalid/out/{pid}", f"https://fixture.example.invalid/img/{pid}.jpg",
                                 price, "GBP", "1", shop, shop_id, fixture_description(), "local_test_fixture",
                                 _ean13(f"50{index:010d}")])
        self._previous = os.environ.get("AWIN_FEED_FILE")
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

    def test_without_offers_the_order_is_the_price(self) -> None:
        cards = self._cards(self._page())
        self.assertEqual([card["id"] for card in cards], ["k5", "k1", "k2", "k3"])
        self.assertEqual([card["role"] for card in cards[1:]], ["Lowest price"] * 3)
        self.assertNotIn("offers first", self._page())

    def test_after_the_recommended_the_products_on_offer_cheapest_first_then_the_rest(self) -> None:
        set_offers_document({"shops": {"1003": _shop("Fixture Store Three", [
            _offer(7, "10% off kettles", code="KETTLE10", terms="One per order."),
        ], joined=True)}})
        page = self._page()
        cards = self._cards(page)
        # k5 the Recommended (the middle price); then Store Three's kettles k3, k6, k9;
        # "More" goes on with the rest, cheapest first.
        self.assertEqual([card["id"] for card in cards], ["k5", "k3", "k6", "k9"])
        self.assertTrue(cards[0]["recommended"])
        for card in cards[1:]:
            self.assertEqual(card["role"], "Offer")
            self.assertTrue(card["marked"])
            self.assertIn("10% off kettles", card["offer"])
            self.assertIn("until 31 Dec", card["offer"])
            self.assertIn("Code: KETTLE10", card["offer"])
            self.assertIn("Offer terms One per order.", card["offer"])
        more = self._cards(self._page(shown=8))
        self.assertEqual([card["id"] for card in more], ["k5", "k3", "k6", "k9", "k1", "k2", "k4", "k7"])
        self.assertEqual([card["role"] for card in more[4:]], ["", "", "", ""])
        self.assertIn("Results for: kettle, offers first, then cheapest first", page)
        self.assertIn("Products a current shop offer covers come first, then the rest by price, lowest first", page)
        self.assertIn("Offers are the shops&#x27; own, as they state them through Awin", page)
        # The place by price stays true: k9 is the dearest of nine.
        self.assertIn("9th cheapest of 9", page)

    def test_an_offer_without_a_code_shows_none(self) -> None:
        set_offers_document({"shops": {"1001": _shop("Fixture Store One", [_offer(8, "15% off everything")])}})
        cards = self._cards(self._page())
        self.assertEqual([card["id"] for card in cards], ["k5", "k1", "k4", "k7"])
        for card in cards[1:]:
            self.assertNotIn("Code:", card["offer"])
            self.assertIn("15% off everything", card["offer"])

    def test_a_recommended_on_offer_keeps_its_labels_and_shows_its_offer(self) -> None:
        set_offers_document({"shops": {"1002": _shop("Fixture Store Two", [_offer(9, "20% off your order")])}})
        cards = self._cards(self._page())
        self.assertEqual(cards[0]["id"], "k5")
        self.assertEqual(cards[0]["role"], "Mid-priced for this category")
        self.assertIn("20% off your order", cards[0]["offer"])
        # Then the other products of Store Two, k2 and k8, then the cheapest of the rest.
        self.assertEqual([card["id"] for card in cards[1:]], ["k2", "k8", "k1"])
        self.assertEqual(cards[3]["role"], "Lowest price")

    def test_an_offer_that_covers_no_product_changes_nothing(self) -> None:
        set_offers_document({"shops": {"1001": _shop("Fixture Store One", [
            _offer(10, "Free delivery on orders over £20"), _offer(11, "Save up to 30% on kettles"),
        ])}})
        self.assertEqual([card["id"] for card in self._cards(self._page())], ["k5", "k1", "k2", "k3"])


class PagesSayTheOrderTests(unittest.TestCase):
    def test_about_and_the_affiliate_disclosure_say_offers_first_and_whom_picwise_earns_from(self) -> None:
        about = render_about_page()
        self.assertIn("Products a current shop offer covers first, then cheapest first", about)
        disclosure = render_affiliate_disclosure_page()
        self.assertIn("those a current shop offer covers first and then cheapest first", disclosure)
        self.assertIn("PicWise is paid nothing to show an offer or to put it first", disclosure)
        # Awin calls the account joined to some of the shops only (31/10): no page says all.
        self.assertIn("PicWise earns a commission only from the shops that have accepted it", disclosure)
        self.assertNotIn("have accepted PicWise into it", disclosure)


if __name__ == "__main__":
    unittest.main()
