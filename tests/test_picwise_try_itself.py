"""Task 6's trial (`deployment/server/try_itself.py`): the question "is it the kind itself"
asked of several models about the same products, before its rules are written.

Pinned here, on a prepared catalogue of the test's own and models of the test's own (no call
leaves the test): the questions are the first cards of the searches, each for the kind its
search is read as, each product as the model reads it and never a link; each model is asked
every question, a kind's products together; the calls stop before the budget, the calls
still out counted; what two models read differently is said by title; a dry run asks
nothing.

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "deployment" / "server", ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import look_itself  # noqa: E402
import try_itself  # noqa: E402
from picwise_ai.client import Asked  # noqa: E402
from test_picwise_look_itself import _write  # noqa: E402


def _model(reads_pilot_drills_as: str, cost: float = 0.01):
    """A model of the test's own: a pilot drill is what it is told, everything else the kind
    itself; each call costs the same."""

    def ask(request: dict) -> Asked:
        lines = [line for line in request["messages"][0]["content"].splitlines() if line[:1].isdigit()]
        answers = [
            {"n": number, "is": reads_pilot_drills_as if "Pilot" in line else "itself",
             "what": "pilot drill" if "Pilot" in line else "the thing"}
            for number, line in enumerate(lines, 1)
        ]
        return Asked({"answers": answers}, "end_turn", request["model"], 1000, 200, 0, 0, cost, 0.5, "")

    return ask


class TrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.folder = tempfile.TemporaryDirectory()
        cls.catalogue = Path(cls.folder.name) / "catalogue.json.gz"
        _write(cls.catalogue)
        cls.prepared = look_itself._load(cls.catalogue, gone="", offers="", families="")
        cls.index = {str(product.provider_product_id): place for place, product in enumerate(cls.prepared.products)}
        cls.questions = try_itself.card_questions(cls.prepared, cls.index, 12)

    @classmethod
    def tearDownClass(cls) -> None:
        from picwise_providers import state

        state._PREPARED_STATE.clear()
        state.remember_product_kinds({})
        cls.folder.cleanup()

    def test_the_questions_are_the_searches_first_cards_for_their_kind(self) -> None:
        by_search = {}
        for question in self.questions:
            by_search.setdefault((question.source, question.kind), []).append(question)
        self.assertEqual({key: len(found) for key, found in by_search.items()},
                         {("kettle", "kettle"): 12, ("laptop", "laptop"): 8, ("drill", "drill"): 12})
        drill = by_search[("drill", "drill")]
        self.assertEqual(sum("Pilot Drill" in question.item["title"] for question in drill), 4)
        item = drill[1].item
        self.assertEqual(sorted(item), ["about", "brand", "category", "price", "title"])
        self.assertEqual(item["price"], "3.00 GBP")
        self.assertNotIn("http", " ".join(item.values()))
        self.assertEqual(drill[1].shop, "Fictional Store One")

    def test_the_cards_after_the_first_are_products_a_trial_has_not_read(self) -> None:
        later = try_itself.card_questions(self.prepared, self.index, 12, skip=8)
        by_search = {}
        for question in later:
            by_search.setdefault(question.source, []).append(question.place)
        # The laptops' search has eight cards in all: none after the first eight.
        self.assertEqual({source: len(places) for source, places in by_search.items()}, {"kettle": 4, "drill": 4})
        first = {question.place for question in try_itself.card_questions(self.prepared, self.index, 8)}
        self.assertFalse(first & {question.place for question in later})

    def test_nothing_was_taken_out_of_a_kind_without_the_ais_lines(self) -> None:
        self.assertEqual(try_itself.taken_questions(self.prepared, 20, 8), [])

    def test_a_model_is_asked_every_question_a_kinds_products_together(self) -> None:
        seen = []

        def ask(request: dict) -> Asked:
            seen.append(request)
            return _model("accessory")(request)

        asked = try_itself.ask_model("claude-haiku-5-5", self.questions, ask, try_itself.Budget(1.0), workers=1)
        self.assertEqual(len(asked.answers), len(self.questions))
        # A call a kind: the kettles, the laptops, the drills.
        self.assertEqual(asked.calls, 3)
        self.assertEqual({request["model"] for request in seen}, {"claude-haiku-5-5"})
        self.assertEqual(sorted(request["messages"][0]["content"].splitlines()[0] for request in seen),
                         ["Kind: drill", "Kind: kettle", "Kind: laptop"])
        sides = [asked.answers[number][0] for number, question in enumerate(self.questions)
                 if "Pilot Drill" in question.item["title"]]
        self.assertEqual(sides, ["accessory"] * 4)
        self.assertAlmostEqual(asked.cost, 0.03)
        line = try_itself.report_model(asked, self.questions)[0]
        self.assertIn("32 of 32 questions answered in 3 calls", line)
        self.assertIn("$0.938 a thousand questions", line)

    def test_the_calls_stop_before_the_budget(self) -> None:
        budget = try_itself.Budget(0.05)
        # A model whose call is guessed at $0.06 before any has come back is not asked at all.
        asked = try_itself.ask_model("claude-sonnet-5-5", self.questions, _model("part"), budget, workers=1)
        self.assertEqual((asked.calls, asked.not_asked, budget.spent), (0, len(self.questions), 0.0))
        # The calls still out count: two guessed at $0.03 each do not both fit beside $0.01 spent.
        budget = try_itself.Budget(0.05)
        budget.settle(0.0, 0.01)
        self.assertTrue(budget.reserve(0.03))
        self.assertFalse(budget.reserve(0.03))
        budget.settle(0.03, 0.02)
        self.assertAlmostEqual(budget.spent, 0.03)
        self.assertFalse(budget.reserve(0.03))
        self.assertTrue(budget.reserve(0.02))

    def test_what_two_models_read_differently_is_said_by_title(self) -> None:
        first = try_itself.ask_model("claude-haiku-5-5", self.questions, _model("itself"), try_itself.Budget(1.0), workers=1)
        second = try_itself.ask_model("claude-opus-5-5", self.questions, _model("accessory"), try_itself.Budget(1.0), workers=1)
        lines = try_itself.report_agreement(first, second, self.questions)
        self.assertIn("both answered 32; the same side 28 of 32 (87.5%)", lines[0])
        self.assertIn("itself / not: 4", lines[1])
        differing = lines[2:]
        self.assertEqual(len(differing), 4)
        self.assertTrue(all("Pilot Drill" in line and "itself (pilot drill) / accessory (pilot drill)" in line
                            for line in differing))
        self.assertTrue(all("row-" not in line and "http" not in line for line in lines))
        searches = try_itself.report_searches([first, second], self.questions)
        self.assertIn('  "drill" (drill): 12; 12, 8', searches)
        self.assertIn("in all: haiku itself 32 of 32 (100.0%), unsure 0; opus itself 28 of 32 (87.5%), unsure 0", searches)

    def test_the_two_readings_together(self) -> None:
        first = try_itself.ask_model("claude-haiku-5-5", self.questions, _model("itself", 0.001), try_itself.Budget(1.0), workers=1)
        second = try_itself.ask_model("claude-sonnet-5-5", self.questions, _model("part", 0.02), try_itself.Budget(1.0), workers=1)
        lines = try_itself.report_two_readings(first, second, self.questions)
        # Every question here is a first card: the second model reads them all again.
        self.assertEqual(lines[0], "no questions outside the first cards")
        self.assertIn("the first cards as the second reads them: itself 28, not 4", lines)
        self.assertIn("read twice in all: 32", lines)
        self.assertIn("$0.094 a thousand at the first reading and $1.875 at the second", lines[2])

    def test_a_dry_run_asks_nothing_and_ends_well(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            status = try_itself.main([str(self.catalogue), "--dry-run"])
        printed = out.getvalue()
        self.assertEqual(status, 0)
        self.assertIn("the AI: not asked (a dry run, or no key)", printed)
        self.assertIn("set A 32 questions", printed)
        self.assertIn("$0.0000 of $1.50 in all", printed)
        self.assertNotIn("http", printed)
        self.assertNotIn("row-", printed)


if __name__ == "__main__":
    unittest.main()
