"""The AI's shelves read by the catalogue (`picwise_providers.ai_shelves`; owner, 2026-11-20:
the same rules for both links, and the AI's mechanism rather than product by product):
rule 1, a second-link row given the AI's Google line as a first-link row carries the shop's;
rule 2, a product of either link doubtful when the AI's line gives none of its kinds. The
look-alikes seen live on 20/11 pinned: TV Cables' "RJ45 Snagless Boots" under "boots",
Plusshop's "Garmin Fenix 6 Strap" under "watches"."""
from __future__ import annotations

import gzip
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import measure_after  # noqa: E402
import scan_shelves  # noqa: E402
from picwise_ai.shelves import ask_key, shop_words, taxonomy_lines  # noqa: E402
from picwise_nlu.concept_understanding import UNCERTAIN_MARKER  # noqa: E402
from picwise_providers import ai_shelves  # noqa: E402
from picwise_providers.awin_adapter import _with_aisle  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.search_selection import _product_concepts, _product_search_fields  # noqa: E402

CABLES = "Electronics > Electronics Accessories > Cables"
BANDS = "Apparel & Accessories > Jewelry > Watch Accessories > Watch Bands"
WATCHES = "Apparel & Accessories > Jewelry > Watches"
EARRINGS = "Apparel & Accessories > Jewelry > Earrings"
SHOES = "Apparel & Accessories > Shoes"
PAINT = "Hardware > Building Consumables > Painting Consumables"
NETWORKING = "Electronics > Networking"


def _second(title: str, brand: str, category: str) -> ProviderProduct:
    raw = {"merchant_id": "7", "aw_product_id": title[:8], "merchant_category": category, "category_name": category}
    return ProviderProduct("awin", title[:8], title, brand, category, "", "", "4.99", "in stock", "GBP", raw)


def _first(title: str, brand: str, product_type: str, google: str) -> ProviderProduct:
    raw = {"advertiser_id": "9", "product_type": product_type, "google_product_category": google}
    return ProviderProduct("awin", title[:8], title, brand, google, "", "", "4.99", "in stock", "GBP", raw)


def _kinds(product: ProviderProduct) -> frozenset[str]:
    return _product_concepts(product, _product_search_fields(product))


