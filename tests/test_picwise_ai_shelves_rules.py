"""The AI's shelves read by the catalogue (`picwise_providers.ai_shelves`; owner, 2026-11-20:
the same rules for both links, and the AI's mechanism rather than product by product):
rule 1, a second-link row given the AI's Google line as a first-link row carries the shop's;
rule 2 (owner, 20/11 19:00), a product of either link in a kind only when the AI's line for
it is on the kind's own list of Google's lines, else doubtful. The look-alikes seen live on
20/11 pinned: TV Cables' "RJ45 Snagless Boots" under "boots", Plusshop's "Garmin Fenix 6
Strap" under "watches", and those the measure after found: washers under "washing machine",
room fragrances under "perfume"."""
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
KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Electric Kettles"
WASHING_MACHINES = "Home & Garden > Household Appliances > Laundry Appliances > Washing Machines"
WASHERS = "Hardware > Hardware Accessories > Hardware Fasteners > Washers"
PERFUME = "Health & Beauty > Personal Care > Cosmetics > Perfume & Cologne"
ROOM_FRAGRANCE = "Home & Garden > Decor > Home Fragrances"
CAMERAS = "Cameras & Optics > Cameras"
DIGITAL_CAMERAS = "Cameras & Optics > Cameras > Digital Cameras"
DUMMY_CAMERAS = "Home & Garden > Business & Home Security > Dummy Surveillance Cameras"
SMART = "Electronics > Electronics Accessories > Wearable Technology"
# The kinds' lists the tests read, in the repository's form.
LISTS = {
    "watch": [WATCHES],
    "smartwatch": [SMART],
    "shoes": [SHOES],
    "boots": [SHOES],
    "kettle": [KETTLES],
    "washing_machine": [WASHING_MACHINES],
    "perfume": [PERFUME],
    "camera": [CAMERAS],
    "software": [],
}
# Lines the check added, each alone.
EXACT = {"camera": ["Home & Garden > Business & Home Security"]}


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
        self.lists = Path(self.folder.name) / "lists.json"
        self.lists.write_text(json.dumps({"kinds": LISTS, "exact": EXACT}), encoding="utf-8")
        names = (ai_shelves.AI_SHELVES_FILE_ENV, ai_shelves.KIND_LINES_FILE_ENV)
        self.before = {name: os.environ.get(name) for name in names}
        os.environ[ai_shelves.KIND_LINES_FILE_ENV] = str(self.lists)
        ai_shelves.reset()

    def tearDown(self) -> None:
        for name, value in self.before.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
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
    def test_a_kind_whose_list_does_not_hold_the_ais_line_makes_the_product_doubtful(self) -> None:
        strap = _first("Nato Strap 20mm Olive", "Acme", "Watches", WATCHES)
        backs = _first("Spare Earring Backs Butterfly Pair - Rosegold", "", "Watches", WATCHES)
        watch = _first("Diesel DZ4283 Mega Chief Chronograph Men's Watch", "Diesel", "Watches > Mens", WATCHES)
        self.assertIn("watch", _kinds(strap))
        self.answer((strap, BANDS), (backs, EARRINGS), (watch, WATCHES))
        self.assertEqual(_kinds(strap), frozenset({UNCERTAIN_MARKER}))
        self.assertEqual(_kinds(backs), frozenset({UNCERTAIN_MARKER}))
        self.assertIn("watch", _kinds(watch))

    def test_the_measures_look_alikes_washers_and_room_fragrances(self) -> None:
        washer = _first("M10 Steel Washer Pack of 50", "", "Washers", "Hardware")
        machine = _first("Bosch Series 4 9kg Washing Machine", "Bosch", "Washing Machines", WASHING_MACHINES)
        room = _first("Flower shop room fragrance - citrus zing", "", "Perfume", ROOM_FRAGRANCE)
        scent = _first("Chanel No 5 Eau de Parfum 50ml", "Chanel", "Perfume", PERFUME)
        self.assertIn("washing_machine", _kinds(washer))
        self.assertIn("perfume", _kinds(room))
        self.answer((washer, WASHERS), (machine, WASHING_MACHINES), (room, ROOM_FRAGRANCE), (scent, PERFUME))
        self.assertEqual(_kinds(washer), frozenset({UNCERTAIN_MARKER}))
        self.assertIn("washing_machine", _kinds(machine))
        self.assertEqual(_kinds(room), frozenset({UNCERTAIN_MARKER}))
        self.assertIn("perfume", _kinds(scent))

    def test_a_line_under_a_lists_line_is_on_it(self) -> None:
        lists = ai_shelves.kind_lists()
        self.assertTrue(ai_shelves.on_list(DIGITAL_CAMERAS, lists["camera"]))
        self.assertTrue(ai_shelves.on_list(CAMERAS, lists["camera"]))
        self.assertFalse(ai_shelves.on_list(DUMMY_CAMERAS, lists["camera"]))
        self.assertFalse(ai_shelves.on_list("Cameras & Optics", lists["camera"]))
        self.assertFalse(ai_shelves.on_list("Cameras & Optics > Cameras Extra", lists["camera"]))

    def test_a_line_the_check_added_holds_no_line_under_it(self) -> None:
        lists = ai_shelves.kind_lists()
        self.assertTrue(ai_shelves.on_list("Home & Garden > Business & Home Security", lists["camera"]))
        self.assertFalse(ai_shelves.on_list(DUMMY_CAMERAS, lists["camera"]))

    def test_a_kinds_list_holds_its_narrower_kinds_lines_and_only_the_kinds_off_their_list_leave(self) -> None:
        lists = ai_shelves.kind_lists()
        self.assertTrue(ai_shelves.on_list(SMART, lists["watch"]))
        self.assertFalse(ai_shelves.on_list(WATCHES, lists["smartwatch"]))
        raw = {ai_shelves.AI_KEY_COLUMN: "k"}
        self.assertEqual(
            ai_shelves.checked_kinds(frozenset({"smartwatch", "watch", "__pet__"}), title="x", brand="", raw=raw,
                                     table={"k": WATCHES}, lists=lists),
            frozenset({"watch", "__pet__"}),
        )
        self.assertEqual(
            ai_shelves.checked_kinds(frozenset({"smartwatch", "watch"}), title="x", brand="", raw=raw,
                                     table={"k": SMART}, lists=lists),
            frozenset({"smartwatch", "watch"}),
        )

    def test_a_kind_with_no_list_or_an_empty_one_is_not_read(self) -> None:
        lists = ai_shelves.kind_lists()
        self.assertNotIn("software", lists)
        raw = {ai_shelves.AI_KEY_COLUMN: "k"}
        for kinds in (frozenset({"software"}), frozenset({"laptop"})):
            self.assertEqual(
                ai_shelves.checked_kinds(kinds, title="x", brand="", raw=raw, table={"k": NETWORKING}, lists=lists),
                kinds,
            )
        self.assertEqual(
            ai_shelves.checked_kinds(frozenset({"laptop", "watch"}), title="x", brand="", raw=raw,
                                     table={"k": NETWORKING}, lists=lists),
            frozenset({"laptop"}),
        )

    def test_the_repositorys_lists_are_read_without_the_setting(self) -> None:
        os.environ.pop(ai_shelves.KIND_LINES_FILE_ENV, None)
        ai_shelves.reset()
        from picwise_ai.kind_lines import KIND_LINES_PATH, read

        kept = {kind for part in ("kinds", "exact") for kind, lines in read(KIND_LINES_PATH, part).items() if lines}
        self.assertEqual(set(ai_shelves.kind_lists()), kept)

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


