"""The scan of the whole catalogue by the AI's shelves (`deployment/server/scan_shelves.py`;
owner, 2026-11-20: «Θέλω να σκαναριστεί σήμερα όλος ο κατάλογος»): one question a key, the
answers checked, kept and never asked again, the calls turned away asked again, and the
limits that stop it."""
from __future__ import annotations

import gzip
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import scan_shelves  # noqa: E402
from picwise_ai import shelves  # noqa: E402
from picwise_ai.client import Asked  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402

KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Electric Kettles"
CABLES = "Electronics > Electronics Accessories > Cables"
BANDS = "Apparel & Accessories > Jewelry > Watch Accessories > Watch Bands"
WATCHES = "Apparel & Accessories > Jewelry > Watches"
LINES = shelves.taxonomy_lines()
_ITEM_RE = re.compile(r"^(\d+)\. (.*?)(?: \| |$)")


def _number(line: str) -> int:
    return LINES.index(line) + 1


def _product(pid: str, title: str, raw: dict, *, brand: str = "Acme", category: str = "") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title,
        brand=brand,
        category_text=category,
        product_url="",
        image_url="",
        price_text="9.99",
        availability_text="in stock",
        currency="GBP",
        raw=raw,
    )


def _items(request: dict) -> list[tuple[int, str]]:
    found = []
    for line in request["messages"][0]["content"].splitlines()[1:]:
        match = _ITEM_RE.match(line)
        if match:
            found.append((int(match.group(1)), match.group(2)))
    return found


def _by_title(request: dict) -> tuple[Asked, str]:
    """A model that shelves by the title's words, and names no line for a gift card."""
    answers = []
    for number, title in _items(request):
        lowered = title.lower()
        if "lead" in lowered:
            answers.append({"n": number, "line": _number(CABLES), "name": "Cables"})
        elif "strap" in lowered:
            answers.append({"n": number, "line": _number(BANDS), "name": "Watch Bands"})
        elif "kettle" in lowered:
            answers.append({"n": number, "line": _number(KETTLES), "name": "Electric Kettles"})
        elif "watch" in lowered:
            answers.append({"n": number, "line": _number(WATCHES), "name": "Watches"})
        elif "gift card" in lowered:
            answers.append({"n": number, "line": 0, "name": "none"})
        else:
            answers.append({"n": number, "line": _number(KETTLES), "name": "Not A Line"})
    return Asked({"products": answers}, "end_turn", shelves.MODEL, 900, 300, 0, 40000, 0.004, 0.01, ""), ""


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def _asking(ask_fn, groups, answers, *, workers=2, budget=10.0, deadline=None, clock=None):
    clock = clock or _Clock()
    return scan_shelves.Asking(
        ask_fn=ask_fn,
        groups=groups,
        answers=answers,
        lines=LINES,
        workers=workers,
        budget=budget,
        deadline=clock.now + 10_000 if deadline is None else deadline,
        clock=clock,
        sleep=clock.sleep,
        today="2026-11-20",
    )


def _catalogue() -> list[ProviderProduct]:
    return [
        _product("1", "Acme Cotton Tee Black XL", {"advertiser_id": "7", "product_type": "Clothing > Tops"}),
        _product("2", "Acme Cotton Tee White S", {"advertiser_id": "7", "product_type": "Clothing > Tops"}),
        _product("3", "Acme Cotton Tee Red M", {"advertiser_id": "7", "product_type": "Clothing > Tops"}),
        _product(
            "4",
            "Russell Hobbs 1.7L Kettle",
            {"advertiser_id": "8", "product_type": "Kettles", "google_product_category": KETTLES},
        ),
        _product(
            "5",
            "IEC Kettle Lead 2m",
            {"merchant_id": "9", "aw_product_id": "5", "merchant_category": "Cables > Kettle Leads",
             "google_product_category": KETTLES},
        ),
        _product(
            "6",
            "Garmin Fenix 6 Strap 22 mm Beige",
            {"merchant_id": "10", "aw_product_id": "6", "merchant_category": "Smart Watches",
             "google_product_category": WATCHES},
        ),
        _product("7", "Acme Gift Card £20", {"advertiser_id": "11", "product_type": "Gifts"}),
    ]


