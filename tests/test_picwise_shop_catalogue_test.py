"""The one look at the shops whose rows a search could show but for a category.

`deployment/bot/shop_catalogue_test.py`. Owner, 2026-10-26: «ναι, ξεκίνα τη δοκιμή στα
56 καταστήματα»: per such shop, its robots.txt, then, only where it allows them and a
few seconds apart, its catalogue's first page (Shopify's `/products.json`), one of its
rows without a category (`/products/<name>.js`), and a page past the 5,000th product
for a large shop, else its collections. Pinned here: robots.txt read as RFC 9309 reads
it (this bot's own group before "*", the longest rule, "*" and "$"), the shop's address
taken from the Awin link's `ued` and no Awin link ever asked, a request robots.txt
disallows never made, the crawl-delay kept, what a catalogue says, and a redirect to
another site not followed.

Every row is local test data: fictional brands, `.invalid` hosts.
"""
from __future__ import annotations

import csv
import gzip
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_spec = importlib.util.spec_from_file_location("shop_catalogue_test", ROOT / "deployment" / "bot" / "shop_catalogue_test.py")
bot = importlib.util.module_from_spec(_spec)
# Its dataclasses look their module up while it loads.
sys.modules[_spec.name] = bot
_spec.loader.exec_module(bot)

_SHOPIFY_ROBOTS = """# we use Shopify as our ecommerce platform
User-agent: *
Disallow: /admin
Disallow: /cart
Disallow: /collections/*sort_by*
Disallow: /*/collections/*sort_by*
Disallow: /search
Allow: /search/
Disallow: /*preview_theme_id*
Sitemap: https://shop-one.example.invalid/sitemap.xml
"""


class RobotsTests(unittest.TestCase):
    def test_a_shopify_robots_allows_its_catalogue(self) -> None:
        rules, delay = bot.robots_rules(_SHOPIFY_ROBOTS)
        self.assertIsNone(delay)
        for target, allowed in (
            ("/products.json?limit=250", True),
            ("/products/fixturon-zip-hoodie.js", True),
            ("/collections.json?limit=250", True),
            ("/collections/all?sort_by=price-ascending", False),
            ("/en-gb/collections/all?sort_by=price", False),
            ("/search?q=kettle", False),
            ("/search/", True),
            ("/cart", False),
        ):
            with self.subTest(target=target):
                self.assertEqual(bot.robots_allows(rules, target), allowed)

    def test_its_own_group_before_everyone_s(self) -> None:
        text = (
            "User-agent: *\nCrawl-delay: 5\nDisallow: /search\n\n"
            "User-agent: Googlebot\nUser-agent: PicWiseBot\nDisallow: /products.json\nCrawl-delay: 7\n"
        )
        rules, delay = bot.robots_rules(text)
        self.assertEqual(delay, 7.0)
        self.assertFalse(bot.robots_allows(rules, "/products.json?limit=250"))
        # Only its own group counts: "*" disallows the search, this group does not.
        self.assertTrue(bot.robots_allows(rules, "/search?q=kettle"))

    def test_the_longest_rule_and_an_end(self) -> None:
        rules, _delay = bot.robots_rules(
            "User-agent: *\nDisallow: /\nAllow: /products/\nDisallow: /products/*.js$\nDisallow: /*.json$\n"
        )
        self.assertTrue(bot.robots_allows(rules, "/products/fixturon-zip-hoodie"))
        self.assertFalse(bot.robots_allows(rules, "/products/fixturon-zip-hoodie.js"))
        self.assertTrue(bot.robots_allows(rules, "/products/fixturon-zip-hoodie.json"))
        self.assertFalse(bot.robots_allows(rules, "/products.json?limit=250"))
        # The longest rule decides, not the last: "/products/" is longer than "/*.json$".
        self.assertTrue(bot.robots_allows(rules, "/products/fixturon-zip-hoodie.js?x=.json"))

    def test_an_empty_disallow_and_no_rules_allow_all(self) -> None:
        for text in ("User-agent: *\nDisallow:\n", "", "Disallow: /\n"):
            with self.subTest(text=text):
                rules, _delay = bot.robots_rules(text)
                self.assertTrue(bot.robots_allows(rules, "/products.json?limit=250"))
        # As long as each other: the Allow.
        rules, _delay = bot.robots_rules("User-agent: *\nDisallow: /products\nAllow: /products\n")
        self.assertTrue(bot.robots_allows(rules, "/products.json"))


