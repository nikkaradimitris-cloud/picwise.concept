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

    def test_a_size_another_shop_sells_cheaper_is_a_card_of_its_own_and_marked(self) -> None:
        # The owner's rule 3 (2026-11-19): the shop with the sizes keeps its card, and
        # marks the size another shop sells alone, cheaper; that shop's card comes first.
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
        self.assertEqual(_ids(ordered), ["b9", "a8"])
        # Size 9 at two shops, the cheaper first: "Lowest price of 2 shops".
        self.assertEqual((ordered[0].price, ordered[0].shops, ordered[0].marks), (47.0, 2, ()))
        self.assertEqual((ordered[1].price, ordered[1].shops), (50.0, 1))
        self.assertEqual(ordered[1].marks, (("Size 9", "£47.00", "Fixture Other Shop"),))

    def test_a_size_another_shop_sells_dearer_stays_in_the_card(self) -> None:
        code = _ean(500000000101)
        ordered = _price_first_products(
            [
                _offer("a8", 50.0, "Fixturon Runner Black Size 8", f"{PAGE}?variant=8", shop="Fixture Shoes"),
                _offer("a9", 50.0, "Fixturon Runner Black Size 9", f"{PAGE}?variant=9", shop="Fixture Shoes",
                       gtin=code),
                _offer("b9", 55.0, "Fixturon Runner Black UK 9", "https://other.example.invalid/p/runner-9",
                       shop="Fixture Other Shop", gtin=code),
            ]
        )
        self.assertEqual(_ids(ordered), ["a8"])
        self.assertEqual((ordered[0].price, ordered[0].shops, ordered[0].marks), (50.0, 2, ()))

    def test_one_product_at_two_shops_without_variants_is_one_card(self) -> None:
        code = _ean(500000000101)
        ordered = _price_first_products(
            [
                _offer("a9", 50.0, "Fixturon Runner Black Size 9", f"{PAGE}?variant=9", shop="Fixture Shoes",
                       gtin=code),
                _offer("b9", 47.0, "Fixturon Runner Black UK 9", "https://other.example.invalid/p/runner-9",
                       shop="Fixture Other Shop", gtin=code),
            ]
        )
        self.assertEqual(_ids(ordered), ["b9"])
        self.assertEqual((ordered[0].price, ordered[0].shops), (47.0, 2))


class OwnPagesTests(unittest.TestCase):
    """Each variant a product of its own, on a page of its own (owner, 2026-11-19, rule 2)."""

    def setUp(self) -> None:
        saved = os.environ.get("PICWISE_FAMILIES_FILE")
        self.folder = Path(tempfile.mkdtemp())

        def restore() -> None:
            if saved is None:
                os.environ.pop("PICWISE_FAMILIES_FILE", None)
            else:
                os.environ["PICWISE_FAMILIES_FILE"] = saved

        self.addCleanup(restore)
        os.environ.pop("PICWISE_FAMILIES_FILE", None)

    def _offers(self) -> list[ProviderProduct]:
        return [
            _offer("s1", 20.0, "Fixturon Tracksuit Navy - S", "https://shoes.example.invalid/products/tracksuit-navy-s"),
            _offer("s2", 22.0, "Fixturon Tracksuit Navy - 2XL", "https://shoes.example.invalid/products/tracksuit-navy-2xl"),
            _offer("g1", 21.0, "Fixturon Tracksuit Grey - S", "https://shoes.example.invalid/products/tracksuit-grey-s"),
        ]

    def test_sizes_on_pages_of_their_own_are_one_card_a_colour_waits_for_the_ai(self) -> None:
        ordered = _price_first_products(self._offers())
        # Navy S and 2XL: one card; grey, a colour apart, stays apart until the AI says.
        self.assertEqual(_ids(ordered), ["s1", "g1"])

    def test_the_ai_s_family_joins_the_colours(self) -> None:
        import json

        path = self.folder / "families.json"
        path.write_text(json.dumps({"sets": {"x": [[1, 2]]}, "families": {
            "fixture shoes\x1fs1": "x-0", "fixture shoes\x1fs2": "x-0", "fixture shoes\x1fg1": "x-0",
        }}), encoding="utf-8")
        os.environ["PICWISE_FAMILIES_FILE"] = str(path)
        from picwise_providers import variant_families

        variant_families._FAMILIES = variant_families._Families()
        ordered = _price_first_products(self._offers())
        self.assertEqual(_ids(ordered), ["s1"])
        self.assertEqual(ordered[0].price, 20.0)


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
    """The page as a buyer sees it."""

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
        # Its colours and sizes named on its card, chosen at the shop (owner, 2026-11-19).
        self.assertIn("Colours at the shop: Black, White", text)
        self.assertIn("Sizes at the shop: 7, 8, 9, 10", text)
        self.assertEqual(page.count('class="pw-card-variants"'), 2)



class CheaperElsewherePageTests(unittest.TestCase):
    """The owner's rule 3 on the page: «πράσινο φθηνότερο στο (α) κατάστημα»."""

    def setUp(self) -> None:
        folder = Path(tempfile.mkdtemp())
        feed = folder / "google.csv.gz"
        columns = (*_COLUMNS, "gtin")
        rows = []
        for number, colour in enumerate(("Black", "White")):
            for size in ("8", "9"):
                row = _row(f"r-{colour}-{size}", f"Fixturon Runner Trainers {colour} Size {size}", "39.99 GBP",
                           f"{PAGE}?variant={colour}{size}")
                row["gtin"] = _ean(500000000200 + number * 10 + int(size))
                rows.append(row)
        # Another shop sells the white size 9 alone, cheaper.
        other = _row("o-white-9", "Fixturon Runner Trainers White UK 9", "35.00 GBP",
                     "https://othershoes.example.invalid/p/runner-white-9", shop_id="303", shop="Fixture Other Shoes")
        other["gtin"] = _ean(500000000219)
        rows.append(other)
        for number, price in enumerate(("29.99 GBP", "49.99 GBP")):
            row = _row(f"t{number}", f"Fixturon Model {number} Trainers", price,
                       f"https://shoes.example.invalid/products/model-{number}")
            row["gtin"] = ""
            rows.append(row)
        with gzip.open(feed, "wt", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
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

    def test_the_cheaper_shop_s_card_comes_first_and_the_card_with_the_variants_marks_it(self) -> None:
        from api.index import app as wsgi_app

        page = b"".join(wsgi_app(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/search", "QUERY_STRING": urlencode({"q": "trainers", "shown": 8}),
             "wsgi.input": io.BytesIO(b""), "wsgi.url_scheme": "https"},
            lambda _status, _headers: None,
        )).decode("utf-8")
        titles = [html.unescape(title) for title in re.findall(r'<h2 [^>]*class="pw-card-title">(.*?)</h2>', page)]
        prices = [html.unescape(price) for price in re.findall(r'<p class="pw-price">(.*?)</p>', page)]
        cards = dict(zip(titles, prices))
        self.assertEqual(cards["Fixturon Runner Trainers White UK 9"], "£35.00")
        self.assertEqual(cards["Fixturon Runner Trainers Black Size 8"], "£39.99")
        marks = [html.unescape(line) for line in re.findall(r'<p class="pw-card-cheaper">(.*?)</p>', page)]
        self.assertEqual(marks, ["White, Size 9 is £35.00 at Fixture Other Shoes"])
        text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", page)).split())
        self.assertIn("Colours at the shop: Black, White", text)
        self.assertIn("4 of 4", text)


if __name__ == "__main__":
    unittest.main()
