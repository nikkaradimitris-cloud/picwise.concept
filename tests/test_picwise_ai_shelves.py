"""The AI's shelves: Google's taxonomy as the model reads it, the answers it checks, and the
trial of 1,000 products (`picwise_ai.shelves`, `deployment/server/measure_shelves.py`;
owner, 2026-11-20: «Ναι κάνε καί τά 2», a trial under $1 before the whole catalogue)."""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import measure_shelves  # noqa: E402
from picwise_ai import shelves  # noqa: E402
from picwise_ai.client import Asked  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402

KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Electric Kettles"
CABLES = "Electronics > Electronics Accessories > Cables"
PAINTING = "Hardware > Building Consumables > Painting Consumables"


def _number(line: str) -> int:
    return shelves.taxonomy_lines().index(line) + 1


def _asked(answer, *, cost=0.002, error="") -> Asked:
    return Asked(answer, "end_turn", shelves.MODEL, 1000, 200, 0, 40000, cost, 3.0, error)


def _product(pid: str, title: str, raw: dict, *, category: str = "") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title,
        brand="Acme",
        category_text=category,
        product_url="",
        image_url="",
        price_text="19.99",
        availability_text="in stock",
        currency="GBP",
        raw=raw,
    )


class TaxonomyTests(unittest.TestCase):
    def test_the_lines_are_googles_in_the_files_order(self) -> None:
        lines = shelves.taxonomy_lines()
        self.assertGreater(len(lines), 5000)
        self.assertEqual(lines[0], "Animals & Pet Supplies")
        self.assertIn(KETTLES, lines)
        self.assertTrue(all(" >  " not in line and not line.endswith(">") for line in lines))

    def test_the_tree_numbers_each_line_and_indents_it_by_its_level(self) -> None:
        tree = shelves.taxonomy_tree(shelves.taxonomy_lines()).splitlines()
        self.assertEqual(tree[0], "1 Animals & Pet Supplies")
        self.assertEqual(tree[_number(KETTLES) - 1], f"   {_number(KETTLES)} Electric Kettles")

    def test_the_cached_part_stays_far_under_the_dearer_prompts(self) -> None:
        # Haiku 5.5 costs five times as much past 100,000 tokens: three characters a
        # token, a guess on the low side, keeps the tree and the instructions under it.
        request = shelves.request_kwargs([{"title": "Kettle"}])
        self.assertLess(sum(len(block["text"]) for block in request["system"]), 300_000)