class ProductNameTests(unittest.TestCase):
    def test_the_name_after_the_last_products(self) -> None:
        for path, name in (
            ("/products/fixturon-zip-hoodie", "fixturon-zip-hoodie"),
            ("/collections/beds/products/Fixturon-Bed-Frame", "fixturon-bed-frame"),
            ("/en-gb/products/fixturon%20lamp", "fixturon lamp"),
            ("/products", ""),
            ("/fixturon-kettle.html", ""),
        ):
            with self.subTest(path=path):
                self.assertEqual(bot.product_name(path), name)


def _awin(address: str) -> str:
    return f"https://www.awin1.com/cread.php?awinmid=1001&awinaffid=999&ued={quote(address, safe='')}"


_FEED = (
    # Shop One: two rows without a category, one with; its address is the Awin link's `ued`.
    ("Fixture Shop One", _awin("https://shop-one.example.invalid/products/fixturon-zip-hoodie?variant=1"),
     "Fixturon Zip Hoodie", "in_stock", ""),
    ("Fixture Shop One", _awin("https://shop-one.example.invalid/products/fixturon-aurora"),
     "Fixturon Aurora 1.7L", "in stock", ""),
    ("Fixture Shop One", _awin("https://shop-one.example.invalid/products/fixturon-glass-kettle"),
     "Fixturon Glass Kettle", "in_stock", "Home & Garden > Kitchen & Dining > Kitchen Appliances > Kettles"),
    # Shop Two: out of stock, one address under a collection.
    ("Fixture Shop Two", _awin("https://www.shop-two.example.invalid/products/fixturon-desk-lamp"),
     "Fixturon Desk Lamp", "out_of_stock", ""),
    ("Fixture Shop Two", _awin("https://www.shop-two.example.invalid/collections/beds/products/fixturon-bed-frame"),
     "Fixturon Bed Frame", "out_of_stock", ""),
    # Shop Three: an Awin link that carries no address of the shop.
    ("Fixture Shop Three", "https://www.awin1.com/pclick.php?p=12345&a=999&m=1003", "Fixturon Mug", "in_stock", ""),
    # Shop Four: none of its rows a search could show but for a category.
    ("Fixture Shop Four", _awin("https://shop-four.example.invalid/products/fixturon-toaster"),
     "Fixturon Toaster", "in_stock", ""),
)

_NOTE = {
    "prepared": True,
    "intake": {
        "shops": [
            {"shop": "Fixture Shop Two", "without_category": {"shown_by_title": 2, "shown_by_type": 0}},
            {"shop": "Fixture Shop One", "without_category": {"shown_by_title": 3, "shown_by_type": 0}},
            {"shop": "Fixture Shop Three", "without_category": {"shown_by_title": 1, "shown_by_type": 0}},
            {"shop": "Fixture Shop Four", "without_category": {"shown_by_title": 0, "shown_by_type": 0}},
        ]
    },
}

_CATALOGUE = {
    "products": [
        {"handle": "fixturon-zip-hoodie", "title": "Fixturon Zip Hoodie", "product_type": "Hoodies",
         "tags": ["winter"], "variants": [{"available": True}]},
        {"handle": "fixturon-aurora", "title": "Fixturon Aurora 1.7L", "product_type": "Kettles", "tags": [],
         "variants": [{"available": False}]},
        {"handle": "fixturon-glass-kettle", "title": "Fixturon Glass Kettle", "product_type": "", "tags": "",
         "variants": [{}]},
        {"handle": "fixturon-pillow", "title": "Fixturon Feather Pillow", "product_type": "Hoodies",
         "tags": ["x"], "variants": [{"available": True}]},
    ]
}


def _json(data: object) -> object:
    return bot.Answer(200, "application/json; charset=utf-8", json.dumps(data).encode())