class KeyTests(unittest.TestCase):
    def test_a_products_sizes_and_colours_are_one_question(self) -> None:
        groups = scan_shelves.groups_of(_catalogue(), LINES)
        self.assertEqual(len(groups), 5)
        tees = [group for group in groups.values() if "Tee" in group.title]
        self.assertEqual(len(tees), 1)
        self.assertEqual(tees[0].products, 3)

    def test_the_shops_own_words_are_read_never_the_google_line(self) -> None:
        self.assertEqual(
            shelves.shop_words({"merchant_category": "Cables > Kettle Leads", "category_name": "Cables > Kettle Leads",
                                "product_type": "Cables > Kettle Leads", "google_product_category": KETTLES}),
            "Cables > Kettle Leads",
        )
        self.assertEqual(shelves.shop_words({"product_type": " Kettles ", "google_product_category": KETTLES}), "Kettles")
        one = shelves.ask_key("Kettle Lead", "Acme", "Cables")
        self.assertEqual(one, shelves.ask_key("kettle  lead", "ACME", "cables"))
        self.assertNotEqual(one, shelves.ask_key("Kettle Lead", "Acme", "Kitchen"))

    def test_what_a_product_is_read_against(self) -> None:
        groups = {group.title: group for group in scan_shelves.groups_of(_catalogue(), LINES).values()}
        self.assertFalse(groups["Russell Hobbs 1.7L Kettle"].second)
        self.assertEqual(groups["Russell Hobbs 1.7L Kettle"].shelf_now, KETTLES)
        self.assertTrue(groups["IEC Kettle Lead 2m"].second)
        self.assertEqual(groups["IEC Kettle Lead 2m"].item["category"], "Cables > Kettle Leads")
        self.assertEqual(groups["Acme Gift Card £20"].shelf_now, "")


