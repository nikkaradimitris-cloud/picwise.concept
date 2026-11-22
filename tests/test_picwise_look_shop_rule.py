"""The look before the «ανέβασε» of how many of a shop's products pass
(`deployment/server/look_shop_rule.py`, `deployment/server/look_bot_rule.py`; the checks'
rules 19.7.1; owner, 2026-11-22: what the bot scans of a shop passes, 20,000 the most).

Pinned here, on a feed and a catalogue of the test's own (nothing leaves the machine, no
shop is asked): the preparation run by the look is the preparation's own, with the caps
counted where they are worked out: per shop what a card can show, what was shown the night
before, what the shops' rule keeps and what is kept in the end; with the switch off no shop
is capped; the summary of a catalogue and the two set side by side; the kinds and the
searches compared; the look at the bot reads the processes, the order and the night's file
and asks no shop; what is printed holds counts, names, titles and prices, never a link or
an id.

Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "deployment" / "server", ROOT / "deployment" / "bot", ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import look_bot_rule  # noqa: E402
import look_shop_rule  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_providers import shop_cap  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category", "aw_deep_link",
    "aw_image_url", "search_price", "currency", "in_stock", "merchant_name", "description", "data_provenance", "ean",
)


def _ean(number: int) -> str:
    body = str(number).zfill(12)
    total = sum(int(char) * (3 if index % 2 else 1) for index, char in enumerate(body))
    return body + str((10 - total % 10) % 10)


def _row(pid: str, title: str, price: float, shop: str, *, kind: str = "Kettles", code: int = 0) -> list[str]:
    return [
        pid, title, title.split()[0], kind, "Kitchen Appliances" if kind == "Kettles" else "Computers",
        f"https://fixture.example.invalid/out/{pid}", f"https://fixture.example.invalid/img/{pid}.jpg",
        f"{price:.2f}", "GBP", "1", shop, fixture_description(), "local_test_fixture",
        _ean(500000007000 + code) if code else "",
    ]


def _feed(path: Path) -> Path:
    """A large shop of nine kettles and three laptops, and a small one of four kettles."""
    rows = [_row(f"b{n}", f"Fixturon Electric Kettle {n} 1.7L", 15.0 + 5 * n, "Fixture Big Store", code=n) for n in range(1, 10)]
    rows += [_row(f"n{n}", f"Fixturon Notebook Laptop {n} 15 inch", 300.0 + 25 * n, "Fixture Big Store", kind="Laptops", code=40 + n)
             for n in range(1, 4)]
    rows += [_row(f"s{n}", f"Sampleworks Electric Kettle {n} 1.0L", 11.0 + n, "Fixture Small Store", code=60 + n) for n in range(1, 5)]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(_COLUMNS)
        writer.writerows(rows)
    return path


def _product(number: int, shop: str, category: str = "Home & Garden > Kitchen") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin", provider_product_id=f"{shop.lower()}-{number}", title=f"Zentra thing {number}", brand="Zentra",
        category_text=category, product_url=f"https://{shop.lower()}.invalid/p/{number}",
        image_url=f"https://{shop.lower()}.invalid/i/{number}.jpg", price_text=f"{10 + number:.2f}",
        availability_text="in stock", currency="GBP", raw={"merchant_name": shop, "availability": "in stock"},
    )


class TheCapsCounted(unittest.TestCase):
    def setUp(self) -> None:
        self.products = [_product(n, "Big") for n in range(6)] + [_product(n, "Small", "Electronics > Audio") for n in range(2)]
        self.kinds = [frozenset({"kettle"})] * 4 + [frozenset({"__uncertain_kind__"})] * 2 + [frozenset({"speaker", "__mark__"})] * 2

    def test_by_shop_category_and_kind(self) -> None:
        from picwise_providers.catalogue_cap import row_key

        shop_keep = [True, True, True, False, False, False, True, True]
        keep = [True, True, False, False, False, False, True, True]
        pool = {row_key(self.products[0]), row_key(self.products[3]), row_key(self.products[6])}
        counts = look_shop_rule.count_caps(self.products, self.kinds, shop_keep=shop_keep, keep=keep, pool=pool,
                                           shop_candidates=[4, 5], cap_candidates=[2])
        self.assertEqual((counts["products"], counts["after_the_shops_rule"], counts["kept"], counts["pool"]), (8, 5, 4, 3))
        self.assertFalse(counts["cap_failed"])
        # can show, shown the night before, after the shops' rule, kept, shown before and
        # left out by the rule, the rule's candidates, the category cap's candidates.
        self.assertEqual(counts["shops"]["Big"], [6, 2, 3, 2, 1, 2, 1])
        self.assertEqual(counts["shops"]["Small"], [2, 1, 2, 2, 0, 0, 0])
        self.assertEqual(sum(entry[0] for entry in counts["categories"].values()), 8)
        self.assertEqual(sorted(entry for entry in counts["categories"].values()), [[2, 2, 2], [6, 3, 2]])
        # A kind is counted by every real kind a product carries, never a mark.
        self.assertEqual(counts["kinds"], {"kettle": [4, 3, 2], "speaker": [2, 2, 2]})

    def test_no_shop_capped_and_a_cap_that_failed_keep_everything(self) -> None:
        counts = look_shop_rule.count_caps(self.products, self.kinds, shop_keep=None, keep=None)
        self.assertEqual((counts["products"], counts["after_the_shops_rule"], counts["kept"]), (8, 8, 8))
        self.assertTrue(counts["cap_failed"])
        self.assertEqual(counts["shops"]["Big"], [6, 0, 6, 6, 0, 0, 0])


class Compared(unittest.TestCase):
    def test_the_kinds(self) -> None:
        before = {"kettle": 200, "laptop": 30, "toaster": 3, "drill": 120}
        after = {"kettle": 90, "laptop": 30, "drill": 61}
        found = look_shop_rule.kinds_compared(before, after)
        self.assertEqual(found["kinds"], 4)
        self.assertEqual((found["empty"], found["under_4"], found["under_24"], found["thin"]), ((0, 1), (1, 1), (1, 1), (2, 4)))
        # Over half lost: 200 to 90 and 3 to none; 120 to 61 is not over half.
        self.assertEqual(found["lose_over_half"], ["kettle", "toaster"])
        self.assertEqual(found["emptied"], ["toaster"])

    def test_the_searches(self) -> None:
        def cards(*titles: str, recommended: str = "") -> list[list]:
            return [["9.99", title, "Shop", title == recommended] for title in titles]

        before = [
            {"q": "kettle", "total": 10, "cards": cards("a", "b", "c", "d", "e", recommended="b")},
            {"q": "laptop", "total": 5, "cards": cards("a", "b", recommended="a")},
            {"q": "drill", "total": 3, "cards": cards("a")},
        ]
        after = [
            # The same first four, another fifth; the same Recommended.
            {"q": "kettle", "total": 9, "cards": cards("a", "b", "c", "d", "f", recommended="b")},
            # Another Recommended among the same cards.
            {"q": "laptop", "total": 5, "cards": cards("a", "b", recommended="b")},
            {"q": "drill", "total": 0, "cards": []},
        ]
        found = look_shop_rule.searches_compared(before, after)
        self.assertEqual((found["searches"], found["same_first"], found["same_cards"]), (3, 2, 1))
        # The same Recommended: the kettles, and the drills, which had none before and none after.
        self.assertEqual((found["same_recommended"], found["same_total"]), (2, 1))
        self.assertEqual(found["emptied"], ["drill"])
        self.assertEqual(found["changed"], ["kettle", "drill"])


class ThePreparationOfTheLook(unittest.TestCase):
    """The look's own run of the preparation, twice: the switch off, then the rule on with
    the most a shop passes set to five for the test."""

    @classmethod
    def setUpClass(cls) -> None:
        from picwise_providers.awin_adapter import clear_awin_feed_parse_cache
        from picwise_providers.state import clear_provider_feed_pipeline_cache

        cls.folder = tempfile.TemporaryDirectory()
        base = Path(cls.folder.name)
        feed = _feed(base / "feed.csv")
        cls.saved = {name: os.environ.get(name) for name in ("AWIN_FEED_FILE", "PICWISE_MEMORY_TRACE", "PICWISE_CHECKS_DECISIONS")}
        os.environ.pop("PICWISE_CHECKS_DECISIONS", None)
        cls.real = (shop_cap.shop_cap_on, shop_cap.SHOP_LIMIT)
        cls.printed = {}
        cls.status = {}
        for name, switch in (("off", False), ("on", True)):
            shop_cap.shop_cap_on = lambda _switch=switch: _switch
            shop_cap.SHOP_LIMIT = 5
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()
            out = io.StringIO()
            with redirect_stdout(out):
                cls.status[name] = look_shop_rule.prepare(base / name, ["--feed-file", str(feed)])
            cls.printed[name] = out.getvalue()
        shop_cap.shop_cap_on, shop_cap.SHOP_LIMIT = cls.real
        cls.caps = {name: json.loads((base / name / look_shop_rule.CAPS_NAME).read_text(encoding="utf-8")) for name in ("off", "on")}
        cls.base = base

    @classmethod
    def tearDownClass(cls) -> None:
        from picwise_providers import state
        from picwise_providers.awin_adapter import clear_awin_feed_parse_cache
        from picwise_providers.state import clear_provider_feed_pipeline_cache

        shop_cap.shop_cap_on, shop_cap.SHOP_LIMIT = cls.real
        for name, value in cls.saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()
        state._PREPARED_STATE.clear()
        state.remember_product_kinds({})
        cls.folder.cleanup()

    def test_both_runs_write_a_catalogue_a_note_and_the_caps(self) -> None:
        for name in ("off", "on"):
            self.assertEqual(self.status[name], 0, self.printed[name])
            for file in (look_shop_rule.CATALOGUE_NAME, look_shop_rule.NOTE_NAME, look_shop_rule.CAPS_NAME):
                self.assertTrue((self.base / name / file).is_file(), (name, file))
            self.assertIn("look: the caps counted: 16 products a card can show", self.printed[name])
        self.assertIn("how many of a shop's products pass off", self.printed["off"])
        self.assertIn("how many of a shop's products pass ON", self.printed["on"])

    def test_the_switch_off_caps_no_shop(self) -> None:
        caps = self.caps["off"]
        self.assertEqual((caps["products"], caps["after_the_shops_rule"], caps["kept"]), (16, 16, 16))
        self.assertEqual(caps["shops"]["Fixture Big Store"][:4], [12, 0, 12, 12])
        self.assertFalse(caps["gate"])
        note = json.loads((self.base / "off" / look_shop_rule.NOTE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(note["checks"]["shop_cap"], {"applied": False, "why": "the switch is off"})
        self.assertEqual(note["products"], 16)

    def test_the_rule_keeps_the_most_of_the_large_shop_and_every_product_of_the_small(self) -> None:
        caps = self.caps["on"]
        self.assertEqual((caps["products"], caps["after_the_shops_rule"], caps["kept"]), (16, 9, 9))
        self.assertEqual(caps["shops"]["Fixture Big Store"][:4], [12, 0, 5, 5])
        self.assertEqual(caps["shops"]["Fixture Small Store"][:4], [4, 0, 4, 4])
        note = json.loads((self.base / "on" / look_shop_rule.NOTE_NAME).read_text(encoding="utf-8"))
        rule = note["checks"]["shop_cap"]
        self.assertEqual((rule["applied"], rule["limit"], rule["capped_shops"], rule["cut"]), (True, 5, 1, 7))
        self.assertEqual(note["products"], 9)
        # Every kind the large shop sold is still there.
        self.assertGreaterEqual(caps["kinds"]["kettle"][2], 5)
        self.assertGreaterEqual(caps["kinds"]["laptop"][2], 1)

    def test_the_preparation_is_put_back_as_it_was(self) -> None:
        import prepare_catalogue as tool

        self.assertEqual(tool._Cap.__call__.__qualname__, "_Cap.__call__")
        self.assertEqual(tool._trace.__name__, "_trace")

    def test_a_summary_of_each_and_the_two_side_by_side(self) -> None:
        for name in ("off", "on"):
            out = io.StringIO()
            with redirect_stdout(out):
                status = look_shop_rule.summary(self.base / name, name=name, seconds=120.0, peak_kb=2 * 1048576)
            self.assertEqual(status, 0, out.getvalue())
        off = json.loads((self.base / "off" / look_shop_rule.SUMMARY_NAME).read_text(encoding="utf-8"))
        on = json.loads((self.base / "on" / look_shop_rule.SUMMARY_NAME).read_text(encoding="utf-8"))
        self.assertEqual((off["products"], on["products"]), (16, 9))
        self.assertEqual(off["shops"], {"Fixture Big Store": 12, "Fixture Small Store": 4})
        self.assertEqual(on["shops"], {"Fixture Big Store": 5, "Fixture Small Store": 4})
        self.assertEqual(off["kinds"]["kettle"], 13)
        self.assertEqual(len(off["searches"]), 40)
        kettle = off["kind_searches"]["kettle"]
        self.assertEqual((kettle["kind"], kettle["total"], len(kettle["cards"])), ("kettle", 13, 4))
        self.assertEqual(sum(1 for card in kettle["cards"] if card[3]), 1)
        # The summary holds no link and no id of a row.
        text = json.dumps([off, on])
        self.assertNotIn("http", text)
        self.assertNotIn("fixture.example", text)
        for row_id in ("b1", "n1", "s1"):
            self.assertNotIn(f'"{row_id}"', text)

        out = io.StringIO()
        with redirect_stdout(out):
            status = look_shop_rule.main(["compare", str(self.base / "off" / look_shop_rule.SUMMARY_NAME),
                                          str(self.base / "on" / look_shop_rule.SUMMARY_NAME)])
        printed = out.getvalue()
        self.assertEqual(status, 0)
        self.assertIn("the rule (at most 5; a kind thin under 100): 1 shops over it, 7 of their products left out", printed)
        # a card can show | shown the night before | shown now | the rule keeps | then kept | ...
        self.assertIn("  Fixture Big Store: 12 | 0 | 12 | 5 | 5 | 0 | 0", printed)
        self.assertIn("(-7)  Fixture Big Store", printed)
        self.assertNotIn("Fixture Small Store:", printed.split("== 3.")[0].split("== 2.")[1])
        self.assertIn("time 2.0 min", printed)
        self.assertIn("peak memory 2.00 GB", printed)
        self.assertIn("== 7. the 40 searches", printed)
        self.assertIn('"kettle" (kettle):', printed)
        self.assertNotIn("http", printed)

    def test_a_missing_summary_is_said(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            status = look_shop_rule.main(["compare", str(self.base / "none.json"), str(self.base / "none.json")])
        self.assertEqual(status, 1)
        self.assertIn("a summary is missing: off, on", out.getvalue())


class TheLookAtTheBot(unittest.TestCase):
    """On a prepared catalogue and a checks' folder of the test's own: no shop is asked."""

    @classmethod
    def setUpClass(cls) -> None:
        from test_picwise_look_itself import _write

        cls.folder = tempfile.TemporaryDirectory()
        base = Path(cls.folder.name)
        cls.catalogue = base / "catalogue.json.gz"
        prepared = _write(cls.catalogue)
        cls.checks = base / "checks"
        cls.checks.mkdir()
        from picwise_checks.rows import row_of

        keys = [row_of(product).key for product in prepared.products]
        lines = [
            {"key": keys[0], "s": 200, "k": True}, {"key": keys[1], "s": 200}, {"key": keys[2], "s": 404},
            {"key": keys[3], "s": 403}, {"key": keys[4], "s": 200, "c": True}, {"key": "a row of no catalogue", "s": 200},
        ]
        (cls.checks / "tonight-2026-11-23.jsonl").write_text(
            "\n".join(json.dumps(line) for line in lines) + "\n{cut short", encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            cls.status = look_bot_rule.main(["--catalogue", str(cls.catalogue), "--checks", str(cls.checks), "--processes", "0"])
        cls.printed = out.getvalue()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.folder.cleanup()

    def test_it_ends_well_and_asks_no_shop(self) -> None:
        self.assertEqual(self.status, 0)
        self.assertIn("no shop was asked, nothing was written", self.printed)
        self.assertEqual(sorted(path.name for path in self.checks.iterdir()), ["tonight-2026-11-23.jsonl"])

    def test_the_pages_are_read_and_the_order_is_worked_out(self) -> None:
        self.assertIn("8 of 8 pages read, on the bot's own process", self.printed)
        self.assertIn("41 products shown, of 1 shops", self.printed)
        self.assertIn("the order names 41 products of 1 shops", self.printed)
        self.assertIn("the ledger: 0 products, 0 shops, nights recorded none", self.printed)

    def test_what_would_be_asked_with_the_rule_off_and_on(self) -> None:
        self.assertIn("in all: 41 products of 1 shops, the rule off; 41 of 1 shops, the rule on", self.printed)
        self.assertIn("  Fictional Store One: 41 | 41 | 41 | 41 | ", self.printed)

    def test_a_pass_counting_for_thirty_nights_and_for_three(self) -> None:
        self.assertIn("a pass counts for 30 nights: shops out 0, cut 0, not shown until checked 0, may enter 0", self.printed)
        self.assertIn("a pass counts for 3 nights: shops out 0, cut 0, not shown until checked 0, may enter 0, named as passed 0",
                      self.printed)

    def test_the_round_running_counted_by_shop(self) -> None:
        self.assertIn("tonight-2026-11-23.jsonl: 6 answers of 1 shops", self.printed)
        self.assertIn("of rows this catalogue does not hold 1", self.printed)
        # answers (in its catalogue, a page, gone, refused, a wall, no answer or another)
        self.assertIn("  Fictional Store One: 5 (1, 1, 1, 1, 1, 0)", self.printed)

    def test_processes_of_their_own_read_the_pages(self) -> None:
        import shop_checks_bot as bot

        said: list[str] = []
        readers = bot.Readers.start(2, said.append)
        try:
            self.assertEqual(said, ["the pages are read on 2 processes of their own"])
            found = look_bot_rule.try_readers(readers, pages=4)
        finally:
            readers.close()
        self.assertEqual(found, "4 of 4 pages read; 2 of 2 processes other than the bot's answered at once")

    def test_nothing_printed_is_a_link_or_an_id(self) -> None:
        self.assertNotIn("http", self.printed)
        self.assertNotIn("row-", self.printed)
        self.assertNotIn("shop.invalid", self.printed)


if __name__ == "__main__":
    unittest.main()
