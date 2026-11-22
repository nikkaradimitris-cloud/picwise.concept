"""The asking of the question "is it the kind itself" (`picwise_ai.itself_asking`, the
morning's service `deployment/server/itself_service.py`, the first asking
`deployment/server/ask_itself.py`; `docs/PICWISE_KIND_ITSELF_RULES.md`, 4.4, 4.7 and 8).

Pinned here, with models of the test's own (no call leaves the test):

- the first reading is Claude Haiku 5.5's, the second Claude Sonnet 5.5's; a first reading
  that would move a product is followed by its second in the same run; a first card is
  read a second time whatever the first said;
- a call holds one kind and 40 products at most, each kind's first call before any kind's
  second;
- a reading with no answer is counted, asked once more, then left;
- a question asked again keeps its answer until the new one is whole;
- the run stops before its budget and at its deadline, and saves its answers along the way;
- the morning's service: the questions named, asked, kept in the file the preparation reads,
  its note counts only; an answers file that cannot be read is never written over;
- the first asking: the nights lived one after another until nothing is named, the first
  cards read again as the answers change them; a dry run asks nothing and writes nothing.

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import gzip
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "deployment" / "server", ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import ask_itself  # noqa: E402
import itself_service  # noqa: E402
from picwise_ai import itself, itself_asking  # noqa: E402
from picwise_ai.client import Asked, Budget  # noqa: E402
from picwise_nlu.concept_understanding import UNCERTAIN_MARKER  # noqa: E402
from picwise_providers import ai_shelves, kind_itself  # noqa: E402
from picwise_providers.kind_itself import Reading, Record  # noqa: E402
from picwise_providers.search_selection import _product_search_fields, kinds_read  # noqa: E402
from test_picwise_kind_itself import _product  # noqa: E402

HAIKU, SONNET = itself.MODEL, itself.SECOND_MODEL
DRILL_V = itself.kind_version("drill")
TODAY = "2026-11-24"


def _item(key: str, title: str, kind: str = "drill", want: str = "first", why: str = "kind", **more) -> dict:
    return {"k": key, "kind": kind, "want": want, "why": why, "title": title, "brand": "Fixturon",
            "category": "Tools > Drills", "price": "9.00 GBP", "about": "", "shop": "Fictional Store One", "products": 1, **more}


class Model:
    """Models of the test's own: what each reads a product as, by words of its title; the
    requests kept, in order. A title with "Silent" gets no answer from the model named."""

    def __init__(self, reads: dict[str, dict[str, str]], cost: dict[str, float] | None = None, silent: str = "") -> None:
        self.reads = reads
        self.cost = cost or {HAIKU: 0.001, SONNET: 0.02}
        self.silent = silent
        self.requests: list[dict] = []

    def said(self, model: str, line: str) -> str:
        for word, answer in self.reads.get(model, {}).items():
            if word in line:
                return answer
        return "itself"

    def __call__(self, request: dict) -> Asked:
        self.requests.append(request)
        model = request["model"]
        lines = [line for line in request["messages"][0]["content"].splitlines() if line[:1].isdigit()]
        answers = [{"n": number, "is": self.said(model, line), "what": "a thing"}
                   for number, line in enumerate(lines, 1) if not (self.silent == model and "Silent" in line)]
        return Asked({"answers": answers}, "end_turn", model, 1000, 200, 0, 0, self.cost[model], 0.5, "")

    def calls(self, model: str) -> list[tuple[str, int]]:
        """The calls made of a model: each call's kind and how many products it held."""
        found = []
        for request in self.requests:
            if request["model"] == model:
                text = request["messages"][0]["content"]
                found.append((text.splitlines()[0], sum(1 for line in text.splitlines() if line[:1].isdigit())))
        return found


def _run(items, records, model, **options):
    options.setdefault("budget", Budget(5.0))
    options.setdefault("workers", 1)
    return itself_asking.run(items, records, ask_fn=model, today=TODAY, **options)


