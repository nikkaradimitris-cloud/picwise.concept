"""One look at whether a shop the bot never asks answers for its products one at a time
(`deployment/bot/shop_product_test.py`; owner, 2026-11-21, of InStock UK: «Πρώτα δοκιμή σε
λίγα»). Pinned here: the shop's rows taken from the feed's copies (in stock by the feed,
each of its own address, spread over them); only what robots.txt allows, the pause before
each request, never an Awin link; a product read from Shopify's JSON or from its page's
schema.org Product; the same product by its barcode or its title; the stock and the price
the shop says beside the feed's; and no address printed but the shop's host.

Every row is local test data: fictional brands, `.invalid` hosts. Nothing leaves the
machine: the answers are the test's own.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "deployment" / "bot"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_spec = importlib.util.spec_from_file_location("shop_product_test", ROOT / "deployment" / "bot" / "shop_product_test.py")
probe = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = probe
_spec.loader.exec_module(probe)
look = probe.look

SHOP = "https://instock.example.invalid"
COLUMNS = ("id", "title", "link", "price", "sale_price", "availability", "gtin", "merchant_name", "image_link")


def _awin(address: str) -> str:
    return "https://www.awin1.com/cread.php?awinmid=1&awinaffid=2&ued=" + quote(address, safe="")


def _row(pid: str, title: str, address: str, *, shop: str = "InStock UK", stock: str = "in_stock",
         price: str = "20.00 GBP", gtin: str = "") -> list[str]:
    return [pid, title, _awin(address), price, "", stock, gtin, shop, f"https://img.example.invalid/{pid}.jpg"]


class _Shop:
    def __init__(self, answers: dict[str, tuple[int, bytes]]) -> None:
        self.answers, self.asked, self.slept = answers, [], []

    def fetch(self, url: str, limit: int) -> "look.Answer":
        self.asked.append(url)
        status, body = self.answers.get(url, (404, b"not here"))
        kind = "application/json" if body[:1] in (b"{", b"[") else "text/html"
        return look.Answer(status, kind, body[:limit])

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)


def _page(name: str, price: str, availability: str, gtin: str = "") -> bytes:
    product = {"@context": "https://schema.org", "@type": "Product", "name": name,
               "offers": {"@type": "Offer", "price": price, "priceCurrency": "GBP",
                          "availability": f"https://schema.org/{availability}"}}
    if gtin:
        product["gtin13"] = gtin
    block = json.dumps({"@graph": [{"@type": "WebPage"}, product]})
    return f'<html><head><script type="application/ld+json">{block}</script></head><body></body></html>'.encode()


class RowsTests(unittest.TestCase):
    def test_the_shops_rows_in_stock_each_of_its_own_address(self) -> None:
        folder = Path(tempfile.mkdtemp())
        copy = folder / "picwise_awin_feed_1.bin"
        with copy.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(COLUMNS)
            writer.writerows([
                _row("i1", "Fixturon Kettle 1.7L", f"{SHOP}/products/kettle-17"),
                _row("i2", "Fixturon Kettle 1.7L Red", f"{SHOP}/products/kettle-17"),  # the same address
                _row("i3", "Fixturon Toaster", f"{SHOP}/toaster-2-slice.html", stock="out_of_stock"),
                _row("o1", "Fixturon Lamp", "https://other.example.invalid/products/lamp", shop="Other Shop"),
                _row("i4", "Fixturon Fan", f"{SHOP}/fan-12.html", gtin="05012345678900"),
            ])
        rows = probe.shop_rows([str(copy)], "InStock UK")
        self.assertEqual([row.address for row in rows], [f"{SHOP}/products/kettle-17", f"{SHOP}/fan-12.html"])
        self.assertEqual((rows[1].gtin, rows[1].price), ("5012345678900", "20.00"))

    def test_a_few_spread_over_them(self) -> None:
        rows = [probe.Row(str(n), f"{SHOP}/{n}", "1", "", "in stock", "") for n in range(100)]
        chosen = probe.spread(rows, 5)
        self.assertEqual([row.title for row in chosen], ["0", "25", "50", "74", "99"])
        self.assertEqual(len(probe.spread(rows[:3], 5)), 3)


class ReadingTests(unittest.TestCase):
    def test_shopify_json_in_pence_and_its_barcodes(self) -> None:
        said = probe.read_shopify({"title": "Fixturon Kettle", "available": False, "variants": [
            {"id": 1, "price": 2499, "available": False, "barcode": "05012345678900"},
            {"id": 2, "price": 1999, "available": False, "barcode": ""}]})
        self.assertEqual(said, {"title": "Fixturon Kettle", "in_stock": False, "price": 19.99, "gtins": {"5012345678900"}})

    def test_a_pages_schema_org_product(self) -> None:
        said = probe.read_page(_page("Fixturon Fan 12&quot;", "29.99", "OutOfStock", gtin="5012345678900").decode())
        self.assertEqual(said, {"title": "Fixturon Fan 12&quot;", "in_stock": False, "price": 29.99,
                                "gtins": {"5012345678900"}})
        self.assertIsNone(probe.read_page("<html><body>no product</body></html>"))

    def test_the_same_product_by_its_barcode_else_its_title(self) -> None:
        row = probe.Row("Fixturon Fan 12 inch White", f"{SHOP}/fan", "29.99 GBP", "", "in stock", "5012345678900")
        found = probe.judge(row, {"title": "Something else", "gtins": {"5012345678900"}, "price": 29.99, "in_stock": True})
        self.assertEqual((found["same"], found["how"], found["price_same"]), (True, "by barcode", True))
        found = probe.judge(row, {"title": "Fixturon Fan 12 inch - White", "gtins": set(), "price": 24.99, "in_stock": True})
        self.assertEqual((found["same"], found["how"], found["price_same"]), (True, "title 100% alike", False))
        found = probe.judge(row, {"title": "Fixturon Heater", "gtins": set(), "price": None, "in_stock": None})
        self.assertEqual((found["same"], found["price_same"]), (False, None))


class AskTests(unittest.TestCase):
    def test_each_product_asked_as_robots_allows_and_no_address_printed(self) -> None:
        rows = [
            probe.Row("Fixturon Kettle 1.7L", f"{SHOP}/products/kettle-17?variant=5", "19.99 GBP", "", "in stock", ""),
            probe.Row("Fixturon Fan 12 inch", f"{SHOP}/fan-12.html", "29.99 GBP", "", "in stock", "5012345678900"),
            probe.Row("Fixturon Lamp", f"{SHOP}/lamp.html", "9.99 GBP", "", "in stock", ""),
            probe.Row("Fixturon Rug", f"{SHOP}/rug.html", "49.99 GBP", "", "in stock", ""),
            probe.Row("Fixturon Desk", f"{SHOP}/private/desk.html", "99.99 GBP", "", "in stock", ""),
        ]
        shop = _Shop({
            f"{SHOP}/robots.txt": (200, b"User-agent: *\nDisallow: /private\nCrawl-delay: 5\n"),
            f"{SHOP}/products.json?limit=1": (500, b""),
            f"{SHOP}/products/kettle-17.js": (200, json.dumps({"title": "Fixturon Kettle 1.7L", "available": True,
                                                                "variants": [{"price": 1999, "available": True}]}).encode()),
            f"{SHOP}/fan-12.html": (200, _page("Fixturon Fan", "24.99", "OutOfStock", gtin="5012345678900")),
            f"{SHOP}/lamp.html": (403, b""),
        })
        output = io.StringIO()
        with redirect_stdout(output):
            counts = probe.ask_products(rows, fetch=shop.fetch, sleep=shop.sleep)
        text = output.getvalue()
        self.assertNotIn(f"{SHOP}/private/desk.html", shop.asked)
        for url in shop.asked:
            self.assertNotIn("awin", url)
        self.assertEqual(shop.slept, [5.0] * (len(shop.asked) - 1))
        self.assertIn("host: instock.example.invalid", text)
        self.assertIn("the catalogue (/products.json): 500", text)
        self.assertIn("== product 1: Shopify JSON; the same product: yes (title 100% alike); the shop: in stock, £19.99; "
                      "the feed: in stock, £19.99; price the same", text)
        self.assertIn("== product 2: its page's JSON-LD; the same product: yes (by barcode); the shop: sold out, £24.99; "
                      "the feed: in stock, £29.99; price differs", text)
        self.assertIn("== product 3: refused (403)", text)
        self.assertIn("== product 4: not found (404)", text)
        self.assertIn("== product 5: not asked, robots.txt disallows it", text)
        self.assertEqual((counts["answered"], counts["same"], counts["in_stock"], counts["price_same"]), (2, 2, 1, 1))
        self.assertEqual((counts["refused"], counts["not_found"]), (2, 1))
        # The shop's host only: no address, no product's name.
        for row in rows:
            self.assertNotIn(row.address, text)
            self.assertNotIn(row.title, text)

    def test_a_refused_robots_txt_asks_nothing_else(self) -> None:
        rows = [probe.Row("Fixturon Kettle", f"{SHOP}/products/kettle", "19.99", "", "in stock", "")]
        shop = _Shop({f"{SHOP}/robots.txt": (403, b"")})
        with redirect_stdout(io.StringIO()):
            counts = probe.ask_products(rows, fetch=shop.fetch, sleep=shop.sleep)
        self.assertEqual(shop.asked, [f"{SHOP}/robots.txt"])
        self.assertEqual(counts["refused"], 1)


if __name__ == "__main__":
    unittest.main()
