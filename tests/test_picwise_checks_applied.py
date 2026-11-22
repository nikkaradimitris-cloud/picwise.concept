"""The checks' decisions in the preparation (`picwise_providers.checks_applied`, the cap's
gate in `catalogue_cap`, the price's source in `catalogue_memory`; the checks' rules 5.3,
6, 7.7, 8.2 and 9).

Pinned: with the switch off nothing is applied; with it on a product cut or of a shop
out is no product a card can show; a proven page reader's stock is the shop's word; the
page's price is the card's price, the feed's sale columns let go and its history started
again; decisions over 2 nights old are not applied; the cap lets a product not shown the
night before take a place only once its checks passed and names the others as
candidates; a product back within 7 nights counts as kept the night before; a product not
shown until it is checked is not marked cut, leaves the cap's memory of the night before
and waits at its gate; the category's brake counts among the rows the AI answered.

Every row is local test data: fictional shops and brands, `.invalid` hosts.
"""
from __future__ import annotations

import gzip
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import checks_applied as applied  # noqa: E402
from picwise_providers.catalogue_cap import cap_catalogue, row_key  # noqa: E402
from picwise_providers.catalogue_memory import product_key, remember_night  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context, evaluate_product_eligibility  # noqa: E402

TODAY = date(2026, 12, 2)


def _product(number: int, *, shop: str = "Kettles", price: str = "24.99", category: str = "Home & Garden > Kitchen",
             raw: dict | None = None) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin", provider_product_id=f"row-{number}", title=f"Zentra Kettle {number}", brand="Zentra",
        category_text=category, product_url=f"https://{shop.lower()}.invalid/p/{number}",
        image_url=f"https://{shop.lower()}.invalid/i/{number}.jpg", price_text=price, availability_text="in stock",
        currency="GBP", raw={"merchant_name": shop, "availability": "in stock", **(raw or {})},
    )


def _decisions(**parts) -> dict:
    return {"format": applied.DECISIONS_FORMAT, "version": 1, "night": "2026-12-01", "shops_out": {}, "cut": {},
            "enter": [], "prices": {}, "stock": {}, "returning": [], **parts}


