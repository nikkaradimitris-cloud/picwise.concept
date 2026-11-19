"""One card per product: its sizes and colours are chosen at the shop.

Owner, 2026-11-19: «ένα μαγαζί πουλάει ένα ζευγάρι παπούτσια και το βγάζει σε έξι
διαφορετικά νούμερα και τέσσερα διαφορετικά χρώματα αυτό κουράζει τον επισκέπτη γιατί
βλέπει ουσιαστικά το ίδιο προϊόν ... βλέπει τα νούμερα και τα χρώματα στο κατάστημα και
όχι σε μας». The feed names a group, a colour or a size on almost no row (81, 108 and 94
of 1,683,586, 19/11); a shop's product page ties them: the size or colour is chosen on
it. Pinned here (`search_selection._join_variants`):

- the rows of one shop with one product page and titles that differ as a size or colour
  makes them differ are one card, at the cheapest, in its place;
- titles further apart on one page (a list page), another shop's page, a front page:
  kept apart;
- one product in several shops by its barcode, and its sizes at one of them: one card,
  "Lowest price of 2 shops";
- a search through the deployed page: the counter and "More" count products, not rows.

Every row is local test data: fictional brands and shops, `.invalid` URLs.
"""
from __future__ import annotations

import csv
import gzip
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
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.search_selection import _price_first_products  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402


def _ean(number: int) -> str:
    body = str(number).zfill(12)
    total = sum(int(char) * (3 if index % 2 else 1) for index, char in enumerate(body))
    return body + str((10 - total % 10) % 10)


def _offer(pid: str, price: float, title: str, link: str, *, shop: str = "Fixture Shoes", gtin: str = "") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=title, brand="Fixturon",
        category_text="Trainers", product_url=f"https://track.example.invalid/{pid}",
        image_url=f"https://cdn.example.invalid/{pid}.jpg", price_text=f"{price:.2f}",
        availability_text="in stock", currency="GBP",
        raw={"merchant_name": shop, "link": link, "ean": gtin},
    )


PAGE = "https://shoes.example.invalid/products/fixturon-runner"


def _ids(ordered) -> list[str]:
    return [entry.product.provider_product_id for entry in ordered]


class JoinTests(unittest.TestCase):
    def test_sizes_and_colours_on_one_page_are_one_card_at_the_cheapest(self) -> None:
        ordered = _price_first_products(
            [
                _offer("r1", 45.0, "Fixturon Runner White Size 9", f"{PAGE}?variant=1"),
                _offer("r2", 40.0, "Fixturon Runner Black Size 8", f"{PAGE}?variant=2"),
                _offer("r3", 42.0, "Fixturon Runner Black Size 10", f"{PAGE}?variant=3"),
                _offer("k1", 30.0, "Fixturon Kettle", "https://shoes.example.invalid/products/fixturon-kettle"),
            ]
        )
        self.assertEqual(_ids(ordered), ["k1", "r2"])
        self.assertEqual([entry.price for entry in ordered], [30.0, 40.0])
        self.assertEqual(ordered[1].shops, 1)

    def test_a_list_page_another_shop_or_a_front_page_keeps_them_apart(self) -> None:
        ordered = _price_first_products(
            [
                # One page, titles far apart: a shop's list page, not one product.
                _offer("l1", 10.0, "Fixturon Runner Black Size 8", PAGE),
                _offer("l2", 11.0, "Fixturon Garden Hose Reel With Wall Bracket", PAGE),
                # The same address at another shop.
                _offer("o1", 12.0, "Fixturon Runner Black Size 9", PAGE, shop="Fixture Other Shop"),
                # A front page names no product.
                _offer("f1", 13.0, "Fixturon Mug Red", "https://home.example.invalid/"),
                _offer("f2", 14.0, "Fixturon Mug Blue", "https://home.example.invalid/"),
            ]
        )
        self.assertEqual(_ids(ordered), ["l1", "l2", "o1", "f1", "f2"])

    def test_one_product_in_two_shops_and_its_sizes_at_one_is_one_card(self) -> None:
        code = _ean(500000000101)
        ordered = _price_first_products(
            [
                _offer("a8", 50.0, "Fixturon Runner Black Size 8", f"{PAGE}?variant=8", shop="Fixture Shoes"),
                _offer("a9", 50.0, "Fixturon Runner Black Size 9", f"{PAGE}?variant=9", shop="Fixture Shoes",
                       gtin=code),
                _offer("b9", 47.0, "Fixturon Runner Black UK 9", "https://other.example.invalid/p/runner-9",
                       shop="Fixture Other Shop", gtin=code),
            ]
        )
        self.assertEqual(_ids(ordered), ["b9"])
        self.assertEqual((ordered[0].price, ordered[0].shops), (47.0, 2))


_COLUMNS = ("advertiser_id", "advertiser_name", "id", "title", "description", "link", "image_link",
            "aw_deep_link", "google_product_category", "brand", "availability", "price", "condition")
_TRAINERS = "Apparel & Accessories > Shoes > Athletic Shoes"


def _row(pid: str, title: str, price: str, link: str, *, shop_id: str = "101", shop: str = "Fixture Shoes") -> dict:
    return {
        "advertiser_id": shop_id, "advertiser_name": shop, "id": pid, "title": title,
        "description": "Fictional trainers for local tests.", "link": link,
        "image_link": f"https://cdn.example.invalid/{pid}.jpg",
        "aw_deep_link": f"https://track.example.invalid/cread.php?awinmid={shop_id}&p={pid}",
        "google_product_category": _TRAINERS, "brand": "Fixturon", "availability": "in_stock",
        "price": price, "condition": "new",
    }


class SearchPageTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = Path(tempfile.mkdtemp())
        feed = folder / "google.csv.gz"
        rows = []
        # One trainer in two colours and four sizes: eight rows, one product page.
        for colour in ("Black", "White"):
            for size in ("7", "8", "9", "10"):
                rows.append(_row(f"r-{colour}-{size}", f"Fixturon Runner Trainers {colour} Size {size}", "39.99 GBP",
                                 f"{PAGE}?variant={colour}{size}"))
        for number, price in enumerate(("29.99 GBP", "49.99 GBP", "59.99 GBP")):
            rows.append(_row(f"t{number}", f"Fixturon Model {number} Trainers", price,
                             f"https://shoes.example.invalid/products/model-{number}"))
        with gzip.open(feed, "wt", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        saved = {name: os.environ.get(name) for name in ("AWIN_FEED_FILE", "AWIN_FEED_URL",
                                                         "PICWISE_PREPARED_CATALOGUE_FILE")}
        os.environ["AWIN_FEED_FILE"] = str(feed)
        os.environ.pop("AWIN_FEED_URL", None)
        os.environ.pop("PICWISE_PREPARED_CATALOGUE_FILE", None)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)

    def test_the_page_counts_products_not_rows(self) -> None:
        from api.index import app as wsgi_app

        page = b"".join(wsgi_app(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/search", "QUERY_STRING": urlencode({"q": "trainers", "shown": 8}),
             "wsgi.input": io.BytesIO(b""), "wsgi.url_scheme": "https"},
            lambda _status, _headers: None,
        )).decode("utf-8")
        text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", page)).split())
        prices = [html.unescape(price) for price in re.findall(r'<p class="pw-price">(.*?)</p>', page)]
        # Four products, the trainer once at £39.99: not eleven cards.
        self.assertEqual(sorted(prices), ["£29.99", "£39.99", "£49.99", "£59.99"])
        self.assertIn("4 of 4", text)
        self.assertEqual(text.count("Fixturon Runner Trainers"), 1)


if __name__ == "__main__":
    unittest.main()