_ANSWERS = {
    "https://shop-one.example.invalid/robots.txt": bot.Answer(200, "text/plain", _SHOPIFY_ROBOTS.encode()),
    "https://shop-one.example.invalid/products.json?limit=250": _json(_CATALOGUE),
    "https://shop-one.example.invalid/products/fixturon-zip-hoodie.js": _json(
        {"title": "Fixturon Zip Hoodie", "type": "Hoodies", "available": True}
    ),
    "https://shop-one.example.invalid/products.json?limit=250&page=21": _json({"products": []}),
    "https://www.shop-two.example.invalid/robots.txt": bot.Answer(
        200, "text/plain",
        b"User-agent: *\nCrawl-delay: 5\n\nUser-agent: PicWiseBot\nDisallow: /products.json\nCrawl-delay: 7\n",
    ),
    "https://www.shop-two.example.invalid/collections.json?limit=250": bot.Answer(
        200, "text/html; charset=utf-8", b"<html>Enter the password</html>"
    ),
}


class AskTheShopsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        folder = Path(self.folder.name)
        self.note = folder / "prepared.json"
        self.note.write_text(json.dumps(_NOTE))
        self.cache = folder / "cache"
        self.cache.mkdir()
        text = io.StringIO()
        writer = csv.writer(text)
        writer.writerow(("advertiser_name", "aw_deep_link", "title", "availability", "google_product_category",
                         "price", "image_link"))
        for shop, link, title, availability, category in _FEED:
            writer.writerow((shop, link, title, availability, category, "19.99 GBP",
                             "https://images.example.invalid/1.jpg"))
        (self.cache / "picwise_awin_feed_0123456789abcdef0123.bin").write_bytes(gzip.compress(text.getvalue().encode()))
        # A download being written is never read.
        (self.cache / "picwise_awin_feed_0123456789abcdef0123.bin.part77").write_bytes(b"not a feed")
        self.asked: list[str] = []
        self.slept: list[float] = []

    def tearDown(self) -> None:
        self.folder.cleanup()

    def _run(self) -> tuple[int, str]:
        def fetch(url: str, limit: int) -> object:
            self.asked.append(url)
            return _ANSWERS.get(url, bot.Answer(404, "text/html"))

        out = io.StringIO()
        with redirect_stdout(out):
            code = bot.main(
                ["--note", str(self.note), "--cache-dir", str(self.cache), "--pause", "1.5", "--large-shop", "2"],
                fetch=fetch, sleep=self.slept.append,
            )
        return code, out.getvalue()

    def test_only_what_robots_allows_at_its_pace_never_an_awin_link(self) -> None:
        code, _out = self._run()
        self.assertEqual(code, 0)
        self.assertEqual(
            self.asked,
            [
                "https://shop-one.example.invalid/robots.txt",
                "https://shop-one.example.invalid/products.json?limit=250",
                "https://shop-one.example.invalid/products/fixturon-zip-hoodie.js",
                "https://shop-one.example.invalid/products.json?limit=250&page=21",
                # Its own group disallows the catalogue; the row's own page and the
                # collections are asked, its crawl-delay apart.
                "https://www.shop-two.example.invalid/robots.txt",
                "https://www.shop-two.example.invalid/products/fixturon-desk-lamp.js",
                "https://www.shop-two.example.invalid/collections.json?limit=250",
            ],
        )
        self.assertEqual(self.slept, [1.5, 1.5, 1.5, 7.0, 7.0])
        self.assertFalse([url for url in self.asked if "awin" in url])

    def test_what_each_shop_says(self) -> None:
        _code, out = self._run()
        lines = out.splitlines()
        self.assertEqual(
            lines[0],
            "the feed's copy of " + lines[0].split("the feed's copy of ")[1].split(",")[0]
            + ", 0 MB: 7 rows read; 3 shops with rows a search could show but for a category, 6 such rows",
        )
        shop_one = out.split("== Fixture Shop One")[1].split("==")[0].splitlines()
        self.assertEqual(
            shop_one,
            [
                ": 3 rows a search could show but for a category (in the feed's copy: 3 rows, 2 without a category)",
                "   host: shop-one.example.invalid (1 host in its rows)",
                "   robots.txt: read; crawl-delay: none",
                "   /products.json: a catalogue of 4 products; a type 3 (75.0%), tags 2; stock said 3, in stock 2",
                (
                    # The title alone reads the pillow as a pillow; its type, "Hoodies", decides.
                    "      a kind from type and title 4 (100.0%), the title alone 3 (75.0%); the type adds 1, "
                    "they differ 1"
                ),
                "      in the feed 3, of them without a category 2",
                "      types: Hoodies (2); Kettles (1)",
                (
                    '   /products/<name>.js (a row without a category): type "Hoodies"; a kind: hoodie '
                    "(the title alone: hoodie); in stock: yes"
                ),
                "   /products.json page 21 (products 5,001 to 5,250): 0 products",
            ],
        )
        shop_two = out.split("== Fixture Shop Two")[1].split("==")[0].splitlines()
        self.assertEqual(
            shop_two,
            [
                ": 2 rows a search could show but for a category (in the feed's copy: 2 rows, 2 without a category)",
                "   host: www.shop-two.example.invalid (1 host in its rows)",
                "   robots.txt: read; crawl-delay: 7 s",
                "   /products.json: not asked, robots.txt disallows it",
                "   /products/<name>.js (a row without a category): 404",
                "   /collections.json: 200, not JSON (text/html)",
            ],
        )
        self.assertIn(
            "        2  read       disallowed         -       -       -  404        -          not JSON     Fixture Shop Two",
            out,
        )
        self.assertIn(
            "== Fixture Shop Three: 1 rows a search could show but for a category (in the feed's copy: 1 rows, "
            "1 without a category)\n   no shop address in its rows: nothing asked",
            out,
        )
        self.assertNotIn("Fixture Shop Four", out)
        self.assertNotIn("awin", out.lower())
        self.assertTrue(
            out.rstrip().endswith(
                "in all: 3 shops, 6 rows a search could show but for a category; a catalogue answered for 1 shops "
                "(3 rows); a type on at least 80% of its first page for 0 shops (0 rows); requests 7"
            ),
            out,
        )

    def test_out_of_time_no_further_shop_is_asked(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = bot.main(
                ["--note", str(self.note), "--cache-dir", str(self.cache), "--budget", "0"],
                fetch=lambda url, limit: self.asked.append(url), sleep=self.slept.append,
            )
        self.assertEqual((code, self.asked), (0, []))
        self.assertIn("== Fixture Shop One: not asked, out of time", out.getvalue())
        self.assertIn("        3  no time    -", out.getvalue())

    def test_no_note_or_no_feed_copy_says_so(self) -> None:
        for missing in ("note", "copy"):
            with self.subTest(missing=missing):
                if missing == "note":
                    self.note.unlink()
                else:
                    self.note.write_text(json.dumps(_NOTE))
                    for copy in self.cache.glob("*.bin"):
                        copy.unlink()
                code, out = self._run()
                self.assertEqual(code, 1)
                self.assertEqual(
                    out.strip(),
                    "no note to read the shops from: FileNotFoundError" if missing == "note"
                    else "no copy of the feed in the download cache",
                )
        self.assertEqual(self.asked, [])


class _Shop(BaseHTTPRequestHandler):
    agents: list[str] = []

    def do_GET(self) -> None:  # noqa: N802
        _Shop.agents.append(self.headers.get("User-Agent", ""))
        if self.path == "/moved":
            self.send_response(301)
            self.send_header("Location", f"http://localhost:{self.server.server_address[1]}/products.json")
            self.end_headers()
            return
        if self.path == "/here":
            self.send_response(302)
            self.send_header("Location", "/products.json")
            self.end_headers()
            return
        body = b'{"products": []}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


class FetchTests(unittest.TestCase):
    def test_its_name_and_no_redirect_to_another_site(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Shop)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}"
            answer = bot.fetch(f"{base}/products.json")
            self.assertEqual((answer.status, answer.body, answer.error), (200, b'{"products": []}', ""))
            # The same site: followed.
            self.assertEqual(bot.fetch(f"{base}/here").status, 200)
            # Another site ("localhost" is not "127.0.0.1"): not followed.
            moved = bot.fetch(f"{base}/moved")
            self.assertEqual(moved.status, 0)
            self.assertEqual(moved.error, f"redirected to another site (localhost:{server.server_address[1]})")
            self.assertEqual(set(_Shop.agents), {bot.USER_AGENT})
            # The same site's redirect asked twice, the other site's once.
            self.assertEqual(len(_Shop.agents), 4)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