class RequestTests(unittest.TestCase):
    def test_the_instructions_and_the_tree_are_the_same_on_every_call_and_cached(self) -> None:
        one = shelves.request_kwargs([{"title": "Russell Hobbs Electric Kettle"}])
        two = shelves.request_kwargs([{"title": "Paint Kettle 2.5L"}, {"title": "Kettle Lead 2m"}])
        self.assertEqual(one["system"], two["system"])
        self.assertEqual(one["system"][-1]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(one["model"], "claude-haiku-5-5")
        self.assertEqual(one["output_config"]["effort"], "low")
        self.assertEqual(one["output_config"]["format"]["type"], "json_schema")
        self.assertNotEqual(one["messages"], two["messages"])

    def test_each_product_is_numbered_with_what_the_model_reads_of_it(self) -> None:
        message = shelves.user_message(
            [
                {"title": "Paint Kettle 2.5L", "brand": "Harris", "price": "3.49", "category": "DIY / Decorating"},
                {"title": "x" * 400, "about": "  A long\n description  "},
            ]
        )
        lines = message.splitlines()
        self.assertEqual(lines[0], "Products (2):")
        self.assertEqual(lines[1], "1. Paint Kettle 2.5L | brand: Harris | price: 3.49 | shop's category: DIY / Decorating")
        self.assertTrue(lines[2].startswith("2. xxx"))
        self.assertIn("…", lines[2])
        self.assertTrue(lines[2].endswith("about: A long description"))
        self.assertNotIn("None", message)


class CheckedLinesTests(unittest.TestCase):
    lines = shelves.taxonomy_lines()

    def test_a_number_and_its_lines_own_name_are_taken(self) -> None:
        answer = {"products": [{"n": 1, "line": _number(KETTLES), "name": "electric  kettles"}]}
        self.assertEqual(shelves.checked_lines(answer, 1, self.lines), {1: KETTLES})

    def test_a_number_and_another_lines_name_are_refused(self) -> None:
        answer = {"products": [{"n": 1, "line": _number(KETTLES) + 1, "name": "Electric Kettles"}]}
        self.assertEqual(shelves.checked_lines(answer, 1, self.lines), {})

    def test_no_line_fits_is_an_answer_of_its_own(self) -> None:
        answer = {"products": [{"n": 1, "line": 0, "name": "none"}, {"n": 2, "line": 0, "name": "Cables"}]}
        self.assertEqual(shelves.checked_lines(answer, 2, self.lines), {1: ""})

    def test_numbers_out_of_range_twice_answered_or_not_numbers_are_left_out(self) -> None:
        answer = {
            "products": [
                {"n": 1, "line": _number(CABLES), "name": "Cables"},
                {"n": 1, "line": _number(KETTLES), "name": "Electric Kettles"},
                {"n": 3, "line": _number(CABLES), "name": "Cables"},
                {"n": 2, "line": len(self.lines) + 1, "name": "Cables"},
                {"n": True, "line": _number(CABLES), "name": "Cables"},
                "Cables",
            ]
        }
        self.assertEqual(shelves.checked_lines(answer, 2, self.lines), {})
        self.assertEqual(shelves.checked_lines(None, 2, self.lines), {})
        self.assertEqual(shelves.checked_lines({"products": "all"}, 2, self.lines), {})


class TrialTests(unittest.TestCase):
    lines = shelves.taxonomy_lines()

    def _catalogue(self) -> list[ProviderProduct]:
        products = []
        for number in range(30):
            products.append(
                _product(
                    f"a{number}",
                    f"Electric Kettle {number}",
                    {"advertiser_id": "1", "advertiser_name": "Shop One", "google_product_category": KETTLES,
                     "product_type": "Kettles", "description": "A kettle."},
                    category=KETTLES,
                )
            )
        # Read back to the taxonomy's spelling, case and spaces aside.
        products.append(
            _product("a-spelt", "Kettle Lead", {"advertiser_id": "2", "advertiser_name": "Shop Two",
                                                "google_product_category": " electronics >electronics accessories> cables "})
        )
        # Too broad, not Google's, or a number: never in A.
        products.append(_product("a-broad", "Toaster", {"advertiser_id": "2", "advertiser_name": "Shop Two",
                                                        "google_product_category": "Home & Garden > Kitchen & Dining"}))
        products.append(_product("a-not", "Toaster", {"advertiser_id": "2", "advertiser_name": "Shop Two",
                                                      "google_product_category": "Kitchen > Toasters > Fancy"}))
        products.append(_product("a-id", "Toaster", {"advertiser_id": "2", "advertiser_name": "Shop Two",
                                                     "google_product_category": "505771"}))
        for number in range(5):
            products.append(
                _product(
                    f"b{number}",
                    f"Paint Kettle {number}",
                    {"merchant_id": "9", "merchant_name": "Tooled Up", "merchant_category": "DIY",
                     "category_name": "diy", "google_product_category": "Hardware"},
                    category="Hardware",
                )
            )
        # A second-link product whose shelf was read precisely keeps no category words.
        products.append(_product("b-precise", "Drill Bit", {"merchant_id": "9", "merchant_name": "Tooled Up",
                                                            "google_product_category": "Hardware > Tool Accessories"}))
        return products

    def test_the_halves_are_picked_as_said_at_most_so_many_of_a_shop(self) -> None:
        chosen = measure_shelves.pick(self._catalogue(), self.lines, total=40, seed=1)
        a = [found for found in chosen if found.half == "A"]
        b = [found for found in chosen if found.half == "B"]
        # B has 5: A takes the rest, at most 15 of a shop.
        self.assertEqual(len(b), 5)
        self.assertEqual(len(a), 16)
        self.assertEqual(sum(1 for found in a if found.shop == "Shop One"), 15)
        spelt = next(found for found in a if found.shop == "Shop Two")
        self.assertEqual(spelt.shelf_now, CABLES)
        for found in a:
            self.assertNotIn("category", found.item)
            self.assertNotEqual(found.item.get("about"), "Kettles")
        self.assertEqual(b[0].item["category"], "DIY")
        self.assertEqual(b[0].shelf_now, "Hardware")
        self.assertEqual(measure_shelves.pick(self._catalogue(), self.lines, total=40, seed=1)[0].title,
                         chosen[0].title)

    def test_the_calls_take_a_and_b_in_turn(self) -> None:
        chosen = measure_shelves.pick(self._catalogue(), self.lines, total=40, seed=1)
        calls = measure_shelves.batches(chosen, 4)
        self.assertEqual([call[0].half for call in calls[:4]], ["A", "B", "A", "B"])
        self.assertEqual(sum(len(call) for call in calls), len(chosen))

    def test_the_answers_are_checked_and_the_budget_stops_the_calls(self) -> None:
        chosen = measure_shelves.pick(self._catalogue(), self.lines, total=40, seed=1)
        calls = measure_shelves.batches(chosen, 4)

        def ask(request):
            count = len(request["messages"][0]["content"].splitlines()) - 1
            return _asked({"products": [
                {"n": n, "line": _number(PAINTING) if "Paint" in request["messages"][0]["content"] else _number(KETTLES),
                 "name": "Painting Consumables" if "Paint" in request["messages"][0]["content"] else "Electric Kettles"}
                for n in range(1, count + 1)
            ]}, cost=0.01)

        with redirect_stdout(io.StringIO()):
            answered, totals, unasked = measure_shelves.run(calls, self.lines, ask_fn=ask, budget=0.024)
        # Two cents guessed before the first; then half again the dearest call.
        self.assertEqual(totals.calls, 1)
        self.assertEqual(unasked, len(calls) - 1)
        with redirect_stdout(io.StringIO()):
            answered, totals, unasked = measure_shelves.run(calls, self.lines, ask_fn=ask, budget=1.0)
        self.assertEqual(unasked, 0)
        self.assertEqual(len(answered), len(chosen))
        report = "\n".join(measure_shelves.report_a(answered) + measure_shelves.report_b(answered))
        # Of A, 15 kettles agree with their shop; the lead does not.
        self.assertIn("the same category (first two levels, the cap's): 15 of 16 (93.8%)", report)
        self.assertIn("the shop: " + CABLES, report)
        self.assertIn("deeper on the same path: 5 of 5 (100.0%)", report)
        totals_report = "\n".join(measure_shelves.report_totals(totals, answered, unasked, 400_000))
        self.assertIn("for 1,000", totals_report)
        self.assertIn("through the Batch API", totals_report)

    def test_a_call_with_no_answer_leaves_its_products_on_their_shelves(self) -> None:
        chosen = measure_shelves.pick(self._catalogue(), self.lines, total=40, seed=1)
        calls = measure_shelves.batches(chosen, 50)
        with redirect_stdout(io.StringIO()):
            answered, totals, _unasked = measure_shelves.run(
                calls, self.lines, ask_fn=lambda request: _asked(None, error="APITimeoutError"), budget=1.0
            )
        self.assertEqual(totals.failed, len(calls))
        self.assertTrue(all(found.line is None for found in answered))
        self.assertEqual(totals.errors["APITimeoutError"], len(calls))

    def test_without_the_key_nothing_is_asked(self) -> None:
        with redirect_stdout(io.StringIO()) as printed:
            code = measure_shelves.main(["/nonexistent/catalogue.json.gz", "--dry-run"])
        self.assertEqual(code, 1)
        self.assertIn("not a prepared catalogue", printed.getvalue())


class WorkflowTests(unittest.TestCase):
    text = (ROOT / ".github" / "workflows" / "ai-shelves-trial.yml").read_text(encoding="utf-8")

    def test_it_runs_only_when_its_own_file_is_pushed_to_the_working_branch(self) -> None:
        self.assertIn("    branches: [ccr-4f47068a-99ikwe]\n    paths:\n      - '.github/workflows/ai-shelves-trial.yml'\n",
                      self.text)
        self.assertNotIn("workflow_dispatch", self.text)
        self.assertIn("permissions:\n  contents: read\n", self.text)
        # Never while the deployment or the setup writes the catalogue.
        self.assertIn("concurrency:\n  group: server-setup\n  cancel-in-progress: false\n", self.text)

    def test_the_owners_budget_and_the_key_only_where_the_ai_is_asked(self) -> None:
        budget = float(self.text.split("BUDGET: '", 1)[1].split("'", 1)[0])
        self.assertLessEqual(budget, 1.00)
        self.assertEqual(self.text.count("secrets.ANTHROPIC_API_KEY"), 1)
        asking = self.text.split("- name: 1,000 products", 1)[1].split("- name:", 1)[0]
        self.assertIn("ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}", asking)
        self.assertIn("--require-hashes", self.text)
        cleanup = self.text.split("- name: Remove the key and the copies from the runner", 1)[1]
        self.assertIn("rm -f ~/.ssh/deploy_key ~/.ssh/config \"$RUNNER_TEMP/catalogue.json.gz\"", cleanup)
        self.assertIn("if: always()", cleanup)


if __name__ == "__main__":
    unittest.main()
