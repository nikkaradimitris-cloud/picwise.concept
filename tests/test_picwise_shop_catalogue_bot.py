"""The nightly bot that asks the shops whose rows carry no category for their catalogue.

`deployment/bot/shop_catalogue_bot.py`. Owner, 2026-10-26: «Θα κάνεις το 2 και το 3»,
the second being the bot for the 55 shops other than InStock UK: each night after the
feed, per shop its robots.txt, then its Shopify catalogue (250 products a request, at
most 200 requests a shop a round), the shop's own type and each product's stock, kept on
the server, never in Supabase; never an Awin link. Pinned here: which shops are asked
(the note's, and the ones the file knows; never InStock UK or a left-out shop), only
what robots.txt allows, the pause, the cap a round and the round after going on where
it stopped, what is kept of each product (only the feed's products; forgotten after
`KEEP_DAYS`), a file the preparation reads, and no address printed.

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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
BOT = ROOT / "deployment" / "bot"
for path in (ROOT, SRC, BOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_spec = importlib.util.spec_from_file_location("shop_catalogue_bot", BOT / "shop_catalogue_bot.py")
bot = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = bot
_spec.loader.exec_module(bot)

from picwise_providers.shop_catalogue import load_shop_catalogues  # noqa: E402

NOW = datetime(2026, 10, 27, 3, 40, tzinfo=timezone.utc)
TODAY = NOW.date().isoformat()
OFFICE = "https://office.example.invalid"
_COLUMNS = ("aw_product_id", "product_name", "merchant_category", "aw_deep_link", "aw_image_url", "search_price",
            "currency", "in_stock", "merchant_name")


def _row(pid: str, shop: str, url: str, category: str = "") -> list[str]:
    return [pid, f"Fixturon Thing {pid}", category, url, f"https://fixture.example.invalid/img/{pid}.jpg", "20.00",
            "GBP", "1", shop]


def _awin(address: str) -> str:
    return "https://www.awin1.com/cread.php?awinmid=1&awinaffid=2&ued=" + quote(address, safe="")


def _products(*entries: tuple[str, str, list[bool]]) -> bytes:
    return json.dumps({"products": [
        {"handle": handle, "title": f"Fixturon {handle}", "product_type": product_type,
         "variants": [{"id": 10 * index + number, "available": available}
                      for number, available in enumerate(stock, start=1)]}
        for index, (handle, product_type, stock) in enumerate(entries, start=1)
    ]}).encode()


class _Shops:
    """The test's shops: what each address answers, and every request made."""

    def __init__(self, answers: dict[str, tuple[int, bytes]]) -> None:
        self.answers = answers
        self.asked: list[str] = []
        self.slept: list[float] = []

    def fetch(self, url: str, limit: int) -> "bot.look.Answer":
        self.asked.append(url)
        status, body = self.answers.get(url, (404, b"not here"))
        content_type = "application/json" if body[:1] in (b"{", b"[") else "text/plain"
        return bot.look.Answer(status, content_type, body[:limit])

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)


def _setup(case: unittest.TestCase, *, extra_note_shops: tuple[str, ...] = (), more_products: int = 0) -> Path:
    folder = Path(tempfile.mkdtemp())
    (folder / "cache").mkdir()
    rows = [
        _row("p1", "Fixture Office Shop", f"{OFFICE}/products/p1"),
        _row("p2", "Fixture Office Shop", _awin(f"{OFFICE}/products/p2?variant=22")),
        _row("p3", "Fixture Office Shop", f"{OFFICE}/products/p3", category="Kettles"),
        _row("p4", "Fixture Office Shop", f"{OFFICE}/products/p4"),
        *(_row(f"p{number}", "Fixture Office Shop", f"{OFFICE}/products/p{number}")
          for number in range(5, 5 + more_products)),
        _row("l1", "Fixture Locked Shop", "https://locked.example.invalid/products/l1"),
        _row("n1", "Fixture Plain Shop", "https://plain.example.invalid/item/n1"),
        _row("a1", "Fixture Awin Shop", "https://www.awin1.com/pclick.php?p=1&a=2&m=3"),
        _row("i1", "InStock UK", "https://instock.example.invalid/products/i1"),
        _row("d1", "So Divine", "https://divine.example.invalid/products/d1"),
    ]
    with (folder / "cache" / "picwise_awin_feed_1.bin").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(_COLUMNS)
        writer.writerows(rows)
    shops = ["Fixture Office Shop", "Fixture Locked Shop", "Fixture Plain Shop", "Fixture Awin Shop", "InStock UK",
             "So Divine", *extra_note_shops]
    note = {"intake": {"shops": [{"shop": name, "without_category": {"shown_by_title": 1}} for name in shops]}}
    (folder / "prepared.json").write_text(json.dumps(note), encoding="utf-8")
    return folder


