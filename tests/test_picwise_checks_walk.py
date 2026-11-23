"""The checks walked night after night, through the ledger and the preparation's side together
(`picwise_checks.ledger`, `picwise_providers.checks_applied`, the cap behind its gate as
`tools/prepare_catalogue.py` works it out; the checks' rules 8 and 9).

Each night here is a night as the server lives it: the bot's side (the order of asking, the
night recorded, the decisions) on the products the catalogue shows, the cap's candidates and
the cut rows the preparation named; then the preparation's side on the whole feed (the
decisions applied, what a card can show, the cap behind its gate, the rows named for the
bot's next night). The shops' answers are made up; nothing is opened.

Pinned (the look of task 7, 22/11, which found the first by walking the two sides together):

- a product never asked by its shop's day 4 is not shown, is named a candidate by the cap
  that same night, is asked the next night and is back the night it passes (9.3, 9.4);
- in a category at its size the places such products leave go only to products that passed,
  and the catalogue never shows a product never asked once its shop's first round is over;
- a product whose page fails is cut that night, asked again the next, and back in its place
  the night it passes (8.1, 8.2); one that keeps failing is asked on its schedule and is back
  the night it passes;
- a night the cap has no memory of the night before (its pool missing or unreadable), the
  gate holds back only the products not checked, never the whole site.

And the rule of how many of a shop's products pass (the checks' rules 19; `scanned`, its
switch on), walked the same way, with the most a shop passes made small:

- a capped shop shows the most and no more, the same products each night, and the bot asks
  it no more than the most (19.3.3, 19.4 e);
- a slow shop settles at what the bot scans of it in a day, the same products each night
  (19.3.2: its shown products asked again first);
- a pass counts for three nights: a product the bot could not reach is shown the night it
  passed and the two after, then waits, is named a candidate and is back the night it
  passes again (19.3.1);
- the products of a capped shop that wait at the gate move no other kind's share in its
  categories (the look of 23/11, the checks' rules 20.7).

Every row is local test data: fictional shops and brands, `.invalid` hosts.
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_checks import ledger as L  # noqa: E402
from picwise_checks.rows import row_from_record, row_of, row_record  # noqa: E402
from picwise_checks.verdicts import FAILED, NO_ANSWER, PASSED, ShopNight, Verdict  # noqa: E402
from picwise_providers import checks_applied as applied  # noqa: E402
from picwise_providers.catalogue_cap import google_pool_path, part_of, row_key  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context, evaluate_product_eligibility  # noqa: E402
from picwise_providers import shop_cap  # noqa: E402



def _load_prepare_tool():
    spec = importlib.util.spec_from_file_location("prepare_catalogue_walk_tool", ROOT / "tools" / "prepare_catalogue.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = _load_prepare_tool()
START = date(2026, 12, 1)
KITCHEN = "Home & Garden > Kitchen"
# Categories of Google's taxonomy as the cap reads them (its first two levels): enough of
# them for the share of 15% to hold, so that the first is a category over its size.
OTHER_CATEGORIES = (
    "Electronics > Audio", "Apparel & Accessories > Clothing", "Toys & Games > Toys", "Sporting Goods > Outdoor Recreation",
    "Health & Beauty > Personal Care", "Hardware > Tools", "Furniture > Chairs", "Baby & Toddler > Nursing & Feeding",
    "Office Supplies > Office Instruments", "Animals & Pet Supplies > Pet Supplies", "Cameras & Optics > Cameras",
    "Luggage & Bags > Backpacks",
)
OK = Verdict(PASSED, by="by address")
DOWN = Verdict(FAILED, NO_ANSWER)


def _product(number: int, *, shop: str = "Kettles", category: str = KITCHEN) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin", provider_product_id=f"row-{number}", title=f"Zentra Kettle {number}", brand="Zentra",
        category_text=category, product_url=f"https://{shop.lower()}.invalid/p/{number}",
        image_url=f"https://{shop.lower()}.invalid/i/{number}.jpg", price_text=f"{20 + number}.99",
        availability_text="in stock", currency="GBP", raw={"merchant_name": shop, "availability": "in stock"},
    )


def _number(key_or_product) -> int:
    text = key_or_product if isinstance(key_or_product, str) else key_or_product.provider_product_id
    return int(text.rsplit("row-", 1)[1])


class Server:
    """The two sides of a night, with the files they hand each other kept in memory."""

    def __init__(self, feed, *, shown=None, asked_a_night, scanned: bool = False, limit: int = 0) -> None:
        # `scanned`: the rule of how many of a shop's products pass (19), with `limit` the most
        # a shop passes (20,000 on the server).
        self.scanned = scanned
        self.limit = limit or shop_cap.SHOP_LIMIT
        self.feed = tuple(feed)
        # How many products the bot gets through a night: one number, or one a shop.
        self.asked_a_night = asked_a_night if isinstance(asked_a_night, dict) else {"": asked_a_night}
        self.ledger = L.Ledger()
        # The catalogue as it is the day the checks start, and the cap's pool of the night
        # before, kept beside the prepared file as on the server.
        self.shown = list(self.feed if shown is None else shown)
        self.folder = tempfile.TemporaryDirectory()
        self.out = Path(self.folder.name) / "catalogue.json.gz"
        self.write_pool({row_key(product) for product in self.shown})
        self.for_the_bot = {"candidates": [], "rows": []}
        self.night_number = 0
        self.gate_off = ""
        # A product's kinds, as the search reads them: every one a kettle, unless a walk says.
        self.kinds_of = lambda product: frozenset({"kettle"})

    def write_pool(self, keys) -> None:
        with gzip.open(google_pool_path(self.out), "wt", encoding="utf-8") as handle:
            json.dump({"v": 1, "keys": sorted(keys)}, handle)

    def lose_pool(self) -> None:
        google_pool_path(self.out).unlink()

    def close(self) -> None:
        self.folder.cleanup()

    def night(self, answers=None, *, reach=None) -> dict:
        """One night; `answers`: a product's number to its page's verdict (the rest pass);
        `reach`: how many products the bot gets through tonight, when not as usual."""
        answers = answers or {}
        if self.scanned:
            with mock.patch.object(shop_cap, "shop_cap_on", return_value=True), \
                    mock.patch.object(shop_cap, "SHOP_LIMIT", self.limit):
                return self._night(answers, reach)
        return self._night(answers, reach)

    def _night(self, answers, reach) -> dict:
        night = START + timedelta(days=self.night_number)
        self.night_number += 1
        # The bot's side (`shop_checks_bot.main` and `run`).
        rows = {row.key: row for row in map(row_of, self.shown)}
        parts = {row_of(product).key: part_of(product, self.kinds_of(product)) for product in self.shown}
        shown = set(rows)
        named = {record[0]: row_from_record(record) for record in self.for_the_bot["rows"]}
        candidates = [key for key in self.for_the_bot["candidates"] if key in named]
        for key, row in named.items():
            rows.setdefault(key, row)
        shown_order = None
        if self.scanned:
            keys_of = [row_of(product).key for product in self.shown]
            shown_order = {shop: [keys_of[place] for place in places] for shop, places in
                           shop_cap.shop_order(self.shown, [self.kinds_of(product) for product in self.shown]).items()}
        order = L.asking_order(self.ledger, night, rows, shown=shown, candidates=candidates, parts=parts,
                               scanned=self.scanned, shown_order=shown_order, limit=self.limit if self.scanned else 0)
        asked = {shop: keys[: (reach if reach is not None else self.asked_a_night.get(shop, self.asked_a_night.get("", 0)))]
                 for shop, keys in order.items()}
        self.ordered = order
        readings = {key: L.Reading(page=answers.get(_number(key), OK)) for keys in asked.values() for key in keys}
        shop_nights = {shop: ShopNight(requests=len(keys) + 1, answers=len(keys) + 1, pages_200=len(keys),
                                       pages_read=len(keys)) for shop, keys in asked.items()}
        for shop in {row.shop for row in rows.values()}:
            shop_nights.setdefault(shop, ShopNight(requests=1, answers=1))
        recorded = L.record_night(self.ledger, night, rows, readings, shop_nights, shown=shown, parts=parts)
        made = L.decisions(self.ledger, night, rows, shown=shown, candidates=candidates, came_back=recorded.came_back,
                           pass_nights=L.PASS_NIGHTS_SCANNED if self.scanned else L.PASS_VALID_NIGHTS,
                           passed_over=self.limit if self.scanned else 0)
        # The preparation's side: the decisions applied to the whole feed
        # (`state._resolve_provider_feed_pipeline_uncached`), what a card can show, then the
        # cap behind its gate as the tool works it out (`prepare_catalogue._Cap`), its pool
        # kept for the next night and the rows named for the bot.
        applied.reset_for_tests()
        judged = applied.apply_checks(self.feed, decisions=made, switch=True, today=night, scanned=self.scanned)
        context = build_feed_availability_context(judged)
        eligible = [product for product in judged if evaluate_product_eligibility(product, feed_ctx=context).card_eligible]
        capping = TOOL._Cap(self.out)
        keep = capping(eligible, [self.kinds_of(product) for product in eligible], context)
        if keep is None:
            raise AssertionError(f"the cap was not worked out: {capping.error}")
        self.shown = [product for product, kept in zip(eligible, keep) if kept]
        capping.write_pool(SimpleNamespace(prepared_at=datetime(night.year, night.month, night.day, 4, 30, tzinfo=timezone.utc)))
        self.gate_off = capping.gate_off
        if capping.candidates is not None:
            self.for_the_bot = capping.candidates
        return {
            "ordered": {shop: len(keys) for shop, keys in order.items()},
            "asked": sorted(_number(key) for keys in asked.values() for key in keys),
            "cut": {_number(key): reason for key, reason in made["cut"].items()},
            "wait": {_number(key): reason for key, reason in made["wait"].items()},
            "enter": sorted(_number(key) for key in made["enter"]),
            "shown": sorted(_number(product) for product in self.shown),
            "candidates": sorted(_number(key) for key in self.for_the_bot["candidates"]),
        }

    def state(self, number: int) -> str:
        product = next((entry for key, entry in self.ledger.products.items() if _number(key) == number), None)
        return product.state if product is not None else ""


class Rules93And94NeverAskedByDayFourTests(unittest.TestCase):
    def setUp(self) -> None:
        applied.reset_for_tests()
        self.addCleanup(applied.reset_for_tests)

    def test_it_waits_is_named_a_candidate_that_night_is_asked_the_next_and_comes_back(self) -> None:
        # A shop the bot gets through one product a night: two of its six are not asked by day 4.
        server = Server([_product(number) for number in range(1, 7)], asked_a_night=1)
        self.addCleanup(server.close)
        for day in range(3):
            night = server.night()
            self.assertEqual((night["shown"], night["wait"]), ([1, 2, 3, 4, 5, 6], {}))
        fourth = server.night()
        self.assertEqual(fourth["wait"], {5: "never checked", 6: "never checked"})
        self.assertEqual(fourth["cut"], {})
        self.assertEqual(fourth["shown"], [1, 2, 3, 4])
        # Named by the cap the same night, so that the bot asks them the next one, before
        # any product it has asked already (rules 10.3).
        self.assertEqual(fourth["candidates"], [5, 6])
        fifth = server.night()
        self.assertEqual((fifth["asked"], fifth["enter"], fifth["shown"]), ([5], [5], [1, 2, 3, 4, 5]))
        sixth = server.night()
        self.assertEqual((sixth["asked"], sixth["enter"], sixth["shown"]), ([6], [6], [1, 2, 3, 4, 5, 6]))
        self.assertEqual(server.night()["candidates"], [])

    def test_in_a_category_at_its_size_the_places_go_only_to_products_that_passed(self) -> None:
        # A category over the cap: 10 of its 60 kettles shown, its size, the other 50 at the
        # gate; 12 other categories of 5 products each, all shown and all asked the first night.
        kitchen = [_product(number) for number in range(1, 61)]
        others = [_product(100 + number, shop="Others", category=OTHER_CATEGORIES[number % 12]) for number in range(60)]
        server = Server(kitchen + others, shown=kitchen[:10] + others, asked_a_night={"Kettles": 2, "Others": 100})
        self.addCleanup(server.close)

        def kettles(night: dict, part: str = "shown") -> list[int]:
            return [number for number in night[part] if number < 100]

        for _day in range(3):
            night = server.night()
            # A full category with nothing cut names no candidate: there is no place open.
            self.assertEqual((kettles(night), kettles(night, "candidates"), night["wait"]), (list(range(1, 11)), [], {}))
        fourth = server.night()
        # Two a night, the cheapest first (rules 10.4): eight asked by day 4, two never.
        self.assertEqual(fourth["wait"], {9: "never checked", 10: "never checked"})
        self.assertEqual(kettles(fourth), list(range(1, 9)))
        # Two places open: the cap names the next ones by its own order among every product at
        # the gate, one and a quarter times the places open and at least 4 (9.4).
        named = kettles(fourth, "candidates")
        self.assertEqual(len(named), 4)
        self.assertFalse(set(named) & set(kettles(fourth)))
        fifth = server.night()
        # The bot asks candidates before any product it has asked already; those that pass
        # take the places that night: the category is at its size again.
        self.assertEqual(len(set(fifth["asked"]) & set(named)), 2)
        self.assertEqual(len(kettles(fifth)), 10)
        self.assertEqual(sorted(set(kettles(fifth)) - set(range(1, 9))), sorted(set(fifth["enter"])))
        for _day in range(10):
            night = server.night()
            self.assertEqual(len(kettles(night)), 10)
            # Never a product shown that was never asked, once its shop's first round is over.
            for number in night["shown"]:
                self.assertEqual(server.state(number), PASSED, number)


class Rules81And82AFailureAndItsWayBackTests(unittest.TestCase):
    def setUp(self) -> None:
        applied.reset_for_tests()
        self.addCleanup(applied.reset_for_tests)

    def _server(self) -> Server:
        # Other products around, so that one cut is not a tenth of the site (the night's brake, 7.4).
        others = [_product(100 + number, shop="Others", category=f"Toys > Kind {number}") for number in range(30)]
        server = Server([_product(number) for number in range(1, 5)] + others, asked_a_night=40)
        self.addCleanup(server.close)
        return server

    def test_cut_that_night_asked_again_the_next_and_back_in_its_place_the_night_it_passes(self) -> None:
        server = self._server()
        first = server.night({2: DOWN})
        self.assertEqual(first["cut"], {2: NO_ANSWER})
        self.assertNotIn(2, first["shown"])
        second = server.night()
        self.assertIn(2, second["asked"])
        self.assertIn(2, second["shown"])

    def test_one_that_keeps_failing_is_asked_on_its_schedule_and_back_the_night_it_passes(self) -> None:
        server = self._server()
        asked_on = []
        for day in range(4):
            night = server.night({2: DOWN})
            self.assertNotIn(2, night["shown"])
            if 2 in night["asked"]:
                asked_on.append(day)
        # 8.1: the night it failed, the next and the two after; then every 7 nights.
        self.assertEqual(asked_on, [0, 1, 2, 3])
        for day in range(4, 10):
            night = server.night({2: DOWN})
            self.assertNotIn(2, night["asked"])
            self.assertNotIn(2, night["shown"])
        tenth = server.night()
        self.assertIn(2, tenth["asked"])
        self.assertIn(2, tenth["shown"])


class ANightWithNoMemoryOfTheNightBeforeTests(unittest.TestCase):
    def setUp(self) -> None:
        applied.reset_for_tests()
        self.addCleanup(applied.reset_for_tests)

    def test_the_gate_holds_back_only_the_products_not_checked_never_the_whole_site(self) -> None:
        # The cap's pool of the night before is lost (a file missing or unreadable): the gate
        # would take every product for a new one. It must not empty the site.
        server = Server([_product(number) for number in range(1, 7)], asked_a_night=1)
        self.addCleanup(server.close)
        for _day in range(3):
            self.assertEqual((server.night()["shown"], server.gate_off), ([1, 2, 3, 4, 5, 6], ""))
        server.lose_pool()
        # That night the feed also brings a product never seen before.
        server.feed += (_product(7),)
        fourth = server.night()
        self.assertTrue(server.gate_off)
        # The two never asked by day 4 are still held back; every other product stays, and
        # the new one, which nothing tells from the rest tonight, is let in.
        self.assertEqual(fourth["wait"], {5: "never checked", 6: "never checked"})
        self.assertEqual(fourth["shown"], [1, 2, 3, 4, 7])
        self.assertEqual(fourth["candidates"], [5, 6])
        # The pool is written again that night: the gate stands from the next, when the product
        # let in unchecked is held back in its turn until the bot has asked it (9.3).
        fifth = server.night()
        self.assertEqual((server.gate_off, fifth["enter"], fifth["shown"]), ("", [5], [1, 2, 3, 4, 5]))
        self.assertEqual(fifth["wait"], {7: "never checked"})


class Rules19WhatTheBotScansPassesTests(unittest.TestCase):
    """The checks' rules 19 (owner, 2026-11-22: «μόνο όσα έχουν σκανναριστεί περνάνε», 20,000
    the most; a pass counts for three nights), walked night after night with its switch on."""

    def setUp(self) -> None:
        applied.reset_for_tests()
        self.addCleanup(applied.reset_for_tests)

    def test_a_capped_shop_shows_the_most_the_same_each_night_and_is_asked_no_more(self) -> None:
        server = Server([_product(number) for number in range(1, 13)], asked_a_night=50, scanned=True, limit=6)
        self.addCleanup(server.close)
        first = server.night()
        # The night the rule starts the site shows all twelve: the bot asks only the first six
        # (19.3.3), and the shop keeps the six that passed before the six never asked (19.4 f).
        self.assertEqual((first["ordered"]["Kettles"], first["asked"]), (6, [1, 2, 3, 4, 5, 6]))
        self.assertEqual(first["shown"], [1, 2, 3, 4, 5, 6])
        for _day in range(8):
            night = server.night()
            self.assertEqual(night["shown"], first["shown"])
            # 19.3.3: never more of the shop asked than the most it passes.
            self.assertLessEqual(night["ordered"]["Kettles"], 6)
            self.assertEqual(night["asked"], first["shown"])

    def test_a_capped_shops_place_left_by_a_cut_goes_to_a_candidate_that_passed(self) -> None:
        # Other products around, in shops under the most, so that one cut is no tenth of the site
        # (7.4); four nights first, so that the shop has passed 20 (7.2).
        others = [_product(100 + number, shop=f"Other{number % 6}", category=f"Toys > Kind {number}") for number in range(36)]
        server = Server([_product(number) for number in range(1, 13)] + others, asked_a_night=50, scanned=True, limit=6)
        self.addCleanup(server.close)
        for _day in range(4):
            server.night()

        def kettles(night: dict, part: str = "shown") -> list[int]:
            return [number for number in night[part] if number < 100]

        second = server.night({3: DOWN})
        second["shown"] = kettles(second)
        self.assertEqual((second["cut"], second["shown"]), ({3: NO_ANSWER}, [1, 2, 4, 5, 6]))
        # One place open: one and a quarter candidates, the next by the order (19.6.2).
        named = second["candidates"]
        self.assertEqual(len(named), 2)
        self.assertFalse(set(named) & {1, 2, 3, 4, 5, 6})
        third = server.night({3: DOWN})
        # The failed product asked on its schedule, the shown again, then one candidate: six of
        # the shop past the failed (19.3.3).
        self.assertIn(3, third["asked"])
        self.assertEqual(len(set(third["asked"]) & set(named)), 1)
        self.assertEqual(len(kettles(third)), 6)
        self.assertEqual(sorted(set(kettles(third)) - {1, 2, 4, 5, 6}), sorted(third["enter"]))

    def test_a_capped_shop_is_asked_no_candidate_its_category_has_no_place_for(self) -> None:
        # The look of 22/11 (three shops with far more rows than the site shows of them: 63,000
        # candidates named for their own places open). The kitchen category is at its size, 10:
        # 4 of the capped shop's 12 kettles and 6 of another shop's. The shop has 2 places open
        # of its 6, the category none: no kettle of it is named, asked or let in, night after
        # night (as built it named 3, the bot asked 2, they passed, the category refused them,
        # and two nights later they were named again, for good).
        big = [_product(number, shop="Big") for number in range(1, 13)]
        small = [_product(50 + number, shop="Small") for number in range(10)]
        others = [_product(100 + number, shop=f"Other{number % 12}", category=OTHER_CATEGORIES[number % 12]) for number in range(60)]
        server = Server(big + small + others, shown=big[:4] + small[:6] + others,
                        asked_a_night={"Big": 50, "Small": 50, "": 100}, scanned=True, limit=6)
        self.addCleanup(server.close)
        for _day in range(8):
            night = server.night()
            self.assertEqual([number for number in night["shown"] if number < 50], [1, 2, 3, 4])
            self.assertEqual(len([number for number in night["shown"] if 50 <= number < 100]), 6)
            self.assertEqual([number for number in night["asked"] if number < 50], [1, 2, 3, 4])
            self.assertEqual(([number for number in night["candidates"] if number < 100], night["enter"]), ([], []))

    def test_a_capped_shops_place_open_in_a_category_with_room_is_filled(self) -> None:
        # The same shop when a kettle of the other shop fails: the category has a place open, and
        # the capped shop two of its own. The cap of the category names the next ones it would
        # take, among them the capped shop's that wait (its own order, no more than it may name);
        # the bot asks them, and the category is at its size again with products that passed.
        big = [_product(number, shop="Big") for number in range(1, 13)]
        small = [_product(50 + number, shop="Small") for number in range(10)]
        others = [_product(100 + number, shop=f"Other{number % 12}", category=OTHER_CATEGORIES[number % 12]) for number in range(60)]
        server = Server(big + small + others, shown=big[:4] + small[:6] + others,
                        asked_a_night={"Big": 50, "Small": 50, "": 100}, scanned=True, limit=6)
        self.addCleanup(server.close)
        for _day in range(4):
            server.night()

        def kitchen(night: dict, part: str = "shown") -> list[int]:
            return [number for number in night[part] if number < 100]

        failed = server.night({50: DOWN})
        self.assertEqual((failed["cut"], len(kitchen(failed))), ({50: NO_ANSWER}, 9))
        named = kitchen(failed, "candidates")
        # One place open in the category: at least 4 named (9.4), the capped shop's among them
        # no more than it may name for its two places open (three).
        self.assertGreaterEqual(len(named), 4)
        of_big = [number for number in named if number < 50]
        self.assertTrue(0 < len(of_big) <= 3)
        self.assertFalse(set(of_big) & {1, 2, 3, 4})
        after = server.night({50: DOWN})
        self.assertTrue(set(after["asked"]) & set(named))
        self.assertEqual(len(kitchen(after)), 10)
        entered = sorted(set(kitchen(after)) - set(kitchen(failed)))
        self.assertEqual(len(entered), 1)
        self.assertIn(entered[0], after["enter"])
        self.assertEqual(server.state(entered[0]), PASSED)
        # The capped shop never shows more than the most it passes.
        for _day in range(4):
            night = server.night({50: DOWN})
            self.assertLessEqual(len([number for number in night["shown"] if number < 50]), 6)
            self.assertEqual(len(kitchen(night)), 10)

    def test_a_capped_shops_products_that_wait_move_no_other_kinds_share(self) -> None:
        # The look of 23/11. The kitchen category is at its size, 10, shared by two kinds: 4
        # toasters of the capped shop, which sells 40, and 6 kettles of another shop, which sells
        # 10. The capped shop has 2 places open of its 6, so its 36 toasters that wait go to the
        # cap of the category to be named among. They are no part of what the shops keep: the
        # kettles keep their 6 places, night after night, and no toaster is named, asked or let
        # in, the category having no place. (Counted like the rest, as they were, the toasters
        # were 40 of the category's 50: each kind's share became 5, a kettle shown the night
        # before left, and a toaster was asked for its place.)
        big = [_product(number, shop="Big") for number in range(1, 41)]
        small = [_product(50 + number, shop="Small") for number in range(10)]
        others = [_product(100 + number, shop=f"Other{number % 12}", category=OTHER_CATEGORIES[number % 12]) for number in range(60)]
        server = Server(big + small + others, shown=big[:4] + small[:6] + others,
                        asked_a_night={"Big": 50, "Small": 50, "": 100}, scanned=True, limit=6)
        server.kinds_of = lambda product: frozenset({"toaster" if _number(product) < 50 else "kettle"})
        self.addCleanup(server.close)
        kettles = [50, 51, 52, 53, 54, 55]
        for _day in range(8):
            night = server.night()
            self.assertEqual([number for number in night["shown"] if number < 50], [1, 2, 3, 4])
            self.assertEqual([number for number in night["shown"] if 50 <= number < 100], kettles)
            self.assertEqual([number for number in night["asked"] if number < 50], [1, 2, 3, 4])
            self.assertEqual(([number for number in night["candidates"] if number < 50], night["enter"]), ([], []))

    def test_a_slow_shop_settles_at_what_the_bot_scans_of_it_in_a_day(self) -> None:
        server = Server([_product(number) for number in range(1, 9)], asked_a_night=3, scanned=True)
        self.addCleanup(server.close)
        first = server.night()
        self.assertEqual(first["asked"], [1, 2, 3])
        for _day in range(2):
            # 19.3.2: the shown products it asked before, asked again first.
            self.assertEqual(server.night()["asked"], [1, 2, 3])
        fourth = server.night()
        # The first round over: the five never reached are not shown; they are candidates.
        self.assertEqual((fourth["shown"], sorted(fourth["wait"])), ([1, 2, 3], [4, 5, 6, 7, 8]))
        self.assertEqual(fourth["candidates"], [4, 5, 6, 7, 8])
        for _day in range(5):
            night = server.night()
            # The same three each night: no turns taken on the site.
            self.assertEqual((night["asked"], night["shown"]), ([1, 2, 3], [1, 2, 3]))

    def test_a_pass_counts_for_three_nights_then_it_waits_and_comes_back_when_it_passes(self) -> None:
        server = Server([_product(number) for number in range(1, 5)], asked_a_night=10, scanned=True)
        self.addCleanup(server.close)
        for _day in range(4):
            self.assertEqual(server.night()["shown"], [1, 2, 3, 4])
        # Passed on the fourth night; the bot reaches none of the shop on the next two.
        for _day in range(2):
            night = server.night(reach=0)
            self.assertEqual((night["asked"], night["shown"], night["wait"]), ([], [1, 2, 3, 4], {}))
        third = server.night(reach=0)
        self.assertEqual(third["wait"], {number: "not passed in 3 nights" for number in range(1, 5)})
        self.assertEqual((third["shown"], third["cut"], third["candidates"]), ([], {}, [1, 2, 3, 4]))
        back = server.night()
        self.assertEqual((back["asked"], back["enter"], back["shown"]), ([1, 2, 3, 4], [1, 2, 3, 4], [1, 2, 3, 4]))

    def test_with_its_switch_off_the_waits_of_three_nights_are_left_aside(self) -> None:
        server = Server([_product(number) for number in range(1, 5)], asked_a_night=10, scanned=True)
        self.addCleanup(server.close)
        for _day in range(4):
            server.night()
        for _day in range(2):
            server.night(reach=0)
        # The bot named them to wait; the preparation, the switch turned off, shows them.
        server.scanned = False
        night = server._night({}, 0)
        self.assertEqual(sorted(night["wait"]), [])
        self.assertEqual(night["shown"], [1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