class ScanTests(unittest.TestCase):
    def test_each_key_is_asked_once_the_largest_first_and_kept(self) -> None:
        groups = scan_shelves.groups_of(_catalogue(), LINES)
        answers: dict = {}
        keys = scan_shelves.to_ask(groups, answers)
        self.assertEqual(groups[keys[0]].products, 3)
        asked = []

        def ask_fn(request):
            asked.extend(title for _number_, title in _items(request))
            return _by_title(request)

        asking = _asking(ask_fn, groups, answers)
        self.assertEqual(scan_shelves.scan(asking, keys, 50), [])
        lines = {groups[key].title: record["line"] for key, record in answers.items()}
        self.assertEqual(lines["IEC Kettle Lead 2m"], CABLES)
        self.assertEqual(lines["Garmin Fenix 6 Strap 22 mm Beige"], BANDS)
        self.assertEqual(lines["Russell Hobbs 1.7L Kettle"], KETTLES)
        self.assertEqual(lines["Acme Gift Card £20"], "")
        # The tees' answer names no line: refused twice, kept as null, never asked again.
        self.assertIsNone(lines["Acme Cotton Tee Black XL"])
        self.assertEqual(asked.count("Acme Cotton Tee Black XL"), 2)
        self.assertEqual(len(asked), 6)
        self.assertEqual(scan_shelves.to_ask(groups, answers), [])
        self.assertEqual(asking.totals.answered, 4)
        self.assertEqual(asking.totals.no_line, 1)

    def test_the_answers_file_keeps_them_and_passes_over_what_is_not_an_answer(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "answers.jsonl.gz"
            scan_shelves.write_answers(path, {"a": {"k": "a", "line": KETTLES, "tries": 1, "at": "2026-11-20"},
                                              "b": {"k": "b", "line": None, "tries": 1, "at": "2026-11-20"}})
            with gzip.open(path, "at", encoding="utf-8") as handle:
                handle.write("not json\n")
                handle.write('{"k": "c", "line": 7}\n')
            answers = scan_shelves.read_answers(path)
            self.assertEqual(sorted(answers), ["a", "b"])
            self.assertEqual(answers["a"]["line"], KETTLES)
            self.assertEqual(scan_shelves.read_answers(Path(folder) / "none.jsonl.gz"), {})

    def test_a_key_refused_once_before_is_asked_once_more_then_kept(self) -> None:
        groups = scan_shelves.groups_of(_catalogue()[:3], LINES)
        key = next(iter(groups))
        answers = {key: {"k": key, "line": None, "tries": 1, "at": "2026-11-19"}}
        self.assertEqual(scan_shelves.to_ask(groups, answers), [key])
        calls = []

        def ask_fn(request):
            calls.append(request)
            return _by_title(request)

        scan_shelves.scan(_asking(ask_fn, groups, answers), [key], 50)
        self.assertEqual(len(calls), 1)
        self.assertEqual(answers[key]["tries"], 2)
        self.assertEqual(scan_shelves.to_ask(groups, answers), [])

    def test_calls_turned_away_for_the_rate_are_asked_again_fewer_at_a_time(self) -> None:
        groups = scan_shelves.groups_of(_catalogue()[3:], LINES)
        turned = {"left": 2}

        def ask_fn(request):
            if turned["left"]:
                turned["left"] -= 1
                return Asked(None, "", "", 0, 0, 0, 0, 0.0, 0.01, "RateLimitError (HTTP 429)"), "rate limited"
            return _by_title(request)

        answers: dict = {}
        asking = _asking(ask_fn, groups, answers, workers=3)
        unasked = scan_shelves.scan(asking, scan_shelves.to_ask(groups, answers), 1)
        self.assertEqual(unasked, [])
        self.assertEqual(asking.totals.turned_away, 2)
        self.assertEqual(len(answers), 4)
        self.assertTrue(all(record["tries"] == 1 for record in answers.values()))

    def test_an_account_with_no_credit_stops_the_run_and_leaves_the_keys_to_the_next(self) -> None:
        groups = scan_shelves.groups_of(_catalogue(), LINES)

        def ask_fn(request):
            message = "Error code: 400 - Your credit balance is too low to access the Anthropic API."
            return Asked(None, "", "", 0, 0, 0, 0, 0.0, 0.01, "BadRequestError (HTTP 400)"), message

        answers: dict = {}
        asking = _asking(ask_fn, groups, answers, workers=1)
        keys = scan_shelves.to_ask(groups, answers)
        unasked = scan_shelves.scan(asking, keys, 2)
        self.assertEqual(answers, {})
        self.assertEqual(sorted(unasked), sorted(keys))
        self.assertIn("no credit", asking.totals.stopped)

    def test_the_budget_and_the_time_stop_the_calls(self) -> None:
        groups = scan_shelves.groups_of(_catalogue(), LINES)

        def ask_fn(request):
            asked, _message = _by_title(request)
            return Asked(asked.answer, "end_turn", shelves.MODEL, 1, 1, 0, 0, 0.01, 0.01, ""), ""

        answers: dict = {}
        asking = _asking(ask_fn, groups, answers, workers=1, budget=0.025)
        keys = scan_shelves.to_ask(groups, answers)
        unasked = scan_shelves.scan(asking, keys, 1)
        self.assertEqual(asking.totals.calls, 2)
        self.assertLessEqual(asking.totals.cost, 0.025)
        self.assertIn("budget", asking.totals.stopped)
        self.assertEqual(len(unasked), len(keys) - 2)

        clock = _Clock()
        late: dict = {}
        asking = _asking(ask_fn, groups, late, clock=clock, deadline=clock.now - 1)
        self.assertEqual(sorted(scan_shelves.scan(asking, keys, 1)), sorted(keys))
        self.assertIn("time", asking.totals.stopped)

    def test_the_report_compares_by_products_and_names_where_words_went(self) -> None:
        groups = scan_shelves.groups_of(_catalogue(), LINES)
        answers: dict = {}
        scan_shelves.scan(_asking(_by_title, groups, answers), scan_shelves.to_ask(groups, answers), 50)
        text = "\n".join(scan_shelves.report(groups, answers))
        self.assertIn("another department 1 of 2 (50.0%)", text)
        self.assertIn("IEC Kettle Lead 2m", text)
        words = "\n".join(scan_shelves.report_words(groups, answers, ("kettle", "strap", "watch")))
        self.assertIn("kettle: 2 products", words)
        self.assertIn("strap: 1 products: Apparel & Accessories > Jewelry 1", words)


class WorkflowTests(unittest.TestCase):
    workflow = (ROOT / ".github" / "workflows" / "ai-shelves-scan.yml").read_text(encoding="utf-8")

    def test_it_runs_only_on_a_push_of_its_own_branch(self) -> None:
        self.assertIn("branches: [claude/shelves-scan]", self.workflow)
        self.assertNotIn("workflow_dispatch", self.workflow)
        self.assertNotIn("pull_request", self.workflow)

    def test_the_key_only_where_the_ai_is_asked_the_catalogue_never_uploaded(self) -> None:
        self.assertEqual(self.workflow.count("secrets.ANTHROPIC_API_KEY"), 1)
        # The catalogue holds the shops' links: read on the runner, never uploaded anywhere.
        self.assertNotIn("upload-artifact", self.workflow)
        self.assertIn('rm -f ~/.ssh/deploy_key ~/.ssh/config "$RUNNER_TEMP/catalogue.json.gz"', self.workflow)
        # No lock the deployment waits for, and one scan at a time.
        self.assertNotIn("server-setup", self.workflow)
        self.assertIn("group: shelves-scan", self.workflow)
        self.assertIn('--budget "$BUDGET"', self.workflow)
        self.assertIn("/srv/picwise/assist/shelves", self.workflow)


if __name__ == "__main__":
    unittest.main()
