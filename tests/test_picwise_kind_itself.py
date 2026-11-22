"""The answers to the question "is it the kind itself", read by the night's preparation
(`picwise_providers.kind_itself`; `docs/PICWISE_KIND_ITSELF_RULES.md`; task 6 of the work
split by model; the owner's plan of 21/11, step 8).

Pinned here, with no call to any AI (the answers are the test's own):

- only a second reading moves a product: a first reading alone or an unsure changes nothing;
- an accessory, a part or a consumable leaves the kind and the broader kinds it carries
  through it; another thing leaves the kind, and its broader kind is asked in turn; a set
  stays where it is (the owner's word of 22/11);
- a product the lists took out of a kind is of it again when its second reading says so,
  with the context it carried; a product left with no kind is doubtful;
- which questions wait: a first reading for every narrowest kind, a second for what the
  first would move; a reading with no answer is asked twice, then left;
- an answer stands until another takes its place: one asked under other words of its kind
  is read as before, named to be asked again, and holds no new product at the gate;
- the brakes hold against what the catalogue showed the night before: the readings since
  the owner's last look are not applied to the products shown then where they would change
  too many of one kind's, nor on a night they would change too many in all; what is held
  stays held until the owner's word; a product not shown the night before, and a reading
  applied on an earlier night, are no change; with no night before, every answer is read;
- the switch off, no answers file, or one that cannot be read: nothing is read;
- a new product waits for its answers, at the cap's gate as the preparation's tool works
  it out, behind the checks' gate; a product shown before never waits; what is asked next
  is each kind's cheapest first, the kinds in turn, each kind's first cards that have no
  second reading, and a new product cheap enough to be a first card named as one;
- through the preparation itself and through its tool, night after night: a product the
  answers take out of a kind is not listed by a search for the kind; what a night shows is
  kept for the next night's brakes; the switch off, everything is back.

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_ai import itself  # noqa: E402
from picwise_nlu.concept_understanding import PET_MARKER, UNCERTAIN_MARKER  # noqa: E402
from picwise_providers import ai_shelves, kind_itself  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.kind_itself import Reading, Record, Shown, settle  # noqa: E402
from picwise_providers.search_selection import _product_search_fields, kinds_read  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache, prepare_feed_catalogue  # noqa: E402

UNCERTAIN = frozenset({UNCERTAIN_MARKER})


def _record(kind: str, first: str | None = None, second: str | None = None, *, day: str = "2026-11-23",
            tries: int = 0, version: str = "v", tried: str | None = None) -> Record:
    return Record(
        key="k", kind=kind, version=version,
        first=Reading(first, "", "claude-haiku-5-5", day) if first else None,
        second=Reading(second, "", "claude-sonnet-5-5", day) if second else None,
        tries=tries, tried=(version if tried is None else tried) if tries else "",
    )


def _lookup(*records: Record):
    by_kind = {record.kind: record for record in records}
    return by_kind.get


class OnlyASecondReadingMovesAProduct(unittest.TestCase):
    DRILL = frozenset({"drill"})

    def test_a_product_with_no_kind_of_its_own_has_no_question(self) -> None:
        for kinds in (frozenset(), UNCERTAIN, frozenset({"__accessory__"})):
            settled = settle(kinds, kinds, _lookup())
            self.assertIs(settled.kinds, kinds)
            self.assertEqual((settled.want_first, settled.want_second), ((), ()))

    def test_a_question_never_asked_waits_for_its_first_reading(self) -> None:
        settled = settle(self.DRILL, self.DRILL, _lookup())
        self.assertIs(settled.kinds, self.DRILL)
        self.assertEqual((settled.want_first, settled.want_second), (("drill",), ()))

    def test_a_question_is_asked_for_the_narrowest_kind_only(self) -> None:
        kinds = frozenset({"robot_vacuum", "vacuum_cleaner"})
        self.assertEqual(settle(kinds, kinds, _lookup()).want_first, ("robot_vacuum",))

    def test_a_first_reading_alone_moves_nothing(self) -> None:
        for first, wanted in (("itself", ()), ("accessory", ("drill",)), ("other", ("drill",)), ("unsure", ("drill",))):
            settled = settle(self.DRILL, self.DRILL, _lookup(_record("drill", first)))
            self.assertIs(settled.kinds, self.DRILL, first)
            # What the first reading would take out, or could not tell, is read again.
            self.assertEqual(settled.want_second, wanted, first)
            self.assertEqual(settled.want_first, ())

    def test_a_set_stays_where_it_is(self) -> None:
        # Owner, 22/11, asked whether a toaster sold with a kettle should be shown when a buyer
        # searches "toaster": «Να φαίνεται». The answer is kept and moves nothing.
        for first in ("set", "itself"):
            settled = settle(self.DRILL, self.DRILL, _lookup(_record("drill", first, "set")))
            self.assertIs(settled.kinds, self.DRILL, first)
            self.assertEqual((settled.out, settled.want_first, settled.want_second), ((), (), ()))
            self.assertEqual(settled.read_twice, ("drill",))
        # What the first reading calls a set is still read again: the second may read an accessory.
        self.assertEqual(settle(self.DRILL, self.DRILL, _lookup(_record("drill", "set"))).want_second, ("drill",))
        self.assertEqual(settle(self.DRILL, self.DRILL, _lookup(_record("drill", "set", "accessory"))).kinds, UNCERTAIN)
        # Nor does it bring a product back to a kind the lists took from it.
        back = settle(self.DRILL, UNCERTAIN, _lookup(_record("drill", "itself", "set")))
        self.assertIs(back.kinds, UNCERTAIN)
        self.assertEqual(back.back, ())
        self.assertIn(kind_itself.SET, kind_itself.ANSWERS)
        self.assertNotIn(kind_itself.SET, kind_itself.NOT_ITSELF)

    def test_what_goes_with_the_thing_leaves_the_kind(self) -> None:
        for said in ("accessory", "part", "consumable"):
            settled = settle(self.DRILL, self.DRILL, _lookup(_record("drill", said, said)))
            self.assertEqual(settled.kinds, UNCERTAIN, said)
            self.assertEqual(settled.out, (("drill", said, "2026-11-23"),))
            self.assertEqual((settled.want_first, settled.want_second), ((), ()))
            self.assertEqual(settled.read_twice, ("drill",))

    def test_the_second_reading_stands_against_the_first(self) -> None:
        # The first would take it out, the second reads it as the kind: it stays.
        settled = settle(self.DRILL, self.DRILL, _lookup(_record("drill", "set", "itself")))
        self.assertIs(settled.kinds, self.DRILL)
        self.assertEqual(settled.out, ())
        # A first card the first read as the kind, and the second does not.
        settled = settle(self.DRILL, self.DRILL, _lookup(_record("drill", "itself", "accessory")))
        self.assertEqual(settled.kinds, UNCERTAIN)

    def test_an_unsure_second_reading_changes_nothing(self) -> None:
        settled = settle(self.DRILL, self.DRILL, _lookup(_record("drill", "other", "unsure")))
        self.assertIs(settled.kinds, self.DRILL)
        self.assertEqual((settled.out, settled.want_second), ((), ()))

    def test_what_goes_with_the_thing_leaves_its_broader_kinds_too(self) -> None:
        kinds = frozenset({"robot_vacuum", "vacuum_cleaner"})
        settled = settle(kinds, kinds, _lookup(_record("robot_vacuum", "part", "part")))
        self.assertEqual(settled.kinds, UNCERTAIN)
        self.assertEqual(settled.out, (("robot_vacuum", "part", "2026-11-23"),))

    def test_another_thing_leaves_the_kind_and_its_broader_kind_is_asked(self) -> None:
        kinds = frozenset({"smartwatch", "watch"})
        settled = settle(kinds, kinds, _lookup(_record("smartwatch", "other", "other")))
        self.assertEqual(settled.kinds, frozenset({"watch"}))
        self.assertEqual(settled.want_first, ("watch",))
        # A watch, then: it stays one.
        both = _lookup(_record("smartwatch", "other", "other"), _record("watch", "itself"))
        self.assertEqual(settle(kinds, kinds, both).kinds, frozenset({"watch"}))
        self.assertEqual(settle(kinds, kinds, both).want_first, ())
        # No watch either.
        neither = _lookup(_record("smartwatch", "other", "other"), _record("watch", "other", "other"))
        self.assertEqual(settle(kinds, kinds, neither).kinds, UNCERTAIN)

    def test_a_broader_kind_another_narrow_kind_holds_stays(self) -> None:
        kinds = frozenset({"car_charger", "wireless_charger", "phone_charger"})
        settled = settle(kinds, kinds, _lookup(_record("car_charger", "accessory", "accessory"),
                                                _record("wireless_charger", "itself")))
        self.assertEqual(settled.kinds, frozenset({"wireless_charger", "phone_charger"}))

    def test_the_context_a_product_carries_stays_with_it(self) -> None:
        kinds = frozenset({"smartwatch", "watch", PET_MARKER})
        settled = settle(kinds, kinds, _lookup(_record("smartwatch", "other", "other")))
        self.assertEqual(settled.kinds, frozenset({"watch", PET_MARKER}))

    def test_a_question_with_no_answer_is_asked_twice_and_then_left(self) -> None:
        self.assertEqual(settle(self.DRILL, self.DRILL, _lookup(_record("drill", tries=1))).want_first, ("drill",))
        left = settle(self.DRILL, self.DRILL, _lookup(_record("drill", tries=kind_itself.MOST_TRIES)))
        self.assertEqual(left.want_first, ())
        self.assertIs(left.kinds, self.DRILL)
        # A second reading that came with no answer twice is asked no more: the product stays.
        self.assertEqual(settle(self.DRILL, self.DRILL, _lookup(_record("drill", "part", tries=1))).want_second, ("drill",))
        left = settle(self.DRILL, self.DRILL, _lookup(_record("drill", "part", tries=kind_itself.MOST_TRIES)))
        self.assertEqual((left.want_second, left.kinds), ((), self.DRILL))


class WhatTheListsTookOut(unittest.TestCase):
    TOY = frozenset({"toy", PET_MARKER})

    def test_it_waits_for_a_first_reading(self) -> None:
        settled = settle(self.TOY, UNCERTAIN, _lookup())
        self.assertIs(settled.kinds, UNCERTAIN)
        self.assertEqual(settled.want_first, ("toy",))

    def test_only_what_the_first_reading_would_bring_back_is_read_again(self) -> None:
        self.assertEqual(settle(self.TOY, UNCERTAIN, _lookup(_record("toy", "itself"))).want_second, ("toy",))
        for first in ("other", "accessory", "unsure"):
            settled = settle(self.TOY, UNCERTAIN, _lookup(_record("toy", first)))
            self.assertEqual((settled.want_first, settled.want_second), ((), ()), first)
            self.assertIs(settled.kinds, UNCERTAIN)

    def test_it_comes_back_when_the_second_reading_says_itself(self) -> None:
        settled = settle(self.TOY, UNCERTAIN, _lookup(_record("toy", "itself", "itself")))
        self.assertEqual(settled.kinds, self.TOY)
        self.assertEqual(settled.back, (("toy", "2026-11-23"),))
        for second in ("other", "accessory", "unsure"):
            self.assertIs(settle(self.TOY, UNCERTAIN, _lookup(_record("toy", "itself", second))).kinds, UNCERTAIN, second)

    def test_it_comes_back_beside_the_kinds_the_lists_left_it(self) -> None:
        before = frozenset({"table", "desk"})
        after = frozenset({"desk"})
        settled = settle(before, after, _lookup(_record("table", "itself", "itself"), _record("desk", "itself")))
        self.assertEqual(settled.kinds, before)

    def test_it_comes_back_with_its_broader_kinds(self) -> None:
        before = frozenset({"robot_vacuum", "vacuum_cleaner"})
        settled = settle(before, UNCERTAIN, _lookup(_record("robot_vacuum", "itself", "itself")))
        self.assertEqual(settled.kinds, before)

    def test_another_thing_may_still_be_the_broader_kind(self) -> None:
        before = frozenset({"smartwatch", "watch"})
        settled = settle(before, UNCERTAIN, _lookup(_record("smartwatch", "other")))
        self.assertEqual(settled.want_first, ("watch",))
        back = settle(before, UNCERTAIN, _lookup(_record("smartwatch", "other"), _record("watch", "itself", "itself")))
        self.assertEqual(back.kinds, frozenset({"watch"}))


class TheAnswersFile(unittest.TestCase):
    def test_what_is_written_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "itself" / "answers.jsonl.gz"
            records = {
                ("k1", "drill"): Record("k1", "drill", "1.abc", Reading("accessory", "hole saw arbor", "claude-haiku-5-5", "2026-11-23"),
                                        Reading("accessory", "hole saw arbor", "claude-sonnet-5-5", "2026-11-23")),
                ("k2", "drill"): Record("k2", "drill", "1.abc", Reading("itself", "combi drill", "claude-haiku-5-5", "2026-11-23")),
                ("k3", "toy"): Record("k3", "toy", "1.def", tries=2),
            }
            kind_itself.write_answers(path, records)
            self.assertEqual(kind_itself.read_answers(path), records)
            text = gzip.open(path, "rt", encoding="utf-8").read()
            self.assertEqual(len(text.splitlines()), 3)
            # A file names no product: keys, kinds and answers only.
            self.assertEqual(sorted(json.loads(text.splitlines()[0])), ["first", "k", "kind", "second", "v"])

    def test_a_line_that_is_no_record_is_passed_over(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "answers.jsonl.gz"
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write("not json\n[1, 2]\n" + json.dumps({"k": "k1", "kind": "drill", "v": "1.a",
                                                              "first": {"is": "broken"}, "second": {"is": "part"}}) + "\n"
                             + json.dumps({"k": "", "kind": "drill"}) + "\n")
            found = kind_itself.read_answers(path)
            self.assertEqual(list(found), [("k1", "drill")])
            self.assertIsNone(found[("k1", "drill")].first)
            self.assertEqual(found[("k1", "drill")].second.said, "part")

    def test_a_file_that_cannot_be_read_holds_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "answers.jsonl.gz"
            path.write_bytes(b"not a gzip file")
            self.assertEqual(kind_itself.read_answers(path), {})
            self.assertEqual(kind_itself.read_answers(Path(folder) / "none.jsonl.gz"), {})
            self.assertEqual(kind_itself.read_answers(None), {})


class TheSwitch(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(kind_itself.reset_for_tests)

    def test_the_repositorys_switch_is_off(self) -> None:
        self.assertEqual(kind_itself.read_switch(), (False, ""))
        self.assertIsNone(kind_itself.begin_night())
        self.assertEqual(kind_itself.last_note(), {"applied": False, "why": "the switch is off"})
        self.assertFalse(kind_itself.gate_on())

    def test_the_switch_and_the_day_of_the_last_look(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "switch.json"
            path.write_text(json.dumps({"gate": True, "looked_until": "2026-11-25"}), encoding="utf-8")
            self.assertEqual(kind_itself.read_switch(path), (True, "2026-11-25"))
            path.write_text(json.dumps({"gate": "yes"}), encoding="utf-8")
            self.assertEqual(kind_itself.read_switch(path), (False, ""))
            path.write_text("not json", encoding="utf-8")
            self.assertEqual(kind_itself.read_switch(path), (False, ""))
            self.assertEqual(kind_itself.read_switch(Path(folder) / "none.json"), (False, ""))

    def test_nothing_is_read_without_answers(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "answers.jsonl.gz"
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(kind_itself.ANSWERS_FILE_ENV, None)
                self.assertIsNone(kind_itself.begin_night(switch=(True, "")))
                self.assertEqual(kind_itself.last_note()["why"], "no answers file named")
            self.assertIsNone(kind_itself.begin_night(switch=(True, ""), path=path))
            self.assertEqual(kind_itself.last_note()["why"], "no answers yet")
            path.write_bytes(b"broken")
            self.assertIsNone(kind_itself.begin_night(switch=(True, ""), path=path))
            self.assertIn("cannot be read", kind_itself.last_note()["why"])
            self.assertFalse(kind_itself.gate_on())
            kind_itself.write_answers(path, {("k", "drill"): _record("drill", "itself")})
            night = kind_itself.begin_night(switch=(True, "2026-11-22"), path=path)
            self.assertIsNotNone(night)
            self.assertEqual(night.looked_until, "2026-11-22")
            self.assertTrue(kind_itself.gate_on())
            # The switch off: nothing read, whatever the file holds.
            self.assertIsNone(kind_itself.begin_night(switch=(False, ""), path=path))
            self.assertFalse(kind_itself.gate_on())


TODAY = "2026-11-24"


def _night(records: dict[tuple[str, str], Record], looked_until: str = "", shown: Shown | None = None) -> kind_itself.Night:
    return kind_itself.Night(records=records, looked_until=looked_until, versions=lambda kind: "v", shown=shown, today=TODAY)


def _shown(rows: dict[str, str], held: dict[str, str] | None = None, night_held: str = "") -> Shown:
    """What the catalogue of the night before showed: each row with the kinds it was shown as."""
    return Shown(rows={row: frozenset(kinds.split()) for row, kinds in rows.items()}, held=held or {},
                 night_held=night_held, night="2026-11-23")


def _row(place: int) -> str:
    return f"row-{place}"


class AnAnswerStandsUntilAnotherTakesItsPlace(unittest.TestCase):
    """The rules' 4.7: a kind described in other words has its questions asked again, and
    until then its answers are read as before."""

    DRILL = frozenset({"drill"})

    def test_an_answer_asked_under_other_words_stands_and_is_asked_again(self) -> None:
        records = {("k", "drill"): _record("drill", "part", "part", version="old")}
        night = _night(records)
        self.assertEqual(night.settle(0, self.DRILL, self.DRILL, "k"), UNCERTAIN)
        self.assertTrue(night.again("k", "drill"))
        self.assertTrue(night.to_ask(0))
        # No reading waits: a new product is not held at the gate for it.
        self.assertFalse(night.waits(0))
        self.assertEqual(night.note()["products_to_ask_again"], 1)
        records[("k", "drill")] = _record("drill", "part", "part", version="v")
        fresh = _night(records)
        self.assertEqual(fresh.settle(0, self.DRILL, self.DRILL, "k"), UNCERTAIN)
        self.assertFalse(fresh.to_ask(0))

    def test_a_question_asked_again_in_vain_is_left_with_its_answer(self) -> None:
        records = {("k", "drill"): _record("drill", "part", "part", version="old", tries=1, tried="v")}
        self.assertTrue(_night(records).again("k", "drill"))
        records[("k", "drill")] = _record("drill", "part", "part", version="old", tries=kind_itself.MOST_TRIES, tried="v")
        night = _night(records)
        self.assertFalse(night.again("k", "drill"))
        self.assertEqual(night.settle(0, self.DRILL, self.DRILL, "k"), UNCERTAIN)
        self.assertFalse(night.to_ask(0))

    def test_tries_count_only_under_todays_words(self) -> None:
        # Asked twice in vain under the kind's old words: under today's it is asked afresh.
        records = {("k", "drill"): _record("drill", version="old", tries=kind_itself.MOST_TRIES)}
        night = _night(records)
        self.assertIs(night.settle(0, self.DRILL, self.DRILL, "k"), self.DRILL)
        self.assertTrue(night.waits(0))
        records[("k", "drill")] = _record("drill", version="v", tries=kind_itself.MOST_TRIES)
        left = _night(records)
        left.settle(0, self.DRILL, self.DRILL, "k")
        self.assertFalse(left.waits(0))

    def test_the_kinds_version_is_the_questions_own(self) -> None:
        version = itself.kind_version("drill")
        record = Record("k", "drill", version, Reading("part"), Reading("part", at="2026-11-23"))
        night = kind_itself.Night(records={("k", "drill"): record})
        self.assertEqual(night.settle(0, self.DRILL, self.DRILL, "k"), UNCERTAIN)
        self.assertFalse(night.again("k", "drill"))
        stale = Record("k", "drill", "0.none", Reading("part"), Reading("part", at="2026-11-23"))
        self.assertTrue(kind_itself.Night(records={("k", "drill"): stale}).again("k", "drill"))


class TheBrakes(unittest.TestCase):
    """The rules' 7.2 to 7.5: the readings since the owner's last look, held against what the
    catalogue showed the night before."""

    DRILL = frozenset({"drill"})
    PRINTER = frozenset({"printer"})

    def _drills(self, parts: int, of: int = 100, day: str = "2026-11-23") -> dict[tuple[str, str], Record]:
        """A kind's products, all with a second reading; the first so many read as parts."""
        records = {(f"k{n}", "drill"): _record("drill", "itself", "itself", day=day) for n in range(of)}
        for n in range(parts):
            records[(f"k{n}", "drill")] = _record("drill", "part", "part", day=day)
        return records

    def _settled(self, night: kind_itself.Night, count: int, kinds: frozenset[str] = DRILL,
                 after: frozenset[str] | None = None) -> list[frozenset[str]]:
        after = kinds if after is None else after
        return night.finish([night.settle(place, kinds, after, f"k{place}") for place in range(count)], _row)

    def test_without_a_night_before_every_answer_is_read(self) -> None:
        # The first night the answers are read: nothing to hold against.
        night = _night(self._drills(30), looked_until="2026-11-22")
        kinds = self._settled(night, 100)
        self.assertEqual(sum(found == UNCERTAIN for found in kinds), 30)
        note = night.note()
        self.assertEqual(note["brakes"], "no memory of the night before: nothing to hold against")
        self.assertEqual((note["left_a_kind"], note["held_by_a_kinds_brake"], note["held_by_the_nights_brake"]), (30, [], ""))

    def test_a_few_changes_are_applied(self) -> None:
        shown = _shown({_row(n): "drill" for n in range(100)})
        night = _night(self._drills(19), looked_until="2026-11-22", shown=shown)
        kinds = self._settled(night, 100)
        self.assertEqual(sum(found == UNCERTAIN for found in kinds), 19)
        note = night.note()
        self.assertEqual(note["brakes"], "stood")
        self.assertEqual((note["left_a_kind"], note["left_by_answer"], note["held_by_a_kinds_brake"]), (19, {"part": 19}, []))
        self.assertEqual((note["changed_of_what_was_shown"], note["held_as_shown"]), (19, 0))
        self.assertEqual(note["products_with_a_second_reading"], 100)
        self.assertEqual(note["kinds_that_lost_the_most"], [{"kind": "drill", "products": 19}])

    def test_a_kinds_brake_holds_what_would_change_too_many_of_its_products(self) -> None:
        # 30 of a kind's 100 products shown the night before; one printer of 900.
        records = self._drills(30)
        records.update({(f"p{n}", "printer"): _record("printer", "itself", "itself") for n in range(900)})
        records[("p0", "printer")] = _record("printer", "part", "part")
        shown = _shown({**{_row(n): "drill" for n in range(100)}, **{_row(100 + n): "printer" for n in range(900)}})
        night = _night(records, looked_until="2026-11-22", shown=shown)
        kinds = [night.settle(place, self.DRILL, self.DRILL, f"k{place}") for place in range(100)]
        kinds += [night.settle(100 + place, self.PRINTER, self.PRINTER, f"p{place}") for place in range(900)]
        kinds = night.finish(kinds, _row)
        # The drills stay as they were shown; the printer's one change is applied.
        self.assertTrue(all(found == self.DRILL for found in kinds[:100]))
        self.assertEqual(kinds[100], UNCERTAIN)
        note = night.note()
        self.assertEqual(note["held_by_a_kinds_brake"], [{"kind": "drill", "products": 30, "since": TODAY}])
        self.assertEqual((note["left_a_kind"], note["changed_of_what_was_shown"], note["held_as_shown"]), (1, 31, 30))
        self.assertEqual(note["held_by_the_nights_brake"], "")
        self.assertEqual(night.held_since, {"drill": TODAY})

    def test_what_a_brake_holds_stays_held_until_the_owners_word(self) -> None:
        # The night after: 25 of the 30 are gone from the feed, the 5 left would not hold a
        # kind by themselves; the kind was held, so they stay as shown.
        shown = _shown({_row(n): "drill" for n in range(100)}, held={"drill": TODAY})
        night = _night(self._drills(5), looked_until="2026-11-22", shown=shown)
        kinds = self._settled(night, 100)
        self.assertTrue(all(found == self.DRILL for found in kinds))
        self.assertEqual(night.note()["held_by_a_kinds_brake"], [{"kind": "drill", "products": 5, "since": TODAY}])
        self.assertEqual(night.held_since, {"drill": TODAY})
        # The owner's word: the day of the last look moved up to the night it was held.
        looked = _night(self._drills(5), looked_until=TODAY, shown=shown)
        kinds = self._settled(looked, 100)
        self.assertEqual(sum(found == UNCERTAIN for found in kinds), 5)
        self.assertEqual((looked.note()["held_by_a_kinds_brake"], looked.held_since), ([], {}))

    def test_a_product_not_shown_the_night_before_is_no_change(self) -> None:
        # A shop's 300 phone cases arrive, read by the lists as phones and by the answers as
        # accessories: they were never shown as phones, so nothing is held.
        phone = frozenset({"smartphone"})
        records = {(f"k{n}", "smartphone"): _record("smartphone", "accessory", "accessory") for n in range(300)}
        records.update({(f"k{n}", "smartphone"): _record("smartphone", "itself", "itself") for n in range(300, 350)})
        shown = _shown({_row(n): "smartphone" for n in range(300, 350)})
        night = _night(records, looked_until="2026-11-22", shown=shown)
        kinds = self._settled(night, 350, phone)
        self.assertEqual(sum(found == UNCERTAIN for found in kinds), 300)
        note = night.note()
        self.assertEqual((note["changed_of_what_was_shown"], note["held_by_a_kinds_brake"], note["left_a_kind"]), (0, [], 300))

    def test_answers_read_on_an_earlier_night_are_no_change(self) -> None:
        # 30 products read as parts nights ago and shown as no drills since.
        shown = _shown({**{_row(n): "" for n in range(30)}, **{_row(n): "drill" for n in range(30, 100)}})
        night = _night(self._drills(30, day="2026-11-10"), looked_until="2026-11-01", shown=shown)
        kinds = self._settled(night, 100)
        self.assertEqual(sum(found == UNCERTAIN for found in kinds), 30)
        self.assertEqual((night.note()["changed_of_what_was_shown"], night.note()["held_by_a_kinds_brake"]), (0, []))

    def test_answers_the_owner_looked_at_are_no_reason_to_brake(self) -> None:
        shown = _shown({_row(n): "drill" for n in range(100)})
        night = _night(self._drills(30), looked_until="2026-11-23", shown=shown)
        kinds = self._settled(night, 100)
        self.assertEqual(sum(found == UNCERTAIN for found in kinds), 30)
        self.assertEqual((night.note()["held_by_a_kinds_brake"], night.note()["changed_of_what_was_shown"]), ([], 0))

    def _sixty_kinds(self, parts: int) -> tuple[list[str], dict[tuple[str, str], Record], Shown]:
        from picwise_nlu.product_concepts import get_product_concepts

        kinds_of_the_site = [concept.concept_id for concept in get_product_concepts()][:60]
        records, rows = {}, {}
        for number, kind in enumerate(kinds_of_the_site):
            for n in range(100):
                said = "part" if n < parts else "itself"
                records[(f"{kind}-{n}", kind)] = _record(kind, said, said)
                rows[_row(100 * number + n)] = kind
        return kinds_of_the_site, records, _shown(rows)

    def _all_settled(self, night: kind_itself.Night, kinds_of_the_site: list[str]) -> list[frozenset[str]]:
        kinds: list[frozenset[str]] = []
        for kind in kinds_of_the_site:
            own = frozenset({kind})
            kinds += [night.settle(len(kinds) + n, own, own, f"{kind}-{n}") for n in range(100)]
        return night.finish(kinds, _row)

    def test_the_whole_night_holds_when_too_many_would_change_in_all(self) -> None:
        # 60 kinds, 10 of each kind's 100 products: no kind passes its own brake (10 is
        # under 20), and 600 of 6,000 products with a second reading is over 5%.
        kinds_of_the_site, records, shown = self._sixty_kinds(10)
        night = _night(records, looked_until="2026-11-22", shown=shown)
        kinds = self._all_settled(night, kinds_of_the_site)
        self.assertFalse(any(found == UNCERTAIN for found in kinds))
        note = night.note()
        self.assertEqual(note["held_by_the_nights_brake"], TODAY)
        self.assertEqual((note["left_a_kind"], note["changed_of_what_was_shown"], note["held_as_shown"]), (0, 600, 600))
        self.assertEqual(note["held_by_a_kinds_brake"], [])
        # The night after, one change of what was shown: the night is held, so it waits too.
        _kinds, records, shown = self._sixty_kinds(0)
        records[(f"{kinds_of_the_site[0]}-0", kinds_of_the_site[0])] = _record(kinds_of_the_site[0], "part", "part")
        held = Shown(rows=shown.rows, held={}, night_held=TODAY, night=TODAY)
        after = _night(records, looked_until="2026-11-22", shown=held)
        self.assertFalse(any(found == UNCERTAIN for found in self._all_settled(after, kinds_of_the_site)))
        self.assertEqual(after.night_held_since, TODAY)
        # The owner's word.
        looked = _night(records, looked_until=TODAY, shown=held)
        self.assertEqual(sum(found == UNCERTAIN for found in self._all_settled(looked, kinds_of_the_site)), 1)
        self.assertEqual(looked.night_held_since, "")

    def test_a_kind_held_before_is_no_reason_to_hold_the_night(self) -> None:
        # 400 drills wait for the owner's word; tonight a printer changes.
        records = {(f"k{n}", "drill"): _record("drill", "part", "part") for n in range(400)}
        records.update({(f"k{n}", "printer"): _record("printer", "itself", "itself") for n in range(400, 1000)})
        records[("k400", "printer")] = _record("printer", "part", "part")
        shown = _shown({**{_row(n): "drill" for n in range(400)}, **{_row(n): "printer" for n in range(400, 1000)}},
                       held={"drill": "2026-11-23"})
        night = _night(records, looked_until="2026-11-22", shown=shown)
        kinds = [night.settle(place, self.DRILL, self.DRILL, f"k{place}") for place in range(400)]
        kinds += [night.settle(place, self.PRINTER, self.PRINTER, f"k{place}") for place in range(400, 1000)]
        kinds = night.finish(kinds, _row)
        self.assertTrue(all(found == self.DRILL for found in kinds[:400]))
        self.assertEqual(kinds[400], UNCERTAIN)
        self.assertEqual(night.night_held_since, "")
        self.assertEqual(night.held_since, {"drill": "2026-11-23"})

    def test_a_brake_holds_what_would_come_back_too(self) -> None:
        toy = frozenset({"toy"})
        records = {(f"k{n}", "toy"): _record("toy", "itself", "itself") for n in range(40)}
        shown = _shown({_row(n): "" for n in range(40)})
        night = _night(records, looked_until="2026-11-22", shown=shown)
        kinds = self._settled(night, 40, toy, UNCERTAIN)
        self.assertTrue(all(found == UNCERTAIN for found in kinds))
        self.assertEqual(night.note()["held_by_a_kinds_brake"], [{"kind": "toy", "products": 40, "since": TODAY}])
        self.assertEqual(night.note()["came_back"], 0)
        looked = _night(records, looked_until="2026-11-23", shown=shown)
        kinds = self._settled(looked, 40, toy, UNCERTAIN)
        self.assertTrue(all(found == toy for found in kinds))
        self.assertEqual(looked.note()["came_back"], 40)
        self.assertEqual(looked.note()["kinds_that_gained_the_most"], [{"kind": "toy", "products": 40}])

    def test_the_note_names_no_product(self) -> None:
        night = _night({("k0", "drill"): _record("drill", "part", "part")}, shown=_shown({_row(0): "drill"}))
        night.finish([night.settle(0, self.DRILL, self.DRILL, "k0")], _row)
        text = json.dumps(night.note())
        self.assertNotIn("k0", text)
        self.assertNotIn("row-0", text)
        self.assertEqual(night.note()["questions_kept"], 1)


