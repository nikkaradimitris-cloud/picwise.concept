"""The debugging's first measure: how the search reads every kind's searches (owner, 2026-11-07).

`deployment/server/print_search_reading.py` (owner: «ζητάω μία μεγάλη γενική απασφαλμάτωση»,
then «Ναι σε όλα, πάμε σε νέα συζήτηση» to the method: category by category, the search read
first, offline and free). Pinned here, with the lexicon as it is and, where a reading is
judged, a reader of the test's own, so that no fault of today's search is written into a
test of the measure:

- the searches built from a name: its other number (English, and a one-word Greek name
  where its ending says which), the words buyers add, every typing slip but on a word's
  first letter or a word of three letters;
- the packs' product families searched without their generated tails;
- each reading judged: the kind, another kind's whole name typed, a broader or narrower
  kind, another kind of the category, a kind of another category, nothing;
- a word spelt right, read alone by a correction as a kind none of whose names holds it,
  listed with the kinds whose names do («μπαταρία» as boots, across categories);
- a shelf of Google's read as a kind its aisle may not hold, listed; one it may hold, not;
- the scoreboard counted per category and part;
- the script, on one category, printing its scoreboard, its faults and a JSON file, and
  exiting 0.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = ROOT / "deployment" / "server" / "print_search_reading.py"
for path in (ROOT / "deployment" / "server", ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import print_search_reading as measure  # noqa: E402
from picwise_nlu.concept_understanding import ConceptReading  # noqa: E402


def _reader(kinds: dict[str, tuple[str, bool]]):
    """A reader that reads each text as the test says: (kind, exact), else nothing."""

    def read(text: str) -> ConceptReading:
        kind, exact = kinds.get(text, (None, True))
        return ConceptReading(query=text, tokens=tuple(text.split()), concept_id=kind, exact=exact)

    return read


class OtherNumberTests(unittest.TestCase):
    def test_english_names_in_the_other_number(self) -> None:
        cases = {
            "batteries": "battery",
            "battery": "batteries",
            "boots": "boot",
            "drill bits": "drill bit",
            "external battery": "external batteries",
            "shelf": "shelves",
            "dress": "dresses",
            "watch": "watches",
            "hoodies": "hoodie",
            "lens": "lenses",
            "gpus": "gpu",
            "chest of drawers": "chests of drawers",
        }
        for name, other in cases.items():
            self.assertEqual(measure.english_other_number(name), other, name)

    def test_english_words_with_no_other_number_a_buyer_types(self) -> None:
        for name in ("glasses", "reading glasses", "jeans", "cookware", "gps", "ups"):
            self.assertIsNone(measure.english_other_number(name), name)

    def test_one_word_greek_names_whose_ending_says_their_number(self) -> None:
        cases = {
            "μπαταρία": "μπαταρίες",
            "ψυγείο": "ψυγεία",
            "ψυγεία": "ψυγείο",
            "φούρνος": "φούρνοι",
            "τηγάνι": "τηγάνια",
            "στρώμα": "στρώματα",
            "στρώματα": "στρώμα",
            "σκούπα": "σκούπες",
            "αφυγραντήρας": "αφυγραντήρες",
        }
        for name, other in cases.items():
            self.assertEqual(measure.greek_other_number(name), other, name)

    def test_greek_endings_of_either_number_and_names_of_more_words_are_left(self) -> None:
        for name in ("πλυντήρια", "κουζίνες", "αλκαλική μπαταρία", "laptop"):
            self.assertIsNone(measure.greek_other_number(name), name)


class SearchesBuiltTests(unittest.TestCase):
    def test_every_slip_but_on_a_words_first_letter(self) -> None:
        found = measure.slips("kettle")
        texts = {text for _how, text in found}
        for how, text in (("missing", "ketle"), ("doubled", "kettlle"), ("swapped", "ktetle"), ("key", "kwttle")):
            self.assertIn((how, text), found)
        self.assertTrue(all(text.startswith("k") for text in texts))
        self.assertNotIn("kettle", texts)
        self.assertEqual(len(texts), len(found))

    def test_no_slip_in_a_word_of_three_letters_and_no_key_without_the_keyboard(self) -> None:
        self.assertEqual(measure.slips("fan"), [])
        self.assertEqual({text.split()[0] for _how, text in measure.slips("fan heater")}, {"fan"})
        self.assertNotIn("key", {how for how, _text in measure.slips("μπαταρία", keyboard=False)})
        self.assertIn(("missing", "μπαταια"), measure.slips("μπαταρία", keyboard=False))

    def test_words_buyers_add(self) -> None:
        added = measure.with_words("watch", "JW")
        self.assertEqual(
            added,
            [
                ("brand", "Pandora watch"),
                ("brand", "Casio watch"),
                ("size", "watch 40mm"),
                ("before", "silver watch"),
                ("need", "watch for women"),
                ("best", "best watch"),
                ("cheap", "cheap watch"),
            ],
        )
        self.assertEqual(set(measure.CATEGORY_WORDS), set(measure.CATEGORY_CODES))

    def test_a_kinds_searches(self) -> None:
        searches = [s for s in measure.kind_searches(["MO"]) if s.kind == "e_bike"]
        texts = {s.text for s in searches}
        self.assertIn("electric bike", texts)
        self.assertIn("Shimano electric bike", texts)
        self.assertTrue(all(s.category == "MO" for s in searches))
        self.assertEqual(len(texts), len(searches))
        # The site reads English only (owner, 2026-11-07): no Greek search is measured.
        self.assertFalse([s for s in searches if s.language == "el"])

    def test_a_kinds_greek_searches_when_greek_is_read(self) -> None:
        previous = os.environ.get("PICWISE_GREEK_SEARCH")
        os.environ["PICWISE_GREEK_SEARCH"] = "on"
        try:
            searches = [s for s in measure.kind_searches(["MO"]) if s.kind == "e_bike"]
        finally:
            if previous is None:
                os.environ.pop("PICWISE_GREEK_SEARCH", None)
            else:
                os.environ["PICWISE_GREEK_SEARCH"] = previous
        self.assertIn("ηλεκτρικό ποδήλατο", {s.text for s in searches})
        self.assertEqual({s.how for s in searches if s.language == "el"} - {"name", "number"}, {"missing", "doubled", "swapped"})

    def test_the_packs_families_without_their_generated_tails(self) -> None:
        cases = {
            "compact laundry appliance family lines taxonomy families": "compact laundry appliance",
            "industrial allen key set families families": "industrial allen key set",
            "compact bench grinder product lines ecosystems": "compact bench grinder",
            "travel power bank family lines compatibility sets": "travel power bank",
            "skin care": "skin care",
            "socket set lines": "socket set",
        }
        for family, search in cases.items():
            self.assertEqual(measure.family_search(family), search, family)
        packs = measure.pack_searches(["HA"])
        self.assertTrue(packs and all(s.kind is None and s.category == "HA" for s in packs))


class ReadingTests(unittest.TestCase):
    def test_what_a_search_is_read_as(self) -> None:
        self.assertEqual(measure.outcome("heater", "heater", "heater"), measure.RIGHT)
        self.assertEqual(measure.outcome("bicycle", "e_bike", "electric bike"), measure.SPELLS)
        self.assertEqual(measure.outcome("robot_vacuum", "vacuum_cleaner", "root vacuum"), measure.BROADER)
        self.assertEqual(measure.outcome("bicycle", "e_bike", "electric bicycles"), measure.NARROWER)
        self.assertEqual(measure.outcome("hand_blender", "blender", "hnd blender"), measure.OTHER_KIND)
        self.assertEqual(measure.outcome("battery", "boots", "μπαταρία"), measure.OTHER_CATEGORY)
        self.assertEqual(measure.outcome("battery", None, "batery"), measure.NOTHING)

    def test_searches_read_by_a_reader(self) -> None:
        searches = [
            measure.Search("battery", "CO", "battery", "en", "name", "battery"),
            measure.Search("μπαταρία", "CO", "battery", "el", "number", "μπαταρίες"),
            measure.Search("table saws", "PT", None, "en", "subcategory", "table saws"),
            measure.Search("drills", "PT", None, "en", "subcategory", "drills"),
            measure.Search("tile cutters", "PT", None, "en", "subcategory", "tile cutters"),
        ]
        reader = _reader(
            {
                "battery": ("battery", True),
                "μπαταρία": ("boots", False),
                "table saws": ("table", True),
                "drills": ("drill", True),
            }
        )
        readings = measure.read_searches(searches, reader)
        self.assertEqual(
            [(r.kind, r.exact, r.outcome) for r in readings],
            [
                ("battery", True, measure.RIGHT),
                ("boots", False, measure.OTHER_CATEGORY),
                ("table", True, measure.OTHER_CATEGORY),
                ("drill", True, measure.RIGHT),
                (None, True, measure.NOTHING),
            ],
        )
        self.assertEqual(readings[1].shown(), '"μπαταρία" -> boots ~')
        board = measure.scoreboard(readings, categories=["CO", "PT"])
        self.assertEqual(board["CO"]["names"][measure.RIGHT], 1)
        self.assertEqual(board["CO"]["greek"][measure.OTHER_CATEGORY], 1)
        self.assertEqual(dict(board["PT"]["packs"]), {measure.OTHER_CATEGORY: 1, measure.RIGHT: 1, measure.NOTHING: 1})
        lines = measure.scoreboard_lines(board)
        self.assertIn("1 of its searches read as a kind of another category", lines[0])

    def test_a_word_spelt_right_read_by_a_correction_as_another_kind_is_a_guess(self) -> None:
        def every_word_as_boots(text: str) -> ConceptReading:
            return ConceptReading(query=text, tokens=(text,), concept_id="boots", exact=False)

        previous = os.environ.get("PICWISE_GREEK_SEARCH")
        os.environ["PICWISE_GREEK_SEARCH"] = "on"
        try:
            read, guesses = measure.word_guesses(every_word_as_boots)
        finally:
            if previous is None:
                os.environ.pop("PICWISE_GREEK_SEARCH", None)
            else:
                os.environ["PICWISE_GREEK_SEARCH"] = previous
        self.assertGreater(read, 1000)
        by_word = {guess.word: guess for guess in guesses}
        battery = by_word["μπαταρια"]
        self.assertIn("battery", battery.holders)
        self.assertIn("car_battery", battery.holders)
        self.assertTrue(battery.across)
        self.assertEqual(battery.nearest, "μποτακια")
        # A word of the boots' own names is no guess.
        self.assertNotIn("μποτακια", by_word)
        self.assertNotIn("boots", by_word)
        # With the site's English only, no Greek word is read alone.
        _read, english_guesses = measure.word_guesses(every_word_as_boots)
        self.assertFalse([guess for guess in english_guesses if measure.is_greek_word(guess.word)])
        self.assertIn("rubber", {guess.word for guess in english_guesses})

    def test_a_word_read_exactly_or_as_nothing_is_no_guess(self) -> None:
        read, guesses = measure.word_guesses(_reader({"rubber": ("router", True)}))
        self.assertGreater(read, 1000)
        self.assertEqual(guesses, [])

    def test_googles_shelves_read_as_a_kind_their_aisle_may_not_hold(self) -> None:
        def drills(text: str) -> ConceptReading:
            kind = "drill" if "drill" in text.lower() else None
            return ConceptReading(query=text, tokens=tuple(text.split()), concept_id=kind, exact=True)

        read, found = measure.shelf_readings(drills)
        self.assertGreater(read, 5000)
        shelves = {shelf.shelf for shelf in found}
        # What goes on a tool is not the tool; nail drills are no power tools.
        self.assertIn("Drill Chucks", shelves)
        self.assertIn("Nail Drills", shelves)
        # Hardware's power tools hold drills.
        self.assertNotIn("Drills", shelves)
        self.assertTrue(all(shelf.kind == "drill" and shelf.category == "PT" for shelf in found))


class ScriptTests(unittest.TestCase):
    def test_the_script_on_one_category(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "reading.json"
            done = subprocess.run(
                [sys.executable, str(SCRIPT), "--category", "JW", "--examples", "1", "--json", str(target)],
                capture_output=True,
                text=True,
                check=False,
                timeout=600,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            out = done.stdout
            self.assertIn("IN SHORT, per category", out)
            self.assertIn("JW jewelry_watches_bags_fashion_accessories: 15 kinds", out)
            self.assertIn("Every search read as a kind of another category", out)
            self.assertIn("== JW jewelry_watches_bags_fashion_accessories", out)
            self.assertNotIn("== HA", out)
            self.assertNotIn("http", out)
            record = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(record["categories"], ["JW"])
            self.assertEqual(set(record["scoreboard"]), {"JW"})
            self.assertTrue(all(fault["category"] == "JW" for fault in record["faults"]))
            self.assertTrue(all(fault["outcome"] != measure.RIGHT for fault in record["faults"]))


if __name__ == "__main__":
    unittest.main()