class TheTwoReadings(unittest.TestCase):
    def test_a_question_never_asked_gets_its_first_reading(self) -> None:
        records: dict = {}
        model = Model({})
        totals = _run([_item("k1", "Cordless Drill A"), _item("k2", "Cordless Drill B")], records, model)
        self.assertEqual({key: (record.version, record.first.said, record.first.by, record.first.at, record.second)
                          for key, record in records.items()},
                         {("k1", "drill"): (DRILL_V, "itself", HAIKU, TODAY, None),
                          ("k2", "drill"): (DRILL_V, "itself", HAIKU, TODAY, None)})
        self.assertEqual((totals.asked["first"], totals.answered["first"], totals.asked["second"]), (2, 2, 0))
        self.assertEqual(model.calls(SONNET), [])

    def test_the_request_is_the_questions_own(self) -> None:
        model = Model({HAIKU: {"Pilot": "accessory"}})
        _run([_item("k1", "Pilot Drill for hole saws")], {}, model)
        first, second = model.requests
        self.assertEqual((first["model"], first["output_config"]["effort"]), (HAIKU, itself.EFFORT))
        self.assertEqual((second["model"], second["output_config"]["effort"]), (SONNET, itself.SECOND_EFFORT))
        for request in (first, second):
            self.assertEqual(request["system"][0]["text"], itself.SYSTEM_PROMPT)
            self.assertEqual(request["messages"][0]["content"], itself.user_message("drill", [_item("k1", "Pilot Drill for hole saws")]))

    def test_what_the_first_reading_would_take_out_is_read_again_in_the_same_run(self) -> None:
        records: dict = {}
        model = Model({HAIKU: {"Pilot": "accessory", "Odd": "unsure"}, SONNET: {"Pilot": "part", "Odd": "itself"}})
        totals = _run([_item("k1", "Cordless Drill A"), _item("k2", "Pilot Drill for hole saws"), _item("k3", "Odd Drill")],
                      records, model)
        self.assertIsNone(records[("k1", "drill")].second)
        pilot = records[("k2", "drill")]
        self.assertEqual((pilot.first.said, pilot.first.by, pilot.second.said, pilot.second.by, pilot.second.at),
                         ("accessory", HAIKU, "part", SONNET, TODAY))
        # What the first could not tell is read again too.
        self.assertEqual((records[("k3", "drill")].first.said, records[("k3", "drill")].second.said), ("unsure", "itself"))
        self.assertEqual(model.calls(SONNET), [("Kind: drill", 2)])
        self.assertEqual((totals.asked["second"], totals.answered["second"], dict(totals.said["second"])),
                         (2, 2, {"part": 1, "itself": 1}))

    def test_a_kind_the_lists_took_is_read_again_only_when_the_first_says_itself(self) -> None:
        records: dict = {}
        model = Model({HAIKU: {"House": "other"}, SONNET: {"Trampoline": "itself"}})
        _run([_item("k1", "Garden Trampoline", "toy", why="taken"), _item("k2", "Tortoise House", "toy", why="taken")],
             records, model)
        self.assertEqual(records[("k1", "toy")].second.said, "itself")
        self.assertEqual((records[("k2", "toy")].first.said, records[("k2", "toy")].second), ("other", None))
        self.assertEqual(model.calls(SONNET), [("Kind: toy", 1)])

    def test_a_first_card_is_read_a_second_time(self) -> None:
        # Named for its second reading by the preparation: the first reading is kept.
        records = {("k1", "drill"): Record("k1", "drill", DRILL_V, Reading("itself", "drill", HAIKU, "2026-11-23"))}
        model = Model({SONNET: {"Pilot": "accessory"}})
        totals = _run([_item("k1", "Pilot Drill for hole saws", want="second", why="first card"),
                       _item("k2", "Cordless Drill B", why="first card")], records, model)
        self.assertEqual(model.calls(HAIKU), [("Kind: drill", 1)])
        self.assertEqual(model.calls(SONNET), [("Kind: drill", 2)])
        first = records[("k1", "drill")]
        self.assertEqual((first.first.at, first.second.said), ("2026-11-23", "accessory"))
        self.assertEqual((records[("k2", "drill")].first.said, records[("k2", "drill")].second.said), ("itself", "itself"))
        self.assertEqual(totals.nothing_to_ask, 0)

    def test_a_question_with_both_readings_or_of_no_kind_is_not_asked(self) -> None:
        whole = Record("k1", "drill", DRILL_V, Reading("itself"), Reading("itself"))
        records = {("k1", "drill"): whole}
        model = Model({})
        totals = _run([_item("k1", "Cordless Drill A"), _item("k9", "A Thing", "no_such_kind"), _item("k1", "Cordless Drill A")],
                      records, model)
        self.assertEqual((totals.nothing_to_ask, model.requests), (3, []))
        self.assertIs(records[("k1", "drill")], whole)
        self.assertNotIn(("k9", "no_such_kind"), records)