class WhatWasShown(unittest.TestCase):
    def test_what_is_written_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = kind_itself.shown_path(Path(folder) / "catalogue.json.gz")
            self.assertEqual(path, Path(folder) / kind_itself.SHOWN_NAME)
            self.assertIsNone(kind_itself.read_shown(path))
            written = kind_itself.write_shown(path, {"awin:1": "drill", "awin:2": "", "awin:3": "robot_vacuum vacuum_cleaner"},
                                              held={"drill": "2026-11-24"}, night_held="", night="2026-11-24")
            self.assertEqual(written, 3)
            shown = kind_itself.read_shown(path)
            self.assertEqual(shown.rows, {"awin:1": frozenset({"drill"}), "awin:2": frozenset(),
                                          "awin:3": frozenset({"robot_vacuum", "vacuum_cleaner"})})
            self.assertEqual((shown.held, shown.night_held, shown.night), ({"drill": "2026-11-24"}, "", "2026-11-24"))

    def test_a_file_that_cannot_be_read_is_no_memory(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / kind_itself.SHOWN_NAME
            path.write_bytes(b"not gzip")
            self.assertIsNone(kind_itself.read_shown(path))
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                json.dump({"v": 99, "rows": {}}, handle)
            self.assertIsNone(kind_itself.read_shown(path))
            self.assertIsNone(kind_itself.read_shown(None))

    def test_the_rows_kept_are_the_products_with_a_question(self) -> None:
        drill = frozenset({"drill"})
        night = _night({("k0", "drill"): _record("drill", "part", "part")})
        kinds = [night.settle(0, drill, drill, "k0"), night.settle(1, drill, drill, "k1"), frozenset({"__accessory__"})]
        products = [_product(n, f"Fixturon Thing {n}", 10.0 + n) for n in range(3)]
        rows = kind_itself.shown_rows(night, products, kinds, [0, 1, 2])
        self.assertEqual(rows, {"awin:row-0": "", "awin:row-1": "drill"})
        self.assertEqual(kind_itself.shown_rows(night, products, kinds, [1]), {"awin:row-1": "drill"})


def _ean(number: int) -> str:
    """A barcode with its check digit right: the Recommended is chosen among the products
    that carry one (`search_selection._median_recommendation`)."""
    body = f"500000{number:06d}"
    total = sum(int(digit) * (3 if place % 2 else 1) for place, digit in enumerate(body))
    return body + str((10 - total % 10) % 10)


def _product(number: int, title: str, price: float, shop: str = "Fictional Store One", gtin: bool = True) -> ProviderProduct:
    raw = {"merchant_name": shop, "in_stock": "1", "product_type": "Tools > Drills"}
    if gtin:
        raw["gtin"] = _ean(number)
    return ProviderProduct(
        provider_key="awin", provider_product_id=f"row-{number}", title=title, brand="Fixturon", category_text="Tools > Drills",
        product_url=f"https://shop.invalid/p/{number}", image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text=f"{price:.2f}", availability_text="in stock", currency="GBP", raw=raw,
    )


class WhatIsAskedNext(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(kind_itself.reset_for_tests)
        self.addCleanup(ai_shelves.reset)
        # Seven drills from 60 to 66, and two "pilot drills" at 3 and 4, read as drills.
        self.products = [_product(n, f"Fixturon Cordless Drill Model{chr(65 + n)} 18V", 60.0 + n) for n in range(7)]
        self.products += [_product(7 + n, f"Fixturon Pilot Drill Type{chr(65 + n)} for hole saws", 3.0 + n) for n in range(2)]
        self.read = lambda place: kinds_read(self.products[place], _product_search_fields(self.products[place]))
        self.keys = [self.read(place)[2] for place in range(len(self.products))]
        self.assertEqual({self.read(place)[1] for place in range(9)}, {frozenset({"drill"})})
        self.assertEqual(len(set(self.keys)), 9)

    def _night(self, records: dict[tuple[str, str], Record]) -> tuple[kind_itself.Night, tuple[frozenset[str], ...]]:
        night = _night(records)
        with mock.patch.object(kind_itself, "_NIGHT", None):
            kinds = kind_itself.settle_catalogue(night, len(self.products), self.read)
        return night, kinds

    def test_the_first_cards_are_the_searchs_own(self) -> None:
        kinds = [frozenset({"drill"})] * 9
        front = kind_itself.first_cards(self.products, kinds, cards=4)
        # The cheapest four, and the Recommended: the middle one in price (the ninth at 62).
        self.assertEqual(front, {"drill": [7, 8, 0, 1, 2]})
        self.assertEqual(kind_itself.first_cards(self.products, kinds)["drill"][:2], [7, 8])

    def test_every_question_waits_before_any_answer(self) -> None:
        night, kinds = self._night({("other", "drill"): _record("drill", "itself")})
        self.assertEqual(set(kinds), {frozenset({"drill"})})
        self.assertEqual(night.note()["products_with_a_question_waiting"], 9)
        items = kind_itself.job_items(night, self.products, range(9), self.read)
        self.assertEqual(len(items), 9)
        # The kind's cheapest first.
        self.assertEqual([item["title"] for item in items[:2]],
                         ["Fixturon Pilot Drill TypeA for hole saws", "Fixturon Pilot Drill TypeB for hole saws"])
        first = items[0]
        self.assertEqual((first["kind"], first["want"], first["why"], first["price"], first["shop"], first["products"]),
                         ("drill", "first", "kind", "3.00 GBP", "Fictional Store One", 1))
        self.assertEqual(first["k"], self.keys[7])
        self.assertNotIn("_price", first)
        self.assertNotIn("http", json.dumps(items))
        self.assertNotIn("row-", json.dumps(items))

    def test_only_the_products_given_are_named(self) -> None:
        night, _kinds = self._night({("other", "drill"): _record("drill", "itself")})
        items = kind_itself.job_items(night, self.products, [0, 7], self.read)
        self.assertEqual([item["k"] for item in items], [self.keys[7], self.keys[0]])

    def test_what_the_first_reading_would_take_out_waits_for_the_second(self) -> None:
        records = {(key, "drill"): _record("drill", "itself") for key in self.keys}
        records[(self.keys[7], "drill")] = _record("drill", "accessory")
        night, kinds = self._night(records)
        self.assertEqual(set(kinds), {frozenset({"drill"})})
        items = kind_itself.job_items(night, self.products, range(9), self.read)
        self.assertEqual([(item["k"], item["want"], item["why"]) for item in items], [(self.keys[7], "second", "kind")])

    def test_a_kinds_first_cards_are_read_a_second_time(self) -> None:
        records = {(key, "drill"): _record("drill", "itself") for key in self.keys}
        records[(self.keys[7], "drill")] = _record("drill", "accessory", "accessory")
        night, kinds = self._night(records)
        self.assertEqual(kinds[7], UNCERTAIN)
        with mock.patch.object(kind_itself, "FRONT", 4):
            front = kind_itself.first_cards(self.products, kinds, cards=4)
            # The arbor gone from the kind, the next cheapest takes its place among the first
            # cards; the Recommended, the middle one of the eight left, is among them already.
            self.assertEqual(front["drill"], [8, 0, 1, 2])
            items = kind_itself.job_items(night, self.products, range(9), self.read, kept=self.products, kept_kinds=kinds)
        self.assertEqual({(item["k"], item["want"], item["why"]) for item in items},
                         {(self.keys[place], "second", "first card") for place in (8, 0, 1, 2)})
        # Once read a second time, a first card is not named again.
        for place in (8, 0, 1, 2):
            records[(self.keys[place], "drill")] = _record("drill", "itself", "itself")
        night, kinds = self._night(records)
        with mock.patch.object(kind_itself, "FRONT", 4):
            self.assertEqual(kind_itself.job_items(night, self.products, range(9), self.read, kept=self.products, kept_kinds=kinds), [])

    def test_an_answer_asked_under_other_words_is_named_to_be_asked_again(self) -> None:
        records = {(key, "drill"): _record("drill", "itself", "itself") for key in self.keys}
        # The arbor's answer was asked when the kind was described otherwise.
        records[(self.keys[7], "drill")] = _record("drill", "accessory", "accessory", version="old")
        night, kinds = self._night(records)
        # It is read as before, and named.
        self.assertEqual(kinds[7], UNCERTAIN)
        items = kind_itself.job_items(night, self.products, range(9), self.read)
        self.assertEqual([(item["k"], item["want"], item["why"], item.get("again")) for item in items],
                         [(self.keys[7], "first", "kind", True)])
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(kind_itself.write_job(items, folder), {"questions": 1, "first": 1, "second": 0, "again": 1})
        # A first card whose answer is of other words is asked again as a first card.
        records[(self.keys[8], "drill")] = _record("drill", "itself", version="old")
        night, kinds = self._night(records)
        with mock.patch.object(kind_itself, "FRONT", 4):
            items = kind_itself.job_items(night, self.products, range(9), self.read, kept=self.products, kept_kinds=kinds)
        self.assertIn((self.keys[8], "first", "first card", True),
                      [(item["k"], item["want"], item["why"], item.get("again")) for item in items])

    def test_a_product_cheaper_than_its_kinds_last_first_card_is_named_as_one(self) -> None:
        # Six drills shown and read; the seventh and the two pilot drills never asked. With a
        # front of four cards, the last first card costs 63: the pilot drills at 3 and 4 would
        # be first cards, the drill at 66 would not.
        records = {(key, "drill"): _record("drill", "itself", "itself") for key in self.keys[:6]}
        night, kinds = self._night(records)
        with mock.patch.object(kind_itself, "FRONT", 4):
            items = kind_itself.job_items(night, self.products, range(9), self.read,
                                          kept=self.products[:6], kept_kinds=kinds[:6])
        self.assertEqual({(item["k"], item["want"], item["why"]) for item in items},
                         {(self.keys[6], "first", "kind"), (self.keys[7], "first", "first card"),
                          (self.keys[8], "first", "first card")})
        # A kind with fewer cards than a front: every product of it is a first card.
        items = kind_itself.job_items(night, self.products, range(9), self.read, kept=self.products[:6], kept_kinds=kinds[:6])
        self.assertEqual({item["why"] for item in items}, {"first card"})
        # With no catalogue to rank against, a question is a kind's own.
        self.assertEqual({item["why"] for item in kind_itself.job_items(night, self.products, range(9), self.read)}, {"kind"})

    def test_the_kinds_take_turns(self) -> None:
        printers = [
            ProviderProduct(
                provider_key="awin", provider_product_id=f"p-{n}", title=f"Fixturon Inkjet Printer Series{chr(65 + n)}",
                brand="Fixturon", category_text="Office > Printers", product_url=f"https://shop.invalid/q/{n}",
                image_url=f"https://shop.invalid/j/{n}.jpg", price_text=f"{90 + n}.00", availability_text="in stock",
                currency="GBP", raw={"merchant_name": "Fictional Store One", "in_stock": "1", "product_type": "Office > Printers"},
            )
            for n in range(2)
        ]
        self.products += printers
        night, kinds = self._night({("other", "drill"): _record("drill", "itself")})
        self.assertEqual(kinds[9], frozenset({"printer"}))
        items = kind_itself.job_items(night, self.products, range(11), self.read)
        self.assertEqual([item["kind"] for item in items[:4]], ["drill", "printer", "drill", "printer"])
        self.assertEqual([item["price"] for item in items[:4]], ["3.00 GBP", "90.00 GBP", "4.00 GBP", "91.00 GBP"])

    def test_the_job_is_a_file_the_asking_reads(self) -> None:
        night, _kinds = self._night({("other", "drill"): _record("drill", "itself")})
        items = kind_itself.job_items(night, self.products, range(9), self.read)
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(kind_itself.write_job(items, folder), {"questions": 9, "first": 9, "second": 0, "again": 0})
            lines = gzip.open(Path(folder) / kind_itself.JOBS_NAME, "rt", encoding="utf-8").read().splitlines()
            self.assertEqual([json.loads(line)["k"] for line in lines], [item["k"] for item in items])
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(kind_itself.JOBS_ENV, None)
            self.assertIsNone(kind_itself.write_job(items))

    def test_a_new_product_waits_for_its_answers(self) -> None:
        records = {(key, "drill"): _record("drill", "itself") for key in self.keys[:7]}
        records[(self.keys[7], "drill")] = _record("drill", "accessory")
        # Nothing read: every product may take a place.
        self.assertTrue(kind_itself.may_enter(self.products[8]))
        with mock.patch.object(kind_itself, "_NIGHT", _night(records)):
            # Answered by its first reading, which would leave it where it is: it may enter.
            self.assertTrue(kind_itself.may_enter(self.products[0]))
            # Waiting for its second reading, and never asked: not yet.
            self.assertFalse(kind_itself.may_enter(self.products[7]))
            self.assertFalse(kind_itself.may_enter(self.products[8]))
        records[(self.keys[7], "drill")] = _record("drill", "accessory", "accessory")
        records[(self.keys[8], "drill")] = _record("drill", tries=2)
        with mock.patch.object(kind_itself, "_NIGHT", _night(records)):
            # Read twice, it enters (as no drill); asked twice with no answer, it is left as read.
            self.assertTrue(kind_itself.may_enter(self.products[7]))
            self.assertTrue(kind_itself.may_enter(self.products[8]))


def _load_prepare_tool():
    spec = importlib.util.spec_from_file_location("prepare_catalogue_itself_tool", ROOT / "tools" / "prepare_catalogue.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TheCapsGate(unittest.TestCase):
    """The cap as the preparation's tool works it out (`tools/prepare_catalogue._Cap`), behind
    the checks' gate and this one."""

    def setUp(self) -> None:
        from picwise_providers import checks_applied
        from picwise_providers.catalogue_cap import google_pool_path, row_key

        self.tool = _load_prepare_tool()
        self.checks = checks_applied
        for clear in (checks_applied.reset_for_tests, kind_itself.reset_for_tests, ai_shelves.reset):
            clear()
            self.addCleanup(clear)
        # Six drills shown the night before; a drill and a "pilot drill" new tonight, both
        # passed by the checks.
        self.products = [_product(n, f"Fixturon Cordless Drill Model{chr(65 + n)} 18V", 60.0 + n) for n in range(7)]
        self.products.append(_product(7, "Fixturon Pilot Drill TypeA for hole saws", 3.0))
        self.read = lambda place: kinds_read(self.products[place], _product_search_fields(self.products[place]))
        self.keys = [self.read(place)[2] for place in range(8)]
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.out = Path(self.folder.name) / "catalogue.json.gz"
        with gzip.open(google_pool_path(self.out), "wt", encoding="utf-8") as handle:
            json.dump({"v": 1, "keys": sorted(row_key(product) for product in self.products[:6])}, handle)
        from picwise_providers.catalogue_memory import product_key
        from picwise_providers.offer_health import build_feed_availability_context

        self.context = build_feed_availability_context(self.products)
        decisions = {"format": checks_applied.DECISIONS_FORMAT, "night": "2026-12-01",
                     "enter": [product_key(product) for product in self.products[6:]]}
        checks_applied.apply_checks(self.products, decisions=decisions, switch=True)
        self.assertTrue(checks_applied.gate_on())

    def _cap(self, records: dict[tuple[str, str], Record] | None):
        night = None
        if records is not None:
            night = _night(records)
            kind_itself.settle_catalogue(night, len(self.products), self.read)
        capping = self.tool._Cap(self.out)
        with mock.patch.object(kind_itself, "_NIGHT", night):
            keep = capping(self.products, [frozenset({"drill"})] * 8, self.context)
        self.assertIsNotNone(keep, capping.error)
        return capping, list(keep)

    def test_without_the_answers_a_product_that_passed_its_checks_enters(self) -> None:
        capping, keep = self._cap(None)
        self.assertEqual(keep, [True] * 8)
        self.assertFalse(capping.itself_gate)
        self.assertIsNone(capping.itself)
        self.assertIsNone(capping.write_itself_job())

    def test_a_new_product_waits_for_its_answers_and_is_named_for_the_ai(self) -> None:
        records = {(key, "drill"): _record("drill", "itself") for key in self.keys[:6]}
        records[(self.keys[7], "drill")] = _record("drill", "accessory")
        capping, keep = self._cap(records)
        self.assertTrue(capping.itself_gate)
        # The six shown stay; the new drill (never asked) and the pilot drill (its second
        # reading to come) wait at the gate.
        self.assertEqual(keep, [True] * 6 + [False, False])
        asked = {(item["k"], item["want"]) for item in capping.itself}
        self.assertIn((self.keys[6], "first"), asked)
        self.assertIn((self.keys[7], "second"), asked)
        # The six shown, the kind's first cards, are named for their second reading.
        self.assertEqual({item["why"] for item in capping.itself if item["k"] in self.keys[:6]}, {"first card"})
        with mock.patch.dict(os.environ, {kind_itself.JOBS_ENV: self.folder.name}):
            self.assertEqual(capping.write_itself_job(), {"questions": 8, "first": 1, "second": 7, "again": 0})
        self.assertTrue((Path(self.folder.name) / kind_itself.JOBS_NAME).is_file())

    def test_what_tonight_shows_is_kept_for_the_next_nights_brakes(self) -> None:
        records = {(key, "drill"): _record("drill", "itself", "itself") for key in self.keys[:7]}
        records[(self.keys[7], "drill")] = _record("drill", "accessory", "accessory")
        night = _night(records)
        kinds = list(kind_itself.settle_catalogue(night, len(self.products), self.read))
        capping = self.tool._Cap(self.out)
        path = kind_itself.shown_path(self.out)
        with mock.patch.object(kind_itself, "_NIGHT", night):
            keep = capping(self.products, kinds, self.context)
            self.assertEqual(list(keep), [True] * 8)
            self.assertEqual(capping.write_itself_shown(), {"rows": 8})
        shown = kind_itself.read_shown(path)
        self.assertEqual(shown.rows["awin:row-0"], frozenset({"drill"}))
        self.assertEqual(shown.rows["awin:row-7"], frozenset())
        self.assertEqual((shown.night, shown.held, shown.night_held), (TODAY, {}, ""))
        # A night that reads no answer keeps nothing: an old file would be no night before.
        self.assertIsNone(self.tool._Cap(self.out).write_itself_shown())
        self.assertFalse(path.exists())

    def test_the_tool_names_where_the_night_before_is_kept(self) -> None:
        kind_itself.remember_at(None)
        self.tool._Cap(self.out)
        self.assertEqual(kind_itself._SHOWN_FILE, kind_itself.shown_path(self.out))

    def test_once_answered_it_enters(self) -> None:
        records = {(key, "drill"): _record("drill", "itself", "itself") for key in self.keys[:7]}
        records[(self.keys[7], "drill")] = _record("drill", "accessory", "accessory")
        capping, keep = self._cap(records)
        self.assertEqual(keep, [True] * 8)
        self.assertEqual(capping.itself, [])

    def test_a_product_shown_before_never_waits(self) -> None:
        # No answer for any of the six shown: they stay, and are named for the AI.
        capping, keep = self._cap({("another", "drill"): _record("drill", "itself")})
        self.assertEqual(keep[:6], [True] * 6)
        self.assertEqual(keep[6:], [False, False])
        self.assertEqual({item["want"] for item in capping.itself}, {"first"})
        self.assertEqual(len(capping.itself), 8)


FEED = ("aw_product_id", "product_name", "brand_name", "merchant_category", "aw_deep_link", "aw_image_url",
        "search_price", "currency", "in_stock", "merchant_name", "ean")


class _AFeed:
    """A feed of the test's own, six drills and three "pilot drills", and where the answers
    are kept."""

    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        rows = []
        for n in range(6):
            rows.append([f"d{n}", f"Fixturon Cordless Drill Model{chr(65 + n)} 18V", "Fixturon", "Drills",
                         f"https://tools.example.invalid/products/d{n}", f"https://fixture.example.invalid/img/d{n}.jpg",
                         f"{60 + n}.00", "GBP", "1", "Fixture Tools Shop", f"50000000000{n:02d}"])
        for n in range(3):
            rows.append([f"a{n}", f"Fixturon Pilot Drill Type{chr(65 + n)} for hole saws", "Fixturon", "Drills",
                         f"https://tools.example.invalid/products/a{n}", f"https://fixture.example.invalid/img/a{n}.jpg",
                         f"{3 + n}.00", "GBP", "1", "Fixture Tools Shop", f"50000000001{n:02d}"])
        feed = self.folder / "feed.csv"
        with feed.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(FEED)
            writer.writerows(rows)
        self.answers = self.folder / "itself" / "answers.jsonl.gz"
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("AWIN_FEED_") and not key.startswith("PICWISE_")}
        env.update({"AWIN_FEED_FILE": str(feed), kind_itself.ANSWERS_FILE_ENV: str(self.answers)})
        patch = mock.patch.dict(os.environ, env, clear=True)
        patch.start()
        self.addCleanup(patch.stop)
        for clear in (clear_awin_feed_parse_cache, clear_provider_feed_pipeline_cache, kind_itself.reset_for_tests,
                      ai_shelves.reset):
            clear()
            self.addCleanup(clear)

    def _keys(self, prepared) -> dict[str, str]:
        return {
            str(product.provider_product_id): kinds_read(product, fields)[2]
            for product, fields in zip(prepared.products, prepared.search_fields)
        }


class ThroughThePreparation(_AFeed, unittest.TestCase):
    """The same pipeline the night's preparation runs."""

    def _prepared(self, switch: tuple[bool, str]):
        clear_provider_feed_pipeline_cache()
        with mock.patch.object(kind_itself, "read_switch", return_value=switch):
            return prepare_feed_catalogue()

    def test_the_answers_take_the_arbors_out_of_the_drills(self) -> None:
        before = self._prepared((False, ""))
        self.assertEqual(len(before.products), 9)
        self.assertEqual(set(before.kinds), {frozenset({"drill"})})
        self.assertEqual(kind_itself.last_note(), {"applied": False, "why": "the switch is off"})
        keys = self._keys(before)
        version = itself.kind_version("drill")
        records = {}
        for product_id, key in keys.items():
            said = "accessory" if product_id.startswith("a") else "itself"
            records[(key, "drill")] = Record(key, "drill", version, Reading(said, "x", "claude-haiku-5-5", "2026-11-23"),
                                            Reading(said, "x", "claude-sonnet-5-5", "2026-11-23"))
        kind_itself.write_answers(self.answers, records)
        # The switch still off: nothing read, whatever the file holds.
        self.assertEqual(set(self._prepared((False, "")).kinds), {frozenset({"drill"})})
        after = self._prepared((True, "2026-11-23"))
        kinds = {str(product.provider_product_id): found for product, found in zip(after.products, after.kinds)}
        self.assertEqual({product_id for product_id, found in kinds.items() if found == frozenset({"drill"})},
                         {f"d{n}" for n in range(6)})
        self.assertEqual({product_id for product_id, found in kinds.items() if found == UNCERTAIN}, {"a0", "a1", "a2"})
        note = kind_itself.last_note()
        self.assertEqual((note["applied"], note["left_a_kind"], note["left_by_answer"], note["came_back"]),
                         (True, 3, {"accessory": 3}, 0))
        self.assertEqual(note["products_with_a_question_waiting"], 0)

    def test_answers_asked_under_other_words_are_read_and_asked_again(self) -> None:
        before = self._prepared((False, ""))
        records = {(key, "drill"): Record(key, "drill", "0.old", Reading("part"), Reading("part", at="2026-11-23"))
                   for key in self._keys(before).values()}
        kind_itself.write_answers(self.answers, records)
        after = self._prepared((True, ""))
        self.assertEqual(set(after.kinds), {UNCERTAIN})
        note = kind_itself.last_note()
        self.assertEqual((note["products_with_a_question_waiting"], note["products_to_ask_again"]), (0, 9))

    def test_the_brakes_hold_against_what_the_night_before_showed(self) -> None:
        before = self._prepared((False, ""))
        keys = self._keys(before)
        version = itself.kind_version("drill")
        records = {}
        for product_id, key in keys.items():
            said = "accessory" if product_id.startswith("a") else "itself"
            records[(key, "drill")] = Record(key, "drill", version, Reading(said, "x", "claude-haiku-5-5", "2026-11-23"),
                                            Reading(said, "x", "claude-sonnet-5-5", "2026-11-23"))
        kind_itself.write_answers(self.answers, records)
        # The night before showed all nine as drills; the three arbors' answers came since
        # the last look and would change a third of the kind.
        from picwise_providers.catalogue_cap import row_key

        shown = self.folder / kind_itself.SHOWN_NAME
        kind_itself.write_shown(shown, {row_key(product): "drill" for product in before.products}, night="2026-11-23")
        kind_itself.remember_at(shown)
        with mock.patch.object(kind_itself, "KIND_BRAKE_MIN", 3):
            held = self._prepared((True, "2026-11-22"))
            self.assertEqual(set(held.kinds), {frozenset({"drill"})})
            note = kind_itself.last_note()
            self.assertEqual(note["brakes"], "stood")
            self.assertEqual([(entry["kind"], entry["products"]) for entry in note["held_by_a_kinds_brake"]], [("drill", 3)])
            self.assertEqual((note["left_a_kind"], note["held_as_shown"]), (0, 3))
            # The owner's word: the look moved up to the answers' day.
            looked = self._prepared((True, "2026-11-23"))
        self.assertEqual(sum(found == UNCERTAIN for found in looked.kinds), 3)
        self.assertEqual(kind_itself.last_note()["held_by_a_kinds_brake"], [])
        # With no memory of a night before, nothing is held.
        kind_itself.remember_at(None)
        with mock.patch.object(kind_itself, "KIND_BRAKE_MIN", 3):
            first = self._prepared((True, "2026-11-22"))
        self.assertEqual(sum(found == UNCERTAIN for found in first.kinds), 3)
        self.assertIn("no memory", kind_itself.last_note()["brakes"])


class ThroughTheTool(_AFeed, unittest.TestCase):
    """Two nights as the server lives them: `tools/prepare_catalogue.py` whole, with the
    answers file, the questions' folder and the public note."""

    def setUp(self) -> None:
        super().setUp()
        import logging

        self.addCleanup(logging.disable, logging.NOTSET)
        self.tool = _load_prepare_tool()
        self.out = self.folder / "prepared" / "catalogue.json.gz"
        self.out.parent.mkdir()
        self.static = self.folder / "public"
        self.static.mkdir()
        self.jobs = self.folder / "itself" / "jobs"
        self.jobs.mkdir(parents=True)
        os.environ[kind_itself.JOBS_ENV] = str(self.jobs)

    def _night(self, switch: tuple[bool, str]) -> tuple[dict, str]:
        import io
        from contextlib import redirect_stdout

        clear_provider_feed_pipeline_cache()
        said = io.StringIO()
        with mock.patch.object(kind_itself, "read_switch", return_value=switch), redirect_stdout(said):
            self.assertEqual(self.tool.main(["--out", str(self.out), "--static-dir", str(self.static)]), 0)
        return json.loads((self.static / "prepared.json").read_text(encoding="utf-8"))["itself"], said.getvalue()

    def _job(self) -> list[dict]:
        with gzip.open(self.jobs / kind_itself.JOBS_NAME, "rt", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle]

    def test_two_nights(self) -> None:
        from picwise_providers.prepared_catalogue import read_prepared_catalogue

        shown = kind_itself.shown_path(self.out)
        # The switch off: nothing read, nothing named, nothing kept for a next night.
        note, said = self._night((False, ""))
        self.assertEqual(note, {"applied": False, "why": "the switch is off"})
        self.assertIn("the kind itself not read (the switch is off)", said)
        self.assertFalse((self.jobs / kind_itself.JOBS_NAME).exists())
        self.assertFalse(shown.exists())
        before = read_prepared_catalogue(self.out)
        self.assertEqual(set(before.kinds), {frozenset({"drill"})})
        keys = self._keys(before)
        version = itself.kind_version("drill")
        # The first asking: the three arbors read twice as accessories, the drills once.
        records = {}
        for product_id, key in keys.items():
            first = Reading("accessory" if product_id.startswith("a") else "itself", "x", "claude-haiku-5-5", "2026-11-23")
            second = Reading("accessory", "x", "claude-sonnet-5-5", "2026-11-23") if product_id.startswith("a") else None
            records[(key, "drill")] = Record(key, "drill", version, first, second)
        kind_itself.write_answers(self.answers, records)
        # The first night the answers are read: the arbors leave, the drills, the kind's
        # first cards, are named for their second reading; what is shown is kept.
        note, said = self._night((True, "2026-11-23"))
        self.assertEqual((note["applied"], note["left_a_kind"], note["left_by_answer"]), (True, 3, {"accessory": 3}))
        self.assertIn("no memory of the night before", note["brakes"])
        self.assertEqual(note["for_the_ai"], {"questions": 6, "first": 0, "second": 6, "again": 0})
        self.assertIn("the kind itself: 3 products read twice, 3 left a kind (accessory 3), 0 came back", said)
        self.assertEqual({(item["want"], item["why"]) for item in self._job()}, {("second", "first card")})
        self.assertNotIn("http", json.dumps(self._job()))
        prepared = read_prepared_catalogue(self.out)
        kinds = {str(product.provider_product_id): found for product, found in zip(prepared.products, prepared.kinds)}
        self.assertEqual({product_id for product_id, found in kinds.items() if found == UNCERTAIN}, {"a0", "a1", "a2"})
        kept = kind_itself.read_shown(shown)
        self.assertEqual(len(kept.rows), 9)
        self.assertEqual(sum(1 for found in kept.rows.values() if found == frozenset({"drill"})), 6)
        # The morning's asking: a drill is read by the second model as a part. The next
        # night it would leave: one change of what was shown, applied, the brakes standing.
        key = keys["d0"]
        records[(key, "drill")] = Record(key, "drill", version, records[(key, "drill")].first,
                                        Reading("part", "x", "claude-sonnet-5-5", "2026-11-24"))
        kind_itself.write_answers(self.answers, records)
        note, _said = self._night((True, "2026-11-23"))
        self.assertEqual((note["brakes"], note["changed_of_what_was_shown"], note["left_a_kind"], note["held_as_shown"]),
                         ("stood", 1, 4, 0))
        self.assertEqual(note["for_the_ai"]["questions"], 5)
        self.assertEqual(kind_itself.read_shown(shown).rows[f"awin:{'d0'}"], frozenset())
        # The switch turned off again: everything back within one preparation.
        note, _said = self._night((False, ""))
        self.assertEqual(note, {"applied": False, "why": "the switch is off"})
        self.assertEqual(set(read_prepared_catalogue(self.out).kinds), {frozenset({"drill"})})
        self.assertFalse(shown.exists())


if __name__ == "__main__":
    unittest.main()