class Rules77TheSwitchTests(unittest.TestCase):
    def setUp(self) -> None:
        applied.reset_for_tests()

    def test_the_switch_is_on_from_the_owners_word_of_22_11(self) -> None:
        # Owner, 2026-11-22, after the look of task 7: «Ανέβασε». Off again only on his word (rules 7.7).
        self.assertTrue(applied.checks_switch_on())

    def test_a_switch_file_missing_unreadable_or_not_true_is_off(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "switch.json"
            self.assertFalse(applied.checks_switch_on(path))
            for text in ("not json", '{"cut": "true"}', '{"cut": false}', "[]"):
                path.write_text(text, encoding="utf-8")
                self.assertFalse(applied.checks_switch_on(path), text)
            path.write_text('{"cut": true}', encoding="utf-8")
            self.assertTrue(applied.checks_switch_on(path))

    def test_with_the_switch_off_nothing_is_applied_or_gated(self) -> None:
        products = (_product(1),)
        decisions = _decisions(cut={product_key(products[0]): "gone"})
        self.assertEqual(applied.apply_checks(products, decisions=decisions, switch=False), products)
        self.assertFalse(applied.gate_on())
        self.assertTrue(applied.may_enter(products[0]))

    def test_decisions_over_two_nights_old_are_not_applied(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "decisions.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                json.dump(_decisions(), handle)
            self.assertEqual(applied.load_decisions(path, today=TODAY)[1], "read")
            self.assertIsNone(applied.load_decisions(path, today=date(2026, 12, 4))[0])
            self.assertIsNone(applied.load_decisions(Path(folder) / "none.json.gz", today=TODAY)[0])


class Rules11TheNightsNoteTests(unittest.TestCase):
    def setUp(self) -> None:
        applied.reset_for_tests()

    def test_the_bots_note_goes_in_the_public_note_switch_on_or_off_its_public_keys_only(self) -> None:
        bot = {"night": "2026-12-01", "decided": 40, "passed": 37, "failed": {"gone": 3},
               "cannot_be_checked": {"Kettles": ["refuses the bot", 1]}, "asked_by_shop": {"Kettles": [12, 10, ""]},
               "prices_tied": {"Kettles": [10, 9]}}
        with tempfile.TemporaryDirectory() as folder:
            decisions = Path(folder) / "decisions.json.gz"
            (Path(folder) / applied.BOT_NOTE_NAME).write_text(json.dumps(bot), encoding="utf-8")
            with mock.patch.dict(os.environ, {applied.DECISIONS_ENV: str(decisions)}):
                applied.apply_checks((_product(1),), switch=False)
                off = applied.last_checks_note()
                applied.apply_checks((_product(1),), decisions=_decisions(), switch=True)
                on = applied.last_checks_note()
        for note in (off, on):
            self.assertEqual(note["bot"]["cannot_be_checked"], {"Kettles": ["refuses the bot", 1]})
            self.assertEqual((note["bot"]["decided"], note["bot"]["failed"]), (40, {"gone": 3}))
            self.assertNotIn("asked_by_shop", note["bot"])
        self.assertFalse(off["applied"])
        self.assertTrue(on["applied"])

    def test_no_note_of_the_bot_no_bot_key(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.dict(os.environ, {applied.DECISIONS_ENV: str(Path(folder) / "decisions.json.gz")}):
                applied.apply_checks((_product(1),), switch=False)
        self.assertNotIn("bot", applied.last_checks_note())


def _named(number: int, **parts) -> ProviderProduct:
    """A product whose title asks the AI its own question (a title's numbers are left out of it)."""
    word = "".join("abcdefghij"[int(digit)] for digit in str(number))
    product = _product(number, **parts)
    return ProviderProduct(**{**product.__dict__, "title": f"Zentra Kettle Model {word.capitalize()}x"})


class Rules55TheCategoryTests(unittest.TestCase):
    def setUp(self) -> None:
        from picwise_providers import ai_shelves

        self.ai_shelves = ai_shelves
        applied.reset_for_tests()
        ai_shelves.reset()
        self.addCleanup(ai_shelves.reset)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.answers = self.folder / "answers.jsonl.gz"
        patch = mock.patch.dict(os.environ, {ai_shelves.AI_SHELVES_FILE_ENV: str(self.answers)})
        patch.start()
        self.addCleanup(patch.stop)

    def key(self, product: ProviderProduct) -> str:
        return self.ai_shelves.key_of(product.title, product.brand, product.raw)

    def write(self, records: list[dict]) -> None:
        with gzip.open(self.answers, "wt", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        self.ai_shelves.reset()

    def test_no_line_refused_for_good_or_a_slip_is_cut_a_line_passes_not_asked_stays(self) -> None:
        products = tuple(_named(number) for number in range(1, 41))
        self.assertEqual(len({self.key(product) for product in products}), 40)
        kettles = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Electric Kettles"
        records = [{"k": self.key(product), "line": kettles, "tries": 0} for product in products[5:]]
        records += [{"k": self.key(products[0]), "line": "", "tries": 0},
                    {"k": self.key(products[1]), "line": None, "tries": 2},
                    {"k": self.key(products[2]), "line": "Animals & Pet Supplies", "tries": 0},
                    {"k": self.key(products[3]), "line": None, "tries": 1}]
        self.write(records)
        done = applied.apply_checks(products, decisions=_decisions(), switch=True)
        cut = {product.title for product in done if product.raw.get(applied.CHECKS_COLUMN) == applied.NO_CATEGORY}
        self.assertEqual(cut, {products[0].title, products[1].title, products[2].title})
        note = applied.last_checks_note()
        self.assertEqual(note["category"], {"answers": True, "no_category": 3, "held_by_its_brake": False,
                                            "not_asked_yet": 2, "with_a_line": 35})
        self.assertEqual(note["cut_by_reason"], {applied.NO_CATEGORY: 3})
        # A product shown stays until asked; a new one waits for its answer, as for its checks.
        context = build_feed_availability_context(done)
        self.assertEqual([evaluate_product_eligibility(product, feed_ctx=context).card_eligible for product in done[:6]],
                         [False, False, False, True, True, True])
        enter = [product_key(product) for product in products]
        applied.apply_checks(products, decisions=_decisions(enter=enter), switch=True)
        self.assertEqual([applied.may_enter(product) for product in products[:6]],
                         [False, False, False, False, False, True])
        # Named for the AI: the ones not asked yet (refused once is asked once more), one item a question.
        items = applied.shelf_items(products)
        self.assertEqual(sorted(item["k"] for item in items), sorted([self.key(products[3]), self.key(products[4])]))
        self.assertEqual(items[0]["shop"], "Kettles")
        written = applied.write_shelf_job(items, self.folder)
        self.assertEqual(written, {"keys": 2, "products": 2})
        with gzip.open(self.folder / applied.SHELF_JOBS_NAME, "rt", encoding="utf-8") as handle:
            self.assertEqual(len(handle.read().splitlines()), 2)

    def test_too_many_with_no_category_in_one_night_none_is_cut(self) -> None:
        products = tuple(_named(number) for number in range(1, 21))
        self.write([{"k": self.key(product), "line": "", "tries": 0} for product in products[:3]]
                   + [{"k": self.key(product), "line": "Electronics > Electronics Accessories > Cables", "tries": 0}
                      for product in products[3:]])
        done = applied.apply_checks(products, decisions=_decisions(), switch=True)
        self.assertFalse(any(applied.CHECKS_COLUMN in product.raw for product in done))
        self.assertTrue(applied.last_checks_note()["category"]["held_by_its_brake"])
        # Held, not let in: a new product with no category still waits.
        self.assertFalse(applied.may_enter(products[0]))

    def test_its_brake_counts_among_the_rows_answered_not_among_every_row_of_the_feed(self) -> None:
        # The feed has many rows for each product shown, most never asked: 3 with none of 20
        # answered is over a tenth however many rows nobody asked stand beside them.
        products = tuple(_named(number) for number in range(1, 321))
        self.write([{"k": self.key(product), "line": "", "tries": 0} for product in products[:3]]
                   + [{"k": self.key(product), "line": "Electronics > Electronics Accessories > Cables", "tries": 0}
                      for product in products[3:20]])
        done = applied.apply_checks(products, decisions=_decisions(), switch=True)
        self.assertFalse(any(applied.CHECKS_COLUMN in product.raw for product in done))
        category = applied.last_checks_note()["category"]
        self.assertEqual((category["held_by_its_brake"], category["no_category"], category["with_a_line"],
                          category["not_asked_yet"]), (True, 3, 17, 300))

    def test_no_answers_file_decides_nothing(self) -> None:
        products = tuple(_named(number) for number in range(1, 4))
        done = applied.apply_checks(products, decisions=_decisions(enter=[product_key(p) for p in products]), switch=True)
        self.assertFalse(any(applied.CHECKS_COLUMN in product.raw for product in done))
        self.assertTrue(all(applied.may_enter(product) for product in products))
        self.assertEqual(applied.shelf_items(products), [])


class Rules6WhatIsCutTests(unittest.TestCase):
    def setUp(self) -> None:
        applied.reset_for_tests()

    def test_a_cut_product_and_a_shop_out_are_no_product_a_card_can_show(self) -> None:
        products = (_product(1), _product(2), _product(3, shop="Toasters"))
        decisions = _decisions(cut={product_key(products[0]): "gone"}, shops_out={"Toasters": "Awin: rejected"})
        result = applied.apply_checks(products, decisions=decisions, switch=True)
        context = build_feed_availability_context(result)
        eligible = [evaluate_product_eligibility(product, feed_ctx=context) for product in result]
        self.assertEqual([item.card_eligible for item in eligible], [False, True, False])
        self.assertIn("checks_failed", eligible[0].reason_codes)
        note = applied.last_checks_note()
        self.assertEqual((note["cut"], note["products_of_shops_out"]), (1, 1))
        self.assertEqual(len(applied.take_cut_products()), 2)
        self.assertEqual(applied.take_cut_products(), [])

    def test_5_2_a_proven_page_readers_stock(self) -> None:
        products = (_product(1),)
        result = applied.apply_checks(products, decisions=_decisions(stock={product_key(products[0]): ["sold out", "x"]}),
                                      switch=True)
        context = build_feed_availability_context(result)
        self.assertFalse(evaluate_product_eligibility(result[0], feed_ctx=context).card_eligible)

    def test_5_3_the_pages_price_is_the_cards_price(self) -> None:
        products = (_product(1, price="19.99", raw={"sale_price": "19.99 GBP", "sale_price_effective_date": "x"}),)
        result = applied.apply_checks(products, decisions=_decisions(prices={product_key(products[0]): ["21.79", "x"]}),
                                      switch=True)
        self.assertEqual(result[0].price_text, "21.79")
        self.assertEqual(result[0].raw[applied.PRICE_SOURCE_COLUMN], applied.SHOP_SITE)
        self.assertNotIn("sale_price", result[0].raw)


class Rules9TheCapsGateTests(unittest.TestCase):
    def setUp(self) -> None:
        applied.reset_for_tests()

    def test_9_3_not_shown_until_checked_is_not_cut_it_waits_at_the_gate_and_is_named_a_candidate(self) -> None:
        products = tuple(_product(number) for number in range(4))
        waiting = product_key(products[1])
        decisions = _decisions(wait={waiting: "never checked"}, enter=[waiting])
        done = applied.apply_checks(products, decisions=decisions, switch=True)
        # No check failed: not marked, still a product a card could show, never passed to the bot as cut.
        self.assertFalse(any(applied.CHECKS_COLUMN in product.raw for product in done))
        context = build_feed_availability_context(done)
        self.assertTrue(all(evaluate_product_eligibility(product, feed_ctx=context).card_eligible for product in done))
        self.assertEqual(applied.take_cut_products(), [])
        note = applied.last_checks_note()
        self.assertEqual((note["cut"], note["not_shown_until_checked"], note["not_shown_until_checked_by_reason"]),
                         (0, 1, {"never checked": 1}))
        # Out of the night before's, and held at the gate whatever else says it may enter.
        self.assertEqual(applied.unchecked_row_keys(done, row_key), frozenset({row_key(products[1])}))
        self.assertFalse(applied.may_enter(done[1]))
        before = frozenset(row_key(product) for product in products) - applied.unchecked_row_keys(done, row_key)
        kinds = [frozenset({"kettle"}) for _product_ in done]
        result = cap_catalogue(done, kinds, feed_ctx=context, kept_before=before, may_enter=applied.may_enter)
        self.assertEqual(result.keep, (True, False, True, True))
        self.assertEqual(result.candidates, (1,))
        applied.apply_checks(products, decisions=_decisions(), switch=True)
        self.assertEqual(applied.unchecked_row_keys(products, row_key), frozenset())

    def test_9_4_a_new_product_takes_a_place_only_once_passed(self) -> None:
        products = tuple(_product(number) for number in range(6))
        passed = product_key(products[1])
        applied.apply_checks(products, decisions=_decisions(enter=[passed]), switch=True)
        context = build_feed_availability_context(products)
        kinds = [frozenset({"kettle"}) for _product_ in products]
        before = {row_key(products[0])}
        result = cap_catalogue(products, kinds, feed_ctx=context, kept_before=before, may_enter=applied.may_enter)
        self.assertEqual(result.keep, (True, True, False, False, False, False))
        self.assertEqual(result.candidates, (2, 3, 4, 5))
        self.assertEqual(result.held_by_checks, 4)
        free = cap_catalogue(products, kinds, feed_ctx=context, kept_before=before)
        self.assertTrue(all(free.keep))
        self.assertEqual(free.candidates, ())

    def test_9_4_in_a_full_category_the_next_ones_by_the_caps_order(self) -> None:
        full = tuple(_product(number, category="Home & Garden > Kitchen") for number in range(40))
        others = tuple(_product(100 + number, category=f"Toys > Kind{number}") for number in range(20))
        products = full + others
        applied.apply_checks(products, decisions=_decisions(), switch=True)
        context = build_feed_availability_context(products)
        kinds = [frozenset({"kettle"}) for _product_ in products]
        before = {row_key(product) for product in full[:10]} | {row_key(product) for product in others}
        result = cap_catalogue(products, kinds, feed_ctx=context, kept_before=before, may_enter=applied.may_enter,
                               share=0.15)
        kept_full = sum(result.keep[:40])
        self.assertEqual(kept_full, 10)
        self.assertGreaterEqual(len(result.candidates), 4)
        self.assertTrue(all(index < 40 for index in result.candidates))

    def test_8_2_a_product_back_within_seven_nights_counts_as_kept_the_night_before(self) -> None:
        products = (_product(1), _product(2))
        applied.apply_checks(products, decisions=_decisions(returning=[product_key(products[0])]), switch=True)
        self.assertEqual(applied.returning_row_keys(products, row_key), frozenset({row_key(products[0])}))


class Rules535ThePricesHistoryTests(unittest.TestCase):
    def test_a_change_of_source_starts_the_history_again(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.sqlite"
            night = datetime(2026, 12, 1, 4, 30, tzinfo=timezone.utc)
            remember_night(path, [_product(1, price="19.99")], prepared_at=night)
            site = _product(1, price="21.79", raw={applied.PRICE_SOURCE_COLUMN: applied.SHOP_SITE})
            summary = remember_night(path, [site], prepared_at=night.replace(day=2))
            self.assertEqual(summary["history_restarted_tonight"], 1)
            with sqlite3.connect(str(path)) as db:
                prices = db.execute("SELECT night, price_pence FROM prices ORDER BY night").fetchall()
                self.assertEqual(prices, [("2026-12-02", 2179)])
            again = remember_night(path, [site], prepared_at=night.replace(day=3))
            self.assertEqual(again["history_restarted_tonight"], 0)
            back = remember_night(path, [_product(1, price="21.79")], prepared_at=night.replace(day=4))
            self.assertEqual(back["history_restarted_tonight"], 1)


if __name__ == "__main__":
    unittest.main()