class TheCalls(unittest.TestCase):
    def test_a_call_holds_one_kind_and_each_kinds_first_call_goes_first(self) -> None:
        items = [_item(f"d{n}", f"Cordless Drill {n}") for n in range(45)]
        items += [_item(f"p{n}", f"Inkjet Printer {n}", "printer") for n in range(3)]
        model = Model({})
        _run(items, {}, model)
        self.assertEqual(model.calls(HAIKU), [("Kind: drill", 40), ("Kind: printer", 3), ("Kind: drill", 5)])

    def test_the_calls_in_turn(self) -> None:
        calls = [("a", [1]), ("a", [2]), ("b", [3]), ("a", [4]), ("c", [5]), ("c", [6])]
        self.assertEqual(itself_asking.in_turn(calls),
                         [("a", [1]), ("b", [3]), ("c", [5]), ("a", [2]), ("c", [6]), ("a", [4])])

    def test_it_stops_before_its_budget(self) -> None:
        items = [_item(f"d{n}", f"Pilot Drill {n}") for n in range(120)]
        records: dict = {}
        model = Model({HAIKU: {"Pilot": "accessory"}}, cost={HAIKU: 0.01, SONNET: 0.05})
        budget = Budget(0.10)
        totals = _run(items, records, model, budget=budget)
        # Three first calls at a cent each; the second reading's first guess is six cents:
        # one call of five, and the next would pass the ten.
        self.assertEqual((totals.calls["first"], totals.calls["second"]), (3, 1))
        self.assertEqual(totals.stopped, "its limit of $0.10")
        self.assertLessEqual(budget.spent, 0.10)
        self.assertEqual((totals.asked["second"], totals.not_asked["second"]), (40, 80))
        self.assertEqual(sum(1 for record in records.values() if record.second is not None), 40)
        self.assertEqual(totals.left(), 80)
        self.assertEqual(totals.note()["stopped"], "its limit of $0.10")

    def test_it_stops_at_its_deadline(self) -> None:
        ticks = iter([0.0, 50.0, 200.0, 200.0, 200.0])
        items = [_item(f"d{n}", f"Cordless Drill {n}") for n in range(100)]
        records: dict = {}
        totals = _run(items, records, Model({}), deadline=100.0, clock=lambda: next(ticks))
        self.assertEqual((totals.calls["first"], totals.stopped), (2, "its time"))
        self.assertEqual((len(records), totals.not_asked["first"]), (80, 20))

    def test_the_answers_are_saved_along_the_way_and_at_the_end(self) -> None:
        saved = []
        items = [_item(f"d{n}", f"Cordless Drill {n}") for n in range(100)]
        records: dict = {}
        _run(items, records, Model({}), save=lambda: saved.append(len(records)), save_every=2)
        self.assertEqual(saved, [80, 100])

    def test_a_call_that_fails_is_a_call_with_no_answer(self) -> None:
        def broken(request: dict) -> Asked:
            return Asked(None, "", "", 0, 0, 0, 0, 0.0, 1.0, "APITimeoutError")

        records: dict = {}
        totals = _run([_item("k1", "Cordless Drill A")], records, broken)
        self.assertEqual((totals.failed_calls["first"], totals.answered["first"], dict(totals.errors)), (1, 0, {"APITimeoutError": 1}))
        self.assertEqual((records[("k1", "drill")].first, records[("k1", "drill")].tries), (None, 1))

        def raising(request: dict) -> Asked:
            raise RuntimeError("no network")

        totals = _run([_item("k2", "Cordless Drill B")], records, raising)
        self.assertEqual(dict(totals.errors), {"RuntimeError": 1})