def _answers(*, robots: bytes = b"User-agent: *\nDisallow: /cart\n") -> dict[str, tuple[int, bytes]]:
    return {
        f"{OFFICE}/robots.txt": (200, robots),
        f"{OFFICE}/products.json?limit=2&page=1": (200, _products(("p1", "Kettles", [True]),
                                                                   ("p2", "Designer", [False, True]))),
        f"{OFFICE}/products.json?limit=2&page=2": (200, _products(("p3", "", [False, False]), ("x9", "Kettles", [True]))),
        f"{OFFICE}/products.json?limit=2&page=3": (200, _products(("p4", "Toasters", [True]))),
        "https://locked.example.invalid/robots.txt": (200, b"User-agent: *\nDisallow: /products.json\n"),
        "https://plain.example.invalid/robots.txt": (404, b""),
    }


def _round(folder: Path, shops: _Shops, **options) -> str:
    output = io.StringIO()
    settings = {"page_size": 2, "now": NOW, "clock": lambda: 0.0}
    settings.update(options)
    with redirect_stdout(output):
        bot.run_round(note=str(folder / "prepared.json"), cache_dir=str(folder / "cache"),
                      catalogues=str(folder / "shops" / "catalogues.json.gz"), fetch=shops.fetch,
                      sleep=shops.sleep, workers=1, **settings)
    return output.getvalue()


def _file(folder: Path) -> dict:
    data, status = load_shop_catalogues(folder / "shops" / "catalogues.json.gz")
    assert status == "read", status
    return data