class TakenTests(_WithAnswers):
    def _prepared(self, products):
        from types import SimpleNamespace

        return SimpleNamespace(
            products=products,
            search_fields=[_product_search_fields(product) for product in products],
            kinds=[_kinds(product) for product in products],
        )

    def test_what_the_lists_took_away_is_counted_by_kind_with_the_ais_lines(self) -> None:
        strap = _first("Nato Strap 20mm Olive", "Acme", "Watches", WATCHES)
        watch = _first("Diesel DZ4283 Mega Chief Chronograph Men's Watch", "Diesel", "Watches > Mens", WATCHES)
        washer = _first("M10 Steel Washer Pack of 50", "", "Washers", "Hardware")
        self.answer((strap, BANDS), (watch, WATCHES), (washer, WASHERS))
        prepared = self._prepared([strap, watch, washer])
        taken = measure_after.taken_away(prepared)
        self.assertEqual(taken.by_kind, {"watch": [0], "washing_machine": [2]})
        self.assertEqual((taken.products, taken.left_with_none, taken.with_kind), (2, 2, 1))
        text = "\n".join(measure_after.report_taken(prepared, taken))
        self.assertIn("taken out of a kind by the lists 2 (left with no kind, so doubtful: 2)", text)
        self.assertIn("watch 1 (Watch Bands 1; e.g. Nato Strap 20mm Olive)", text)
        self.assertIn("washing_machine 1 (Washers 1;", text)

    def test_a_sample_of_them_is_judged_and_the_real_ones_counted(self) -> None:
        from types import SimpleNamespace

        straps = [_first(f"Nato Strap {n}mm Olive", "Acme", "Watches", WATCHES) for n in range(12, 26)]
        real = _first("Casio Classic Digital Watch", "Casio", "Watches", WATCHES)
        self.answer(*[(strap, BANDS) for strap in straps], (real, BANDS))
        prepared = self._prepared([*straps, real])
        taken = measure_after.taken_away(prepared)
        self.assertEqual(len(taken.by_kind["watch"]), 15)
        sample = measure_after.hidden_sample(taken)
        self.assertEqual(len(sample["watch"]), measure_after.SAMPLE_A_KIND)
        self.assertEqual(sample, measure_after.hidden_sample(taken))

        def ask(request):
            rows = request["messages"][0]["content"].split("Products:\n")[1].splitlines()
            return SimpleNamespace(
                answer={"answers": [{"n": n, "answer": "yes" if "Casio" in row else "no"} for n, row in enumerate(rows, 1)]},
                cost_usd=0.001,
            )

        measure_after.SAMPLE_A_KIND, before = 15, measure_after.SAMPLE_A_KIND
        try:
            out, cost = measure_after.hidden_check(prepared, taken, ask, 1.0)
        finally:
            measure_after.SAMPLE_A_KIND = before
        text = "\n".join(out)
        self.assertIn("judged 15 of the products the lists took out of a kind", text)
        self.assertIn("really that kind 1 of 15 (6.7%)", text)
        self.assertIn("about 1 real ones hidden", text)
        self.assertIn("watch 1/15", text)
        self.assertIn("Casio Classic Digital Watch (watch; Watch Bands)", text)
        self.assertAlmostEqual(cost, 0.001)
        self.assertEqual(measure_after.hidden_check(prepared, taken, None, 1.0)[0], ["not judged (no AI)"])


class WorkflowTests(unittest.TestCase):
    workflow = (ROOT / ".github" / "workflows" / "ai-shelves-after.yml").read_text(encoding="utf-8")

    def test_it_runs_on_its_own_branch_reads_the_server_and_changes_nothing(self) -> None:
        self.assertIn("branches: [claude/shelves-after]", self.workflow)
        self.assertEqual(self.workflow.count("secrets.ANTHROPIC_API_KEY"), 1)
        self.assertNotIn("upload-artifact", self.workflow)
        self.assertNotIn("sudo tee", self.workflow)
        self.assertNotIn("sudo mv", self.workflow)
        self.assertEqual(self.workflow.count("PICWISE_AI_SHELVES_FILE"), 2)
        self.assertIn("rm -rf ~/.ssh/deploy_key", self.workflow)


if __name__ == "__main__":
    unittest.main()