class NoAnswer(unittest.TestCase):
    def test_a_first_reading_with_no_answer_is_asked_once_more_and_then_left(self) -> None:
        records: dict = {}
        items = [_item("k1", "Silent Drill"), _item("k2", "Cordless Drill B")]
        model = Model({}, silent=HAIKU)
        _run(items, records, model)
        silent = records[("k1", "drill")]
        self.assertEqual((silent.first, silent.tries, silent.tried), (None, 1, DRILL_V))
        self.assertEqual(records[("k2", "drill")].first.said, "itself")
        _run(items, records, model)
        self.assertEqual(records[("k1", "drill")].tries, kind_itself.MOST_TRIES)
        before = len(model.requests)
        totals = _run(items, records, model)
        self.assertEqual((len(model.requests), totals.nothing_to_ask), (before, 2))

    def test_a_second_reading_with_no_answer_is_counted_on_the_record(self) -> None:
        records: dict = {}
        model = Model({HAIKU: {"Silent": "accessory"}}, silent=SONNET)
        _run([_item("k1", "Silent Pilot Drill")], records, model)
        record = records[("k1", "drill")]
        self.assertEqual((record.first.said, record.second, record.tries, record.tried), ("accessory", None, 1, DRILL_V))
        # The preparation names it for its second reading; it answers this time.
        answering = Model({SONNET: {"Silent": "part"}})
        _run([_item("k1", "Silent Pilot Drill", want="second")], records, answering)
        record = records[("k1", "drill")]
        self.assertEqual((record.second.said, record.tries, record.tried), ("part", 0, ""))
        self.assertEqual(answering.calls(HAIKU), [])


class AskedAgain(unittest.TestCase):
    """An answer asked under other words of its kind (the rules' 4.7)."""

    def _old(self) -> dict:
        return {("k1", "drill"): Record("k1", "drill", "1.old", Reading("accessory", "arbor", HAIKU, "2026-11-01"),
                                        Reading("accessory", "arbor", SONNET, "2026-11-01"))}

    def test_the_new_answer_takes_its_place_when_whole(self) -> None:
        records = self._old()
        # Haiku now reads it as the kind; the old answer had a second reading, so it is read again.
        model = Model({SONNET: {"Pilot": "part"}})
        totals = _run([_item("k1", "Pilot Drill for hole saws", again=True)], records, model)
        record = records[("k1", "drill")]
        self.assertEqual((record.version, record.first.said, record.first.at, record.second.said, record.second.at),
                         (DRILL_V, "itself", TODAY, "part", TODAY))
        self.assertEqual((totals.replaced, len(model.requests)), (1, 2))

    def test_it_stands_while_the_second_reading_has_not_come(self) -> None:
        records = self._old()
        _run([_item("k1", "Silent Pilot Drill", again=True)], records, Model({}, silent=SONNET))
        record = records[("k1", "drill")]
        self.assertEqual((record.version, record.first.said, record.second.said, record.tries, record.tried),
                         ("1.old", "accessory", "accessory", 1, DRILL_V))
        # The budget ends before the second reading: nothing is counted against it.
        records = self._old()
        totals = _run([_item("k1", "Pilot Drill", again=True)], records, Model({}), budget=Budget(0.005))
        record = records[("k1", "drill")]
        self.assertEqual((record.version, record.second.said, record.tries, totals.replaced), ("1.old", "accessory", 0, 0))
        self.assertEqual(totals.not_asked["second"], 1)

    def test_an_old_answer_with_no_second_reading_is_replaced_by_the_first(self) -> None:
        records = {("k1", "drill"): Record("k1", "drill", "1.old", Reading("itself", "drill", HAIKU, "2026-11-01"))}
        model = Model({})
        totals = _run([_item("k1", "Cordless Drill A", again=True)], records, model)
        record = records[("k1", "drill")]
        self.assertEqual((record.version, record.first.at, record.second, totals.replaced), (DRILL_V, TODAY, None, 1))
        self.assertEqual(model.calls(SONNET), [])

    def test_asked_again_in_vain_twice_it_is_left_with_its_answer(self) -> None:
        records = self._old()
        model = Model({}, silent=HAIKU)
        for _night in range(3):
            _run([_item("k1", "Silent Pilot Drill", again=True)], records, model)
        record = records[("k1", "drill")]
        self.assertEqual((record.version, record.second.said, record.tries, len(model.requests)), ("1.old", "accessory", 2, 2))


