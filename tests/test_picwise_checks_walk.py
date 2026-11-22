"""The checks walked night after night, through the ledger and the preparation's side together
(`picwise_checks.ledger`, `picwise_providers.checks_applied`, the cap's gate in
`catalogue_cap`; the checks' rules 8 and 9).

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
  the night it passes.

Every row is local test data: fictional shops and brands, `.invalid` hosts.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_checks import ledger as L  # noqa: E402
from picwise_checks.rows import row_from_record, row_of, row_record  # noqa: E402
from picwise_checks.verdicts import FAILED, NO_ANSWER, PASSED, ShopNight, Verdict  # noqa: E402
from picwise_providers import checks_applied as applied  # noqa: E402
from picwise_providers.catalogue_cap import cap_catalogue, part_of, row_key  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context, evaluate_product_eligibility  # noqa: E402

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

    def __init__(self, feed, *, shown=None, asked_a_night, share: float = 0.15) -> None:
        self.feed = tuple(feed)
        # How many products the bot gets through a night: one number, or one a shop.
        self.asked_a_night = asked_a_night if isinstance(asked_a_night, dict) else {"": asked_a_night}
        self.share = share
        self.ledger = L.Ledger()
        # The catalogue as it is the day the checks start: what the cap kept the night before.
        self.shown = list(self.feed if shown is None else shown)
        self.pool = {row_key(product) for product in self.shown}
        self.for_the_bot = {"candidates": [], "rows": []}
        self.night_number = 0

    def night(self, answers=None) -> dict:
        """One night; `answers`: a product's number to its page's verdict (the rest pass)."""
        answers = answers or {}
        night = START + timedelta(days=self.night_number)
        self.night_number += 1
        # The bot's side (`shop_checks_bot.main` and `run`).
        rows = {row.key: row for row in map(row_of, self.shown)}
        parts = {row_of(product).key: part_of(product, frozenset({"kettle"})) for product in self.shown}
        shown = set(rows)
        named = {record[0]: row_from_record(record) for record in self.for_the_bot["rows"]}
        candidates = [key for key in self.for_the_bot["candidates"] if key in named]
        for key, row in named.items():
            rows.setdefault(key, row)
        order = L.asking_order(self.ledger, night, rows, shown=shown, candidates=candidates, parts=parts)
        asked = {shop: keys[: self.asked_a_night.get(shop, self.asked_a_night.get("", 0))] for shop, keys in order.items()}
        readings = {key: L.Reading(page=answers.get(_number(key), OK)) for keys in asked.values() for key in keys}
        shop_nights = {shop: ShopNight(requests=len(keys) + 1, answers=len(keys) + 1, pages_200=len(keys),
                                       pages_read=len(keys)) for shop, keys in asked.items()}
        for shop in {row.shop for row in rows.values()}:
            shop_nights.setdefault(shop, ShopNight(requests=1, answers=1))
        recorded = L.record_night(self.ledger, night, rows, readings, shop_nights, shown=shown, parts=parts)
        made = L.decisions(self.ledger, night, rows, shown=shown, candidates=candidates, came_back=recorded.came_back)
        # The preparation's side (`state._resolve_provider_feed_pipeline_uncached`, `prepare_catalogue._Cap`).
        applied.reset_for_tests()
        judged = applied.apply_checks(self.feed, decisions=made, switch=True, today=night)
        context = build_feed_availability_context(judged)
        eligible = [product for product in judged if evaluate_product_eligibility(product, feed_ctx=context).card_eligible]
        before = (frozenset(self.pool) | applied.returning_row_keys(eligible, row_key)) \
            - applied.unchecked_row_keys(eligible, row_key)
        cap = cap_catalogue(eligible, [frozenset({"kettle"}) for _product_ in eligible], feed_ctx=context,
                            kept_before=before, share=self.share, may_enter=applied.may_enter)
        self.shown = [product for product, kept in zip(eligible, cap.keep) if kept]
        self.pool = set(cap.kept_keys)
        self.for_the_bot = applied.candidates_document([eligible[index] for index in cap.candidates],
                                                       applied.take_cut_products(), row_record, row_of)
        return {
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
        return Server([_product(number) for number in range(1, 5)] + others, asked_a_night=40)

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


if __name__ == "__main__":
    unittest.main()
