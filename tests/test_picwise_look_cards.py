"""An hour's look at the first cards of common searches (`deployment/server/look_cards.py`;
owner, 2026-11-21: some buttons do not lead to the shop, some prices differ from the
shop's, some photos never load; task 2 of the work split by model).

Pinned here: the cards are read from the site's own page as it is drawn; the button is
judged as `/out/feed` finds a product, by its id alone, the last of an id standing, and is
never pressed; the shop's own address is read from the link as text, its page asked only
as robots.txt allows, never an Awin link; a price the shop says differently, and in another
currency, is told; a photo a shop refuses with another site's address as Referer is told
from one that is gone; the ids two shops share are counted as the site's index meets them.

Every row is local test data: fictional brands, `.invalid` hosts. Nothing leaves the
machine: the answers are the test's own.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "deployment" / "bot"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_spec = importlib.util.spec_from_file_location("look_cards", ROOT / "deployment" / "server" / "look_cards.py")
cards = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cards
_spec.loader.exec_module(cards)
look = cards.look

from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402

SHOP = "https://shop.example.invalid"
FIXTURE = ROOT / "tests" / "fixtures" / "provider_feed_local_test_fixture.csv"


def _awin(address: str) -> str:
    return "https://www.awin1.com/cread.php?awinmid=1&awinaffid=2&ued=" + quote(address, safe="")


def _product(pid: str, title: str, shop: str, address: str, price: str = "20.00") -> ProviderProduct:
    raw = {"merchant_name": shop, "availability": "in stock", "aw_product_id": pid}
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=title, brand="Fixturon", category_text="Kettles",
        product_url=_awin(address), image_url=f"https://img.example.invalid/{pid}.jpg", price_text=price,
        availability_text="in stock", currency="GBP", raw=raw,
    )


def _page(name: str, price: str, currency: str = "GBP", availability: str = "InStock") -> bytes:
    product = {"@context": "https://schema.org", "@type": "Product", "name": name,
               "offers": {"@type": "Offer", "price": price, "priceCurrency": currency,
                          "availability": f"https://schema.org/{availability}"}}
    return (f'<html><head><script type="application/ld+json">{json.dumps(product)}</script></head>'
            "<body></body></html>").encode()


class _Shops:
    def __init__(self, answers: dict[str, tuple[int, bytes]]) -> None:
        self.answers, self.asked, self.slept = answers, [], []

    def fetch(self, url: str, limit: int) -> "look.Answer":
        self.asked.append(url)
        status, body = self.answers.get(url, (404, b""))
        return look.Answer(status, "application/json" if body[:1] in (b"{", b"[") else "text/html", body[:limit])


class ReadCardsTests(unittest.TestCase):
    def test_the_first_cards_of_the_sites_own_page(self) -> None:
        from picwise_app import PicwiseLocalApp
        from picwise_providers.awin_adapter import clear_awin_feed_parse_cache
        from picwise_providers.state import clear_provider_feed_pipeline_cache
        from picwise_search import search_warmup

        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("AWIN_FEED_", "PICWISE_PREPARED", "PICWISE_SHOP_CATALOGUES"))}
        env["AWIN_FEED_FILE"] = str(FIXTURE)
        with mock.patch.dict(os.environ, env, clear=True):
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()
            self.addCleanup(clear_awin_feed_parse_cache)
            self.addCleanup(clear_provider_feed_pipeline_cache)
            self.addCleanup(search_warmup._reset_search_warmup_for_tests)
            page = PicwiseLocalApp().picwise_reference_html("laptop")
        found = cards.read_cards(page)
        self.assertEqual(len(found), 4)
        for card in found:
            self.assertTrue(card["pid"].startswith("fx-laptop-"), card)
            self.assertEqual(card["button"], "/out/feed")
            self.assertIn("Laptop", card["title"])
            self.assertTrue(card["price"].startswith("£"), card)
            self.assertTrue(card["image"].startswith("https://fixture.example.invalid/images/"), card)
            self.assertIn("via Awin", card["shop"])


class SharedIdsTests(unittest.TestCase):
    def test_of_each_id_the_last_stands_and_the_others_buttons_lead_to_it(self) -> None:
        products = [
            _product("1", "Fixturon Kettle", "Shop A", f"{SHOP}/a/1"),
            _product("2", "Fixturon Toaster", "Shop A", f"{SHOP}/a/2"),
            _product("1", "Testline Drill", "Shop B", f"{SHOP}/b/1"),
            _product("3", "Fixturon Fan", "Shop A", f"{SHOP}/a/3"),
            _product("3", "Fixturon Fan Blue", "Shop A", f"{SHOP}/a/3b"),
        ]
        shared = cards.shared_ids(products)
        self.assertEqual((shared["ids"], shared["ids_of_two_shops"], shared["products_led_elsewhere"],
                          shared["of_another_shop"]), (2, 1, 2, 1))
        self.assertEqual(shared["pairs"], [(("Shop A", "Shop B"), 1), (("Shop A", "Shop A"), 1)])
        self.assertEqual(shared["examples"], ["Shop A: Fixturon Kettle -> Shop B: Testline Drill"])


class LookAtCardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.kettle = _product("1", "Fixturon Kettle 1.7L", "Shop A", f"{SHOP}/kettle-17", price="19.99")
        self.drill = _product("1", "Testline Drill 18V", "Shop B", "https://other.example.invalid/drill")
        self.fan = _product("2", "Fixturon Fan 12 inch", "Shop A", f"{SHOP}/products/fan-12", price="29.99")
        self.prepared = SimpleNamespace(
            availability_context=build_feed_availability_context((self.kettle, self.drill, self.fan)))
        self.by_id = {"1": [self.kettle, self.drill], "2": [self.fan]}
        self.shops = _Shops({
            f"{SHOP}/robots.txt": (404, b""),
            f"{SHOP}/kettle-17": (200, _page("Fixturon Kettle 1.7L", "19.99")),
            f"{SHOP}/products/fan-12": (200, b"<html><body>no product data</body></html>"),
            f"{SHOP}/products/fan-12.js": (200, json.dumps({"title": "Fixturon Fan 12 inch", "available": False,
                                                            "variants": [{"price": 3299, "available": False}]}).encode()),
        })
        self.asker = cards.Asker(self.shops.fetch, self.shops.slept.append, lambda: 0.0, pause=3.0)

    def _photos(self, answers: dict[tuple[str, bool], tuple[int, str, int, float]]):
        def ask(url: str, referer: str | None) -> tuple[int, str, int, float]:
            return answers.get((url, referer is not None), (404, "", 0, 0.1))
        return ask

    def test_a_shared_id_leads_the_button_to_the_other_shops_product(self) -> None:
        card = {"pid": "1", "title": "Fixturon Kettle 1.7L", "shop": "Shop A via Awin", "price": "£19.99",
                "image": "https://img.example.invalid/1.jpg"}
        photos = self._photos({("https://img.example.invalid/1.jpg", True): (403, "", 0, 0.2),
                               ("https://img.example.invalid/1.jpg", False): (200, "image/jpeg", 2048, 0.2)})
        found = cards.look_at_card(card, self.by_id, self.prepared, self.asker, photos)
        self.assertEqual(found["button"][1], "leads to another product")
        self.assertIn("Shop B: Testline Drill 18V", found["button"][0])
        # The shop's page is the card's own product's, read from its link as text.
        self.assertEqual(found["page"][1], "200, the same product, in stock")
        self.assertEqual(found["price"], ("the same (£19.99)", "the same"))
        self.assertEqual(found["photo"][0], "FAILS (403); loads without our address as Referer")
        for url in self.shops.asked:
            self.assertNotIn("awin", url)
            self.assertNotIn("other.example.invalid", url)

    def test_shopify_json_where_the_page_says_nothing_and_a_price_that_differs(self) -> None:
        card = {"pid": "2", "title": "Fixturon Fan 12 inch", "shop": "Shop A via Awin", "price": "£29.99",
                "image": "https://img.example.invalid/2.jpg"}
        photos = self._photos({("https://img.example.invalid/2.jpg", True): (200, "image/webp", 4096, 6.5)})
        found = cards.look_at_card(card, self.by_id, self.prepared, self.asker, photos)
        self.assertEqual(found["button"][1], "leads to its product, Awin cread")
        self.assertEqual(found["page"][1], "200, the same product, sold out")
        self.assertEqual(found["price"][0], "DIFFERS: the card £29.99, the shop 32.99 (+10%)")
        self.assertEqual(found["photo"], ("loads (image/webp, 6.5 s) SLOW", "loads slow"))
        # One robots.txt for the host, then each page; never closer than the pause.
        self.assertEqual(self.shops.asked[0], f"{SHOP}/robots.txt")

    def test_a_price_in_another_currency_is_told(self) -> None:
        self.shops.answers[f"{SHOP}/kettle-17"] = (200, _page("Fixturon Kettle 1.7L", "23.50", currency="EUR"))
        card = {"pid": "1", "title": "Fixturon Kettle 1.7L", "shop": "Shop A via Awin", "price": "£19.99", "image": ""}
        found = cards.look_at_card(card, {"1": [self.kettle]}, self.prepared, self.asker, self._photos({}))
        self.assertEqual(found["button"][1], "leads to its product, Awin cread")
        self.assertEqual(found["price"], ("DIFFERS: the card £19.99, the shop 23.50 EUR (+18%)", "differs (EUR)"))
        self.assertEqual(found["photo"], ("no photo address", "no photo address"))

    def test_no_product_under_the_id(self) -> None:
        card = {"pid": "9", "title": "Gone", "shop": "Shop A via Awin", "price": "£1.00", "image": ""}
        found = cards.look_at_card(card, self.by_id, self.prepared, self.asker, self._photos({}))
        self.assertEqual(found, {"button": ("FAILS: no product under its id (\"no longer available\")",
                                            "no product under its id")})


class MainTests(unittest.TestCase):
    def test_the_report_counts_each_part_and_prints_no_address(self) -> None:
        kettle = _product("1", "Fixturon Kettle 1.7L", "Shop A", f"{SHOP}/kettle-17", price="19.99")
        prepared = SimpleNamespace(products=(kettle,), prepared_at=__import__("datetime").datetime(2026, 11, 21, 12, 48),
                                   availability_context=build_feed_availability_context((kettle,)))
        card_page = (
            '<article class="pw-card pw-card-recommended" data-choice-id="c1"><img class="pw-product-image" '
            'src="https://img.example.invalid/1.jpg" alt="x"><h2 title="Fixturon Kettle 1.7L" class="pw-card-title">'
            'Fixturon Kettle 1.7L</h2><p class="pw-card-shop">Shop A via Awin</p><p class="pw-price">£19.99</p>'
            '<a class="pw-card-cta pw-card-cta-link" href="/out/feed?pid=1&amp;q=kettle&amp;src=search&amp;rec=1">View</a>'
            "</article>"
        )
        shops = _Shops({f"{SHOP}/robots.txt": (404, b""), f"{SHOP}/kettle-17": (200, _page("Fixturon Kettle 1.7L", "19.99"))})
        out = io.StringIO()
        with redirect_stdout(out):
            code = cards.main(["--search", "kettle"], get=lambda url: card_page, fetch=shops.fetch, sleep=lambda s: None,
                              clock=lambda: 0.0, ask_photo=lambda url, referer: (200, "image/jpeg", 100, 0.1),
                              prepared=prepared)
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("ids two products or more share: 0", text)
        self.assertIn("== kettle: 1 cards", text)
        self.assertIn("button: leads to its product (Awin cread)", text)
        self.assertIn("  button: leads to its product, Awin cread 1", text)
        self.assertIn("  price: the same 1", text)
        self.assertIn("  photo: loads 1", text)
        self.assertNotIn(f"{SHOP}/kettle-17", text)
        self.assertNotIn("awin1.com", text)


if __name__ == "__main__":
    unittest.main()