class TheNote(unittest.TestCase):
    def test_counts_and_the_cost_only(self) -> None:
        records: dict = {}
        model = Model({HAIKU: {"Pilot": "accessory"}})
        totals = _run([_item("key-one", "Cordless Drill A"), _item("key-two", "Pilot Drill for hole saws")], records, model)
        note = totals.note()
        self.assertEqual((note["questions"], note["first"]["asked"], note["first"]["answered"], note["second"]["answered"]),
                         (2, 2, 2, 1))
        self.assertEqual((note["first"]["said"], note["second"]["said"]), ({"accessory": 1, "itself": 1}, {"itself": 1}))
        self.assertEqual((note["cost_usd"], note["left"], note["stopped"]), (0.021, 0, ""))
        text = json.dumps(note) + " ".join(itself_asking.report(totals))
        for word in ("key-one", "Cordless", "Fixturon", "Fictional"):
            self.assertNotIn(word, text)
        self.assertIn("$0.0210", itself_asking.report(totals)[-1])


class TheMorningsService(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.directory = Path(self.folder.name)
        (self.directory / "jobs").mkdir()
        self.items = [_item("k1", "Cordless Drill A"), _item("k2", "Pilot Drill for hole saws")]

    def _run(self, model, **options) -> dict:
        with redirect_stdout(io.StringIO()) as said:
            note = itself_service.run(self.directory, ask_fn=model, today=TODAY, workers=1, **options)
        self.said = said.getvalue()
        return note

    def test_the_questions_named_are_asked_and_kept_for_the_preparation(self) -> None:
        self.assertEqual(kind_itself.write_job(self.items, self.directory / "jobs"),
                         {"questions": 2, "first": 2, "second": 0, "again": 0})
        note = self._run(Model({HAIKU: {"Pilot": "accessory"}, SONNET: {"Pilot": "accessory"}}))
        records = kind_itself.read_answers(self.directory / itself_service.ANSWERS_NAME)
        self.assertEqual({key: (record.first.said, record.second.said if record.second else None) for key, record in records.items()},
                         {("k1", "drill"): ("itself", None), ("k2", "drill"): ("accessory", "accessory")})
        self.assertEqual((note["night"], note["named"], note["left"], note["cost_usd"], note["questions_kept"]),
                         (TODAY, 2, 0, 0.021, 2))
        self.assertEqual(json.loads((self.directory / itself_service.NOTE_NAME).read_text(encoding="utf-8")), note)
        # Everything named was asked: the job is done with.
        self.assertFalse((self.directory / "jobs" / itself_service.JOB_NAME).exists())
        for word in ("k1", "Cordless", "Fixturon"):
            self.assertNotIn(word, json.dumps(note) + self.said)
        # The preparation reads the file: the pilot drill is no drill.
        night = kind_itself.Night(records=records, today=TODAY)
        drill = frozenset({"drill"})
        self.assertEqual(night.settle(0, drill, drill, "k2"), frozenset({UNCERTAIN_MARKER}))

    def test_the_answers_kept_before_stay(self) -> None:
        kept = {("k0", "printer"): Record("k0", "printer", "1.x", Reading("itself"), Reading("other"))}
        kind_itself.write_answers(self.directory / itself_service.ANSWERS_NAME, kept)
        kind_itself.write_job(self.items, self.directory / "jobs")
        note = self._run(Model({}))
        records = kind_itself.read_answers(self.directory / itself_service.ANSWERS_NAME)
        self.assertEqual(records[("k0", "printer")], kept[("k0", "printer")])
        self.assertEqual((len(records), note["questions_kept_before"], note["questions_kept"]), (3, 1, 3))

    def test_a_run_stopped_by_its_brake_keeps_the_job(self) -> None:
        kind_itself.write_job([_item(f"d{n}", f"Pilot Drill {n}") for n in range(90)], self.directory / "jobs")
        note = self._run(Model({HAIKU: {"Pilot": "accessory"}}, cost={HAIKU: 0.01, SONNET: 0.05}), budget=0.05)
        self.assertEqual(note["stopped"], "its limit of $0.05")
        self.assertGreater(note["left"], 0)
        self.assertTrue((self.directory / "jobs" / itself_service.JOB_NAME).exists())
        self.assertIn("stopped at its limit", self.said)

    def test_an_answers_file_that_cannot_be_read_is_never_written_over(self) -> None:
        answers = self.directory / itself_service.ANSWERS_NAME
        answers.write_bytes(b"not a gzip file")
        kind_itself.write_job(self.items, self.directory / "jobs")
        model = Model({})
        note = self._run(model)
        self.assertEqual((note["stopped"], model.requests), ("the answers file cannot be read: nothing asked", []))
        self.assertEqual(answers.read_bytes(), b"not a gzip file")

    def test_no_job_is_no_asking(self) -> None:
        model = Model({})
        note = self._run(model)
        self.assertEqual((note["named"], note["left"], note["cost_usd"], model.requests), (0, 0, 0.0, []))

    def test_a_line_that_is_no_question_is_passed_over(self) -> None:
        job = self.directory / "jobs" / itself_service.JOB_NAME
        with gzip.open(job, "wt", encoding="utf-8") as handle:
            handle.write("not json\n[1]\n" + json.dumps({"k": 5, "kind": "drill"}) + "\n" + json.dumps(self.items[0]) + "\n")
        self.assertEqual([item["k"] for item in itself_service.read_job(job)], ["k1"])
        self.assertEqual(itself_service.read_job(self.directory / "none.gz"), [])

    def test_without_the_key_nothing_is_asked(self) -> None:
        kind_itself.write_job(self.items, self.directory / "jobs")
        with mock.patch.dict(os.environ, {}, clear=False), redirect_stdout(io.StringIO()) as said:
            os.environ.pop("ANTHROPIC_API_KEY", None)
            self.assertEqual(itself_service.main(["--dir", str(self.directory)]), 0)
        self.assertIn("no key", said.getvalue())
        self.assertFalse((self.directory / itself_service.ANSWERS_NAME).exists())

    def test_the_limits_are_the_rules(self) -> None:
        self.assertEqual((itself_service.BUDGET_USD, itself_service.STOP_AFTER_SECONDS), (5.0, 7200.0))
        self.assertEqual(itself_service.JOB_NAME, kind_itself.JOBS_NAME)

    def test_the_unit_runs_as_the_ai_layer_with_its_key_after_the_preparation(self) -> None:
        server = ROOT / "deployment" / "server"
        unit = (server / "picwise-itself.service").read_text(encoding="utf-8")
        self.assertIn("User=picwise-assist", unit)
        self.assertIn("EnvironmentFile=-/etc/picwise/assist.env", unit)
        self.assertIn("After=network-online.target picwise-prepare.service picwise-shelves.service", unit)
        self.assertIn("ReadWritePaths=/srv/picwise/assist/itself", unit)
        self.assertIn("/srv/picwise/venv-ai/bin/python", unit)
        self.assertIn('itself_service.py" --dir /srv/picwise/assist/itself', unit)
        timer = (server / "picwise-itself.timer").read_text(encoding="utf-8")
        self.assertIn("OnCalendar=*-*-* 05:40:00 UTC", timer)
        prepare = (server / "picwise-prepare.service").read_text(encoding="utf-8")
        self.assertIn(f"Environment={kind_itself.ANSWERS_FILE_ENV}=/srv/picwise/assist/itself/answers.jsonl.gz", prepare)
        self.assertIn(f"Environment={kind_itself.JOBS_ENV}=/srv/picwise/assist/itself/jobs", prepare)
        self.assertIn("ReadWritePaths=-/srv/picwise/assist/itself/jobs", prepare)
        deploy = (server / "deploy.sh").read_text(encoding="utf-8")
        self.assertIn('install -d -o picwise-assist -g picwise-assist -m 2750 "$ASSIST/itself"', deploy)
        self.assertIn('install -d -o picwise -g picwise-assist -m 2770 "$ASSIST/itself/jobs"', deploy)
        self.assertIn("systemctl enable --now picwise-itself.timer", deploy)
        # Put in place with the rest, and put back with the rest when a release is refused.
        self.assertEqual(deploy.count("picwise-itself.service picwise-itself.timer"), 2)
        # Without the key: no questions written, no timer.
        self.assertIn('"${ASSIST:?}/itself/jobs"', deploy)
        self.assertIn("picwise-shelves.timer \\\n    picwise-itself.timer", deploy)


class TheFirstAsking(unittest.TestCase):
    """The nights lived one after another (`ask_itself.rounds`)."""

    def setUp(self) -> None:
        self.addCleanup(kind_itself.reset_for_tests)
        self.addCleanup(ai_shelves.reset)
        # Seven drills from 60 to 66; three "pilot drills" at 3, 4 and 5, read as drills.
        self.products = [_product(n, f"Fixturon Cordless Drill Model{chr(65 + n)} 18V", 60.0 + n) for n in range(7)]
        self.products += [_product(7 + n, f"Fixturon Pilot Drill Type{chr(65 + n)} for hole saws", 3.0 + n) for n in range(3)]
        found = [kinds_read(product, _product_search_fields(product)) for product in self.products]
        self.read = found.__getitem__
        self.keys = [key for _before, _after, key in found]

    def _rounds(self, model, records=None, **options):
        records = {} if records is None else records
        said: list[str] = []
        options.setdefault("budget", Budget(5.0))
        done, night = ask_itself.rounds(self.products, self.read, records, ask_fn=model, today=TODAY, workers=1,
                                        say=said.append, **options)
        return records, done, night, said

    def test_every_question_is_asked_and_the_first_cards_are_read_twice(self) -> None:
        # Haiku misses one pilot drill; Sonnet, reading the first cards, does not.
        model = Model({HAIKU: {"TypeA": "accessory", "TypeB": "accessory"}, SONNET: {"Pilot": "accessory"}})
        with mock.patch.object(kind_itself, "FRONT", 4):
            records, done, night, said = self._rounds(model)
        self.assertEqual(len(records), 10)
        out = {key for (key, _kind), record in records.items() if record.second and record.second.said == "accessory"}
        self.assertEqual(out, set(self.keys[7:]))
        # Round 1: every question's first reading; the kind's four cheapest, its first
        # cards as the lists read them, read a second time the same morning: the pilot
        # drill Haiku missed among them. Round 2: the three drills that took the pilot
        # drills' places among the first cards; round 3 names nothing.
        self.assertEqual([(totals.asked["first"], totals.asked["second"]) for totals in done], [(10, 4), (0, 3)])
        self.assertIn("round 3: 0 questions", said[-1])
        note = night.note()
        self.assertEqual((note["left_a_kind"], note["left_by_answer"], note["products_with_a_question_waiting"]),
                         (3, {"accessory": 3}, 0))
        self.assertEqual(ask_itself.effect(night)[1], "would leave a kind: 3 products (accessory 3); would come back: 0")

    def test_what_is_kept_is_not_asked_again(self) -> None:
        model = Model({HAIKU: {"Pilot": "accessory"}, SONNET: {"Pilot": "accessory"}})
        with mock.patch.object(kind_itself, "FRONT", 4):
            records, _done, _night, _said = self._rounds(model)
            asked = len(model.requests)
            _records, done, _night, said = self._rounds(model, records)
        self.assertEqual((len(model.requests), done), (asked, []))
        self.assertIn("round 1: 0 questions", said[0])

    def test_a_dry_run_names_the_first_round_and_asks_nothing(self) -> None:
        records, done, _night, said = self._rounds(None)
        self.assertEqual((records, done), ({}, []))
        self.assertIn("round 1: 10 questions in 1 kinds: 10 for a first reading, 0 for a second", said[0])
        # Ten first readings; the ten are first cards, so ten second readings too.
        self.assertEqual(said[1], "by the trials of 22/11: the first readings about $0.00; the second, 10 to 10, $0.01 to $0.01;"
                                  " in all $0.01 to $0.01, before the rounds after it (the first cards that take the place of"
                                  " those that leave)")
        self.assertEqual(said[2], "the questions by shop, 1 shops: Fictional Store One 10")
        # The ten products are one kind's first cards, all of them.
        self.assertIn("10 cards in 1 kinds, 10 questions", said[3])

    def test_it_stops_with_its_budget(self) -> None:
        model = Model({HAIKU: {"Pilot": "accessory"}}, cost={HAIKU: 0.01, SONNET: 0.05})
        records, done, _night, _said = self._rounds(model, budget=Budget(0.03))
        self.assertEqual((len(done), done[0].stopped), (1, "its limit of $0.03"))
        self.assertEqual(sum(1 for record in records.values() if record.second), 0)

    def test_the_rounds_end(self) -> None:
        model = Model({HAIKU: {"Pilot": "accessory"}, SONNET: {"Pilot": "accessory"}})
        with mock.patch.object(kind_itself, "FRONT", 4):
            _records, done, _night, _said = self._rounds(model, most=1)
        self.assertEqual(len(done), 1)

    def test_the_tool_on_a_catalogue_copy_dry(self) -> None:
        from picwise_providers import state
        from test_picwise_look_itself import _write

        with tempfile.TemporaryDirectory() as folder:
            catalogue = Path(folder) / "catalogue.json.gz"
            out = Path(folder) / "answers.jsonl.gz"
            _write(catalogue)
            try:
                with mock.patch.dict(os.environ, {}, clear=False), redirect_stdout(io.StringIO()) as said:
                    os.environ.pop("ANTHROPIC_API_KEY", None)
                    os.environ.pop("GITHUB_ACTIONS", None)
                    self.assertEqual(ask_itself.main([str(catalogue), "--out", str(out), "--dry-run"]), 0)
            finally:
                state._PREPARED_STATE.clear()
                state.remember_product_kinds({})
            text = said.getvalue()
            self.assertIn("the AI: not asked", text)
            self.assertIn("round 1:", text)
            self.assertIn("0 rounds; 0 readings kept; $0.0000 of $20.00", text)
            self.assertFalse(out.exists())
            # Answers kept that cannot be read: nothing is asked or written.
            broken = Path(folder) / "kept.jsonl.gz"
            broken.write_bytes(b"not gzip")
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(ask_itself.main([str(catalogue), "--out", str(out), "--answers", str(broken), "--dry-run"]), 1)
            finally:
                state._PREPARED_STATE.clear()
                state.remember_product_kinds({})


class TheDryRunsGuess(unittest.TestCase):
    def test_the_first_rounds_cost_by_the_trials_shares(self) -> None:
        # The dry run of 22/11 on the server's catalogue (run 45031171329): 73,290 questions.
        items = ([_item("k", "x")] * 62298 + [_item("k", "x", why="taken")] * 3904 + [_item("k", "x", why="first card")] * 7088)
        self.assertEqual(
            ask_itself.estimate(items),
            "by the trials of 22/11: the first readings about $2.71; the second, 13,864 to 17,602, $8.04 to $10.21;"
            " in all $10.75 to $12.92, before the rounds after it (the first cards that take the place of those that leave)")
        # A question named for its second reading is counted whole.
        self.assertIn("the second, 2 to 2,", ask_itself.estimate([_item("k", "x", want="second")] * 2))


class TheFirstAskingsWorkflow(unittest.TestCase):
    workflow = (ROOT / ".github" / "workflows" / "ai-itself-ask.yml").read_text(encoding="utf-8")

    def test_it_asks_nothing_until_it_is_turned_and_puts_the_answers_where_the_preparation_reads(self) -> None:
        self.assertIn("branches: [claude/itself-ask]", self.workflow)
        # Dry by default: turned only on the owner's word for the cost.
        self.assertIn("DRY_RUN: 'yes'", self.workflow)
        self.assertIn('if [ "$DRY_RUN" != "no" ]; then dry="--dry-run"; fi', self.workflow)
        self.assertIn("env.DRY_RUN == 'no'", self.workflow)
        self.assertIn("BUDGET: '20'", self.workflow)
        self.assertEqual(self.workflow.count("secrets.ANTHROPIC_API_KEY"), 1)
        self.assertNotIn("upload-artifact", self.workflow)
        # The folder as the deployment makes it; the answers before kept, the copy checked.
        deploy = (ROOT / "deployment" / "server" / "deploy.sh").read_text(encoding="utf-8")
        self.assertIn('install -d -o picwise-assist -g picwise-assist -m 2750 "$ASSIST/itself"', deploy)
        self.assertIn("sudo install -d -o picwise-assist -g picwise-assist -m 2750 $folder", self.workflow)
        self.assertIn("folder=/srv/picwise/assist/itself", self.workflow)
        self.assertLess(self.workflow.index("answers.before.jsonl.gz"), self.workflow.index("sudo mv -f"))
        self.assertLess(self.workflow.index("the copy on the server differs"), self.workflow.index("sudo mv -f"))
        self.assertIn('rm -rf ~/.ssh/deploy_key ~/.ssh/config "$RUNNER_TEMP/site"', self.workflow)
        prepare = (ROOT / "deployment" / "server" / "picwise-prepare.service").read_text(encoding="utf-8")
        self.assertIn("=/srv/picwise/assist/itself/answers.jsonl.gz", prepare)


if __name__ == "__main__":
    unittest.main()
