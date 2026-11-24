"""The categories the site shows: a switch for each category and subcategory of Google's
taxonomy (`picwise_providers.category_scope`, `data/category_switches.json`,
`docs/PICWISE_CATEGORY_SWITCHES.md`; the owner, 2026-11-22 and 2026-11-23).

Pinned here:
- the repository's list: every line one of Google's, every top line of Google's on it, each
  with a name for the owner; its switch false until the owner's «ανέβασε»; frozen with the
  code; the owner's decisions, line by line, as they read with the switch on;
- the rule: a product is shown only when its top line is on the list and no line above it,
  its own included, is closed; a level the list does not name takes its parent's word; a
  list that cannot be read decides nothing;
- the night: with the switch off nothing leaves and the note counts what would; with it on
  what is closed leaves the preparation before anything counts products; a product with no
  line from the AI, or a slip, is not decided here; no answers, nothing decided;
- the cut products the bot asks again: not those of a closed category;
- the site: under "No products found", what PicWise covers, only with the switch on;
- the health run's line.
Every shop, product and address is fictional.
"""
from __future__ import annotations

import dataclasses
import gzip
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
SERVER = ROOT / "deployment" / "server"
for path in (HERE, ROOT, SRC, SERVER):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import ai_shelves, category_scope  # noqa: E402
from picwise_providers.category_scope import levels_of  # noqa: E402

TAXONOMY = ROOT / "data" / "taxonomy_sources" / "google" / "taxonomy.en-US.txt"


