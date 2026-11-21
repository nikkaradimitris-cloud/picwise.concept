"""The nightly shops' bot reads both Awin links' copies, and a second-link row's own address.

The second opinion of 2026-11-21 found in the night's note that the bot had read no shop
since 19/11: it read only the newest copy of the feed (`shop_catalogue_test.feed_copy`),
and since both links (19/11 evening) the download cache holds one copy per link, the
second link's the newest; the first link's shops were no longer in it, and the second
link's rows link through Awin's "pclick.php", which carries no address, so every one of
its shops ended "no address". With `shop_catalogue.STOCK_DAYS` at 3, no shop's own site
would have checked any stock from 23/11. The owner's rules: every shop's own site checks
its feed's stock (2026-11-12), and the rules of the first feed hold for the second
(2026-11-20). Pinned here: every copy of the feed written within `COPIES_APART_HOURS` of
the newest is read, never a partial one; a shop of either link is asked at its own
address, a second-link row's being its `merchant_deep_link`, never an Awin link; and a
shop not asked for lack of time keeps when it was last read, so that the next round asks
it first.

Every row is local test data: fictional brands, `.invalid` hosts. Nothing leaves the
machine: the answers are the test's own.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import unittest
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import test_picwise_shop_catalogue_bot as base  # noqa: E402  (its helpers; its tests stay its own)

bot = base.bot
look = bot.look
NOW = base.NOW
TODAY = base.TODAY
OFFICE = base.OFFICE
TOOLS = "https://tools.example.invalid"
FIRST_COLUMNS = base._COLUMNS
# Awin's own format, as the second link gives it: the link through Awin, and the shop's own.
SECOND_COLUMNS = ("aw_product_id", "product_name", "merchant_category", "aw_deep_link", "merchant_deep_link",
                  "aw_image_url", "search_price", "currency", "in_stock", "merchant_name", "merchant_id")


def _pclick(pid: str) -> str:
    return f"https://www.awin1.com/pclick.php?p={pid}&a=2&m=7"


def _second_row(pid: str, shop: str, own: str) -> list[str]:
    return [pid, f"Fixturon Tool {pid}", "Tools > Drills", _pclick(pid), own,
            f"https://fixture.example.invalid/img/{pid}.jpg", "30.00", "GBP", "1", shop, "7"]


def _write(path: Path, columns: tuple[str, ...], rows: list[list[str]], *, hours_ago: float = 0.0) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)
    when = time.time() - hours_ago * 3600
    os.utime(path, (when, when))


def _setup() -> Path:
    """A cache with the first link's copy, written minutes before the second link's, and
    a note naming the shops of both."""
    folder = Path(base.tempfile.mkdtemp())
    (folder / "cache").mkdir()
    _write(folder / "cache" / "picwise_awin_feed_first.bin", FIRST_COLUMNS, [
        base._row("p1", "Fixture Office Shop", f"{OFFICE}/products/p1"),
        base._row("p2", "Fixture Office Shop", base._awin(f"{OFFICE}/products/p2?variant=22")),
    ], hours_ago=0.1)
    _write(folder / "cache" / "picwise_awin_feed_second.bin", SECOND_COLUMNS, [
        _second_row("t1", "Fixture Tools Shop", f"{TOOLS}/products/t1?variant=5"),
        _second_row("t2", "Fixture Tools Shop", f"{TOOLS}/products/t2"),
        # Its own address given through Awin too: read from the link as text.
        _second_row("t3", "Fixture Tools Shop", base._awin(f"{TOOLS}/products/t3")),
        # No address of its own: nothing to ask.
        _second_row("z1", "Fixture Silent Shop", ""),
    ])
    shops = ["Fixture Office Shop", "Fixture Tools Shop", "Fixture Silent Shop"]
    note = {"intake": {"shops": [{"shop": name, "rows": 2} for name in shops]}}
    (folder / "prepared.json").write_text(json.dumps(note), encoding="utf-8")
    return folder


def _answers() -> dict[str, tuple[int, bytes]]:
    return {
        f"{OFFICE}/robots.txt": (200, b"User-agent: *\nDisallow: /cart\n"),
        f"{OFFICE}/products.json?limit=2&page=1": (200, base._products(("p1", "Kettles", [True]),
                                                                        ("p2", "Kettles", [False, True]))),
        f"{OFFICE}/products.json?limit=2&page=2": (200, base._products()),
        f"{TOOLS}/robots.txt": (404, b""),
        f"{TOOLS}/products.json?limit=2&page=1": (200, base._products(("t1", "Drills", [True]), ("t2", "Drills", [False]))),
        f"{TOOLS}/products.json?limit=2&page=2": (200, base._products(("t3", "Drills", [True]))),
    }


class FeedCopiesTests(unittest.TestCase):
    def test_every_links_copy_the_newest_first_never_an_old_or_partial_one(self) -> None:
        folder = _setup()
        cache = folder / "cache"
        # A copy of a link no longer read (its key changed), and a download not finished.
        _write(cache / "picwise_awin_feed_old.bin", FIRST_COLUMNS, [], hours_ago=look.COPIES_APART_HOURS + 2)
        (cache / "picwise_awin_feed_first.bin.part123").write_text("half", encoding="utf-8")
        self.assertEqual(
            [Path(path).name for path in look.feed_copies(str(cache))],
            ["picwise_awin_feed_second.bin", "picwise_awin_feed_first.bin"],
        )
        # Until 21/11 the bot read this one alone: the second link's.
        self.assertEqual(Path(look.feed_copy(str(cache))).name, "picwise_awin_feed_second.bin")

    def test_a_link_that_failed_to_download_is_still_read_while_the_preparation_reads_it(self) -> None:
        folder = _setup()
        _write(folder / "cache" / "picwise_awin_feed_first.bin", FIRST_COLUMNS, [], hours_ago=24)
        self.assertEqual(len(look.feed_copies(str(folder / "cache"))), 2)

    def test_no_copy_nothing_asked(self) -> None:
        folder = _setup()
        for path in (folder / "cache").iterdir():
            path.unlink()
        self.assertEqual(look.feed_copies(str(folder / "cache")), [])
        shops = base._Shops(_answers())
        output = base._round(folder, shops)
        self.assertIn("no copy of the feed", output)
        self.assertEqual(shops.asked, [])


class OwnAddressTests(unittest.TestCase):
    def test_the_links_own_else_the_rows_merchant_deep_link(self) -> None:
        own = bot.own_address
        self.assertEqual(own(base._awin(f"{OFFICE}/products/p2"), {}), f"{OFFICE}/products/p2")
        self.assertEqual(own(f"{OFFICE}/products/p1", {"merchant_deep_link": f"{TOOLS}/x"}), f"{OFFICE}/products/p1")
        self.assertEqual(own(_pclick("t1"), {"merchant_deep_link": f"{TOOLS}/products/t1"}), f"{TOOLS}/products/t1")
        self.assertEqual(own(_pclick("t3"), {"merchant_deep_link": base._awin(f"{TOOLS}/products/t3")}),
                         f"{TOOLS}/products/t3")
        self.assertEqual(own(_pclick("z1"), {}), "")
        self.assertEqual(own(_pclick("z1"), {"merchant_deep_link": "not a link"}), "")
        self.assertEqual(own(_pclick("z1"), {"merchant_deep_link": _pclick("z1")}), "")


class BothLinksRoundTests(unittest.TestCase):
    def test_the_shops_of_both_links_are_asked_at_their_own_addresses(self) -> None:
        folder = _setup()
        shops = base._Shops(_answers())
        output = base._round(folder, shops)
        entries = base._file(folder)["shops"]
        office, tools = entries["Fixture Office Shop"], entries["Fixture Tools Shop"]
        self.assertEqual(office["status"], "read")
        self.assertEqual(office["products"], {"p1": ["Kettles", 1, TODAY, []], "p2": ["Kettles", 1, TODAY, ["21"]]})
        self.assertEqual(tools["status"], "read")
        self.assertEqual(tools["products"], {
            "t1": ["Drills", 1, TODAY, []], "t2": ["Drills", 0, TODAY, ["21"]], "t3": ["Drills", 1, TODAY, []],
        })
        self.assertEqual(entries["Fixture Silent Shop"]["status"], "no address")
        self.assertIn(f"{TOOLS}/robots.txt", shops.asked)
        for url in shops.asked:
            self.assertNotIn("awin", url)
        self.assertIn("the feed's copies: 2, 6 rows read; 3 shops to ask, 3 of them in them, 2 with an address", output)
        # Shop names and counts; no shop's address.
        self.assertNotIn("example.invalid", output)

    def test_a_shop_in_both_links_is_read_from_both(self) -> None:
        folder = _setup()
        _write(folder / "cache" / "picwise_awin_feed_first.bin", FIRST_COLUMNS, [
            base._row("t4", "Fixture Tools Shop", base._awin(f"{TOOLS}/products/t4")),
        ], hours_ago=0.1)
        feed, read = bot.read_feeds(look.feed_copies(str(folder / "cache")), {"Fixture Tools Shop"})
        self.assertEqual(read, 5)
        tools = feed["Fixture Tools Shop"]
        self.assertEqual((tools.rows, sorted(tools.names)), (4, ["t1", "t2", "t3", "t4"]))
        self.assertEqual(dict(tools.hosts), {"tools.example.invalid": 4})


class OrderTests(unittest.TestCase):
    def test_a_shop_not_asked_for_lack_of_time_keeps_when_it_was_last_read(self) -> None:
        folder = _setup()
        before = (NOW - timedelta(days=2)).isoformat(timespec="seconds")
        bot.write(str(folder / "shops" / "catalogues.json.gz"), {"version": 1, "shops": {
            "Fixture Office Shop": {"status": "read", "read_at": before,
                                    "products": {"p1": ["Kettles", 1, (NOW.date() - timedelta(days=2)).isoformat(), []]}},
        }})
        shops = base._Shops(_answers())
        base._round(folder, shops, budget_minutes=0)
        self.assertEqual(shops.asked, [])
        entries = base._file(folder)["shops"]
        self.assertEqual((entries["Fixture Office Shop"]["status"], entries["Fixture Office Shop"]["read_at"]),
                         ("not asked, out of time", before))
        # What it knew is kept, with the day it was seen.
        self.assertEqual(entries["Fixture Office Shop"]["products"]["p1"][2], (NOW.date() - timedelta(days=2)).isoformat())
        # Never read: no time of a reading.
        self.assertEqual(entries["Fixture Tools Shop"]["read_at"], "")

    def test_the_next_round_asks_first_the_shops_read_longest_ago(self) -> None:
        folder = _setup()
        bot.write(str(folder / "shops" / "catalogues.json.gz"), {"version": 1, "shops": {
            "Fixture Office Shop": {"status": "read", "read_at": NOW.isoformat(timespec="seconds"), "products": {}},
            "Fixture Tools Shop": {"status": "not asked, out of time",
                                   "read_at": (NOW - timedelta(days=3)).isoformat(timespec="seconds"), "products": {}},
        }})
        shops = base._Shops(_answers())
        base._round(folder, shops)
        self.assertEqual(shops.asked[0], f"{TOOLS}/robots.txt")
        self.assertIn(f"{OFFICE}/robots.txt", shops.asked)


if __name__ == "__main__":
    unittest.main()