class RoundTests(unittest.TestCase):
    def test_a_round_reads_each_allowed_catalogue_and_keeps_the_feeds_products(self) -> None:
        folder = _setup(self)
        shops = _Shops(_answers())
        output = _round(folder, shops)
        office = _file(folder)["shops"]["Fixture Office Shop"]
        self.assertEqual(office["products"], {
            "p1": ["Kettles", 1, TODAY, []],
            # Variant ids are the test's own: ten times the place on its page, plus one.
            "p2": ["Designer", 1, TODAY, ["21"]],
            "p3": ["", 0, TODAY, ["11", "12"]],
            "p4": ["Toasters", 1, TODAY, []],
        })
        self.assertEqual((office["status"], office["next_page"], office["pages"], office["requests"]), ("read", 1, 3, 4))
        self.assertEqual(office["complete_at"], NOW.isoformat(timespec="seconds"))
        self.assertIn("Fixture Office Shop: read", output)
        # Shop names and counts; no shop's address (the bot's own user agent names its page).
        self.assertNotIn("example.invalid", output)
        self.assertNotIn("awin1", output)

    def test_only_what_robots_allows_and_never_an_awin_link_or_a_shop_left_alone(self) -> None:
        folder = _setup(self)
        shops = _Shops(_answers())
        _round(folder, shops)
        self.assertEqual(shops.asked[0], f"{OFFICE}/robots.txt")
        # The locked shop: its robots.txt only.
        self.assertEqual([url for url in shops.asked if "locked" in url], ["https://locked.example.invalid/robots.txt"])
        self.assertEqual(
            [url for url in shops.asked if "plain" in url],
            ["https://plain.example.invalid/robots.txt", "https://plain.example.invalid/products.json?limit=2&page=1"],
        )
        for url in shops.asked:
            self.assertNotIn("awin", url)
            self.assertNotIn("instock", url)
            self.assertNotIn("divine", url)
        entries = _file(folder)["shops"]
        self.assertEqual(entries["Fixture Locked Shop"]["status"], "robots.txt disallows the catalogue")
        self.assertEqual(entries["Fixture Plain Shop"]["status"], "catalogue 404")
        self.assertEqual(entries["Fixture Awin Shop"]["status"], "no address")
        self.assertNotIn("InStock UK", entries)
        self.assertNotIn("So Divine", entries)

    def test_the_pause_or_the_crawl_delay_before_each_page(self) -> None:
        folder = _setup(self)
        shops = _Shops(_answers())
        _round(folder, shops)
        self.assertEqual(shops.slept, [3.0, 3.0, 3.0, 3.0])
        folder = _setup(self)
        shops = _Shops(_answers(robots=b"User-agent: *\nCrawl-delay: 5\n"))
        _round(folder, shops)
        self.assertEqual(shops.slept[:3], [5.0, 5.0, 5.0])
        folder = _setup(self)
        shops = _Shops(_answers(robots=b"User-agent: *\nCrawl-delay: 120\n"))
        _round(folder, shops)
        self.assertEqual([url for url in shops.asked if "office" in url], [f"{OFFICE}/robots.txt"])
        self.assertEqual(_file(folder)["shops"]["Fixture Office Shop"]["status"], "crawl-delay too long")

    def test_a_round_stops_at_its_cap_and_the_next_goes_on_where_it_stopped(self) -> None:
        folder = _setup(self)
        shops = _Shops(_answers())
        _round(folder, shops, max_requests=3)
        office = _file(folder)["shops"]["Fixture Office Shop"]
        self.assertEqual((office["status"], office["next_page"], office["requests"]), ("read, goes on next round", 3, 3))
        self.assertEqual(sorted(office["products"]), ["p1", "p2", "p3"])
        self.assertEqual(office["complete_at"], "")
        shops = _Shops(_answers())
        _round(folder, shops, max_requests=3)
        self.assertIn(f"{OFFICE}/products.json?limit=2&page=3", shops.asked)
        self.assertNotIn(f"{OFFICE}/products.json?limit=2&page=1", shops.asked)
        office = _file(folder)["shops"]["Fixture Office Shop"]
        self.assertEqual((office["status"], office["next_page"]), ("read", 1))
        self.assertEqual(sorted(office["products"]), ["p1", "p2", "p3", "p4"])

    def test_a_shop_that_pages_no_further_is_read_as_far_as_it_lets(self) -> None:
        # Shopify answers 400 past page 100 (Back to the Office, run 40329354654).
        folder = _setup(self)
        answers = _answers()
        answers[f"{OFFICE}/products.json?limit=2&page=3"] = (400, b"")
        shops = _Shops(answers)
        _round(folder, shops)
        office = _file(folder)["shops"]["Fixture Office Shop"]
        self.assertEqual(
            (office["status"], office["next_page"], office["pages"], office["page_limit"]),
            ("read to the shop's page limit; its collections not listed (error 404)", 1, 2, 2),
        )
        self.assertEqual(office["complete_at"], NOW.isoformat(timespec="seconds"))
        # A round that went on from page 3 starts again from page 1, once.
        bot.write(str(folder / "shops" / "catalogues.json.gz"), {"version": 1, "shops": {
            "Fixture Office Shop": {"read_at": NOW.isoformat(), "next_page": 3, "products": {}},
        }})
        shops = _Shops(answers)
        _round(folder, shops)
        self.assertEqual(
            [url for url in shops.asked if url.startswith(f"{OFFICE}/products.json")],
            [f"{OFFICE}/products.json?limit=2&page={page}" for page in (3, 1, 2, 3)],
        )
        office = _file(folder)["shops"]["Fixture Office Shop"]
        self.assertEqual((office["next_page"], office["requests"]), (1, 6))
        self.assertEqual(sorted(office["products"]), ["p1", "p2", "p3"])

    def test_a_large_catalogue_is_read_on_by_its_collections(self) -> None:
        # Owner, 2026-10-26: «Ναι» to reading Back to the Office by its collections.
        folder = _setup(self, more_products=3)
        answers = _answers()
        answers.update({
            f"{OFFICE}/products.json?limit=2&page=3": (400, b""),
            f"{OFFICE}/collections.json?limit=2&page=1": (200, json.dumps({"collections": [
                {"handle": "kettles", "products_count": 3}, {"handle": "all", "products_count": 9}]}).encode()),
            f"{OFFICE}/collections.json?limit=2&page=2": (200, json.dumps({"collections": [
                {"handle": "toasters", "products_count": 1}, {"handle": "huge", "products_count": 30_000}]}).encode()),
            f"{OFFICE}/collections.json?limit=2&page=3": (200, b'{"collections": []}'),
            f"{OFFICE}/collections/kettles/products.json?limit=2&page=1": (
                200, _products(("p4", "Toasters", [True]), ("p5", "Kettles", [True]))),
            f"{OFFICE}/collections/kettles/products.json?limit=2&page=2": (200, _products(("p6", "Kettles", [False]))),
            f"{OFFICE}/collections/toasters/products.json?limit=2&page=1": (200, _products(("p7", "Toasters", [True]))),
        })
        shops = _Shops(answers)
        _round(folder, shops)
        office = _file(folder)["shops"]["Fixture Office Shop"]
        self.assertEqual(office["status"], "read to the shop's page limit; its 4 collections read")
        self.assertEqual(sorted(office["products"]), ["p1", "p2", "p3", "p4", "p5", "p6", "p7"])
        self.assertEqual(office["products"]["p6"][1], 0)
        self.assertEqual((office["requests"], office["collections"], office["collection_cursor"]), (10, [], [0, 1]))
        for url in shops.asked:
            self.assertNotIn("/collections/all/", url)
            self.assertNotIn("/collections/huge/", url)
        # The next round pages the catalogue only to its limit, lists the collections
        # again, and stops at its cap...
        shops = _Shops(answers)
        _round(folder, shops, max_requests=6)
        self.assertNotIn(f"{OFFICE}/products.json?limit=2&page=3", shops.asked)
        office = _file(folder)["shops"]["Fixture Office Shop"]
        self.assertEqual(office["status"], "read to the shop's page limit; its collections read to 0 of 4, goes on next round")
        self.assertEqual(office["collection_cursor"], [0, 1])
        # ...and the one after goes on with the collections, without listing them again.
        shops = _Shops(answers)
        _round(folder, shops, max_requests=10)
        self.assertEqual(
            [url[len(OFFICE):] for url in shops.asked if "/collections" in url],
            ["/collections/kettles/products.json?limit=2&page=1", "/collections/kettles/products.json?limit=2&page=2",
             "/collections/toasters/products.json?limit=2&page=1"],
        )
        office = _file(folder)["shops"]["Fixture Office Shop"]
        self.assertEqual(office["status"], "read to the shop's page limit; its 4 collections read")

    def test_out_of_time_no_shop_is_started(self) -> None:
        folder = _setup(self)
        shops = _Shops(_answers())
        _round(folder, shops, budget_minutes=0)
        self.assertEqual(shops.asked, [])
        self.assertEqual(_file(folder)["shops"]["Fixture Office Shop"]["status"], "not asked, out of time")

    def test_a_product_not_seen_for_long_is_forgotten(self) -> None:
        folder = _setup(self)
        old = (NOW.date() - timedelta(days=bot.KEEP_DAYS + 1)).isoformat()
        recent = (NOW.date() - timedelta(days=10)).isoformat()
        bot.write(str(folder / "shops" / "catalogues.json.gz"), {"version": 1, "shops": {
            "Fixture Locked Shop": {"read_at": NOW.isoformat(), "products": {"l1": ["Kettles", 1, recent, []]}},
            "Fixture Office Shop": {"read_at": NOW.isoformat(), "products": {"p1": ["Kettles", 1, old, []]}},
            "Fixture Gone Shop": {"read_at": f"{old}T03:40:00+00:00", "products": {"g1": ["Kettles", 1, old, []]}},
        }})
        shops = _Shops({**_answers(), f"{OFFICE}/products.json?limit=2&page=1": (500, b"")})
        _round(folder, shops)
        entries = _file(folder)["shops"]
        # Not asked again (robots.txt disallows), so kept while recent.
        self.assertEqual(entries["Fixture Locked Shop"]["products"], {"l1": ["Kettles", 1, recent, []]})
        # Its catalogue failed, and what it had was too old.
        self.assertEqual(entries["Fixture Office Shop"]["products"], {})
        self.assertEqual(entries["Fixture Office Shop"]["status"], "catalogue 500")
        # A shop no longer in the feed, read long ago.
        self.assertNotIn("Fixture Gone Shop", entries)

    def test_a_shop_the_file_knows_is_asked_again_though_the_note_no_longer_names_it(self) -> None:
        folder = _setup(self)
        note = {"intake": {"shops": []}}
        (folder / "prepared.json").write_text(json.dumps(note), encoding="utf-8")
        bot.write(str(folder / "shops" / "catalogues.json.gz"), {"version": 1, "shops": {
            "Fixture Office Shop": {"read_at": NOW.isoformat(), "products": {}},
        }})
        shops = _Shops(_answers())
        _round(folder, shops)
        self.assertIn(f"{OFFICE}/products.json?limit=2&page=1", shops.asked)
        self.assertEqual(sorted(_file(folder)["shops"]), ["Fixture Office Shop"])

    def test_a_shop_answering_every_page_alike_ends_its_catalogue(self) -> None:
        folder = _setup(self)
        same = _products(("p1", "Kettles", [True]), ("p2", "Designer", [True]))
        answers = _answers()
        for page in (1, 2, 3):
            answers[f"{OFFICE}/products.json?limit=2&page={page}"] = (200, same)
        shops = _Shops(answers)
        _round(folder, shops)
        office = _file(folder)["shops"]["Fixture Office Shop"]
        self.assertEqual((office["pages"], office["next_page"], office["status"]), (2, 1, "read"))


if __name__ == "__main__":
    unittest.main()