class _WithAnswers(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "answers.jsonl.gz"
        self.before = os.environ.get(ai_shelves.AI_SHELVES_FILE_ENV)
        ai_shelves.reset()

    def tearDown(self) -> None:
        if self.before is None:
            os.environ.pop(ai_shelves.AI_SHELVES_FILE_ENV, None)
        else:
            os.environ[ai_shelves.AI_SHELVES_FILE_ENV] = self.before
        ai_shelves.reset()
        self.folder.cleanup()

    def answer(self, *pairs: tuple[ProviderProduct, str | None]) -> None:
        with gzip.open(self.path, "wt", encoding="utf-8") as handle:
            for product, line in pairs:
                key = ask_key(product.title, product.brand, shop_words(product.raw))
                handle.write(json.dumps({"k": key, "line": line, "tries": 1}) + "\n")
            handle.write("not an answer\n")
        os.environ[ai_shelves.AI_SHELVES_FILE_ENV] = str(self.path)
        ai_shelves.reset()


class SecondLinkTests(_WithAnswers):
    def test_without_the_answers_nothing_changes(self) -> None:
        os.environ.pop(ai_shelves.AI_SHELVES_FILE_ENV, None)
        boots = _with_aisle(_second("RJ45 Snagless Boots for Cat6 6.5mm Pink 50 Pack", "", "RJ45 Boots"))
        self.assertEqual(boots.raw["google_product_category"], SHOES)
        self.assertIn("merchant_category", boots.raw)
        self.assertNotIn(ai_shelves.AI_KEY_COLUMN, boots.raw)
        self.assertIn("boots", _kinds(boots))

    def test_the_ais_line_is_the_rows_google_line_as_a_first_link_rows(self) -> None:
        boots = _second("RJ45 Snagless Boots for Cat6 6.5mm Pink 50 Pack", "", "RJ45 Boots")
        key = ask_key(boots.title, boots.brand, shop_words(boots.raw))
        self.answer((boots, CABLES))
        boots = _with_aisle(boots)
        self.assertEqual(boots.raw["google_product_category"], CABLES)
        self.assertEqual(boots.category_text, CABLES)
        self.assertEqual(boots.raw["product_type"], "RJ45 Boots")
        self.assertEqual(boots.raw[ai_shelves.AI_KEY_COLUMN], key)
        for column in ("merchant_category", "category_name"):
            self.assertNotIn(column, boots.raw)
        self.assertEqual(_kinds(boots), frozenset({UNCERTAIN_MARKER}))

    def test_the_live_look_alikes_leave_their_kind_the_real_things_keep_it(self) -> None:
        rows = [
            (_second("RJ45 Snagless Boot Yellow", "", "Cat6 Accessories"), CABLES, None),
            (_second("Garmin Fenix 6 Strap 22 mm Beige", "Garmin", "Smart Watches"), BANDS, None),
            (_second("Plastic Paint Kettle 2.5L", "", "Decorating > Paint Kettles"), PAINT, None),
            (_second("Garmin Forerunner 55 GPS Running Watch", "Garmin", "Smart Watches"), WATCHES, "watch"),
            (_second("Women's Chelsea Boots Black", "", "Footwear"), SHOES, "boots"),
        ]
        self.answer(*[(product, line) for product, line, _kind in rows])
        for product, _line, kind in rows:
            kinds = _kinds(_with_aisle(product))
            if kind is None:
                self.assertEqual(kinds, frozenset({UNCERTAIN_MARKER}), product.title)
            else:
                self.assertIn(kind, kinds, product.title)

    def test_no_line_or_no_answer_keeps_the_guess(self) -> None:
        none = _second("Gift Card 20", "", "Gift Cards")
        other = _second("RJ45 Snagless Boots for Cat6 6.5mm Pink 50 Pack", "", "RJ45 Boots")
        self.answer((none, ""))
        self.assertNotIn(ai_shelves.AI_KEY_COLUMN, _with_aisle(none).raw)
        self.assertEqual(_with_aisle(other).raw["google_product_category"], SHOES)


class BothLinksTests(_WithAnswers):
    def test_a_kind_the_ais_line_does_not_give_makes_the_product_doubtful(self) -> None:
        strap = _first("Nato Strap 20mm Olive", "Acme", "Watches", WATCHES)
        backs = _first("Spare Earring Backs Butterfly Pair - Rosegold", "", "Watches", WATCHES)
        watch = _first("Diesel DZ4283 Mega Chief Chronograph Men's Watch", "Diesel", "Watches > Mens", WATCHES)
        self.assertIn("watch", _kinds(strap))
        self.answer((strap, BANDS), (backs, EARRINGS), (watch, WATCHES))
        self.assertEqual(_kinds(strap), frozenset({UNCERTAIN_MARKER}))
        self.assertEqual(_kinds(backs), frozenset({UNCERTAIN_MARKER}))
        self.assertIn("watch", _kinds(watch))

    def test_a_line_of_no_known_kind_doubts_only_from_another_department(self) -> None:
        away = _first("Garmin Forerunner 55 GPS Running Watch", "Garmin", "Watches", WATCHES)
        near = _first("Casio Classic Digital Watch", "Casio", "Watches", WATCHES)
        self.answer((away, NETWORKING), (near, "Apparel & Accessories > Jewelry"))
        self.assertEqual(_kinds(away), frozenset({UNCERTAIN_MARKER}))
        self.assertIn("watch", _kinds(near))

    def test_the_british_name_of_a_department_is_the_same_department(self) -> None:
        self.assertEqual(ai_shelves._department("Clothing & Accessories > Shoes"), ai_shelves._department(SHOES))
        trainers = _first("Nike Air Max 90 Trainers", "Nike", "Trainers", "Clothing & Accessories > Shoes")
        kinds = _kinds(trainers)
        self.answer((trainers, "Apparel & Accessories"))
        self.assertEqual(_kinds(trainers), kinds)

    def test_no_answer_no_line_or_no_kind_changes_nothing(self) -> None:
        refused = _first("Nato Strap 20mm Olive", "Acme", "Watches", WATCHES)
        none = _first("Nato Strap 20mm Olive", "Other", "Watches", WATCHES)
        self.answer((refused, None), (none, ""))
        self.assertIn("watch", _kinds(refused))
        self.assertIn("watch", _kinds(none))
        self.assertEqual(
            ai_shelves.checked_kinds(frozenset({UNCERTAIN_MARKER}), title="x", brand="", raw={}, table={"k": CABLES}),
            frozenset({UNCERTAIN_MARKER}),
        )


class AnswersFileTests(_WithAnswers):
    def test_only_lines_given_are_read_and_a_new_file_is_read_again(self) -> None:
        one = _second("RJ45 Boot Grey", "", "RJ45 Boots")
        two = _second("Kettle Lead 2m", "", "Cables")
        self.answer((one, CABLES), (two, None))
        self.assertEqual(list(ai_shelves.answers().values()), [CABLES])
        original = ai_shelves._RECHECK_SECONDS
        ai_shelves._RECHECK_SECONDS = 0.0
        try:
            time.sleep(0.01)
            self.answer((one, NETWORKING), (two, CABLES))
            os.utime(self.path, ns=(time.time_ns(), time.time_ns() + 10_000_000))
            self.assertEqual(sorted(ai_shelves.answers().values()), [CABLES, NETWORKING])
        finally:
            ai_shelves._RECHECK_SECONDS = original
        self.assertEqual(ai_shelves.read_answers(Path(self.folder.name) / "none.gz"), {})

    def test_the_scan_asks_a_row_by_the_key_it_keeps(self) -> None:
        boots = _second("RJ45 Snagless Boots for Cat6 6.5mm Pink 50 Pack", "", "RJ45 Boots")
        key = ask_key(boots.title, boots.brand, shop_words(boots.raw))
        self.answer((boots, CABLES))
        kept = _with_aisle(boots)
        self.assertEqual(list(scan_shelves.groups_of([kept], taxonomy_lines())), [key])


class MeasureAfterTests(unittest.TestCase):
    def test_the_report_counts_the_wrong_cards_by_link_and_names_them(self) -> None:
        found = [
            measure_after.Searched("boots", "boots", 120, [
                measure_after.Card("1", "Chelsea Boots", "Shoe Shop", "40", False, "yes"),
                measure_after.Card("2", "RJ45 Snagless Boot", "TV Cables", "0.07", True, "no"),
                measure_after.Card("3", "Ankle Boots", "Shoe Shop", "30", True, "unsure"),
            ]),
            measure_after.Searched("watches", "watch", 50, [
                measure_after.Card("4", "Casio Watch", "Watch Shop", "20", False, "yes"),
            ]),
            measure_after.Searched("lego", "", 0, [], error="KeyError"),
        ]
        totals, each = measure_after.report(found)
        text = "\n".join(totals)
        self.assertIn("judged 3", text)
        self.assertIn("right 2 of 3 (66.7%); wrong 1", text)
        self.assertIn("second link: 1 cards judged, wrong 1 of 1 (100.0%)", text)
        self.assertIn("TV Cables 1", text)
        self.assertIn('"boots" (boots, 120 products): 1 right, 1 wrong of 3 -- RJ45 Snagless Boot (TV Cables, 2nd)', each[0])
        self.assertIn("the search failed (KeyError)", each[2])


class DoubtedTests(unittest.TestCase):
    def test_what_rule_two_took_away_is_counted_by_kind(self) -> None:
        from types import SimpleNamespace

        strap = _first("Nato Strap 20mm Olive", "Acme", "Watches", WATCHES)
        watch = _first("Diesel DZ4283 Mega Chief Chronograph Men's Watch", "Diesel", "Watches > Mens", WATCHES)
        products = [strap, watch]
        prepared = SimpleNamespace(
            products=products,
            search_fields=[_product_search_fields(product) for product in products],
            kinds=[frozenset({UNCERTAIN_MARKER}), frozenset({"watch"})],
        )
        text = "\n".join(measure_after.doubted(prepared))
        self.assertIn("products with a kind 1; doubtful 1, of which the AI's line made doubtful 1", text)
        self.assertIn("watch 1 (e.g. Nato Strap 20mm Olive)", text)


class WorkflowTests(unittest.TestCase):
    workflow = (ROOT / ".github" / "workflows" / "ai-shelves-after.yml").read_text(encoding="utf-8")

    def test_it_runs_on_its_own_branch_reads_the_server_and_changes_nothing(self) -> None:
        self.assertIn("branches: [claude/shelves-after]", self.workflow)
        self.assertEqual(self.workflow.count("secrets.ANTHROPIC_API_KEY"), 1)
        self.assertNotIn("upload-artifact", self.workflow)
        self.assertNotIn("sudo tee", self.workflow)
        self.assertNotIn("sudo mv", self.workflow)
        self.assertIn("PICWISE_AI_SHELVES_FILE", self.workflow)
        self.assertIn("rm -rf ~/.ssh/deploy_key", self.workflow)


if __name__ == "__main__":
    unittest.main()