def _google_lines() -> set[str]:
    return {line.strip() for line in TAXONOMY.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")}


def _repo_list_on() -> category_scope.Switches:
    switches = category_scope.read_switches(category_scope.SWITCHES_FILE)
    assert switches is not None
    return dataclasses.replace(switches, on=True)


def _write_list(path: Path, lines: list[tuple[str, bool]], *, on: bool = True, site: dict | None = None) -> Path:
    site = site or {}
    path.write_text(json.dumps({
        "on": on,
        "lines": [{"google": google, "name": google, "on": state, **({"site": site[google]} if google in site else {})}
                  for google, state in lines],
    }), encoding="utf-8")
    return path


def _product(key: str, shop: str = "Fixture Store One") -> SimpleNamespace:
    # The AI's key kept in the row (`ai_shelves.AI_KEY_COLUMN`), as a second-link row keeps it.
    return SimpleNamespace(title=f"Fixture product {key}", brand="Fixturon",
                           raw={ai_shelves.AI_KEY_COLUMN: key, "merchant_name": shop})


class TheRepositorysListTests(unittest.TestCase):
    def setUp(self) -> None:
        category_scope.reset_for_tests()
        self.addCleanup(category_scope.reset_for_tests)
        self.payload = json.loads(category_scope.SWITCHES_FILE.read_text(encoding="utf-8"))

    def test_it_reads_and_its_switch_is_on_by_the_owners_word(self) -> None:
        # True from 2026-11-23 18:25 Athens: «Ανέβασε ότι έχεις φτιάξει στο site ανέβασε όλες τις
        # υλοποιήσεις». Turned off again only on his word.
        switches = category_scope.read_switches()
        self.assertIsNotNone(switches)
        self.assertTrue(switches.on)
        self.assertIs(self.payload["on"], True)
        self.assertEqual(self.payload["set"], "2026-11-23")
        self.assertIn("Ανέβασε", self.payload["by"])
        self.assertTrue(category_scope.scope_on())
        self.assertTrue(category_scope.site_words().startswith("PicWise covers home & garden"))

    def test_every_line_is_googles_and_every_top_line_of_googles_is_on_it(self) -> None:
        known = _google_lines()
        listed = [line["google"] for line in self.payload["lines"]]
        self.assertEqual(len(listed), len(set(listed)))
        for google in listed:
            self.assertIn(google, known)
        self.assertEqual({line for line in known if ">" not in line}, {line for line in listed if ">" not in line})

    def test_every_line_has_a_name_for_the_owner_and_a_true_or_false(self) -> None:
        for line in self.payload["lines"]:
            self.assertTrue(line["name"].strip(), line)
            self.assertNotEqual(line["name"], line["google"], line)
            self.assertIsInstance(line["on"], bool, line)

    def test_a_line_with_some_subcategories_listed_lists_them_all(self) -> None:
        # So that the dashboard to come shows every subcategory of a category the owner chose
        # in part. The one exception: one of the 80 tools, the rest open with their line.
        known = _google_lines()
        listed = {line["google"] for line in self.payload["lines"]}
        for parent in sorted(listed - {"Hardware > Tools"}):
            depth = parent.count(">") + 1
            under = {line for line in listed if line.startswith(parent + " > ") and line.count(">") == depth}
            if under:
                children = {line for line in known if line.startswith(parent + " > ") and line.count(">") == depth}
                self.assertEqual(under, children, parent)

    def test_the_list_is_frozen_with_the_code(self) -> None:
        from picwise_providers.prepared_catalogue import _FROZEN_FILES

        self.assertIn("data/category_switches.json", _FROZEN_FILES)

    def test_the_owners_decisions_line_by_line(self) -> None:
        switches = _repo_list_on()
        shown = [
            # Home & garden: appliances, kitchen, lighting, garden, home security.
            "Home & Garden > Household Appliances > Vacuums",
            "Home & Garden > Kitchen & Dining > Kitchen Appliances > Microwave Ovens",
            "Home & Garden > Kitchen & Dining > Kitchen Appliances > Deep Fryers",
            "Home & Garden > Lighting > Lamps",
            "Home & Garden > Lawn & Garden",
            "Home & Garden > Business & Home Security",
            # Furniture and tools.
            "Furniture > Sofas",
            "Furniture > Beds & Accessories > Mattresses",
            "Hardware > Tools > Drills",
            # Electronics, with the computer's parts and the television mounts.
            "Electronics > Computers > Laptops",
            "Electronics > Communications > Telephony > Mobile Phones",
            "Electronics > Video > Televisions",
            "Electronics > Video > Video Accessories",
            "Electronics > Electronics Accessories > Computer Components > I/O Cards & Adapters > Video Cards & Adapters",
            "Electronics > Electronics Accessories > Memory > RAM",
            "Electronics > Circuit Boards & Components > Printed Circuit Boards > Computer Circuit Boards > Motherboards",
            "Electronics > Video Game Console Accessories",
            "Electronics > Print, Copy, Scan & Fax > Printers, Copiers & Fax Machines",
            "Cameras & Optics > Cameras",
            "Cameras & Optics > Camera & Optic Accessories > Camera & Video Camera Lenses",
            # Fashion, jewellery and watches; hats, scarves and gloves.
            "Apparel & Accessories > Shoes",
            "Apparel & Accessories > Clothing > Dresses",
            "Apparel & Accessories > Jewelry > Watches",
            "Apparel & Accessories > Jewelry > Rings",
            "Apparel & Accessories > Clothing Accessories > Hats",
            "Apparel & Accessories > Clothing Accessories > Scarves & Shawls",
            "Apparel & Accessories > Clothing Accessories > Gloves & Mittens",
            "Apparel & Accessories > Clothing Accessories > Sunglasses",
            "Apparel & Accessories > Handbags, Wallets & Cases",
            # Toys, video games, perfume.
            "Toys & Games > Toys > Building Toys",
            "Toys & Games > Games > Board Games",
            "Toys & Games > Puzzles",
            "Software > Video Game Software",
            "Health & Beauty > Personal Care > Cosmetics > Perfume & Cologne",
            # 23/11 18:20, asked of what had closed without being talked over: sports in, and of
            # the vehicles the tyres alone («Ποτέ δεν αποφασίσαμε ότι κλείνουμε τα λάστιχα»).
            "Sporting Goods > Outdoor Recreation > Cycling > Bicycles",
            "Sporting Goods > Exercise & Fitness",
            "Vehicles & Parts > Vehicle Parts & Accessories > Motor Vehicle Parts > Motor Vehicle Wheel Systems"
            " > Motor Vehicle Tires > Automotive Tires",
            "Vehicles & Parts > Vehicle Parts & Accessories > Motor Vehicle Parts > Motor Vehicle Wheel Systems"
            " > Motor Vehicle Tires > Motorcycle Tires",
        ]
        closed = [
            # Out by category: pet shop, beauty and grooming, baby, luggage, sports, the car.
            "Animals & Pet Supplies > Pet Supplies",
            "Health & Beauty > Personal Care > Shaving & Grooming > Electric Razors",
            "Health & Beauty > Personal Care > Hair Care > Hair Styling Tools > Hair Dryers",
            "Health & Beauty > Personal Care > Deodorant & Anti-Perspirant > Deodorant",
            "Health & Beauty > Personal Care > Cosmetics > Makeup",
            "Baby & Toddler > Baby Toys & Activity Equipment",
            "Luggage & Bags > Backpacks",
            "Office Supplies",
            # Asked on 23/11 18:20 and left closed.
            "Media > Books",
            "Food, Beverages & Tobacco",
            "Arts & Entertainment",
            "Business & Industrial",
            # Of the vehicles, everything but the tyres.
            "Vehicles & Parts > Vehicles",
            "Vehicles & Parts > Vehicle Parts & Accessories > Motor Vehicle Parts > Motor Vehicle Engine Oil Circulation",
            "Vehicles & Parts > Vehicle Parts & Accessories > Motor Vehicle Parts > Motor Vehicle Wheel Systems"
            " > Motor Vehicle Rims & Wheels",
            "Vehicles & Parts > Vehicle Parts & Accessories > Vehicle Safety & Security",
            # The accessories and consumables of the categories that stay.
            "Electronics > Electronics Accessories > Cables",
            "Electronics > Electronics Accessories > Adapters",
            "Electronics > Electronics Accessories > Power",
            "Electronics > Electronics Accessories > Electronics Films & Shields",
            "Electronics > Electronics Accessories > Remote Controls",
            "Electronics > Communications > Telephony > Mobile Phone Accessories > Mobile Phone Cases",
            "Electronics > Radar Detectors",
            "Electronics > Print, Copy, Scan & Fax > Printer, Copier & Fax Machine Accessories",
            "Apparel & Accessories > Jewelry > Watch Accessories > Watch Bands",
            "Apparel & Accessories > Clothing > Underwear & Socks",
            "Apparel & Accessories > Costumes & Accessories",
            "Toys & Games > Games > Poker Chips & Sets",
            "Toys & Games > Games > Slot Machines",
            "Toys & Games > Toys > Wind-Up Toys",
            "Furniture > Sofa Accessories",
            "Furniture > Baby & Toddler Furniture",
            "Hardware > Tool Accessories",
            "Hardware > Plumbing",
            # What the owner was asked on 23/11 and left out.
            "Home & Garden > Linens & Bedding",
            "Home & Garden > Pool & Spa",
            "Home & Garden > Fireplaces",
            "Home & Garden > Flood, Fire & Gas Safety",
            "Home & Garden > Household Supplies",
            "Home & Garden > Decor",
            "Home & Garden > Lighting > Light Bulbs",
            "Home & Garden > Household Appliance Accessories",
            "Home & Garden > Plants",
        ]
        for line in shown:
            self.assertTrue(switches.is_open(levels_of(line)), line)
        for line in closed:
            self.assertFalse(switches.is_open(levels_of(line)), line)

    def test_what_a_visitor_is_told_with_the_switch_on(self) -> None:
        with mock.patch.object(category_scope, "read_switches", return_value=_repo_list_on()):
            self.assertEqual(
                category_scope.site_words(),
                "PicWise covers home & garden, furniture, tools, electronics, cameras, fashion, jewellery & watches,"
                " toys & games, sports & outdoors, video games, perfume and car tyres.",
            )


class TheRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        category_scope.reset_for_tests()
        self.addCleanup(category_scope.reset_for_tests)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "list.json"

    def test_a_closed_category_closes_everything_under_it(self) -> None:
        _write_list(self.path, [("Electronics", False), ("Electronics > Computers", True)])
        switches = category_scope.read_switches(self.path)
        self.assertFalse(switches.is_open(levels_of("Electronics > Computers > Laptops")))
        self.assertEqual(switches.closing(levels_of("Electronics > Computers")).google, "Electronics")

    def test_a_level_the_list_does_not_name_takes_its_parents_word(self) -> None:
        _write_list(self.path, [("Electronics", True), ("Electronics > Electronics Accessories > Cables", False)])
        switches = category_scope.read_switches(self.path)
        self.assertTrue(switches.is_open(levels_of("Electronics > Electronics Accessories > Memory > RAM")))
        self.assertFalse(switches.is_open(levels_of("Electronics > Electronics Accessories > Cables > USB Cables")))

    def test_a_top_line_not_on_the_list_is_not_shown(self) -> None:
        _write_list(self.path, [("Electronics", True)])
        switches = category_scope.read_switches(self.path)
        self.assertFalse(switches.is_open(levels_of("Sporting Goods > Athletics")))
        self.assertFalse(switches.is_open(()))

    def test_spaces_and_case_do_not_count(self) -> None:
        _write_list(self.path, [("Electronics", True), ("Electronics > Video", False)])
        switches = category_scope.read_switches(self.path)
        self.assertFalse(switches.is_open(levels_of("electronics >  VIDEO > Televisions")))
        self.assertTrue(switches.is_open(levels_of(" ELECTRONICS>Computers ")))

    def test_a_list_that_cannot_be_read_decides_nothing(self) -> None:
        self.assertIsNone(category_scope.read_switches(Path(self.folder.name) / "none.json"))
        self.path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(category_scope.read_switches(self.path))
        self.path.write_text(json.dumps({"on": True, "lines": [{"google": "Electronics", "name": "x", "on": "yes"}]}),
                             encoding="utf-8")
        self.assertIsNone(category_scope.read_switches(self.path))
        self.path.write_text(json.dumps({"on": True, "lines": [{"google": "Electronics", "on": True},
                                                               {"google": "electronics", "on": False}]}),
                             encoding="utf-8")
        self.assertIsNone(category_scope.read_switches(self.path))

    def test_the_list_is_read_again_when_it_changes(self) -> None:
        _write_list(self.path, [("Electronics", True)], on=False)
        self.assertFalse(category_scope.read_switches(self.path).on)
        _write_list(self.path, [("Electronics", True)], on=True)
        stat = self.path.stat()
        os.utime(self.path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
        self.assertTrue(category_scope.read_switches(self.path).on)

    def test_what_a_visitor_is_told_names_each_open_line_once(self) -> None:
        _write_list(self.path, [("Electronics", True), ("Electronics > Video", True), ("Furniture", False),
                                ("Software", True), ("Software > Video Game Software", True)],
                    site={"Electronics": "electronics", "Electronics > Video": "televisions",
                          "Furniture": "furniture", "Software > Video Game Software": "video games"})
        self.assertEqual(category_scope.site_words(self.path), "PicWise covers electronics and video games.")
        _write_list(self.path, [("Electronics", True)], on=False, site={"Electronics": "electronics"})
        stat = self.path.stat()
        os.utime(self.path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
        self.assertEqual(category_scope.site_words(self.path), "")


class TheNightTests(unittest.TestCase):
    LIST = [("Electronics", True), ("Electronics > Electronics Accessories", True),
            ("Electronics > Electronics Accessories > Cables", False), ("Sporting Goods", False)]
    ANSWERS = {
        "laptop": "Electronics > Computers > Laptops",
        "cable": "Electronics > Electronics Accessories > Cables > USB Cables",
        "ball": "Sporting Goods > Team Sports > Football",
        "odd": "Somewhere > Else",
        "slip": "Animals & Pet Supplies",
        "none": "",
    }

    def setUp(self) -> None:
        category_scope.reset_for_tests()
        self.addCleanup(category_scope.reset_for_tests)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "list.json"
        self.products = [_product("laptop", "Shop A"), _product("cable", "Shop A"), _product("cable", "Shop B"),
                         _product("ball", "Shop B"), _product("odd"), _product("slip"), _product("none"),
                         _product("unasked")]

    def switches(self, *, on: bool) -> category_scope.Switches:
        return category_scope.read_switches(_write_list(self.path, self.LIST, on=on))

    def test_with_the_switch_off_nothing_leaves_and_the_note_counts_what_would(self) -> None:
        keep = category_scope.settle(self.products, switches=self.switches(on=False), table=self.ANSWERS)
        self.assertIsNone(keep)
        note = category_scope.last_note()
        self.assertFalse(note["applied"])
        self.assertIn("switch is off", note["why"])
        self.assertEqual((note["products"], note["open"], note["closed"], note["undecided"]), (8, 1, 4, 3))
        self.assertEqual(note["not_listed"], 1)
        held = {line["google"]: (line["products"], line["open"]) for line in note["lines"]}
        self.assertEqual(held["Electronics"], (3, True))
        self.assertEqual(held["Electronics > Electronics Accessories"], (2, True))
        self.assertEqual(held["Electronics > Electronics Accessories > Cables"], (2, False))
        self.assertEqual(held["Sporting Goods"], (1, False))
        self.assertEqual(note["closed_by_shop"][0], {"shop": "Shop B", "closed": 2, "open": 0})

    def test_with_the_switch_on_what_is_closed_leaves(self) -> None:
        keep = category_scope.settle(self.products, switches=self.switches(on=True), table=self.ANSWERS)
        # The laptop stays; the cables, the ball and the line not on the list leave; a slip, no
        # line and no answer yet are the checks' to decide (their rules 5.5).
        self.assertEqual(keep, [True, False, False, False, False, True, True, True])
        self.assertTrue(category_scope.last_note()["applied"])

    def test_nothing_closed_keeps_every_product_without_a_list_of_places(self) -> None:
        keep = category_scope.settle(self.products[:1], switches=self.switches(on=True), table=self.ANSWERS)
        self.assertIsNone(keep)

    def test_without_the_ais_answers_or_the_list_nothing_is_decided(self) -> None:
        self.assertIsNone(category_scope.settle(self.products, switches=self.switches(on=True), table={}))
        self.assertIn("no answers", category_scope.last_note()["why"])
        with mock.patch.object(category_scope, "read_switches", return_value=None):
            self.assertIsNone(category_scope.settle(self.products, table=self.ANSWERS))
        self.assertIn("cannot be read", category_scope.last_note()["why"])

    def test_a_failure_keeps_every_product_and_is_noted(self) -> None:
        with mock.patch.object(category_scope, "settle", side_effect=RuntimeError("https://x.example.invalid/p")):
            self.assertIsNone(category_scope.settle_or_keep(self.products))
        note = category_scope.last_note()
        self.assertEqual(note["applied"], False)
        self.assertIn("RuntimeError", note["error"])
        self.assertNotIn("http", note["error"])
        with mock.patch.object(category_scope, "read_switches", side_effect=OSError("disk")):
            self.assertEqual(category_scope.passing(self.products), self.products)

    def test_the_cut_products_the_bot_asks_again_are_not_those_of_a_closed_category(self) -> None:
        with mock.patch.object(ai_shelves, "answers", return_value=self.ANSWERS):
            with mock.patch.object(category_scope, "read_switches", return_value=self.switches(on=True)):
                kept = category_scope.passing(self.products)
                self.assertTrue(category_scope.closes(self.products[1]))
            self.assertEqual([product.raw[ai_shelves.AI_KEY_COLUMN] for product in kept],
                             ["laptop", "slip", "none", "unasked"])
            with mock.patch.object(category_scope, "read_switches", return_value=self.switches(on=False)):
                self.assertEqual(len(category_scope.passing(self.products)), len(self.products))
                self.assertFalse(category_scope.closes(self.products[1]))


class ThePreparationTests(unittest.TestCase):
    """The list in the night's preparation (`state.prepare_feed_catalogue`), on the fixture feed of
    the prepared catalogue's tests: kettles and laptops; the laptops given a closed line."""

    def setUp(self) -> None:
        from test_picwise_prepared_catalogue import _PreparedMixin

        self.mixin = type("Mixin", (_PreparedMixin, unittest.TestCase), {"runTest": lambda self: None})()
        self.mixin.setUp()
        self.addCleanup(self.mixin.doCleanups)
        category_scope.reset_for_tests()
        self.addCleanup(category_scope.reset_for_tests)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        before = os.environ.get(ai_shelves.AI_SHELVES_FILE_ENV)

        def restore() -> None:
            if before is None:
                os.environ.pop(ai_shelves.AI_SHELVES_FILE_ENV, None)
            else:
                os.environ[ai_shelves.AI_SHELVES_FILE_ENV] = before
            ai_shelves.reset()

        self.addCleanup(restore)

    def _prepare_with(self, *, on: bool):
        from picwise_providers.state import clear_provider_feed_pipeline_cache, prepare_feed_catalogue
        from test_picwise_prepared_catalogue import _feed_rows

        self.mixin._write_feed(_feed_rows())
        os.environ.pop(ai_shelves.AI_SHELVES_FILE_ENV, None)
        ai_shelves.reset()
        products = prepare_feed_catalogue().products
        answers = Path(self.folder.name) / "answers.jsonl.gz"
        with gzip.open(answers, "wt", encoding="utf-8") as handle:
            for product in products:
                laptop = "Laptop" in product.title
                line = ("Electronics > Electronics Accessories > Cables" if laptop
                        else "Home & Garden > Kitchen & Dining > Kitchen Appliances")
                handle.write(json.dumps({"k": ai_shelves.key_of(product.title, product.brand, product.raw),
                                         "line": line, "tries": 1}) + "\n")
        os.environ[ai_shelves.AI_SHELVES_FILE_ENV] = str(answers)
        ai_shelves.reset()
        clear_provider_feed_pipeline_cache()
        listed = _write_list(Path(self.folder.name) / "list.json", [
            ("Home & Garden", True), ("Electronics", True),
            ("Electronics > Electronics Accessories", True), ("Electronics > Electronics Accessories > Cables", False),
        ], on=on)
        with mock.patch.object(category_scope, "SWITCHES_FILE", listed):
            return products, prepare_feed_catalogue()

    def test_with_the_switch_on_the_closed_category_leaves_the_catalogue(self) -> None:
        before, prepared = self._prepare_with(on=True)
        laptops = [product for product in before if "Laptop" in product.title]
        self.assertTrue(laptops)
        self.assertFalse([product for product in prepared.products if "Laptop" in product.title])
        self.assertEqual(len(prepared.products), len(before) - len(laptops))
        note = category_scope.last_note()
        self.assertTrue(note["applied"])
        self.assertEqual(note["closed"], len(laptops))

    def test_with_the_switch_off_every_product_stays_and_the_note_counts(self) -> None:
        before, prepared = self._prepare_with(on=False)
        self.assertEqual(len(prepared.products), len(before))
        note = category_scope.last_note()
        self.assertFalse(note["applied"])
        self.assertEqual(note["closed"], len([product for product in before if "Laptop" in product.title]))

    def test_the_looks_count_of_what_todays_catalogue_would_lose(self) -> None:
        import look_category_switches
        from picwise_providers.prepared_catalogue import write_prepared_catalogue

        before, prepared = self._prepare_with(on=False)
        write_prepared_catalogue(prepared, Path(self.folder.name) / "catalogue.json.gz")
        # The repository's list, read as if on: the laptops' line (cables) is closed there too.
        # As the look keeps it: written as JSON, read back by its "print".
        counted = json.loads(json.dumps(look_category_switches.shown(Path(self.folder.name)), ensure_ascii=False))
        laptops = len([product for product in before if "Laptop" in product.title])
        self.assertEqual((counted["products"], counted["closed"], counted["open"], counted["undecided"]),
                         (len(before), laptops, len(before) - laptops, 0))
        self.assertEqual(counted["closed_by_line"], [["Καλώδια (Electronics > Electronics Accessories > Cables)", laptops]])
        self.assertEqual(counted["closed_by_shop"], [["Fixture Store One", laptops, len(before) - laptops]])
        out = io.StringIO()
        with redirect_stdout(out):
            look_category_switches.print_all({"products_shown": 9, "categories": category_scope.last_note()}, counted)
        printed = out.getvalue()
        self.assertIn(f"would close {laptops:,}", printed)
        self.assertIn("Fixture Store One", printed)
        self.assertNotIn("http", printed)


class TheSiteTests(unittest.TestCase):
    def setUp(self) -> None:
        category_scope.reset_for_tests()
        self.addCleanup(category_scope.reset_for_tests)

    def test_under_no_products_found_what_picwise_covers_only_with_the_switch_on(self) -> None:
        from picwise_surface.reference import _no_products_try_html

        off = dataclasses.replace(_repo_list_on(), on=False)
        with mock.patch.object(category_scope, "read_switches", return_value=off):
            self.assertNotIn("PicWise covers", _no_products_try_html())
        with mock.patch.object(category_scope, "read_switches", return_value=_repo_list_on()):
            line = _no_products_try_html()
        self.assertIn("for example", line)
        self.assertIn("PicWise covers home &amp; garden, furniture, tools,", line)
        self.assertTrue(line.endswith("video games, perfume and car tyres."))


class TheLooksWorkflowTests(unittest.TestCase):
    def test_it_runs_on_its_own_branch_reads_only_and_removes_the_key(self) -> None:
        text = (ROOT / ".github" / "workflows" / "server-look-category-switches.yml").read_text(encoding="utf-8")
        self.assertIn("branches: [claude/category-switches-look]", text)
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn('rm -rf ~/.ssh/deploy_key ~/.ssh/config "$RUNNER_TEMP/look"', text)
        # The list's switch is set in the runner's copy of the code only, never pushed.
        self.assertIn('Path(os.environ["CODE"]) / "data" / "category_switches.json"', text)
        self.assertNotIn("git push", text)
        self.assertNotIn("sudo tee", text)
        self.assertIn('- {name: "off", categories: "off", checks: "server"}', text)
        self.assertIn('- {name: "on", categories: "on", checks: "server"}', text)


class TheHealthRunTests(unittest.TestCase):
    def test_the_line_of_the_categories(self) -> None:
        import print_health

        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        note = Path(folder.name) / "prepared.json"
        check = print_health.Health(datetime(2026, 11, 24, 8, 0, tzinfo=timezone.utc))
        with mock.patch.object(print_health, "PREPARED_NOTE", note):
            note.write_text(json.dumps({"prepared": True}), encoding="utf-8")
            print_health.look_at_categories(check)
            self.assertEqual(check.lines, [])
            note.write_text(json.dumps({"categories": {
                "applied": False, "products": 1600000, "open": 900000, "closed": 500000, "undecided": 200000,
                "closed_by_shop": [{"shop": "Fixture Store One", "closed": 40000, "open": 2}],
            }}), encoding="utf-8")
            print_health.look_at_categories(check)
            note.write_text(json.dumps({"categories": {"applied": False, "why": "the list cannot be read"}}),
                            encoding="utf-8")
            print_health.look_at_categories(check)
        self.assertEqual(check.lines, [
            "categories: the switch off; of 1,600,000 products a card can show 500,000 would be closed, 900,000 open,"
            " 200,000 with no category from the AI yet; most closed: Fixture Store One 40,000",
            "categories: the list decided nothing (the list cannot be read)",
        ])
        self.assertEqual(check.over, [])


if __name__ == "__main__":
    unittest.main()


class LowestPriceTests(unittest.TestCase):
    """The lowest price of a category (owner, 2026-11-24: «κανένα προϊόν μέσα στα αρώματα δεν
    μπορεί να έχει λιγότερο από 10 λίρες ... όλες τις κατηγορίες και υποκατηγορίες ... ένα
    ελάχιστο ποσό»; the 95 floors proposed, «Τα εγκρίνω όπως είναι», closed lines too)."""

    ANSWERS = {
        "laptop": "Electronics > Computers > Laptops",
        "mouse": "Electronics > Electronics Accessories > Computer Components > Input Devices",
        "plain": "Electronics > Video",
    }

    def setUp(self) -> None:
        category_scope.reset_for_tests()
        self.addCleanup(category_scope.reset_for_tests)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "list.json"

    def _switches(self, lines: list[dict]) -> category_scope.Switches | None:
        self.path.write_text(json.dumps({"on": True, "lines": lines}), encoding="utf-8")
        return category_scope.read_switches(self.path)

    def _priced(self, key: str, price: str) -> SimpleNamespace:
        product = _product(key)
        product.price_text = price
        return product

    def test_under_its_lines_floor_leaves_a_line_without_one_takes_the_nearest_above(self) -> None:
        switches = self._switches([
            {"google": "Electronics", "name": "Τεχνολογία", "on": True, "min": 10},
            {"google": "Electronics > Computers", "name": "Υπολογιστές", "on": True, "min": 60},
            {"google": "Electronics > Electronics Accessories", "name": "Αξεσουάρ", "on": True},
        ])
        products = [self._priced("laptop", "49.99"), self._priced("laptop", "299.00"),
                    self._priced("mouse", "7.99"), self._priced("mouse", "12.00"),
                    self._priced("plain", "9.99"), self._priced("laptop", "")]
        keep = category_scope.settle(products, switches=switches, table=self.ANSWERS)
        self.assertEqual(keep, [False, True, False, True, False, True])
        note = category_scope.last_note()
        self.assertEqual(note["under_floor"], 3)
        lines = {line["google"]: line for line in note["lines"]}
        self.assertEqual((lines["Electronics > Computers"]["min"], lines["Electronics > Computers"]["under_floor"]),
                         (60.0, 1))
        self.assertEqual(lines["Electronics"]["under_floor"], 2)
        self.assertNotIn("min", lines["Electronics > Electronics Accessories"])

    def test_a_floor_that_is_no_number_leaves_the_list_unread(self) -> None:
        self.assertIsNone(self._switches([{"google": "Electronics", "name": "x", "on": True, "min": "ten"}]))
        self.assertIsNone(self._switches([{"google": "Electronics", "name": "x", "on": True, "min": -1}]))

    def test_the_repositorys_floors_as_the_owner_approved_them(self) -> None:
        switches = _repo_list_on()
        floors = {line.google: line.min_price for line in switches.lines if line.min_price is not None}
        self.assertEqual(len(floors), 95)
        self.assertEqual(floors["Health & Beauty > Personal Care > Cosmetics > Perfume & Cologne"], 10.0)
        # A closed line carries its floor too, should it open («και ας είναι κλειστό»).
        self.assertEqual(floors["Health & Beauty > Personal Care > Cosmetics"], 5.0)
        self.assertEqual(floors["Furniture > Sofas"], 150.0)
        self.assertEqual(floors["Apparel & Accessories > Shoes"], 15.0)
        perfume = switches.floor(levels_of("Health & Beauty > Personal Care > Cosmetics > Perfume & Cologne > Women"))
        self.assertEqual(perfume.min_price, 10.0)
        chair = switches.floor(levels_of("Furniture > Chairs > Arm Chairs"))
        self.assertEqual((chair.google, chair.min_price), ("Furniture", 25.0))

